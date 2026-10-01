# Scan every page from the scanner plugged into this computer, using Windows'
# own scanner service (WIA) - no scanner software needed. Each page is saved
# as a JPEG in the folder given, and its path printed on its own line.
# The Thunder Claims program reads them, sends them to Main encrypted, and
# deletes the folder. Errors are printed as "ERROR: ..." for the program.
param([Parameter(Mandatory = $true)][string]$OutDir, [int]$Dpi = 200)
$ErrorActionPreference = "Stop"
$JPEG = "{B96B3CAE-0728-11D3-9D7B-0000F81EF32E}"
try {
  $dm = New-Object -ComObject WIA.DeviceManager
  $scanners = @($dm.DeviceInfos | Where-Object { $_.Type -eq 1 })
  if ($scanners.Count -eq 0) { Write-Output "ERROR: No scanner found. Check it is plugged in and switched on, then try again."; exit 2 }
  $dlg = New-Object -ComObject WIA.CommonDialog
  # one scanner: use it; several: Windows asks which
  if ($scanners.Count -eq 1) { $dev = $scanners[0].Connect() } else { $dev = $dlg.ShowSelectDevice(1, $true, $false) }
  if (-not $dev) { Write-Output "ERROR: No scanner chosen."; exit 3 }
  # use the document feeder when there is one (3087 = capabilities, 3088 = select, 1 = feeder)
  $feeder = $false
  foreach ($p in $dev.Properties) {
    if ($p.PropertyID -eq 3087 -and ($p.Value -band 1)) { $feeder = $true }
  }
  if ($feeder) { foreach ($p in $dev.Properties) { if ($p.PropertyID -eq 3088) { try { $p.Value = 1 } catch {} } } }
  $item = $dev.Items.Item(1)
  foreach ($p in $item.Properties) {
    switch ($p.PropertyID) {
      6146 { try { $p.Value = 2 } catch {} }      # intent: greyscale - small files, readable text
      6147 { try { $p.Value = $Dpi } catch {} }   # horizontal dpi
      6148 { try { $p.Value = $Dpi } catch {} }   # vertical dpi
    }
  }
  $n = 0
  while ($true) {
    try {
      $img = $item.Transfer($JPEG)
    } catch {
      $code = $_.Exception.HResult
      if ($n -gt 0 -and ($code -eq -2145320957 -or $code -eq -2145320954)) { break }  # feeder empty / no more pages
      if ($n -eq 0 -and $code -eq -2145320957) { Write-Output "ERROR: The feeder is empty. Load the pages and try again."; exit 4 }
      if ($n -gt 0) { break }
      Write-Output ("ERROR: The scanner said: " + $_.Exception.Message); exit 5
    }
    $n++
    $path = Join-Path $OutDir ("page{0:D3}.jpg" -f $n)
    if ($img.FormatID -ne $JPEG) {
      $ip = New-Object -ComObject WIA.ImageProcess
      $ip.Filters.Add($ip.FilterInfos.Item("Convert").FilterID)
      $ip.Filters.Item(1).Properties.Item("FormatID").Value = $JPEG
      $ip.Filters.Item(1).Properties.Item("Quality").Value = 85
      $img = $ip.Apply($img)
    }
    $img.SaveFile($path)
    Write-Output $path
    if (-not $feeder) { break }   # flatbed: one page per click
    if ($n -ge 200) { break }
  }
} catch {
  Write-Output ("ERROR: " + $_.Exception.Message); exit 1
}
