# SMB Help Document | Zimaspace Docs

Source: https://www.zimaspace.com/docs/zimaos/smb-troubleshooting.html

SMB Help Document | Zimaspace Docs

Zima-Docs

ZimaOS

ZimaCube

ZimaBoard

Forum

English

中文

日本語

Português

Español

Store

SMB Help Document

Core issues

- Incorrect authentication method: entered directly smb://IP When connecting, the system defaults to using anonymous or system users, resulting in authentication failure and excessively long connection response times.
- MacOS 14. x version cache issue: After the first authentication fails, even if the correct account and password are entered later, the connection cannot be established. You must bypass macOS cache by entering a username with inconsistent case to re authenticate. For example, if the correct account password is zimaos/zimaos , first input
smb://zimaos: [email protected] /ZimaOS-HD (password error) after failure, enter again
smb://zimaos: [email protected] /ZimaOS-HD still unable to connect. must enter
smb://Zimaos:zimaos @10.0.0.99/ZimaOS-HD (or continue to change the case of the username).

Server SMB service status check

Ensure that the SMB service on the server has started properly.

When the server is not started, Windows and macOS will display corresponding error prompts.

When entering the wrong username for anonymous login, the folder appears blank.

When entering the correct username but entering the wrong password, there will be a password error prompt.
2.The current connected account name can be determined through commands to confirm the login status.

Client solution

Windows 10/11

Clear existing connection records:

net use \\%IP%\ /delete /y

Example: net use \\10.0.0.99\ /delete /y

Save connection credentials:

cmdkey /add:% IP% /user:%USERNAME% /pass:%PASSWORD%

Example: cmdkey /add:10.0.0.99 /user:zimaos /pass:zimaos

Map network drivers:

net use \\%IP%\ /USER:% USERNAME% %PASSWORD% /PERSISTENT:YES

Example: net use \\10.0.0.99\ /USER:zimaos zimaos /PERSISTENT:YES

Windows connection SMB script:

You can combine the above commands into a batch file for easy and quick execution.
Windows connection smb script
`@echo off
echo Please enter the following details:
set /p IP=Enter IP Address:
set /p USERNAME=Enter Username:
set /p PASSWORD=Enter Password:

:: Delete previous network drive if exists
net use \%IP%\ /delete /y

:: Save credentials using cmdkey
cmdkey /add:%IP% /user:%USERNAME% /pass:%PASSWORD%

:: Map the network drive
net use \%IP%\ /USER:%USERNAME% %PASSWORD% /PERSISTENT:YES

:: Open the network share
start explorer \%IP%\

:: Pause for a moment to allow explorer to open the folder
timeout /t 2 /nobreak > NUL

:: Refresh the folder window using PowerShell
powershell -Command “
Add-Type -TypeDefinition @’
using System.Runtime.InteropServices;
public class WinAPI {
[DllImport("user32.dll")]
public static extern bool SendMessage(IntPtr hWnd, int Msg, IntPtr wParam, IntPtr lParam);
}
‘@
$HWND = (Get-Process | Where-Object { $_.MainWindowTitle -match ‘%IP%’ }).MainWindowHandle
if ($HWND -ne [IntPtr]::Zero) {
[WinAPI]::SendMessage($HWND, 0x0111, [IntPtr]0x702C, [IntPtr]0)
} else {
Write-Host "Window not found."
}
“

echo Commands executed successfully.
pause`

MacOS

Connect using Finder:

Press Command+K to open the ‘Connect Server’ window.

Input smb://USERNAME:PASSWORD @IP/PATH .

Example: smb://zimaos:zimaos @1.0.0.99/ZimaoS-HD .

Resolve macOS 14. x cache issue:

If the first authentication fails, try changing the case of the username, for example: smb://Zimaos:zimaos @1.0.0.99/ZimaoS-HD .
Last updated: 2026-06-09 Prev Next
Contents
Core issues

Server SMB service status check

Client solution
Windows 10/11

MacOS

Back to Top

What's Zima

Overview

Install Guide

Get Started

Features

Remote Access

Thunderbolt PC Direct

Explore

Sync Photos with Immich

Media Server Setup with Jellyfin

NVR Camera Server

Share via SAMBA

Sync Photos via Configurable CLI

Connect with Cloud Drives

Build Multiple Clones using rsync

Data Migration

ZFS Setup

More RAID Options

Migrate all Files!

