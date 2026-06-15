# A Simple Guide to Installing Syncthing on ZimaOS | Zimaspace Docs

Source: https://www.zimaspace.com/docs/zimaos/syncthing-install.html

A Simple Guide to Installing Syncthing on ZimaOS | Zimaspace Docs

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

A Simple Guide to Installing Syncthing on ZimaOS

Originally published on the IceWhale Community Forum by Muditha Liyanagama (Community Contributor) : Source URL

Hello fellow ZimaOS and Zimaboard enthusiasts!

I’ve found that while the ZimaOS community and the Ice-whale team offer fantastic support, finding clear, organized, and detailed installation guides can sometimes be a challenge. For those of us who prefer a straightforward, step-by-step approach, especially when troubleshooting those tiny, frustrating issues, this guide is for you. This is the first in a series of articles I plan to write on ZimaOS and Zimaboard, and I hope it proves helpful.

I performed this installation on a Zimaboard2 with the following specifications:

CPU: Intel(R) N150 4 Cores 2.90 GHz 4 Threads

RAM: 16 GB 6400 MHz LPDDR5

GPU : Intel Corporation Alder Lake-N [Intel Graphics]

Operating System: ZimaOS v1.5.3 Plus

Let’s get Syncthing installed

Step 1: Accessing the App Store

Sign in to your ZimaOS interface.

Navigate to the App Store .

Step 2: Finding and Selecting Syncthing

In the App Store search bar, type Syncthing.

Select Syncthing (Backup) from the search results.

Step 3: Custom Installation

Locate the Install button. Instead of clicking it directly, click the small down arrow next to it.

Select Custom Install .

Step 4: Critical Configuration Before Installation

This is where we set up the essential parameters for Syncthing to work correctly.

Syncthing Folder Path:

This is the primary location where Syncthing will manage your synchronized files. Any subfolders you create within this path will be accessible for synchronization.

Important Note: You cannot use the root of any mounted disk or system folders (like Gallery, Media, Document, etc.) as your Syncthing folder path. This is because running Syncthing with these paths typically requires root user privileges, which is not recommended for security reasons.

PGID and PUID:

These are crucial identifiers that tell Syncthing which user permissions to use. Setting them incorrectly can lead to synchronization problems and may require a full uninstall and reinstall to fix.

How to find your PGID and PUID:

In ZimaOS, go to Settings .

Navigate to General .

Enable Developer mode .

Go to View .

Click on SSH Access to enable it.

Click on Web-based terminal .

Sign in using your ZimaOS username and password.

Once logged into the terminal, enter the following commands, pressing Enter after each. Remember to replace username with your actual ZimaOS username. id -u username id -g username

The output will display your PUID (User ID) and PGID (Group ID). Carefully copy and paste these numbers into the corresponding fields under the Environment Variables section in the Syncthing custom installation screen, as shown in the example image provided. For me, the PGID was 1000 and the PUID was 999.

Double-Check: Before proceeding, review all your settings very carefully . Ensure the Syncthing folder path is valid and that your PGID and PUID values are correctly entered.

Install: Once you are confident that all settings are correct, click the Install button.

Step 5: Post-Installation - Synchronization Best Practices

After Syncthing has been successfully installed:

When you are synchronizing folders, always create the destination folder path through Syncthing itself .

Do NOT create the destination folder directly using ZimaOS’s default file browser. Doing so can sometimes lead to unexpected synchronization issues.

I hope this detailed guide makes installing Syncthing on your ZimaOS device a smooth and successful experience! Happy synchronizing!
Last updated: 2026-06-09 Prev Next
Contents
Step 1: Accessing the App Store

Step 2: Finding and Selecting Syncthing

Step 3: Custom Installation

Step 4: Critical Configuration Before Installation

Step 5: Post-Installation - Synchronization Best Practices
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
