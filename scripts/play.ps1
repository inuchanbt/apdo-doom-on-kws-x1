# SPDX-License-Identifier: GPL-2.0-or-later
param([switch]$NoBrowser,[int]$Port=0,[string]$UsbPort='')
. "$PSScriptRoot\env.ps1"
$taskArgs=@("$PSScriptRoot\pc-controller.py",'--port',"$Port")
if ($NoBrowser) {$taskArgs+='--no-browser'}
if ($UsbPort) {$taskArgs+=@('--usb-port',$UsbPort)}
& $env:KWS_PYTHON @taskArgs
