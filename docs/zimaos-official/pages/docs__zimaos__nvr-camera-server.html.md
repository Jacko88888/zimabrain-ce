# NVR Camera Server | Zimaspace Docs

Source: https://www.zimaspace.com/docs/zimaos/nvr-camera-server.html

NVR Camera Server | Zimaspace Docs

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

NVR Camera Server

Introduce

This tutorial will guide you through how to create a home video surveillance system on CasaOS using Kerberos.io and ZimaBoard. We will use CasaOS’s Docker custom installation feature to simplify the installation and configuration process, and will also explain in detail how to configure an RTSP camera.

1. Preparation

ZimaBoard X 1

Make sure the ZimaBoard is connected to power and the Internet, and CasaOS is installed

RTSP-compatible IP camera

2. Get the RTSP link of the camera

Since different manufacturers’ cameras have different ways of getting the RTSP link, please refer to your camera’s user manual or the manufacturer’s official website for relevant instructions, or log in to the camera’s management interface to find the RTSP link. In this tutorial, we successfully tested TP-Link and Tuya brand cameras and verified their compatibility with Kerberos.io. In addition, we expect the system to be compatible with cameras from brands such as Hikvision, Ezviz, Dahua, eufy, and Yousee.

3. Configure Kerberos.io

Step 1: Log in to CasaOS

Make sure ZimaBoard is connected to power and the internet, and CasaOS is installed.

Access the CasaOS web interface (usually http:// ).

Step 2: Install Docker using CasaOS

Open the App Store

Click Custom Installation

Click Import

Paste the following code to configure Docker into the input field
version: ‘3’ # Docker Compose file version

services:
kerberos:
image: kerberos/kerberos # Use the kerberos/kerberos image
container_name: kerberos # Container name
ports:
- “8080:80” # Map host port 8080 to container port 80
volumes:
- ./config:/config # Mount the host’s config directory to /config in the container
- ./recordings:/etc/opt/kerberosio/capture # Mount the host’s recordings directory to /etc/opt/kerberosio/capture in the container
restart: unless-stopped # Container restart policy: restart automatically unless stopped manually
environment:
- TZ=Europe/London # Set the container’s timezone to Europe/London
- KERBEROSIO_SETTINGS_PORT=80 # Set the Kerberos service listening port to 80
- KERBEROSIO_SETTINGS_RECORDSTREAM=”/config/recordings” # Set the recording stream location to /config/recordings

5. Click Submit
6. Fill in ‘tag’: latset and ‘title’: kerberos

7. Submit and wait for the installation to complete

Step 3: Configure Kerberos.io

Open http:// :8080 in your browser to enter the Kerberos.io settings interface.

Create an account and password and log in to Kerberos.io.

Click ‘Configuration’

Select ‘IP camera’

Enter the obtained RTSP URL, for example: rtsp://admin: Hjj12345@10.0.171.52 /stream1.

Configure the resolution and frame rate, for example: 720x480.

After the configuration is completed, you can view the captured images and videos in the Kerberos interface

You can also view the monitoring status in real time on the main interface

This system is suitable for users who need to monitor a specific area in real time, especially in home and small office scenarios. Although the system currently only supports the configuration of a single camera, its easy installation, efficient performance and good brand compatibility make it a reliable monitoring solution.
Last updated: 2026-06-09 Prev Next
Contents
Introduce
1. Preparation

2. Get the RTSP link of the camera

3. Configure Kerberos.io
Step 1: Log in to CasaOS

Step 2: Install Docker using CasaOS

Step 3: Configure Kerberos.io

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
