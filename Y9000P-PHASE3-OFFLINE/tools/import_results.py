#!/usr/bin/env python3
"""Import PRIVATE Phase 3 collector data into a machine-minimal local readiness report."""
import argparse
import datetime as dt
import json
import re
from pathlib import Path

HERE=Path(__file__).resolve().parent.parent

def read_text(folder,name):
    path=folder/name
    if not path.is_file() or path.is_symlink():
        return None
    if path.stat().st_size>10_000_000:
        raise ValueError("Unexpected oversized diagnostic input")
    return path.read_text(encoding="utf-8",errors="replace")

def read_json(folder,name):
    text=read_text(folder,name)
    return json.loads(text) if text is not None else None

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--input",required=True,help="PRIVATE collector run directory")
    a.add_argument("--out",help="New local output directory")
    args=a.parse_args()
    src=Path(args.input).expanduser().resolve(strict=True)
    if not src.is_dir():
        raise ValueError("Input must be a directory")
    meta=read_json(src,"summary.json")
    if not isinstance(meta,dict) or meta.get("schema")!="phase3-summary-v1":
        raise ValueError("Not a Phase 3 collector manifest")
    gpu=read_json(src,"gpu-pci.json") or {}
    devices=gpu.get("gpu_devices",[])
    nvidia=any(d.get("vendor_id")=="10DE" and d.get("device_id")=="2D59" for d in devices)
    intel=any(d.get("vendor_id")=="8086" for d in devices)
    bar_clue=any(d.get("vendor_id")=="10DE" and
                 (d.get("location_and_resource_clues",{}).get("IODeviceMemory") or
                  d.get("location_and_resource_clues",{}).get("assigned-addresses"))
                 for d in devices)
    displays=read_json(src,"displays.json")
    metal=[]
    def scan(x):
        if isinstance(x,dict):
            for k,v in x.items():
                if "metal" in str(k).lower() and not isinstance(v,(dict,list)):
                    metal.append(str(v)[:75])
                else: scan(v)
        elif isinstance(x,list):
            for v in x: scan(v)
    scan(displays)
    inventory=(read_text(src,"kext-loaded.txt") or "")+"\n"+(read_text(src,"kext-inventory.txt") or "")
    observed={name:bool(re.search(re.escape(name),inventory,re.I)) for name in
              ("NVRM","NVAccel","NVRMFB","WhateverGreen","WhateverXe","Lilu","AMFIPass")}
    statuses=read_text(src,"collection-status.tsv") or ""
    failures=[line.split("\t")[0] for line in statuses.splitlines()[1:]
              if any(t in line for t in ("FAILED","INACCESSIBLE","ABSENT"))]
    checks={
        "exact_Tahoe_26_7_3":meta.get("macos")=="26.7.3",
        "Intel_x86_64":meta.get("arch")=="x86_64",
        "full_build_captured":bool(meta.get("build")),
        "NVIDIA_10DE_2D59_observed":nvidia,
        "Intel_GPU_candidate_observed":intel,
        "PCI_resources_clues_observed_NOT_validated_BARs":bool(bar_clue),
        "display_report_collected":displays is not None,
        "metal_fields_collected":bool(metal),
        "AuxKC_inspection_collected":read_text(src,"auxkc-inspect.txt") is not None,
        "EFI_snapshot_allowlisted":read_json(src,"efi-config-sanitized.json") is not None,
        "actual_booted_EFI_proven":False,
        "independent_rescue_USB_booted":False,
        "system_level_rollback_rehearsed":False,
        "private_Tahoe_ABI_verified":False
    }
    result={
        "schema":"phase3-import-review-v1",
        "decision":"NO-GO",
        "macos":meta.get("macos"),"build":meta.get("build"),"darwin":meta.get("darwin"),
        "architecture":meta.get("arch"),
        "observed_metal_fields":metal[:6],
        "kext_names_present":observed,
        "failed_closed_sections":failures,
        "gates":checks,
        "warning":"Resource clues do not prove PCI BAR mapping. No startup-EFI/recovery/ABI certification is inferred."
    }
    out=Path(args.out).expanduser() if args.out else HERE/"analysis-output"/("import-"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S-%f"))
    dst=out.resolve()
    if dst==src or src in dst.parents:
        raise ValueError("Refusing to overwrite the private input")
    out.mkdir(parents=True,exist_ok=False,mode=0o700)
    (out/"import-review.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    lines=["# Phase 3 import readiness","","**NO-GO: experimental driver installation not authorized.**",
           "Exact build: "+str(result["build"]),"", "| Gate | Result |","|---|---|"]
    for name,value in checks.items():
        lines.append("| "+name+" | "+("PRESENT" if value else "MISSING / NOT VERIFIED")+" |")
    lines.extend(["","Kext name presence: "+json.dumps(observed,sort_keys=True),
                  "Metal evidence fields: "+("; ".join(metal[:6]) if metal else "not available"),
                  "Failed data sections: "+(", ".join(failures) if failures else "none reported"),
                  "EFI startup identity remains unverified; compare boot-path and GPT UUID locally on Y9000P.",
                  "No full diagnostics, EFI or private hardware identifiers are copied into this derived report."])
    (out/"IMPORT-REVIEW.md").write_text("\n".join(lines)+"\n")
    print("NO-GO: derived private review written to "+str(out))
if __name__=="__main__":
    main()
