param([int]$Disk, [string]$Log)
# Repair a primary GPT header whose partition-entry pointer was changed to a
# location that holds no entries. Only LBA 1 is written, and only if the
# valid entries are confirmed to be at LBA 2.
$ErrorActionPreference = 'Stop'
Start-Transcript -Path $Log -Force | Out-Null
try {
    Add-Type -TypeDefinition @"
public static class Crc32f { static uint[] t = Make(); static uint[] Make() { var a = new uint[256]; for (uint i = 0; i < 256; i++) { uint c = i; for (int k = 0; k < 8; k++) c = (c & 1) != 0 ? 0xEDB88320u ^ (c >> 1) : c >> 1; a[i] = c; } return a; }
public static uint Of(byte[] b, int off, int len) { uint c = 0xFFFFFFFFu; for (int i = off; i < off + len; i++) c = t[(c ^ b[i]) & 0xFF] ^ (c >> 8); return c ^ 0xFFFFFFFFu; } }
"@
    $d = Get-Disk -Number $Disk
    "Disk $Disk : $($d.FriendlyName), $([math]::Round($d.Size/1GB,1)) GB, bus $($d.BusType)"
    if ($d.BusType -ne 'USB' -or $d.Size -gt 200GB) { throw 'Refusing: not a small USB drive.' }
    $fs = New-Object IO.FileStream("\\.\PhysicalDrive$Disk", [IO.FileMode]::Open, [IO.FileAccess]::ReadWrite, [IO.FileShare]::ReadWrite)
    $buf = New-Object byte[] (34*512); $fs.Position = 0; [void]$fs.Read($buf,0,$buf.Length)
    $hdr = New-Object byte[] 512; [Array]::Copy($buf,512,$hdr,0,512)
    if ([Text.Encoding]::ASCII.GetString($hdr,0,8) -ne 'EFI PART') { throw 'No GPT header at LBA 1.' }
    $hs = [BitConverter]::ToUInt32($hdr,12)
    $entLba = [BitConverter]::ToUInt64($hdr,72)
    $n = [BitConverter]::ToUInt32($hdr,80); $sz = [BitConverter]::ToUInt32($hdr,84)
    "Header entry pointer now: $entLba"
    if ($entLba -eq 2) { 'Already points at LBA 2 - nothing to do.'; return }
    $crcAt2 = [Crc32f]::Of($buf, 1024, [int]($n*$sz))
    if ($crcAt2 -ne [BitConverter]::ToUInt32($hdr,88)) { throw 'Entries at LBA 2 do not match the header CRC - not touching it.' }
    'Valid partition entries confirmed at LBA 2.'
    [IO.File]::WriteAllBytes((Join-Path (Split-Path $Log) "lba1_before_fix_disk$Disk.bin"), $hdr)
    [BitConverter]::GetBytes([uint64]2).CopyTo($hdr,72)
    [Array]::Clear($hdr,16,4); [BitConverter]::GetBytes([Crc32f]::Of($hdr,0,$hs)).CopyTo($hdr,16)
    $fs.Position = 512; $fs.Write($hdr,0,512); $fs.Flush(); $fs.Close()
    'Written. Verifying...'
    $fs = New-Object IO.FileStream("\\.\PhysicalDrive$Disk", [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
    $v = New-Object byte[] 512; $fs.Position = 512; [void]$fs.Read($v,0,512)
    $c = [BitConverter]::ToUInt32($v,16); $t = [byte[]]$v.Clone(); [Array]::Clear($t,16,4)
    "Entry pointer: $([BitConverter]::ToUInt64($v,72)), header CRC valid: $([Crc32f]::Of($t,0,$hs) -eq $c)"
} catch { "ERROR: $($_.Exception.Message)" } finally { if ($fs) { $fs.Close() }; Stop-Transcript | Out-Null }
