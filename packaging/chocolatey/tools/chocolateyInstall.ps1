# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
#
# Downloads and silently installs the official geocog MSI release asset.
# __URL64__ and __CHECKSUM64__ are injected by the release workflow.
$ErrorActionPreference = 'Stop'

$packageArgs = @{
  packageName    = 'geocog'
  fileType       = 'msi'
  url64bit       = '__URL64__'
  checksum64     = '__CHECKSUM64__'
  checksumType64 = 'sha256'
  silentArgs     = '/qn /norestart'
  validExitCodes = @(0, 3010, 1641)
}

Install-ChocolateyPackage @packageArgs
