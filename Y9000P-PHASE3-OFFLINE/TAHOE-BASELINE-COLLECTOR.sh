#!/bin/bash
# Y9000P Tahoe Phase 3 -- read-only. Run as normal user. No system writes.
set -u
set -o pipefail
umask 077

HERE="$(cd "$(dirname "$0")" && pwd -P)" || exit 2
RED="$HERE/tools/redact.pl"
GPU="$HERE/tools/gpu_ioreg.pl"
OC="$HERE/tools/oc_snapshot.pl"
BASE="$HOME/Y9000P-Diagnostics"
EFI=""
SELFTEST=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --help|-h)
      echo "Usage: bash TAHOE-BASELINE-COLLECTOR.sh [--efi-config /Volumes/EFI/EFI/OC/config.plist] [--output /absolute/path/inside/HOME] [--self-test]"
      exit 0 ;;
    --self-test) SELFTEST=1; shift ;;
    --efi-config) [ "$#" -ge 2 ] || exit 2; EFI="$2"; shift 2 ;;
    --output) [ "$#" -ge 2 ] || exit 2; BASE="$2"; shift 2 ;;
    *) echo "Unsupported argument; refusing operation" >&2; exit 2 ;;
  esac
done
for f in "$RED" "$GPU" "$OC"; do
  [ -f "$f" ] || { echo "Missing privacy filter: $f" >&2; exit 2; }
done
/usr/bin/perl -MJSON::PP -MXML::Parser -e 'exit 0' 2>/dev/null || {
  echo "Perl sanitizers unavailable; no data collected" >&2; exit 3;
}
if [ "$SELFTEST" -eq 1 ]; then
  result="$(printf 'Serial Number: TESTPRIVATE\nMAC: aa:bb:cc:dd:ee:ff\nGPU: 10DE:2D59\n' | /usr/bin/perl "$RED" text)" || exit 3
  case "$result" in
    *TESTPRIVATE*|*aa:bb:cc:dd:ee:ff*) echo "Privacy self-test FAIL" >&2; exit 4;;
    *10DE:2D59*) echo "Privacy self-test PASS; no target data read"; exit 0;;
    *) echo "Privacy self-test FAIL" >&2; exit 4;;
  esac
