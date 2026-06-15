# Getting Started with iSCSI on ZimaOS | Zimaspace Docs

Source: https://www.zimaspace.com/docs/zimaos/iscsi-setup.html

Getting Started with iSCSI on ZimaOS | Zimaspace Docs

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

Getting Started with iSCSI on ZimaOS

ZimaOS offers a variety of network sharing protocols to meet different storage and file-sharing needs, including NFS, SAMBA, and iSCSI:

NFS (Network File System) : Ideal for file sharing in Unix/Linux systems, it supports high-concurrency access and cross-platform file sharing.

SAMBA : It offers excellent compatibility. Supporting advanced permission management and encrypted transmission, it is an ideal choice for cross-platform environments.

iSCSI (Internet Small Computer System Interface) : Maps remote storage devices to local disks via IP networks, making it suitable for high-performance block storage scenarios, such as virtualization environments and database storage.

These network sharing protocols ensure users can choose the most suitable solution based on their needs.

This tutorial provides a guide on how to configure and use iSCSI on ZimaOS, helping you quickly achieve efficient block storage sharing. Before start, let’s explain a few concepts.

Target, targetcli and iSCSI Initiator.

A target is what you will set up on the server side. Here the server is ZimaOS . And targetcli is the tool that you use to do the set up.

On the client machine, you need to use the iSCSI Initiator to connect to your target on the server. In this tutorial, we will take Windows as an example.

ZimaOS Side

Set up iSCSI Target

First, you need to enter the ZimaOS web terminal and obtain the root privilege.

ZimaOS dashboard -> Settings -> General -> Developer mode -> Web-based terminal

Log in and switch to root sudo -i
lauch targetcli targetcli
Now, you are in targetcli />
Create a target:
Navigate to iscsi directory /> cd iscsi
create an iSCSI target /iscsi> create
↓This is the output: Created target iqn.2003-01.org.linux-iscsi.zimacube.x8664:sn.66390bd598df.
Created TPG 1.
Global pref auto_add_default_portal=true
Created default portal listening on all IPs (0.0.0.0), port 3260.
You might need to remoeve the target oneday,this operation will remove the entire target,including all ACLs, LUNs, and portals /iscsi> delete iqn.2003-01.org.linux-iscsi.zimacube.x8664:sn.66390bd598df
Also, you can specify a name creating a target: /iscsi> create iqn.2025-03.com.icewhale:888
↓This is the output Created target iqn.2025-03.com.icewhale:888.
Created TPG 1.
Global pref auto_add_default_portal=true
Created default portal listening on all IPs (0.0.0.0), port 3260.

Backstore and Creation

iSCSI Backstores are created for storage use by the target. First, let’s enter the backstores directory.
Navigate to backstores
/> cd /backstores

There are four types of backstore.
Creating backstore with a file:
/backstores> cd fileio
/backstores/fileio> create file1 /media/myRAID5/disk1.img 200M write_back=false
Created fileio file1 with size 209715200

↑This is the system output
Creating backstore with a block storage object:
/backstores> cd block
/backstores/block> create name=block_backend dev=/dev/sdf

Created block storage object block_backend using /dev/sdf.

↑This is the output
You can use lsblk to identify block devices.
Creating backstore with other types:
Creating backstore with pscsi storage object
/backstores> cd pscsi
/backstores> create name=pscsi_backend dev=/dev/sr0

or creating backstore with RAM
/backstores> cd ramdisk
/backstores> create name=rd_backend size=1GB

LUN links the target and backstores

Enter luns of one iqn
/> cd /iscsi/iqn.2025-03.com.icewhale:888/tpg1/luns

link the backtore to this target
/iscsi/iqn.20...888/tpg1/luns> create /backstores/fileio/file1

Ctreated LUN 0

↑This is the output

Access Control Lists

We need to create an ACL to grant access for the initiator.
Navigate to iqn’s acls directory
/> cd /iscsi/iqn.2025-03.com.icewhale:888/tpg1/acls

Make this initiator_iqn_name accessable,you need to find or define the initiator_iqn_name on the client machine
/iscsi/iqn.20...888/tpg1/acls> create iqn.1991-05.com.microsoft:desktop-44sqg6u

↓This is the output
Created Node ACL for iqn.1991-05.com.microsoft:desktop-44sqg6u
Created mapped LUN 0.

Windows Side

On Windows, connecting to an iSCSI target is easy.

Type iSCSI Initiator in the search bar and click the prompting icon.

You might need to enable this function first according to the prompt window.

On the iSCSI Initiator Properties panel, you can find the initiator_iqn_name in the Configuration tab.

In the Targets tab, input the server’s IP and click Quick Connect... .
Choose the right name and click Connect .

In the search bar, type Disk Management and the Create and format... icon will prompt you. Click and enter, you will find the storage device just connected.

Initialize Disk and use it like a local disk!

For how to initialize disk on Windows, refer to this artical .
This is the basic use of targetcli . For detailed tutorial, refer to redhat docs . If you encounter any issues during use, feel free to let us know at any time. You can also join our community and Discord to discuss more about NAS and ZimaOS. We look forward to your feedback!
Last updated: 2026-06-09 Prev Next
Contents
Target, targetcli and iSCSI Initiator.

ZimaOS Side
Set up iSCSI Target

Backstore and Creation

LUN links the target and backstores

Access Control Lists

Windows Side
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
