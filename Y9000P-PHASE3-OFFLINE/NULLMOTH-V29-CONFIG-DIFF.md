# NullMoth v2.9 expected OpenCore differences

**This is a prospective requirements matrix, NOT a measured Y9000P diff and NOT a patch.** The current Y9000P config has not been provided.

| Item | Current value | Upstream expected state | Risk |
|---|---|---|---|
| Boot args | UNKNOWN | `nvfb=1 nvaccel=1 nvfbheads=4 -nvkmsnosmooth amfi_get_out_of_my_way=0x1 amfi=0x80 ipc_control_port_options=0` | Display + AMFI/security; review each token |
| Conflicting args | UNKNOWN | no `nv_disable=1`, `-wegnoegpu` or `agdpmod=pikera` | Might change existing GPU routing |
| csr-active-config | UNKNOWN | required bits `0x0A43`, typically `430A0000` little-endian | SIP change, manual approval |
| NVRAM Delete | UNKNOWN | boot-args and csr-active-config entries | NVRAM reset semantics |
| SecureBootModel | UNKNOWN | Disabled | Security downgrade |
| Kernel Add | UNKNOWN | Lilu and AMFIPass enabled; Lilu first | Kext dependency/version check |
| WhateverGreen | UNKNOWN | If enabled, `gfxrst=4` | Project warns of NVIDIA panic |
| WhateverXe | UNKNOWN | Must not co-exist with experimental NVIDIA | BLOCK |
| Kernel Block | UNKNOWN | `com.apple.iokit.IONDRVSupport`, Strategy Exclude | Framebuffer/black-screen risk |
| NVIDIA Kext OpenCore injection | UNKNOWN | NVRM/NVAccel/NVRMFB/NVRMAGDC must load from AuxKC, not OC | Prevent double injection |
| SMBIOS/SystemProductName/BoardProduct | UNKNOWN | Preserve existing values | **ANY automatic conversion = BLOCK** |
| ResizeGpuBars / ResizeAppleGpuBars | UNKNOWN | Preserve, investigate BAR hardware first | Firmware PCI boot risk |
| Actual EFI | UNKNOWN | Must prove booted internal GPT partition | Copied USB EFI not acceptable |

The 1401 app may modify OpenCore, NVRAM, system Kexts, GPU bundles, AuxKC and persistent daemons. Its Tahoe preparation can propose SMBIOS edits. This laptop already boots Tahoe; reject automatic SMBIOS migration.

Generate actual per-key differences from an offline EFI copy using `tools/efi_auditor.py` once the private baseline exists.