fi
[ "$(/usr/bin/id -u)" != "0" ] || { echo "Do not run with sudo" >&2; exit 2; }
HOME_REAL="$(cd "$HOME" && pwd -P)" || exit 2
case "$BASE" in "$HOME"/*) ;; *) echo "Output must be an absolute path inside HOME" >&2; exit 2;; esac
[ ! -L "$BASE" ] || { echo "Symlink output rejected" >&2; exit 2; }
/bin/mkdir -p -m 700 "$BASE" || exit 2
BASE_REAL="$(cd "$BASE" && pwd -P)" || exit 2
case "$BASE_REAL" in "$HOME_REAL"/*) ;; *) echo "Output resolves outside HOME" >&2; exit 2;; esac
OUT="$(/usr/bin/mktemp -d "$BASE_REAL/run-XXXXXXXX")" || exit 2
/bin/chmod 700 "$OUT" || exit 2
STATUS="$OUT/collection-status.tsv"
printf 'section\tstatus\n' > "$STATUS"
note(){ printf '%s\t%s\n' "$1" "$2" >> "$STATUS"; }

# Capture streams through redaction filter; never write command output before filtering.
capture_text(){
  local name="$1"; shift
  local target="$OUT/.$name.partial"
  if "$@" 2>&1 | /usr/bin/perl "$RED" text > "$target"; then
    /bin/mv "$target" "$OUT/$name"
    note "$name" "CAPTURED_REDACTED"
  else
    /bin/rm -f "$target"
    note "$name" "FAILED_CLOSED"
  fi
}
capture_json(){
  local name="$1"; shift
  local target="$OUT/.$name.partial"
  if "$@" 2>&1 | /usr/bin/perl "$RED" json > "$target"; then
    /bin/mv "$target" "$OUT/$name"
    note "$name" "CAPTURED_REDACTED"
  else
    /bin/rm -f "$target"
    note "$name" "FAILED_CLOSED"
  fi
}
# Do not use uname -a, HardwareDataType or broad ioreg dumps in exported files.
capture_text sw-vers.txt /usr/bin/sw_vers
capture_text kernel.txt /usr/bin/uname -srvmp
capture_text darwin.txt /usr/bin/uname -r
capture_text arch.txt /usr/bin/uname -m
capture_text hw-model.txt /usr/sbin/sysctl -n hw.model
capture_json displays.json /usr/sbin/system_profiler SPDisplaysDataType -json
capture_json pci-profiler.json /usr/sbin/system_profiler SPPCIDataType -json

# GPU stream undergoes allowlisting THEN structural redaction.
TMP="$OUT/.gpu.partial"
if /usr/sbin/ioreg -r -l -w0 -c IOPCIDevice 2>/dev/null |
   /usr/bin/perl "$GPU" | /usr/bin/perl "$RED" json > "$TMP"; then
  /bin/mv "$TMP" "$OUT/gpu-pci.json"
  note gpu-pci.json "ALLOWLISTED_REDACTED"
else
  /bin/rm -f "$TMP"
  note gpu-pci.json "FAILED_CLOSED"
fi

capture_text kext-loaded.txt /usr/bin/kmutil showloaded --list-only
if [ -f /Library/KernelCollections/AuxiliaryKernelExtensions.kc ]; then
  capture_text auxkc-stat.txt /usr/bin/stat -f 'bytes=%z modified=%Sm' /Library/KernelCollections/AuxiliaryKernelExtensions.kc
  capture_text auxkc-inspect.txt /usr/bin/kmutil inspect -a x86_64 -A /Library/KernelCollections/AuxiliaryKernelExtensions.kc
else
  note auxkc-inspect.txt "ABSENT_OR_INACCESSIBLE"
fi
capture_text sip-status.txt /usr/bin/csrutil status
capture_text boot-args.txt /usr/sbin/nvram boot-args
capture_text csr-nvram.txt /usr/sbin/nvram 7C436110-AB2A-4BBB-A880-FE41995C9F82:csr-active-config
capture_text opencore-version.txt /usr/sbin/nvram 4D1FDA02-38C7-4A6A-9CC6-4BCCA8B30102:opencore-version
capture_text opencore-bootpath.txt /usr/sbin/nvram 4D1FDA02-38C7-4A6A-9CC6-4BCCA8B30102:boot-path
# UUIDs and system IDs are removed. Never claim partition identity from this anonymized output.
# Only allowlisted disk identifiers/classes, no volume names or raw partition UUIDs.
capture_text disk-evidence.txt /bin/bash "$HERE/tools/disk_evidence.sh"

# Enumerate relevant installed third-party names, not entire /Library or protected policy DB.
KLIST="$OUT/.kext-inventory.partial"
: > "$KLIST"
for dir in /Library/Extensions /Library/GPUBundles; do
  for item in "$dir"/*.kext "$dir"/*.bundle "$dir"/nvmtl; do
    [ -e "$item" ] || continue
    name="$(basename "$item")"
    case "$name" in
      *NV*|*nv*|*Intel*|*Whatever*|*Lilu*|*AMFI*|*Xe*)
        id=''
        if [ -f "$item/Contents/Info.plist" ]; then
          id=$(/usr/bin/plutil -extract CFBundleIdentifier raw "$item/Contents/Info.plist" 2>/dev/null || :)
        fi
        printf '%s\t%s\t%s\n' "$dir" "$name" "$id" >> "$KLIST" ;;
    esac
  done
done
if /usr/bin/perl "$RED" text < "$KLIST" > "$OUT/.kext-clean"; then
  /bin/mv "$OUT/.kext-clean" "$OUT/kext-inventory.txt"
  note kext-inventory.txt "ALLOWLISTED"
fi
/bin/rm -f "$KLIST"

# Never mount EFI. The optional candidate config MUST be pre-mounted by the owner.
if [ -n "$EFI" ]; then
  if [ -f "$EFI" ] && [ ! -L "$EFI" ] &&
     [ "$(basename "$EFI")" = "config.plist" ] &&
     /usr/bin/plutil -lint "$EFI" >/dev/null 2>&1; then
    TMP="$OUT/.config.partial"
    if /usr/bin/plutil -convert xml1 -o - "$EFI" 2>/dev/null |
       /usr/bin/perl "$OC" > "$TMP"; then
      /bin/mv "$TMP" "$OUT/efi-config-sanitized.json"
      note efi-config-sanitized.json "ALLOWLISTED_NON_BOOTABLE"
    else
      /bin/rm -f "$TMP"
      note efi-config-sanitized.json "FAILED_CLOSED"
    fi
  else
    note efi-config-sanitized.json "NOT_READABLE_OR_INVALID"
  fi
else
  note efi-config-sanitized.json "NOT_REQUESTED"
fi
OS=$(/usr/bin/sw_vers -productVersion 2>/dev/null || :)
BUILD=$(/usr/bin/sw_vers -buildVersion 2>/dev/null || :)
DAR=$(/usr/bin/uname -r 2>/dev/null || :)
ARCH=$(/usr/bin/uname -m 2>/dev/null || :)
for x in "$OS" "$BUILD" "$DAR" "$ARCH"; do
  case "$x" in ''|*[!A-Za-z0-9._-]*) echo "OS metadata unexpected" >&2; exit 4;; esac
done
cat > "$OUT/summary.json" <<JSON
{
  "schema":"phase3-summary-v1",
  "macos":"$OS",
  "build":"$BUILD",
  "darwin":"$DAR",
  "arch":"$ARCH",
  "expected_gpu":"10DE:2D59",
  "efi_source_proven":false,
  "target_abi_proven":false,
  "rescue_usb_rehearsed":false,
  "system_rollback_rehearsed":false,
  "writes_system":false
}
JSON
cat > "$OUT/READ-ME-FIRST.txt" <<'TXT'
PRIVATE MACHINE DIAGNOSTICS: DO NOT POST TO PUBLIC GITHUB.
No EFI mounts, system writes, Kext loading, SIP changes, NVRAM changes or reboots.
efi-config-sanitized.json is non-bootable and contains only allowlisted fields.
Boot EFI identity is NOT established. Cross-check raw boot-path GPT UUID
against actual internal EFI Partition UUID privately ON THE TARGET SCREEN.
Any FAILED_CLOSED section means missing evidence, not a passed check.
TXT
/bin/chmod -R go-rwx "$OUT"
echo "Private read-only diagnostic result directory: $OUT"
echo "Actual booted EFI: UNVERIFIED; requires human GPT partition cross-check."
