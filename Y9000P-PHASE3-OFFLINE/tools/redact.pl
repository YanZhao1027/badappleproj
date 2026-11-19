#!/usr/bin/perl
# Sanitizes captured text/JSON BEFORE output is written to disk.
use strict;
use warnings;
use JSON::PP;
binmode STDIN;
binmode STDOUT;
my $mode=shift(@ARGV)//'text';
local $/;
my $source=<STDIN>;
$source='' unless defined($source);

sub key_private {
  my($k)=@_;
  return ($k =~ /(?:serial|uuid|unique.?id|mlb|rom|mac.?address|bssid|ssid|host.?name|computer.?name|user.?name|account.?name|password|secret|token|credential|private.?key|network.?address|ip.?address)/i);
}
sub strip {
  my($s)=@_;
  $s =~ s/\b[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\b/[UUID-REDACTED]/ig;
  $s =~ s/\b(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}\b/[MAC-REDACTED]/ig;
  $s =~ s{/(?:Users|home)/[^/\s"']+}{[HOME-REDACTED]}g;
  $s =~ s/\b(?:\d{1,3}\.){3}\d{1,3}\b/[IP-REDACTED]/g;
  return $s;
}
sub txt {
  my($s)=@_;
  $s=strip($s);
  $s =~ s{\b(?:serial|mlb|rom|uuid|mac|password|secret|token|ssid)=[^\s\r\n]+}{[SENSITIVE-ARG-REDACTED]}gim;
  $s =~ s{(^[^\n]*?\b(?:IOPlatformSerialNumber|SystemSerialNumber|BoardSerialNumber|Serial Number|SerialNumber|MLB|ROM|SystemUUID|Partition UUID|Volume UUID|Disk UUID|MAC Address|Ethernet Address|BSSID|SSID|Hostname|Computer Name|Password|Secret|Token|Credential)\b\s*(?:["']?\s*[:=]\s*|["']?\s+))[^\r\n]*}{1[REDACTED]}gim;
  return $s;
}
sub walk {
  my($x)=@_;
  if(ref($x) eq 'HASH') {
    my %res;
    for my $k (keys %$x) {
      $res{$k}= key_private($k)? '[REDACTED]':walk($x->{$k});
    }
    return \%res;
  }
  if(ref($x) eq 'ARRAY'){return [map {walk($_)} @$x];}
  if(!ref($x) && defined($x)){return txt($x);}
  return $x;
}
if($mode eq 'text'){
  print txt($source);
} elsif($mode eq 'json'){
  my $obj=eval {JSON::PP->new->utf8->decode($source)};
  if($@){print STDERR "JSON redaction failed, no output\n";exit 3;}
  print JSON::PP->new->canonical->pretty->utf8->encode(walk($obj));
} else {
  die "Expected text or json mode\n";
}