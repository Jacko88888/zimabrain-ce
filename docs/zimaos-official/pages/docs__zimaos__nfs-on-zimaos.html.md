# How to use NFS on ZimaOS | Zimaspace Docs

Source: https://www.zimaspace.com/docs/zimaos/nfs-on-zimaos.html

How to use NFS on ZimaOS | Zimaspace Docs

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

How to use NFS on ZimaOS

Network file sharing protocols allow you to share files and directories from your computer with other devices on the network. Common protocols include SAMBA, NFS, and FTP.
Advantages of network sharing:
Aspect USB Copy Messaging Apps Network Sharing Storage Local duplicates Multiple copies Centralized, no duplicates Management Manual, error-prone Scattered in chats Centralized control Media Usage Full copy required Full download needed Streaming support Collaboration Physical transfer File size limits Real-time multi-access
ZimaOS currently provides CLI and GUI support for SAMBA. In versions after 1.3.2, ZimaOS also integrates NFS functionality (at CLI level). This tutorial demonstrates how to use NFS on ZimaOS to share folders and access them from Windows, macOS, and Ubuntu.
You need to create or find a folder for sharing first. Here, I will use /DATA/C/demo as an example.

Edit the Configuration File

Use vi to edit the /etc/exports file, which is the configuration file for NFS.

Obtain root privileges
you need to enter the ZimaOS web terminal and obtain the root privilege.
ZimaOS dashboard -> Settings -> General -> Developer mode -> Web-based terminal
Log in and switch to root sudo -i

Edit the configuration file vi /etc/exports

In the /etc/exports, paste this line /DATA/C/demo *(rw,sync,no_subtree_check)
Note:

The first column specifies the shared folder(e.g., /DATA/C/demo)

The second column defines

The subnet that has the permission to access

e.g., 10.0.0.0/8

The * stands for allowing accessing from all networks

Allow Read and Write permission for network users(rw)

Writing Method, usually sync or async is taken (sync in this case)

No_subtree_check allows full access to the shared directory without subtree restrictions

Refer to this: https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/5/html/deployment_guide/s1-nfs-server-config-exports#s1-nfs-server-config-exports

It will work automatically, even after reboot.

Bring the Configuration File into Effect

In some cases,you may need to run this command in the shell to make the configuraion effective.
systemctl restart nfs-server

or
exportfs -a

Use（Mount/Unmount) the NFS Folders

On ZimaOS/Ubuntu

Tested on ZimaOS 1.3.2-beta2 and Ubuntu 22.04.5 LTS

Here on a client machine
open Terminal
switch to root first
make a dir for mounting sudo -i
mkdir /mnt/demo

mount the nfs folder
this ip is the Server’s IP mount 10.0.0.71:/DATA/C/demo /mnt/demo

Now you can view and use your sharing
you may want to remove the mounted NFS folders one day
Just check mounted folders df -h
or mount | grep nfs

unmount the nfs folders umount /mnt/demo

On macOS

Tested on macOS Sequoia on M4 Chip
make a directory for mounting mkdir ~/demo

mount the nfs folder
you need to use sudo to mount
it will prompt you to input the password sudo mount -t nfs -o resvport 10.0.0.71:/DATA/C/demo ~/demo

open the folder for using open .

you may want to remove the mounted NFS folders one day
Just check mounted folders df -h
or mount | grep nfs

unmount the nfs folders sudo umount /mnt/demo

On Windows

Tested on Windows 11

you may need enter to CMD first
since the terminal may place you in Powershell by default on Windows 11
cmd

You may need to change W: to an available character that is not occupied
mount \\10.0.0.71\DATA\C\demo W:

Now you can view and use your sharing

you may want to remove the mounted NFS folders one day
Just check mounted folders
net use

unmount the nfs folders
net use W: /delete

The screenshot after mounting on Windows:

Useful Tips

Here are some commands that you may need further.
On the ZimaOS server

check the status of nfs-service systemctl status nfs-server

remove or comment out the line of /etc/exports to disable sharing
run this to make it effective exportfs -a
or systemctl restart nfs-server

If you encounter any issues during use, feel free to let us know at any time. You can also join our community and Discord to discuss more about NAS and ZimaOS. We look forward to your feedback!
Last updated: 2026-06-09 Prev Next
Contents
Edit the Configuration File

Bring the Configuration File into Effect

Use（Mount/Unmount) the NFS Folders
On ZimaOS/Ubuntu

On macOS

On Windows

Useful Tips
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
