$ErrorActionPreference = "Stop"

$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $projectPath ".venv\Scripts\python.exe"
$siteUrl = "http://127.0.0.1:8000"
$logPath = Join-Path $projectPath "website-server.log"
$errorLogPath = Join-Path $projectPath "website-server-error.log"

function Test-SitePort {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync("127.0.0.1", 8000)
        return $task.Wait(500) -and $client.Connected
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

if (-not (Test-Path -LiteralPath $pythonPath)) {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show(
        "Hindi makita ang Python environment ng website.",
        "MB Future Tech AI",
        "OK",
        "Error"
    ) | Out-Null
    exit 1
}

if (-not (Test-SitePort)) {
    Start-Process `
        -FilePath $pythonPath `
        -ArgumentList @("-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000") `
        -WorkingDirectory $projectPath `
        -WindowStyle Hidden `
        -RedirectStandardOutput $logPath `
        -RedirectStandardError $errorLogPath

    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Milliseconds 500
        if (Test-SitePort) {
            $ready = $true
            break
        }
    }

    if (-not $ready) {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show(
            "Hindi nag-start ang website. Tingnan ang website-server-error.log.",
            "MB Future Tech AI",
            "OK",
            "Error"
        ) | Out-Null
        exit 1
    }
}

Start-Process $siteUrl
