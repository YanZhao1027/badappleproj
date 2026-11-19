#!/usr/bin/env python3
"""Static read-only OpenCore configuration auditor. No EFI writes, no patch generation."""
import argparse
import datetime as dt
import json
import plistlib
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
APPLE = "7C436110-AB2A-4BBB-A880-FE41995C9F82"
HIDDEN = re.compile(r"serial|mlb|uuid|rom|mac.?address|password|secret|token", re.I)

def load_config(path):
    path = Path(path).expanduser()
    if path.is_dir():
        options = [path/"EFI/OC/config.plist", path/"OC/config.plist", path/"config.plist"]
        path = next((q for q in options if q.is_file()), None)
        if not path:
            raise ValueError("No offline EFI copy config.plist found")
    if path.is_symlink() or not path.is_file():
        raise ValueError("A regular local EFI COPY or sanitized snapshot is required")
    if path.suffix == ".json":
        doc = json.loads(path.read_text())
        if doc.get("schema") != "phase3-efi-snapshot-v1" or doc.get("redacted") is not True:
            raise ValueError("Unknown sanitized snapshot schema")
        return doc["config"], "SANITIZED_NON_BOOTABLE", path
    with path.open("rb") as f:
        return plistlib.load(f), "OFFLINE_PLIST_COPY", path

def get(node, *keys, default=None):
    for key in keys:
        if not isinstance(node, dict):
            return default
        node = node.get(key)
    return default if node is None else node

def nvram_group(cfg, sub):
    groups = get(cfg, "NVRAM", sub, default={})
    return next((v for k, v in groups.items() if str(k).upper() == APPLE), {})

def shown(v, secret=False):
    if secret:
        return "[IDENTITY-OMITTED]"
    if v is None:
        return "(unset)"
    if isinstance(v, bytes):
        return "DATA(hex:" + v.hex() + ")"
    if isinstance(v, dict) and "__data_hex" in v:
        return "DATA(hex:" + str(v["__data_hex"]) + ")"
    if isinstance(v, (list,dict)):
        return "[STRUCTURED-VALUE]"
    s = str(v)[:320]
    s = re.sub(r"\b[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\b","[UUID]",s,flags=re.I)
    s = re.sub(r"\b(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}\b","[MAC]",s,flags=re.I)
    return s

def csr_bits(value):
    if isinstance(value,bytes):
        return int.from_bytes(value,"little")
    if isinstance(value,dict) and "__data_hex" in value:
        try: return int.from_bytes(bytes.fromhex(value["__data_hex"]),"little")
        except (ValueError,TypeError): return None
    return None

def enabled_kexts(cfg):
    result=[]
    for i,row in enumerate(get(cfg,"Kernel","Add",default=[]) or []):
        if isinstance(row,dict):
            result.append((i, str(row.get("BundlePath","")).split("/")[-1], row.get("Enabled") is True))
    return result

