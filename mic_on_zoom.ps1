
$python = "C:\Users\oranm\AppData\Local\Programs\Python\Python313\python\pythonw.exe"
$script = "C:\Users\oranm\AppData\Local\Programs\Python\Python313\python\mego\python\projects\mic_project.py"

function Get-ProcByCommandLine($needle) {
  $procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*$needle*" }
  return $procs
}

$zoomRunning = $false
try {
  $zoomRunning = (Get-Process -Name "Zoom" -ErrorAction SilentlyContinue) -ne $null
} catch {}

$micRunning = Get-ProcByCommandLine "mic_project.py"

# אם זום פתוח ואין mic -> מפעילים
if ($zoomRunning -and ($micRunning.Count -eq 0)) {
  Start-Process -FilePath $python -ArgumentList "`"$script`"" | Out-Null
}

# אם זום סגור ויש mic -> עוצרים
if (-not $zoomRunning -and ($micRunning.Count -gt 0)) {
  foreach ($p in $micRunning) {
    try { Stop-Process -Id $p.ProcessId -Force } catch {}
  }
}