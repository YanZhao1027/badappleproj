#!/usr/bin/env python3
"""Run synthetic-only tests. No real EFI, Kext, NVRAM or user system changes."""
import json
import plistlib
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APPLE="7C436110-AB2A-4BBB-A880-FE41995C9F82"

def run(*cmd,input=None):
    return subprocess.run(cmd,input=input,capture_output=True,text=True,timeout=20)

def synthetic_config():
    return {
      "NVRAM":{
        "Add":{APPLE:{"boot-args":"-v nv_disable=1","csr-active-config":bytes.fromhex("00000000")}},
        "Delete":{APPLE:[]}},
      "Kernel":{"Add":[
        {"BundlePath":"WhateverXe.kext","Enabled":True},
        {"BundlePath":"AMFIPass.kext","Enabled":True},
        {"BundlePath":"Lilu.kext","Enabled":True},
        {"BundlePath":"WhateverGreen.kext","Enabled":True}],"Block":[]},
      "Misc":{"Security":{"SecureBootModel":"Default"}},
      "PlatformInfo":{"Generic":{"SystemProductName":"MacBookPro16,1","SystemSerialNumber":"SYNTHETICPRIVATE"},
                      "SMBIOS":{"SystemProductName":"MacBookPro16,1"}},
      "UEFI":{"Quirks":{"ResizeGpuBars":14}},
      "Booter":{"Quirks":{"ResizeAppleGpuBars":0}}
    }

class TestPhase3(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.temp=Path(tmp.name)
        (self.temp/"efi").mkdir()
        self.conf=self.temp/"efi"/"config.plist"
        self.conf.write_bytes(plistlib.dumps(synthetic_config()))
    def test_collector_syntax(self):
        r=run("/bin/bash","-n",str(ROOT/"TAHOE-BASELINE-COLLECTOR.sh"))
        self.assertEqual(r.returncode,0,r.stderr)
    def test_reject_install_argument(self):
        r=run("/bin/bash",str(ROOT/"TAHOE-BASELINE-COLLECTOR.sh"),"--install")
        self.assertNotEqual(r.returncode,0)
    def test_collector_selftest_no_read(self):
        r=run("/bin/bash",str(ROOT/"TAHOE-BASELINE-COLLECTOR.sh"),"--self-test")
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn("PASS",r.stdout)
    def test_text_redaction(self):
        data="Serial Number: SECRET123\nMAC: aa:bb:cc:dd:ee:ff\nUUID: 123e4567-e89b-12d3-a456-426614174000\nGPU: 10DE:2D59\n"
        r=run("/usr/bin/perl",str(ROOT/"tools/redact.pl"),"text",input=data)
        self.assertEqual(r.returncode,0,r.stderr)
        for value in ("SECRET123","aa:bb:cc:dd:ee:ff","123e4567-e89b-12d3-a456-426614174000"):
            self.assertNotIn(value,r.stdout)
        self.assertIn("10DE:2D59",r.stdout)
    def test_efi_snapshot_is_nonbootable_and_private(self):
        xml=subprocess.check_output(["/usr/bin/plutil","-convert","xml1","-o","-",str(self.conf)])
        r=subprocess.run(["/usr/bin/perl",str(ROOT/"tools/oc_snapshot.pl")],input=xml,capture_output=True,timeout=20)
        self.assertEqual(r.returncode,0,r.stderr)
        data=json.loads(r.stdout)
        self.assertFalse(data["bootable"])
        self.assertEqual(data["schema"],"phase3-efi-snapshot-v1")
        self.assertNotIn("SystemSerialNumber",data["config"]["PlatformInfo"]["Generic"])
        self.assertNotIn("SYNTHETICPRIVATE",r.stdout.decode())
    def test_gpu_parser(self):
        src='''+-o IGPU@2 <class IOPCIDevice>
 | "vendor-id" = <86800000>
 | "device-id" = <a7800000>
 | "class-code" = <00000300>
+-o PEGP@0 <class IOPCIDevice>
 | "vendor-id" = <de100000>
 | "device-id" = <592d0000>
 | "subsystem-id" = <20170000>
 | "IODeviceMemory" = ({"address"=0x80000000})
'''
        r=run("/usr/bin/perl",str(ROOT/"tools/gpu_ioreg.pl"),input=src)
        self.assertEqual(r.returncode,0,r.stderr)
        obj=json.loads(r.stdout)
        ids={(d["vendor_id"],d["device_id"]) for d in obj["gpu_devices"]}
        self.assertIn(("8086","80A7"),ids)
        self.assertIn(("10DE","2D59"),ids)
    def test_efi_audit_blocks_conflicts(self):
        dest=self.temp/"review"
        r=run("python3",str(ROOT/"tools/efi_auditor.py"),"--current",str(self.conf),"--out",str(dest))
        self.assertEqual(r.returncode,0,r.stderr)
        review=json.loads((dest/"efi-review.json").read_text())
        self.assertEqual(review["decision"],"NO-GO")
        self.assertFalse(review["applied"])
        codes={f["code"] for f in review["findings"]}
        self.assertIn("XE_CONFLICT",codes)
        self.assertIn("EFI_STARTUP_UNPROVEN",codes)
    def test_import_no_go(self):
        private=self.temp/"private"/"run-ABCDEFGH"
        private.mkdir(parents=True)
        (private/"summary.json").write_text(json.dumps({
            "schema":"phase3-summary-v1","macos":"26.7.3",
            "build":"25G100","darwin":"25.6.0","arch":"x86_64","writes_system":False
        }))
        (private/"gpu-pci.json").write_text(json.dumps({"gpu_devices":[
            {"vendor_id":"10DE","device_id":"2D59",
             "location_and_resource_clues":{"IODeviceMemory":"synthetic memory resource"}}
        ]}))
        dest=self.temp/"import"
        r=run("python3",str(ROOT/"tools/import_results.py"),"--input",str(private),"--out",str(dest))
        self.assertEqual(r.returncode,0,r.stderr)
        report=json.loads((dest/"import-review.json").read_text())
        self.assertEqual(report["decision"],"NO-GO")
        self.assertFalse(report["gates"]["actual_booted_EFI_proven"])

if __name__=="__main__":
    unittest.main(verbosity=2)
