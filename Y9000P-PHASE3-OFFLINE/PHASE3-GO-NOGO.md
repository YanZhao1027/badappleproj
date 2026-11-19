# Phase 3 GO / NO-GO

**Current: READ-ONLY INVESTIGATION GO; ANY DRIVER INSTALLATION NO-GO.**

## Baseline
- [ ] Y9000P exact Tahoe ProductVersion, BuildVersion and Darwin recorded
- [ ] NVIDIA 10DE:2D59 and subsystem found in IORegistry
- [ ] Intel GPU, NVIDIA routing and BAR mappings independently verified
- [ ] SPDisplays/Metal and loaded Kexts recorded
- [ ] Auxiliary KC and target third-party Kext inventory verified
- [ ] SIP, AMFI, boot-args, SecureBootModel and SMBIOS reviewed
- [ ] No enabled Intel WhateverXe with experimental NVIDIA

## Actual startup EFI
- [ ] Physical internal disk and GPT EFI partition independently identified
- [ ] Boot-path GPT UUID matches this partition; identifiers remain private
- [ ] Tahoe boots without installation USB
- [ ] Internal EFI backed up byte-for-byte and full config diff reviewed
- [ ] No automatic SMBIOS/BoardProduct conversion; no Windows Boot Manager or Windows partition changes

## Actual recovery (all UNREHEARSED now)
- [ ] Separate rescue USB actually boots this laptop
- [ ] Tahoe Recovery loads, Data volume can be unlocked
- [ ] Backup of /Library/Extensions, /Library/GPUBundles, relevant LaunchDaemons and Auxiliary KC verified
- [ ] Offline Kext/graphic plugin removal path is rehearsed
- [ ] Matching Tahoe build auxiliary kernel collection restore/rebuild demonstrated
- [ ] Windows EFI recovery is limited to OpenCore-owned files; Windows Boot Manager stays unchanged
- [ ] An actual black-screen/login-loop recovery can restore the **system**, not merely EFI

## ABI/security approval
- [ ] Tahoe 26.7.3 private ABI compatibility evidence sufficient
- [ ] Only official NullMoth v2.9 and OGKM 620.70.06 used
- [ ] Exact owner-reviewed per-key diff and complete rollback gate signed off

**STOP** on ambiguous EFI, copied installer USB inferred as startup EFI, SMBIOS auto-conversion, loss of Windows boot capability, missing recovery media, or absence of system-level AuxKC restoration. The toolkit never authorizes on-target deployment.