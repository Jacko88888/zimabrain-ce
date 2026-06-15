# iSCSI usage tutorial | Zimaspace Docs

Source: https://www.zimaspace.com/docs/zimaos/iscsi-guide.html

iSCSI usage tutorial | Zimaspace Docs

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

iSCSI usage tutorial

iSCSI (Internet Small Computer System Interface) is a protocol for transmitting SCSI commands over a network, allowing storage devices to communicate over a network, similar to directly connected storage. It can virtualize storage resources, achieve centralized management, network sharing, and remote access, and is suitable for scenarios such as data centers, virtualized environments, and backup and recovery.
Through this tutorial, you will learn how to configure and use iSCSI in ZimaOS to improve storage management efficiency, simplify network storage architecture, and achieve flexible data access methods.

Prerequisites

The hard disk used is not in use

Confirm the client’s IQN

Operation steps

Server

Make sure your ZimaOS has been upgraded to 1.2.5 or above.

Use the command sudo -i to enter superuser mode，Start targetcli targetcli

Create a LUN, assuming /dev/sde is used as the storage backend(Here we use sde. You can use the lsblk to view the device status and change to sda or sdb ..): cd backstores/block
create myblockdev /dev/sde

Create an iSCSI target ( iqn.2024-10.com.zima:target1 is an example) cd /iscsi
create iqn.2024-10.com.zima:target1

Add a LUN to the target cd iqn.2024-10.com.zima:target1/tpg1/luns
create /backstores/block/myblockdev

Set the ACL (access control list) to allow the connection. The IQN here needs to be consistent with the client(Open iSCSI Initiator, it is in the Configuration tab) cd ../acls
create iqn.1993-08.org.debian:01:bb1e6772dfb6

Client

Windows

Open iSCSI Initiator, in the Discovery tab, click Discover Portal

Configure the IP address, click OK

In the Targets tab, click Connect

Open Computer Management, click Storage > Disk Management, and you can see the newly connected iSCSI volume

Linux

Discover iSCSI targets iscsiadm -m discovery -t sendtargets -p <IP_ADDRESS>

Replace <IP_ADDRESS> with the IP address of the server

Log in to the iSCSI target iscsiadm -m node --login

Last updated: 2026-06-09 Prev Next
Contents
Prerequisites

Operation steps
Server

Client

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
