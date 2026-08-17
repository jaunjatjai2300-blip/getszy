$ErrorActionPreference='Stop'
$dir='C:\tmp\getszy-audit\legacy-getszy\frontend\src'
$pat1 = @'
api\.(get|post|put|delete|patch)\(\s*['"]([^'"]+?)(?=['"]|\$\{)
'@
$pat2 = @'
api\.(get|post|put|delete|patch)\(\s*[`]([^`]+?)(?=[`]|\$\{)
'@
$out=@()
Get-ChildItem -Path $dir -Recurse -Include *.jsx,*.js | ForEach-Object {
  $file=$_.FullName
  $rel=$file.Substring($dir.Length+1)
  $lines=Get-Content -Path $file
  for ($i=0;$i -lt $lines.Count;$i++){
    $l=$lines[$i]
    if ($l -match $pat1) { $out += "$rel`t$($Matches[1].ToUpper())`t$($Matches[2])" }
    if ($l -match $pat2) { $out += "$rel`t$($Matches[1].ToUpper())`t$($Matches[2])" }
  }
}
$out | Sort-Object -Unique | Set-Content -Encoding utf8 C:\tmp\getszy-audit\frontend_calls.txt
"TOTAL frontend api calls (unique): " + ($out|Sort-Object -Unique).Count
