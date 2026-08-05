# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
#
# Chocolatey's auto-uninstaller handles MSI removal via the product code
# recorded at install time; this script is a safety net that removes any
# geocog MSI still registered in Add/Remove Programs.
$ErrorActionPreference = 'Stop'

$packageArgs = @{
  packageName   = 'geocog'
  fileType      = 'msi'
  silentArgs    = "/qn /norestart"
  validExitCodes = @(0, 3010, 1605, 1614, 1641)
}

[array]$key = Get-UninstallRegistryKey -SoftwareName 'geocog*'
if ($key.Count -eq 1) {
  $key | ForEach-Object {
    $packageArgs['silentArgs'] = "$($_.PSChildName) /qn /norestart"
    $packageArgs['file']       = ''
    Uninstall-ChocolateyPackage @packageArgs
  }
} elseif ($key.Count -eq 0) {
  Write-Warning "geocog has already been uninstalled."
}
