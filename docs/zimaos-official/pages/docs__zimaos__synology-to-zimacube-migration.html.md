# From Synology to ZimaCube，migrate all files! | Zimaspace Docs

Source: https://www.zimaspace.com/docs/zimaos/synology-to-zimacube-migration.html

From Synology to ZimaCube，migrate all files! | Zimaspace Docs

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

From Synology to ZimaCube，migrate all files!

Welcome to the world of ZimaOS! I mean new friends who have come from other brand camps such as Synology, hello!

ZimaOS is a game-changer for NAS enthusiasts, pro users and studio users. Its intuitive interface simplifies data backup and management, ensuring your critical files are always secure. ZimaOS excels in Docker application installation, streamlining the process with just a few clicks.

We are honored that you have chosen ZimaCube as the first hardware to experience ZimaOS. In order to help everyone quickly transfer files from Synology devices to ZimaCube, we have prepared this tutorial.

Of course, transferring files to ZimaCube is very easy. Let’s get started.

This tutorial is also applicable to other devices with ZimaOS installed.

SMB/SAMBA will be our method

SMB (Server Message Block) is a protocol built into the Windows system for sharing files and other services over the network. SAMBA implements the SMB protocol, which enriches the file sharing methods of * nix-like systems.

Both ZimaOS and Synology DSM are well-implemented/compatible with SMB, whether through SAMBA or self-implementation, making file sharing and transfer very convenient.

Mount shares from DSM in ZimaOS

At the beginning of Synology setup, many users set up sharing when creating directories; some users did not give sharing function when creating directories. Therefore, before migrating, you may need to create a new shared directory and then move the data you want to migrate to this shared directory.

Go to the ZimaOS Dashboard and launch the Files App. Then, in the left navigation bar of the Files App UI, find the “+” sign next to Storage and click it, then click “LAN Storage”.

In the pop-up window, enter the Synology DMS IP Address. Mine is 10.0.0.11 here and you need to fill in the correct IP Address of your device. Now click the Connect button.

If your DSM shared account is not a Guest, but an account specifically set up with a user and password, you need to enter the correct DSM account and password here.

Copy and paste files from Synology DSM in ZimaOS

When you click the Connect button and successfully connect, Synology will appear as a network device under Storage. And on the right side, the shared directory of Synology will appear.

Go to the shared directory and select the files and directories we want to migrate. You can press Ctrl + A to select all files. Then, click the Copy button in the upper right corner.

Now enter the ZimaOS storage area. Go to the target directory and select the Paste xx items button in the upper right corner.

[

You need to ensure that the remaining capacity of the destination storage pool is greater than the total volume of the file to be copied and pasted.

Now, wait for the file migration to complete. After the migration is complete, please experience the convenience that ZimaOS brings to your data management!
Last updated: 2026-06-09 Prev Next
Contents
Welcome to the world of ZimaOS! I mean new friends who have come from other brand camps such as Synology, hello!
SMB/SAMBA will be our method

Mount shares from DSM in ZimaOS

Copy and paste files from Synology DSM in ZimaOS

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
