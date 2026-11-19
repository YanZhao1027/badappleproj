# Offline EFI configuration reviewer

Use `python3 tools/efi_auditor.py` on the MacBook Air with a **COPY** of the working EFI `config.plist` or sanitized `efi-config-sanitized.json`; optional independent proposed config and target diagnostics. It produces `EFI-REVIEW.md` and `efi-review.json` in a new output directory; **does not modify any input** or produce a bootable patch.

Checks include:
- Boot-args required/missing/conflicting, AMFI flags, SIP mask 0x0A43 and NVRAM Delete entries
- SecureBootModel, IONDRVSupport Block, Lilu/AMFIPass and WhateverGreen order, gfxrst=4
- Enabled WhateverXe conflicts and duplicate NVIDIA Kext EFI injection
- SMBIOS model/BoardProduct changes (always BLOCK automatic conversion)
- Proposed ResizeGpuBars/ResizeAppleGpuBars alterations
- Target exact Tahoe build/architecture, GPU PCI ID, AuxKC and EFI provenance gaps

**EFI boot source is never inferred from a copied config or matching SMBIOS.** A boot-path plus GPT partition UUID must be independently checked on the target; with ambiguity the result is NO-GO.

The expected-state JSON expresses research assumptions from v2.9, not a guaranteed install-safe config. A real 1401 action can make conditional changes; the user must review every actual delta. Neither parsing success nor compilation success proves Tahoe ABI loadability.