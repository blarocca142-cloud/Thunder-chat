$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$dir = Join-Path $here "gradle\wrapper"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$out = Join-Path $dir "gradle-wrapper.jar"
Write-Host "Downloading gradle-wrapper.jar..."
Invoke-WebRequest -Uri "https://github.com/gradle/gradle/raw/v8.9.0/gradle/wrapper/gradle-wrapper.jar" -OutFile $out
Get-Item $out | Format-List FullName, Length
Write-Host "Done. Close Android Studio and open this folder again:"
Write-Host $here
