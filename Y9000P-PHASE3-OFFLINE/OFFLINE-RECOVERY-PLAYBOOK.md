# Offline recovery playbook — Y9000P Tahoe 26.7.3

**Evidence status for each A–E: SOURCE-DERIVED, NOT REHEARSED ON THE Y9000P.** Phase 2 verified official release bytes and inspected installation source on a separate Mac; it did not boot-test recovery. **EFI restoration alone is never a complete system-level rollback.**

## Pre-install prerequisites
Before authorizing any NVIDIA experiment, privately preserve the exact *actually booted* internal EFI with GPT partition identity, a **separate rescue EFI actually boot-tested on this laptop**, the existing macOS Data volume and FileVault unlock method, target build, /Library/Extensions, /Library/GPUBundles, /Library/NullMoth, relevant /Library/LaunchDaemons, pre-test AuxiliaryKernelExtensions.kc and system Kext policy state. Do not alter Windows Boot Manager, Microsoft/Boot, Windows partitions or the rescue EFI. Keep failed-state backups and originals distinct.

## A. Rescue USB from black screen or panic
**Not rehearsed.** Select the already boot-tested USB explicitly in firmware boot selector without changing Windows boot entries. Confirm its picker actually appears. Use the previous non-NVIDIA boot configuration. If macOS still panics, assume an installed system Kext or AuxKC might remain active; proceed to B/D. Do not treat rescue EFI boot as complete rollback.

## B. Tahoe Recovery: remove experimental components
**Not rehearsed.** Enter the target's verified Recovery path. Identify exact APFS System/Data volume group, unlock FileVault through authorized credentials, inspect mounts and make backups before edits. Restore original third-party Kext set instead of blindly deleting every item. NullMoth candidates: NVRM, NVAccel, NVRMFB, NVRMAGDC, optional NVPrimarySelector/NMXAudio. Do not remove unrelated Intel or AMD GPU drivers, USB, Wi-Fi or storage Kexts. Continue to D; removal from /Library/Extensions alone does not repair AuxKC.

## C. Windows-only OpenCore EFI repair
**Not rehearsed.** In existing Windows, inspect physical disk and GPT partition identity first. Restore only the backed-up **OpenCore-owned EFI files** to the previously verified *internal* ESP after owner review. Do NOT touch Microsoft/Boot, BCD, Windows Boot Manager, Windows partition layout, or firmware Windows entries. If UUID/partition uncertain: STOP. Windows EFI recovery does not repair macOS Kexts, GPU bundles or AuxKC.

## D. Recovery-level system restoration and Auxiliary KC
**Not rehearsed, no Tahoe 26.7.3 matched KDK validated.** Back up the failed state first. On target Tahoe's **Data volume**, reconcile:
- /Library/Extensions/{NVRM,NVAccel,NVRMFB,NVRMAGDC,NVPrimarySelector,NMXAudio}.kext with original manifest.
- /Library/GPUBundles/{NVMTLDriver.bundle,nvmtl,nvmtl-allow.txt,NVIDIAShared.bundle} with original versions.
- /Library/NullMoth and com.nullmoth.* LaunchDaemons (bootguard, lastgood, recover, update), preserving unrelated software.
- /Library/KernelCollections/AuxiliaryKernelExtensions.kc: restore a verified backup *only if same build and no unrelated changes*, **or** rebuild from the original target-compatible Kext repository and matching Tahoe tools/KDK; inspect collection for absence of experimental NVIDIA and presence of all original required Kexts.
- Kext approval/load-history state under /var/db/SystemPolicyConfiguration/KextPolicy if changed; installer code can update Kext cdhash in some upgrade paths. Treat this as an explicit rollback gap.
- Restore original OpenCore/SIP/AMFI/boot-args/SMBIOS after system components and AuxKC agree. Preserve target permissions and FileVault policies.

**Never blindly delete an AuxKC**; it may include unrelated required third-party Kexts. Never use MacBook Air macOS 27 SDK/KDK as a substitute for target Tahoe.

## E. Official 1401 removal or no-driver boot
**Source-reviewed, not executed or target-validated.** Actual 1401 v2.9 `nullmoth-setup.sh` supports `NullMothSafe.efi` removal picker path, `nullmoth-remove` marker, `com.nullmoth.recover`, and a `--remove` workflow; official `uninstall.sh` rebuilds/removes AuxKC and cleans GPU bundles. The Tahoe update pathway also refers to `-nvoff` boot-arg. These mechanisms require the correct EFI, functioning boot handoff, intact Data volume and scripts, and sometimes macOS services. They cannot be assumed to work in an early panic/black-screen loop. **Do not use the removal entry on a copied installation USB unless startup EFI is independently verified.**

## Failure categories
- **Black before OpenCore picker:** firmware/PCI BAR or EFI, try tested rescue USB.
- **Panic during macOS boot:** installed Kext/AuxKC must be inspected, not merely EFI.
- **Login loop or WindowServer crash:** NVMTLDriver/AMFI/private ABI and graphics bundles are suspects; restore full graphics stack.
- **Power-off/reboot instability:** preserve firmware state evidence; do not induce repeated experimental boots.

## Completion criteria
A rollback is complete only when original EFI and Windows boot state are preserved, target third-party Kexts and GPU bundles match baseline, Auxiliary KC is verifiably consistent with exact target build, security settings are restored, and the laptop performs stable repeat boots. Every step is currently **UNREHEARSED**. Do not perform recovery writes without a separate explicitly approved, target-specific plan.