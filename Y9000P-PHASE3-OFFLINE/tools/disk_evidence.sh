#!/bin/bash
# Read-only allowlist of diskutil properties. Never mount, label, write or expose raw UUID/volume names.
set -u
set -o pipefail
/usr/sbin/diskutil list 2>/dev/null |
  /usr/bin/awk '
    /^\/dev\/disk[0-9]+/ {
      if (match($0,/\/dev\/disk[0-9]+/)) print "WHOLE_DISK " substr($0,RSTART,RLENGTH);
    }
    /^[[:space:]]*[0-9]+:/ {
      id=$NF;
      if (id !~ /^disk[0-9]+s[0-9]+$/) next;
      type="OTHER";
      if ($0 ~ / EFI /) type="EFI";
      else if ($0 ~ /Apple_APFS|APFS Container/) type="APFS";
      else if ($0 ~ /Microsoft Basic Data|Windows_NTFS/) type="WINDOWS_TYPE";
      else if ($0 ~ /DOS_FAT_32|Windows_FAT_32/) type="FAT32";
      print "PARTITION " id " CATEGORY " type;
    }
  '
# Target APFS root volume only; expose a narrow list of non-unique public properties.
# Keep GPT Partition UUID out of stored output; manually inspect on target screen.
printf '%s\n' '--- ROOT DISK FACTS ---'
/usr/sbin/diskutil info / 2>/dev/null |
  /usr/bin/awk -F: '
    /^[[:space:]]*(Device Identifier|Part of Whole|Device Location|Protocol|Removable Media|APFS Physical Store|File System Personality|Partition Type):/ {
      key=$1; value=$2;
      sub(/^[[:space:]]*/,"",key);
      sub(/^[[:space:]]*/,"",value);
      if (value ~ /^[[:space:]]*$/) value="UNKNOWN";
      print key "=" value;
    }
  '
