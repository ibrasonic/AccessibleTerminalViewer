$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$staging = Join-Path $projectRoot "build\AccessibleTerminalViewer"
$dist = Join-Path $projectRoot "dist"
$archive = Join-Path $dist "AccessibleTerminalViewer-1.0.0.zip"
$package = Join-Path $dist "AccessibleTerminalViewer-1.0.0.nvda-addon"

if (Test-Path -LiteralPath $staging) {
	Remove-Item -LiteralPath $staging -Recurse -Force
}
New-Item -ItemType Directory -Path $staging | Out-Null
New-Item -ItemType Directory -Path $dist -Force | Out-Null

Copy-Item -LiteralPath (Join-Path $projectRoot "addon\manifest.ini") -Destination $staging
Copy-Item -LiteralPath (Join-Path $projectRoot "addon\installTasks.py") -Destination $staging
Copy-Item -LiteralPath (Join-Path $projectRoot "addon\globalPlugins") -Destination $staging -Recurse
Copy-Item -LiteralPath (Join-Path $projectRoot "doc") -Destination $staging -Recurse
Copy-Item -LiteralPath (Join-Path $projectRoot "LICENSE") -Destination $staging

if (Test-Path -LiteralPath $archive) {
	Remove-Item -LiteralPath $archive -Force
}
if (Test-Path -LiteralPath $package) {
	Remove-Item -LiteralPath $package -Force
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open(
	$archive,
	[System.IO.Compression.ZipArchiveMode]::Create
)
try {
	Get-ChildItem -LiteralPath $staging -File -Recurse |
		Where-Object {
			$_.Extension -ne ".pyc" -and
			$_.FullName -notmatch "[\\/]__pycache__[\\/]"
		} |
		ForEach-Object {
			$entryName = $_.FullName.Substring($staging.Length + 1).Replace("\", "/")
			[System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
				$zip,
				$_.FullName,
				$entryName,
				[System.IO.Compression.CompressionLevel]::Optimal
			) | Out-Null
		}
}
finally {
	$zip.Dispose()
}
Move-Item -LiteralPath $archive -Destination $package
for ($attempt = 1; $attempt -le 3; $attempt++) {
	try {
		Remove-Item -LiteralPath $staging -Recurse -Force
		break
	}
	catch {
		if ($attempt -eq 3) {
			throw
		}
		Start-Sleep -Milliseconds 250
	}
}
Write-Output "Created $package"
