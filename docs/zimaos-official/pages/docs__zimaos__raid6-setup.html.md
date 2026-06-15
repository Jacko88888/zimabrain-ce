# How to Create Raid6 on ZimaOS? | Zimaspace Docs

Source: https://www.zimaspace.com/docs/zimaos/raid6-setup.html

How to Create Raid6 on ZimaOS? | Zimaspace Docs

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

How to Create Raid6 on ZimaOS?

Introduction

Currently, ZimaOS supports RAID0/1/5, but we understand that many users require RAID6 for enhanced redundancy. To address this, we’ve prepared a step-by-step guide for creating RAID6 through the command line. Please follow the instructions below.
We look forward to accelerating our support for more RAID levels in the future!
Tips
If the system is rebooted, you’ll need to reassemble the RAID6 array.

Prerequisites

You will need at least four hard drives.

You need to learn how to get to the command line page by clicking on this .

You need to run the commands in the tutorial with superuser privileges (root privileges). You can use sudo to elevate privileges, such as sudo mkfs.ext4 /dev/md0

Use the command lsblk to check the available hard drives.

If MOUNTPOINTS has a mount point, you need to cancel it with the following command.

umount /dev/sda

Steps to Create RAID6

Create the RAID6 array with at least four drives using the following command:
mdadm -Cv /dev/md0 --level=6 --name=foldername --raid-devices=4 /dev/sda /dev/sdb /dev/sdc /dev/sdd --run --homehost=zimaos

/dev/md0 is the name of the new RAID device.

--level=6 indicates you’re creating a RAID6 array.

--name=foldername specifies the name of the RAID array.

--raid-devices=4 tells the system to use four hard drives.

/dev/sda /dev/sdb /dev/sdc /dev/sdd are the drives participating in the array.

Format the RAID using the following command:
mkfs.ext4 /dev/md0

Create a directory for mounting the RAID:
cd /media
mkdir foldername

Mount the RAID using the following command:
mount -t ext4 /dev/md0 /media/foldername

Once created, enter the path in the web-based File to display it

Notice:

If the system is rebooted, you’ll need to reassemble the RAID6 array:
mdadm -Av /dev/md0 /dev/sda /dev/sdb /dev/sdc /dev/sdd
mount /dev/md0 /media/foldername
Last updated: 2026-06-09 Prev Next
Contents
Introduction

Prerequisites

Steps to Create RAID6

Notice:
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
