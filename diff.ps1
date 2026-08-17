$ErrorActionPreference='Stop'
# Load backend routes (col 3 = path)
$bk=@{}
Get-Content C:\tmp\getszy-audit\backend_routes.txt | ForEach-Object {
  $parts=$_ -split "`t"
  if ($parts.Count -ge 3) { $bk[$parts[2]] = $true }
}
# Normalize: replace uuid/int/slug segments with *
function Norm($p){
  $segs=$p.TrimEnd('/') -split '/'
  $out=@()
  foreach($s in $segs){
    if ($s -match '^\{?[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-') { $out += '*' }
    elseif ($s -match '^\{?[^/]+\}$') { $out += '*' }   # {id} style
    elseif ($s -match '^[0-9a-f]{24}$') { $out += '*' }  # mongo id
    elseif ($s -match '^[0-9]+$') { $out += '*' }
    else { $out += $s }
  }
  return ($out -join '/')
}
# Build normalized backend set
$bkN=@{}
$bk.Keys | ForEach-Object { $bkN[(Norm $_)] = $true }
# Load frontend calls (col 3 = path), strip query
$calls=Get-Content C:\tmp\getszy-audit\frontend_calls.txt | ForEach-Object {
  $parts=$_ -split "`t"
  if ($parts.Count -ge 3){
    $p=$parts[2] -split '\?' | Select-Object -First 1
    [PSCustomObject]@{file=$parts[0]; method=$parts[1]; path=$p}
  }
}
$missing=@()
$seen=@{}
foreach($c in $calls){
  $np=Norm $c.path
  # exact or normalized match?
  $ok = $bk.ContainsKey($c.path) -or $bkN.ContainsKey($np)
  if (-not $ok -and -not $seen.ContainsKey($np)) {
    $seen[$np]=$true
    $missing += "$($c.method)`t$np`t$($c.file)"
  }
}
"=== FRONTEND CALLS WITH NO BACKEND ROUTE (candidate dead tabs) ==="
$missing | Sort-Object -Unique
"COUNT: " + ($missing|Sort-Object -Unique).Count
