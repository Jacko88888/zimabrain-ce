# Link Synology and SMB Shares | Zimaspace Docs

Source: https://www.zimaspace.com/docs/zimaos/synology-smb-connect.html

Link Synology and SMB Shares | Zimaspace Docs

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

Link Synology and SMB Shares

How to Share and Get files from a NAS? SAMBA may be the most important way

When we talk about Network Attached Storage, we want our files be stored, managed in one place and be accessed from every place. But how is that going?

You can always access your data by visiting ZimaOS’ WebUI, which has a beautifully organized interface and a fluent experience. However, when your work involves files referring, or you need a more complex operation on file system hierarchy, mounting your NAS drives to your client system through technologys like SMB/SAMBA will be a better way.

SMB (Server Message Block) is a protocol built into the Windows system for sharing files and other services over the network. SAMBA implements the SMB protocol, which enriches the file sharing methods of *nix-like systems. ZimaOS is equipped with SAMBA, making file sharing and transfer very convenient. In the following content, we will describe both SMB and SAMBA as SMB for convenience purposes.

Create a shared folder on ZimaOS

Launch the Files app on ZimaOS’ dashboard and find the destination folder that carries the files you want to share. Right click on the folder and select Share.

A dialogue window will prompt you with the URLs you need to mount shared folder on corresponding systems.

These two URLs are for pro users to manually mount drives. Additionally, with Zima client on corresponding systems, we can make the mounting process easier.

Mount your SMB shared folder on Windows

Download Zima-latest setup.exe from findzima and open it. It will boot the installation process and Zima client will be launched automatically after installation. You will find the Zima icon to the right of your taskbar, which is shown as a question mark due to the state of being unconnected.
Right click the icon and select Scan and Connect to Zima.

Locate your Zima device and click Connect.

Zima.exe will prompt you to enter your WebUI’s username and password to log in. After that, your zima.exe icon will turn from a question mark into a ZIMA mark, which means your zima.exe has entered a logged in status.

Right click on the zima icon and select Open in File Explorer, which will mount your shared folder to your Windows system and open it up automatically!
Manually mount zimacube under Windows

Temporary mount

Click on this computer.

Enter “\Device Intranet IP” in the address bar, which is the IP address of zimacube

Enter the network credentials

After verification, Windows SMB mount is completed

Mount as a network hard disk
This method is suitable for personal computers. When your computer and zimacube are in the same LAN, the mount is completed automatically, and when you select “Remember my credentials”, you can avoid the password verification step and log in permanently without a password; the disadvantage is that each folder needs to be mounted separately and repeated operations are performed. For example: when you want to mount “My Files” and “A Certain File Group” at the same time, you need to mount them separately

Open “My Computer”, right-click “My Computer” and select “Map Network Drive”.

Enter the IP address of your device and the name of the disk you want to mount

By default, “Reconnect at login (R)” is checked, and the folder will be automatically mounted after booting, without manual operation; it is recommended to check “Use other credentials to connect”, because Windows logs in through the local account of the current computer by default. If it is not checked, you may encounter a situation where you cannot change the user name;

Enter the user name and password

Mount through “Add a network location”
This method of mounting is not recommended. Under certain operations, Windows will clear the files in your folder, causing unnecessary data loss.
Note: to work properly, your Windows and ZimaOS need be in the same local area network(LAN).

Mount your SMB shared folder on macOS

Like above, we have also prepared a zima app for Mac users on findzima . The usage of the Mac zima app is pretty the same as the Windows one. Just refer to the content above.

Do you recall what Files app prompts you when you finish creating a shared folder? On macOS, we will use the URLs you just get for manually mounting!

Open Finder on your mac and press CMD+K, then copy paste the corresponding URL to the input box.

Click Connect. For now, on the prompt dialogue, choose Guest and click Connect.

For ZimaOS v1.2.3 users, choose Registered User and input the correct username and password.

Now, you will get your shared folder opened up and it will be listed on the left column of the Finder app.

How about the URL for Windows Explorer? What is the differences between zima automating mounting and mannually mounting the drive via URL?

Currently our SMB sharing uses the Guest account. In future versions, we will introduce multiple users to the sharing function and strengthen permission management. We hope these can meet more diverse needs of everyone.

Not just LAN

In fact, not only on LAN, but also on direct network and WAN, you can easily connect your Zima device and map the shared directory as a network drive. We will release relevant tutorials. Thank you for your continued attention.

If you encounter any issues during use, feel free to let us know at any time. You can also join our community and Discord to discuss more about NAS and ZimaOS. We look forward to your feedback!
Last updated: 2026-06-09 Prev Next
Contents
Create a shared folder on ZimaOS

Mount your SMB shared folder on Windows

Mount your SMB shared folder on macOS

Not just LAN
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
