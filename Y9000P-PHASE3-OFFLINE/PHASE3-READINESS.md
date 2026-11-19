# Phase 3 readiness

**Current status: read-only collection GO; driver installation NO-GO.**

Host: MacBook Air, Apple Silicon, macOS 27.2. Target: Y9000P IRX11, x86_64 Tahoe 26.7.3, RTX 5060 Laptop `10DE:2D59`.

## Already established by Phase 2
Official v2.9 tar.gz and 1401 DMG SHA256 PASS; contained x86_64 Mach-O and Tahoe 26 NVAccel. No target Mac ABI, BAR, EFI boot-source or recovery ability has been demonstrated.

## Read-only session goals
- Exact sw_vers, build and Darwin.
- IOPCIDevice NVIDIA and Intel GPU IDs, subsystem, slot and resource/BAR *clues* (not validated BAR registers).
- Displays and Metal status.
- Loaded Kexts, installed NVIDIA/Intel/WhateverGreen Kexts and AuxKC existence/inspect results.
- SIP, boot-args, AMFI flags and proposed SecureBootModel from a selected **candidate** EFI.
- Redacted OpenCore boot-path evidence and partition listing, but never an unsupported claim of unique startup EFI identity.
- Sanitized, non-bootable allowlisted EFI configuration snapshot only if user supplies an already mounted and identified config path.

## Provenance gate
On the target, independently cross-check OpenCore NVRAM boot-path GPT Partition UUID with the actual internal EFI Partition UUID. Keep the UUID privately on-screen. Boot Tahoe with installation USB disconnected; keep a separate actually boot-tested rescue USB. Matching SMBIOS, serial or boot-args alone proves nothing about which EFI was used.

## Missing hard prerequisites
A target baseline; independent EFI partition evidence; verified rescue boot; actual Tahoe Recovery/Data volume access; baseline Kext/GPUBundles/AuxKC backups; target private ABI evidence; GPU resource validation; supervised reversible changes reviewed by the owner.

Never upload any real machine reports, raw EFI configuration, serial, MLB, ROM, UUID, network MAC or unique identifiers to this public repository.