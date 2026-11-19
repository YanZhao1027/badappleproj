# NullMoth v2.9 — pinned Phase 2 release evidence

Official release: https://github.com/nullmoth/nvidia-macos-driver/releases/tag/v2.9  
Source commit: `7412cdde81447f78da0ebb64216dc258d8beaedb`  
OGKM: `620.70.06`  
Target: Intel macOS Tahoe 26.7.3, RTX 5060 Laptop `10DE:2D59`.

| Official asset | SHA256 | Status inherited from Phase 2 |
|---|---|---|
| nullmoth-nvidia-2.9.tar.gz | `b624bf07c78cea03043e096383d5c8b01e4fb2c804a6ba377a4e66a2566422ef` | PASS |
| 1401-Mac-2.9.dmg | `0510e132a1edebfaafedf9c2d141dcfe30f1787fd98b8f07c3f48a96f089c129` | PASS |
| SHA256SUMS.txt | `741de0d14c827bdf7edbcab29161fc45c9969a62dee1f9575506a0458aabeab3` | PASS |
| nullmoth-nvidia-2.9.tar.gz.sig | `707180e9c39cfdc5c14988c3e98c5a342202dc5db84debfe9001a193618a72ec` | Hash matched, independent signer NOT authenticated |
| nullmoth-nvidia-2.9.tar.gz.bsig | `1c46232f6084976ee1df551b5d0e97bb316a8176d6b13121e428c21275863865` | Hash matched, independent signer NOT authenticated |

Do not redownload or replace this baseline. The official package includes x86_64 and macOS 26-specific NVAccel. These facts do NOT establish target 26.7.3 private-ABI compatibility. No official binaries are distributed in this public repo.