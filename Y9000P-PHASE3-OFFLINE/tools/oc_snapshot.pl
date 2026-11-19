#!/usr/bin/perl
# Parse plist XML from stdin and output a NON-BOOTABLE allowlisted JSON audit snapshot.
use strict;
use warnings;
use JSON::PP;
use XML::Parser;
use MIME::Base64 qw(decode_base64);
binmode STDIN;
binmode STDOUT;
local $/;
my $src=<STDIN>;
defined($src) or die "No plist XML supplied\n";
my @stack;
my $root;
sub put {
  my($v)=@_;
  if(!@stack){$root=$v;return;}
  my $p=$stack[-1];
  if($p->{tag} eq 'dict'){
    my $key=delete $p->{key};
    defined($key) or die "Unkeyed dictionary entry\n";
    $p->{v}->{$key}=$v;
  } elsif ($p->{tag} eq 'array'){
    push @{$p->{v}},$v;
  } elsif ($p->{tag} eq 'plist'){
    $p->{v}=$v;
  } else {die "Bad plist parent\n";}
}
my $parser=XML::Parser->new(Handlers=>{
  Start=>sub{
    my($parser,$tag)=@_;
    push @stack,{tag=>$tag,text=>'',v=>($tag eq 'dict'?{}:$tag eq 'array'?[]:undef)};
  },
  Char=>sub{my($p,$c)=@_;$stack[-1]->{text}.=$c if @stack;},
  End=>sub{
    my($p,$tag)=@_;
    my $f=pop @stack;
    defined($f)&&$f->{tag} eq $tag or die "Broken plist XML\n";
    if($tag eq 'key'){
      @stack&&$stack[-1]->{tag} eq 'dict' or die "Key outside dictionary\n";
      $stack[-1]->{key}=$f->{text};return;
    }
    my $v;
    if($tag eq 'dict'||$tag eq 'array'||$tag eq 'plist'){$v=$f->{v};}
    elsif($tag eq 'string'||$tag eq 'date'){$v=$f->{text};}
    elsif($tag eq 'integer'||$tag eq 'real'){$v=0+($f->{text}||0);}
    elsif($tag eq 'true'){$v=JSON::PP::true;}
    elsif($tag eq 'false'){$v=JSON::PP::false;}
    elsif($tag eq 'data'){$v={'__data_hex'=>unpack('H*',decode_base64($f->{text}))};}
    else {die "Unsupported XML element: $tag\n";}
    put($v);
  }
});
eval{$parser->parse($src)};
if($@||ref($root) ne 'HASH'){print STDERR "Could not parse config plist\n";exit 3;}
sub h {return ref($_[0]) eq 'HASH'?$_[0]:{};}
sub selection {
  my($d,@keys)=@_;
  $d=h($d);
  return {map {exists($d->{$_})?($_=>$d->{$_}):()} @keys};
}
my $apple='7C436110-AB2A-4BBB-A880-FE41995C9F82';
my $nv=h($root->{NVRAM});
my $adds=h($nv->{Add});
my($g)=grep {uc($_) eq $apple} keys %$adds;
my $nvobj=h(defined($g)?$adds->{$g}:{});
my $safeadd=selection($nvobj,qw(boot-args csr-active-config));
if(exists $safeadd->{'boot-args'}){
  my $v=$safeadd->{'boot-args'};
  if(ref($v)){delete $safeadd->{'boot-args'};} else {
    my @tokens=split /\s+/,$v;
    @tokens=map {/serial|mlb|uuid|rom=|mac=|password|secret|token|ssid/i?'[SENSITIVE-ARG-REDACTED]':$_} @tokens;
    $safeadd->{'boot-args'}=join(' ',@tokens);
  }
}
my $dels=h($nv->{Delete});
my($dg)=grep{uc($_) eq $apple}keys %$dels;
my @delete=grep {$_ eq 'boot-args'||$_ eq 'csr-active-config'} @{(defined($dg)&&ref($dels->{$dg}) eq 'ARRAY')?$dels->{$dg}:[]};
my $kernel=h($root->{Kernel});
my @add=map{selection($_,qw(Arch BundlePath Enabled ExecutablePath PlistPath MinKernel MaxKernel))} grep{ref($_) eq 'HASH'}@{ref($kernel->{Add}) eq 'ARRAY'?$kernel->{Add}:[]};
my @block=map{selection($_,qw(Arch Identifier Enabled Strategy MinKernel MaxKernel))} grep{ref($_) eq 'HASH'}@{ref($kernel->{Block}) eq 'ARRAY'?$kernel->{Block}:[]};
my $pi=h($root->{PlatformInfo});
my $result={
  schema=>'phase3-efi-snapshot-v1',redacted=>JSON::PP::true,bootable=>JSON::PP::false,
  note=>'Only allowlisted audit fields. DO NOT use as OpenCore config.plist.',
  config=>{
    NVRAM=>{Add=>{$apple=>$safeadd},Delete=>{$apple=>\@delete}},
    Kernel=>{Add=>\@add,Block=>\@block},
    Misc=>{Security=>selection(h(h($root->{Misc})->{Security}),qw(SecureBootModel ExposeSensitiveData))},
    PlatformInfo=>{
      Automatic=>$pi->{Automatic},UpdateSMBIOSMode=>$pi->{UpdateSMBIOSMode},
      Generic=>selection($pi->{Generic},qw(SystemProductName SpoofVendor ProcessorType)),
      SMBIOS=>selection($pi->{SMBIOS},qw(SystemProductName BoardProduct)),
      DataHub=>selection($pi->{DataHub},qw(SystemProductName BoardProduct))
    },
    UEFI=>{Quirks=>selection(h(h($root->{UEFI})->{Quirks}),qw(ResizeGpuBars))},
    Booter=>{Quirks=>selection(h(h($root->{Booter})->{Quirks}),qw(ResizeAppleGpuBars))}
  }
};
print JSON::PP->new->canonical->pretty->utf8->encode($result);