Enable SSH

Docker App's Paths

Plex Operation Guide

Share via link

Download Large Language Model

Recover Your Password

Get Network ID

Achieve Fastest Transfer Speed

Samba with Multi-User

Download and Install ZimaClient

Create Raid6

Immich Tutorial

iSCSI usage tutorial

Setup Emby Server

Pi-hole

Deploy Radarr

System Quick Recovery Guide

Setting Up ZimaCube as DLNA Server

Time Machine Features

NFS on ZimaOS

Deploy Deepseek R1

iSCSI on ZimaOS

ZimaOS QTS Two-Way Sync Guide

SMB Help Document

ZimaOS-Search work

Rebuilding RAID after reinstalling the system

AI Description with ZimaOS

Enable AI Search

Enable Intel AX210

3-2-1 Backup

Migrate from CasaOS to ZimaOS

UPS Setup

ISO on PVE

Deploy OpenClaw

Deploy Hermes

Dev

Install Guide

Networking

Setup Python

Build Apps

7th Bay LED

Update offline

Disk Format Supported

Community Makes

How to Contribute

Implemented User-Suggested Drivers

Syncthing Install Guide

Paperless-ngx Install Guide

Paperless‑AI Install Guide

AzuraCast Install Guide

Zabbix Install Guide

Version Logs

v 1.5.1

v 1.5.0

v 1.4.4

v 1.4.3

v 1.4.2

v 1.4.1

v 1.4.0

v 1.3.3

v 1.3.2

v 1.3.1

v 1.3.0

v 1.2.5

v 1.2.4

v 1.2.3

v 1.2.2

FAQ

UPS Compatibility List

Encryption Folder

Reset Network Settings

Keep in touch _

Join our subscribers list to get the latest news, updates and special offers.

Subscribe

Products

ZimaCube

ZimaBoard

ZimaBlade

Accessories

CasaOS

Resource

ZimaSpace

Blog

Support

Discord

Community

Contact

Refund Policy

Privacy Policy

Terms of Service

Shipping Policy

Explore

Gallery

Made with IceWhale

Community

About Us

Blog

Distributors

Affiliate

© 2020-2024 IceWhale Technology Limited. All rights reserved.

ZimaOS

ZimaCube

ZimaBoard

Forum

What's Zima

Overview

Install Guide

Get Started

Features

Remote Access

Thunderbolt PC Direct

Explore

Sync Photos with Immich

Media Server Setup with Jellyfin

NVR Camera Server

Share via SAMBA

Sync Photos via Configurable CLI

Connect with Cloud Drives

Build Multiple Clones using rsync

Data Migration

ZFS Setup

More RAID Options

Migrate all Files!

Enable SSH

Docker App's Paths

Plex Operation Guide

Share via link

Download Large Language Model

Recover Your Password

Get Network ID

Achieve Fastest Transfer Speed

Samba with Multi-User

Download and Install ZimaClient

Create Raid6

Immich Tutorial

iSCSI usage tutorial

Setup Emby Server

Pi-hole

Deploy Radarr

System Quick Recovery Guide

Setting Up ZimaCube as DLNA Server

Time Machine Features

NFS on ZimaOS

Deploy Deepseek R1

iSCSI on ZimaOS

ZimaOS QTS Two-Way Sync Guide

SMB Help Document

ZimaOS-Search work

Rebuilding RAID after reinstalling the system

AI Description with ZimaOS

Enable AI Search

Enable Intel AX210

3-2-1 Backup

Migrate from CasaOS to ZimaOS

UPS Setup

ISO on PVE

Deploy OpenClaw

Deploy Hermes

Dev

Install Guide

Networking

Setup Python

Build Apps

7th Bay LED

Update offline

Disk Format Supported

Community Makes

How to Contribute

Implemented User-Suggested Drivers

Syncthing Install Guide

Paperless-ngx Install Guide

Paperless‑AI Install Guide

AzuraCast Install Guide

Zabbix Install Guide

Version Logs

v 1.5.1

v 1.5.0

v 1.4.4

v 1.4.3

v 1.4.2

v 1.4.1

v 1.4.0

v 1.3.3

v 1.3.2

v 1.3.1

v 1.3.0

v 1.2.5

v 1.2.4

v 1.2.3

v 1.2.2

FAQ

UPS Compatibility List

Encryption Folder

Reset Network Settings

English English 中文 日本語 Português Español