def assess(current, proposed, diagnostics):
    requirements=json.loads((HERE/"NULLMOTH-V29-CONFIG-REQUIREMENTS.json").read_text())
    findings=[]; diffs=[]
    def add(level,code,text):
        findings.append(dict(level=level,code=code,detail=text))
    def diff(path,old,new,why,level="REVIEW"):
        diffs.append(dict(path=path,before=shown(old,HIDDEN.search(path) is not None),
                          after=shown(new,HIDDEN.search(path) is not None),risk=level,reason=why))
    oldargs=get(nvram_group(current,"Add"),"boot-args",default="")
    oldtokens=oldargs.split() if isinstance(oldargs,str) else []
    missing=[x for x in requirements["required_boot_args"] if x not in oldtokens]
    conflicts=[x for x in requirements["incompatible_boot_args"] if x in oldtokens]
    if missing:
        add("BLOCK","BOOT_ARGS_MISSING","Missing: "+", ".join(missing))
        diff("NVRAM.Add.<AppleGUID>.boot-args",oldargs,
             "add tokens: "+" ".join(missing),"Security/Metal changes require approval","HIGH")
    if conflicts:
        add("BLOCK","BOOT_ARGS_CONFLICT","Conflicting NVIDIA suppression args: "+", ".join(conflicts))
        diff("NVRAM.Add.<AppleGUID>.boot-args remove",oldargs,"remove: "+" ".join(conflicts),
             "May affect existing hybrid graphics","HIGH")
    csr=csr_bits(get(nvram_group(current,"Add"),"csr-active-config"))
    needed=0x0A43
    if csr is None:
        add("BLOCK","CSR_UNKNOWN","csr-active-config is absent/unparseable")
    elif (csr & needed)!=needed:
        add("BLOCK","CSR_INSUFFICIENT","Needed SIP mask bits 0x0A43 not present")
        diff("NVRAM.Add.<AppleGUID>.csr-active-config",f"0x{csr:X}","required bits 0x0A43",
             "Security downgrade; preserve unrelated bits and require consent","HIGH")
    elif csr != needed:
        add("REVIEW","CSR_ADDITIONAL","Additional SIP mask bits exist; verify existing protection state")
    deletion=nvram_group(current,"Delete")
    for key in ("boot-args","csr-active-config"):
        if key not in deletion:
            add("REVIEW","NVRAM_DELETE_MISSING","NVRAM.Delete missing "+key)
    sec=get(current,"Misc","Security","SecureBootModel")
    if sec!="Disabled":
        add("BLOCK","SECUREBOOT_CHANGE","SecureBootModel is not Disabled; change is security-sensitive")
        diff("Misc.Security.SecureBootModel",sec,"Disabled","Unsigned experimental Kext risk","HIGH")
    records=enabled_kexts(current)
    enabled=[x for _,x,on in records if on]
    def position(name):
        return next((i for i,x,on in records if x==name and on),None)
    for name in ("Lilu.kext","AMFIPass.kext"):
        if name not in enabled:
            add("BLOCK","REQUIRED_KEXT_MISSING",name+" not enabled in OpenCore")
            diff("Kernel.Add",enabled,"enable "+name,"Kext dependencies/version/signature must be checked","HIGH")
    lilu=position("Lilu.kext"); amfi=position("AMFIPass.kext"); weg=position("WhateverGreen.kext")
    if lilu is not None and amfi is not None and lilu>amfi:
        add("BLOCK","LOAD_ORDER","Lilu must precede AMFIPass")
    if weg is not None:
        if lilu is None or lilu>weg:
            add("BLOCK","LOAD_ORDER","WhateverGreen must follow Lilu")
        if "gfxrst=4" not in oldtokens:
            add("BLOCK","WEG_PANIC_RISK","WhateverGreen present without gfxrst=4")
            diff("boot-args",oldargs,"add gfxrst=4","Upstream panic mitigation","HIGH")
    for name in ("WhateverXe.kext","IntelWhateverXe.kext"):
        if name in enabled: add("BLOCK","XE_CONFLICT",name+" enabled alongside proposed NVIDIA")
    for name in ("NVRM.kext","NVAccel.kext","NVRMFB.kext","NVRMAGDC.kext"):
        if name in enabled:
            add("BLOCK","DUPLICATE_KEXT_SOURCE",name+" must not be injected from EFI")
    if len(enabled)!=len(set(enabled)):
        add("BLOCK","DUPLICATE_KEXT","Duplicate enabled bundle path")
    blocks=get(current,"Kernel","Block",default=[]) or []
    if not any(isinstance(row,dict) and row.get("Identifier")=="com.apple.iokit.IONDRVSupport"
               and row.get("Enabled") is True and row.get("Strategy")=="Exclude" for row in blocks):
        add("BLOCK","IONDRV_CHANGE","Required IONDRVSupport Strategy Exclude not enabled")
        diff("Kernel.Block","unknown","IONDRVSupport Exclude","May affect firmware framebuffer/black-screen recovery","HIGH")
    models=[get(current,"PlatformInfo",s,"SystemProductName") for s in ("Generic","SMBIOS","DataHub")]
    values={v for v in models if isinstance(v,str) and v}
    if len(values)>1:
        add("BLOCK","SMBIOS_INCONSISTENT","Generic/SMBIOS/DataHub models disagree")
    if not values:
        add("BLOCK","SMBIOS_UNKNOWN","SMBIOS model missing from inputs")
    add("BLOCK","SMBIOS_AUTO_MIGRATION","Any *automatic* SMBIOS/BoardProduct/serial/MLB/ROM conversion is strictly forbidden")
    if proposed is not None:
        for group in ("Generic","SMBIOS","DataHub"):
            for key in ("SystemProductName","BoardProduct","SystemSerialNumber","MLB","ROM","SystemUUID"):
                old=get(current,"PlatformInfo",group,key)
                new=get(proposed,"PlatformInfo",group,key)
                if old!=new:
                    add("BLOCK","PROPOSED_SMBIOS_MUTATION",f"{group}.{key} changed")
                    diff(f"PlatformInfo.{group}.{key}",old,new,"Never auto-apply identity/model change","BLOCK")
        watch=[("Misc","Security","SecureBootModel"),
               ("Kernel","Add"),("Kernel","Block"),
               ("UEFI","Quirks","ResizeGpuBars"),
               ("Booter","Quirks","ResizeAppleGpuBars")]
        for route in watch:
            a=get(current,*route); b=get(proposed,*route)
            if a!=b:
                diff(".".join(route),a,b,"Actual proposed change; manual inspection required","HIGH")
    if diagnostics:
        summ=json.loads((diagnostics/"summary.json").read_text())
        if summ.get("macos")!="26.7.3" or summ.get("arch")!="x86_64":
            add("BLOCK","TARGET_OS_MISMATCH","Not confirmed exact Intel Tahoe 26.7.3")
        if not summ.get("build"):
            add("BLOCK","BUILD_UNKNOWN","Full macOS build is absent")
        gpufile=diagnostics/"gpu-pci.json"
        gpu=json.loads(gpufile.read_text()) if gpufile.is_file() else {}
        if not any(d.get("vendor_id")=="10DE" and d.get("device_id")=="2D59"
                   for d in gpu.get("gpu_devices",[])):
            add("BLOCK","GPU_ID_UNCONFIRMED","NVIDIA 10DE:2D59 not captured")
        if not (diagnostics/"auxkc-inspect.txt").is_file():
            add("BLOCK","AUXKC_UNCONFIRMED","No successful Auxiliary KC inspect")
    else:
        add("BLOCK","TARGET_DIAGNOSTICS_MISSING","No private target baseline provided")
    add("BLOCK","EFI_STARTUP_UNPROVEN","Copy/serial/boot-args cannot uniquely identify actual booted EFI. Independently verify GPT UUID on target")
    add("BLOCK","RESCUE_UNREHEARSED","No boot-tested rescue USB, Data volume access or Auxiliary KC rollback rehearsal evidenced")
    return dict(schema="phase3-efi-review-v1",decision="NO-GO",applied=False,
                findings=findings,differences=diffs)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current",required=True)
    parser.add_argument("--proposed")
    parser.add_argument("--diagnostics")
    parser.add_argument("--out")
    args=parser.parse_args()
    cfg,kind,src=load_config(args.current)
    prop=load_config(args.proposed)[0] if args.proposed else None
    diag=Path(args.diagnostics).expanduser() if args.diagnostics else None
    report=assess(cfg,prop,diag)
    out=Path(args.out).expanduser() if args.out else HERE/"analysis-output"/("audit-"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S-%f"))
    resolved=out.resolve()
    if resolved==src.parent.resolve() or src.parent.resolve() in resolved.parents:
        raise ValueError("Output must not be inside EFI input directory")
    out.mkdir(parents=True,exist_ok=False,mode=0o700)
    (out/"efi-review.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    lines=["# Offline OpenCore audit","","**NO-GO. Nothing applied.**",f"Input: {kind}","",
           "## Per-key changes (NOT executable)","",
           "| Key | Current | Proposal | Risk |","|---|---|---|---|"]
    esc=lambda v:str(v).replace("|",r"\|").replace("\n"," ")
    for d in report["differences"]:
        lines.append("| "+esc(d["path"])+" | "+esc(d["before"])+" | "+esc(d["after"])+" | "+d["risk"]+" |")
    lines.extend(["","## Findings",""])
    for f in report["findings"]:
        lines.append(f"- **{f['level']} — {f['code']}**: {f['detail']}")
    lines.extend(["","EFI startup identity and rescue capability require independent proof before any driver test."])
    (out/"EFI-REVIEW.md").write_text("\n".join(lines)+"\n")
    print(f"NO-GO (read-only); {len(report['findings'])} findings; output: {out}")

if __name__=="__main__":
    main()
