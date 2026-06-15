# ZimaOS & QTS Two-Way Sync Guide | Zimaspace Docs

Source: https://www.zimaspace.com/docs/zimaos/zimaos-qts-two-way-sync-guide.html

ZimaOS & QTS Two-Way Sync Guide | Zimaspace Docs

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

ZimaOS & QTS Two-Way Sync Guide

Real-World Pain Point: Cross-NAS Synchronization Challenges

A user recently asked: “Our team uses both ZimaOS and QNAP QTS systems. Manually transferring files consumes 2+ hours daily. How can we automate bidirectional sync?” This guide solves this exact problem.

Why WebDAV + Zerotier?

Figure 1: Architecture of cross-system file synchronization via WebDAV and Zerotier

Keywords: ZimaOS and QTS Two-Way Sync

WebDAV : Cross-platform file collaboration protocol

Zerotier : Virtual LAN tool for NAT traversal without public IP requirements

Advantages : Easy configuration, automatic sync and resumable sync

Step-by-Step Implementation

Step 1: Configure WebDAV on ZimaOS

Install App : Search “WebDAV” in ZimaOS App Store

Critical Parameters (Figure 2):

Credentials: Default casaos

Sync Directory: Select target folder via “Choose Directory Icon”(second red circle)

Port: Note custom port (e.g., 5005 )

Figure 2: ZimaOS WebDAV configuration interface

Step 2: Establish Zerotier Network

Get Network ID :

ZimaOS Dashboard → Settings → Network → Remote access → Enable → Click “NetworkID” to copy

Install Zerotier and enable SSH. (Related resources can be found at the bottom of the article)

QNAP Configuration :

SSH into QTS and run:
zerotier-cli join [ZimaOS NetworkID]

Verify Connectivity :

Get ZimaOS Zerotier IP: Network → Virtual Network → Static IP

Test with ping [ZimaOS Zerotier IP]

Step 3: Create HBS 3 Sync Task

Setup Sync :

Install “HBS 3” from QTS App Center

Launch HBS 3 and Select Snyc → Two-Way Sync Job → Add WebDAV account

Optimization :

Choose ‘conflict policy’ to rename local files

Set ‘job schedule frequency’ to 30 ~ 300s

Conclusion & Resources

You’ve achieved:
✅ Real-time cross-system sync
✅ NAT penetration without public IP
✅ Automated files two-way sync
If you encounter any issues during use, feel free to let us know at any time. You can also join our community and Discord to discuss more about NAS and ZimaOS. We look forward to your feedback!

Further Reading:
Zerotier Official Manual for QNAP
Enabled SSH access on QNAP
Keep Files Synced Between ZimaOS and Synology DSM
Last updated: 2026-06-09 Prev Next
Contents
Real-World Pain Point: Cross-NAS Synchronization Challenges

Why WebDAV + Zerotier?
Keywords: ZimaOS and QTS Two-Way Sync

Step-by-Step Implementation
Step 1: Configure WebDAV on ZimaOS

Step 2: Establish Zerotier Network

Step 3: Create HBS 3 Sync Task

Conclusion & Resources
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
