$ErrorActionPreference='Stop'
$dir='C:\tmp\getszy-audit\legacy-getszy\backend'
$out=@()
$files = @(Get-ChildItem -Path $dir -Name routes_*.py) + @('server.py')
foreach ($file in $files) {
  $lines = Get-Content -Path (Join-Path $dir $file)
  $prefixMap=@{}
  for ($i=0;$i -lt $lines.Count;$i++){
    $l=$lines[$i]
    if ($l -match '(\w+)\s*=\s*APIRouter\(prefix=([''"])([^''""]*?)\2') {
      $prefixMap[$Matches[1]]=$Matches[3]
    }
    if ($l -match '@(\w+)\.(get|post|put|delete|patch)\(\s*([''"])((?:[^''""]|\$\{[^}]*\})*?)\3') {
      $var=$Matches[1]; $method=$Matches[2].ToUpper(); $p=$Matches[4]
      $px = if ($prefixMap.ContainsKey($var)) { $prefixMap[$var] } else { '' }
      if ($p.StartsWith('/')) {
        if ($px -and $p.StartsWith($px)) { $full=$p } else { $full=$px+$p }
      } else { $full=$px+'/'+$p }
      $out += "$file`t$method`t$full"
    }
  }
}
$out | Sort-Object -Unique | Set-Content -Encoding utf8 C:\tmp\getszy-audit\backend_routes.txt
"TOTAL backend routes: " + ($out|Sort-Object -Unique).Count
