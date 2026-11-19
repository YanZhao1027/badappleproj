#!/usr/bin/perl
# Read full ioreg stream from stdin, emit only allowlisted NVIDIA/Intel GPU entries.
use strict;
use warnings;
use JSON::PP;
binmode STDIN;
local $/;
my $src=<STDIN>;
$src='' unless defined($src);
my @nodes=split /(?=^\s*\+-o\s+)/m,$src;
my @matches;
sub le16 {
  my($v)=@_;
  return undef unless defined $v;
  return uc($2.$1) if $v=~/^<([a-fA-F0-9]{2})([a-fA-F0-9]{2})[a-fA-F0-9]*>/;
  return undef;
}
for my $node (@nodes) {
  my($name)=$node=~/^\s*\+-o\s+([^\n<]+)/m;
  my %f;
  for my $ln (split /\n/,$node){
    if($ln=~/^\s*[| ]*"([^"]+)"\s*=\s*(.*)$/){
      my($k,$v)=($1,$2);
      if($k=~/^(?:vendor-id|device-id|subsystem-id|subsystem-vendor-id|class-code|reg|assigned-addresses|IODeviceMemory|AAPL,slot-name|model|device_type|IOName|IOPCIExpressLinkStatus|IOPCIExpressLinkCapabilities|IOPCIExpressLinkWidth|IOPCIExpressLinkSpeed)$/){
        $f{$k}=substr($v,0,1600);
      }
    }
  }
  my $vendor=le16($f{'vendor-id'});
  next unless defined($vendor);
  my $class=$f{'class-code'}//'';
  my $intel_display=$vendor eq '8086' && ($class=~/^<000003/i || ($name//'')=~/IGPU|GFX|UHD|Iris|Display/i);
  next unless $vendor eq '10DE'||$intel_display;
  my %entry=(vendor_id=>$vendor,device_id=>le16($f{'device-id'})//'UNKNOWN',
             category=>$vendor eq '10DE'?'NVIDIA_PCI':'INTEL_DISPLAY_CANDIDATE',
             registry_node=>substr($name//'UNKNOWN',0,100));
  for my $k (qw(subsystem-id subsystem-vendor-id)){
    my $v=le16($f{$k});
    $entry{$k eq 'subsystem-id'?'subsystem_id':'subsystem_vendor_id'}=$v if defined($v);
  }
  my %resources;
  for my $k (qw(reg assigned-addresses IODeviceMemory AAPL,slot-name model device_type IOName IOPCIExpressLinkStatus IOPCIExpressLinkCapabilities IOPCIExpressLinkWidth IOPCIExpressLinkSpeed)){
    $resources{$k}=$f{$k} if exists($f{$k});
  }
  $entry{location_and_resource_clues}=\%resources;
  push @matches,\%entry;
}
print JSON::PP->new->canonical->pretty->utf8->encode({
  schema=>'phase3-gpu-ioreg-v1',
  warning=>'IORegistry memory resources are NOT proven physical PCI BAR registers. Correlate with target firmware evidence.',
  gpu_devices=>\@matches
});