# Phase 3 static and synthetic verification record

**Observed on 2026-11-19 on MacBook Air macOS 27.2, Apple Silicon.** This is host-only validation; **none of these tests ran on the Y9000P**.

## Test procedure

```bash
/bin/bash -n TAHOE-BASELINE-COLLECTOR.sh
/bin/bash -n tools/disk_evidence.sh
/usr/bin/perl -c tools/redact.pl
/usr/bin/perl -c tools/oc_snapshot.pl
/usr/bin/perl -c tools/gpu_ioreg.pl
python3 -m py_compile tools/efi_auditor.py tools/import_results.py
python3 tests/test_phase3.py
```

On the independently cloned public repository, all eight synthetic Python tests **PASSED**:
1. collector Bash parse
2. reject unsupported / install-like flag
3. collector self-test without system data access
4. text private identifier redaction
5. EFI config allowlist and non-bootable output, with synthetic serial excluded
6. Intel 8086 and RTX 10DE:2D59 IOPCIDevice parsing
7. EFI auditor NO-GO on simulated WhateverXe conflict/unknown startup source
8. import script NO-GO when EFI/recovery evidence is missing

The collector has **not** been used for live Y9000P baseline capture. GPU BAR decoding remains indicative only; real target display, ABI, booted EFI and Auxiliary KC compatibility are **unverified**. No physical recovery method A–E has been rehearsed. Manual per-target acceptance is mandatory.

## Safety boundaries checked

No installer, Kext loader, `kmutil create`, `nvram` writer, `csrutil` changer, EFI disk mount, disk formatter, Windows Boot Manager modifier, firmware writer or reboot is called by the read-only collector. The only intended writes are freshly created reports under the current user's HOME. The optional EFI input is read from an *already mounted* operator-selected candidate, and output is non-bootable allowlisted JSON. Public repository contains no real target diagnostics or private EFI copies.

**Decision:** read-only offline diagnostic preparation GO; installation NO-GO.
