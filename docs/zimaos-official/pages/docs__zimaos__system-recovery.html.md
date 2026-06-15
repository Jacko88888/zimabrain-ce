# ZimaOS System Quick Recovery Guide | Zimaspace Docs

Source: https://www.zimaspace.com/docs/zimaos/system-recovery.html

ZimaOS System Quick Recovery Guide | Zimaspace Docs

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

ZimaOS System Quick Recovery Guide

Introduction

ZimaOS is a lightweight NAS operating system that uses a dual-partition design (Slot A and Slot B), each partition is about 6GB in size. When one partition fails, you can easily switch to the backup partition to ensure that the system continues to run. This tutorial will guide you on how to switch to the backup partition when there is a problem with the system.

Preparation

Before you begin, make sure you have a monitor and keyboard connected.

Step by step guide:

Step 1: Boot the device

Power on the ZimaOS device.

Step 2: Enter the GRUB menu

When the system boots up, pay close attention to the screen display. Quickly press the ↑ and ↓ arrow keys on the keyboard to bring up the GRUB menu. The GRUB menu is displayed as follows:

Step 3: Select Boot Partition

Use the arrow keys to select the alternate partition you wish to boot from (e.g. if Slot A crashes, select Slot B).

Step 4: Boot Selected Partition

Press Enter to boot from the selected partition.

Now you can successfully enter the ZimaOS system

Tips

How do I know which partition I am currently in?

Run the terminal command rauc status and check the output to determine the currently booted partition.

In the output, booted indicates the currently booted partition.

Additional Notes:

Data safety:

Switching partitions will not affect user data, because ZimaOS user data is usually stored in a separate partition (such as /data).

Understanding menu options:

“OK=1” means the partition is in good condition, “TRY=1” or “TRY=0” indicates the number of times the partition has been tried to boot.

Rescue shell option is for advanced users to troubleshoot or repair the system, but it is not necessary to select it unless necessary.

Advanced operations:

Press the ‘e’ key to edit the boot command, and press the ‘c’ key to enter the command line mode for experienced users.

If you need further assistance or have other questions, please contact the ZimaOS team: feedback@zimaos.com .
Last updated: 2026-06-09 Prev Next
Contents
Introduction

Preparation

Step by step guide:
Step 1: Boot the device

Step 2: Enter the GRUB menu

Step 3: Select Boot Partition

Step 4: Boot Selected Partition

Tips

Additional Notes:
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
