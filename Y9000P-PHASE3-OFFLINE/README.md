# Y9000P NullMoth v2.9 — Phase 3 offline (read-only)

**Target:** Intel macOS Tahoe 26.7.3, Y9000P IRX11, RTX 5060 Laptop `10DE:2D59`.  
**Decision:** Read-only investigation GO; on-target driver installation **NO-GO**.

## On the Y9000P (one-time offline baseline)

Copy this **folder only** to a confirmed safe USB **data** partition or a trusted local folder. Do not write to an EFI/System/Windows partition or format the USB. Do not run the collector with sudo.

From Terminal, inside this directory:

```bash
/bin/bash TAHOE-BASELINE-COLLECTOR.sh --self-test
/bin/bash TAHOE-BASELINE-COLLECTOR.sh
```

Private output is written to `$HOME/Y9000P-Diagnostics/run-XXXXXXXX/`. It includes complete macOS build/Darwin, GPU PCI and Intel display candidates, subsystem and BAR/resource clues, SPDisplays/Metal fields, loaded/present Kext names, AuxKC inspection, SIP, boot-args and redacted OpenCore startup clues.

**Optional** EFI audit snapshot: after *you* have already mounted and independently identified the correct partition, pass its path to a **read-only** collector invocation:

```bash
/bin/bash TAHOE-BASELINE-COLLECTOR.sh --efi-config /Volumes/EFI/EFI/OC/config.plist
```

The collector never mounts EFI. Its `efi-config-sanitized.json` is a **non-bootable allowlisted JSON**, not a full bootable EFI backup. It excludes serial, MLB, ROM, UUID and other non-audit fields. If the privacy filters are unavailable, it stops or marks that section FAILED_CLOSED.

**Never upload any private collector result or real EFI to this public repository**, even if automatically redacted. Review locally before any private transfer.

## Offline import on MacBook Air (Python 3 standard library)

Copy the Y9000P's private `run-XXXXXXXX` folder to a separate trusted Mac location, then from this project directory run:

```bash
python3 tools/import_results.py --input /private/location/run-XXXXXXXX
python3 tools/efi_auditor.py --current /private/location/run-XXXXXXXX/efi-config-sanitized.json --diagnostics /private/location/run-XXXXXXXX
```

For an **actual** per-key EFI change proposal, use `--current /private/WORKING-EFI-COPY/EFI/OC/config.plist` and optionally `--proposed /private/PROPOSED-EFI-COPY/config.plist`. The reviewer writes reports to a new `analysis-output` folder; never to the input EFI or system. It does not modify config.plist, inject Kexts, change NVRAM or produce automatic installation changes.

## Evidence limitations

- A copied install USB, matching SMBIOS or boot-args **does not uniquely determine which OpenCore EFI booted**. Privately compare OpenCore boot-path and the GPT EFI Partition UUID on the Y9000P, and confirm independent internal boot without the installation USB.
- IOKit memory resources are not definitive PCI BAR register evidence. Target BIOS/GPU routing and private Tahoe ABI need additional verification.
- Recovery USB, Windows EFI restore, Tahoe Recovery and offline Auxiliary KC rollback are **not rehearsed**. Read `OFFLINE-RECOVERY-PLAYBOOK.md` and `PHASE3-GO-NOGO.md` before considering any installation.

## Test locally (no hardware access, no system writes)

```bash
python3 tests/test_phase3.py
```

Eight synthetic tests passed on the MacBook Air's isolated copy on 2026-11-19. Full success on Y9000P remains untested. Driver install, EFI writes, SIP/AMFI/NVRAM changes, SMBIOS migration and reboot are **out of scope**.

## Included files

`PHASE3-READINESS.md`, `TAHOE-BASELINE-COLLECTOR.sh`, `EFI-CHANGE-AUDITOR.md`, `OFFLINE-RECOVERY-PLAYBOOK.md`, `NULLMOTH-V29-CONFIG-DIFF.md`, `PHASE3-GO-NOGO.md`, `RELEASE-HASHES.md`, `NULLMOTH-V29-CONFIG-REQUIREMENTS.json`, `tools/`, `tests/`.

The upstream v2.9 official release has already been verified in Phase 2. This repo contains reference hashes, not NVIDIA driver or EFI binary payloads.
