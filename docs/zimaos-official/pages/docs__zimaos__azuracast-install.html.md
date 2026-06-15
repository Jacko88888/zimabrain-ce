# A Comprehensive Guide to Installing AzuraCast on ZimaOS via the Command Line | Zimaspace Docs

Source: https://www.zimaspace.com/docs/zimaos/azuracast-install.html

A Comprehensive Guide to Installing AzuraCast on ZimaOS via the Command Line | Zimaspace Docs

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

A Comprehensive Guide to Installing AzuraCast on ZimaOS via the Command Line

This guide is adapted from the original article, A Comprehensive Guide to Installing AzuraCast on ZimaOS via the Command Line , by community member Muditha Liyanagama . We extend our sincere thanks for their work.

Introduction

AzuraCast is a powerful, self-hosted, all-in-one web radio management suite. It allows you to run multiple online radio stations, manage playlists, configure AutoDJ, and explore many other creative broadcasting options.

Previously, I wrote a guide on installing AzuraCast using the ZimaOS GUI. However, after further testing, I found that the GUI method is unstable, and AzuraCast’s web updater does not function properly when installed that way.

In this guide, I’ll show you a more reliable method: installing AzuraCast on ZimaOS using the command line. This approach is significantly more stable, and web updates work correctly.

This tutorial is intended for home or private use, accessible within your local network or via Tailscale. If you plan to expose your AzuraCast instance to the public internet, you may need to configure additional network and security settings.

This method has been tested on both Zimaboard 1 and Zimaboard 2 .

Let’s get started.

Step 1: Enable Developer Mode and SSH Access

Go to ZimaOS Settings → General → Developer mode

Click View

Enable SSH Access

Click Web-based terminal

A new browser tab will open with the ZimaOS terminal interface.

Step 2: Log In to the Terminal as Root

In the terminal:

Enter your login username → press Enter

Enter your password → press Enter

Type: sudo -i

Press Enter

Enter your password again → press Enter

Now you are logged in as the root user.

Step 3: Create the AzuraCast Installation Directory

AzuraCast should be installed inside the AppData directory.

1. Go to your AppData folder

(Example path — yours may differ)

cd /ZimaOS-HD/AppData

2. Create an AzuraCast directory

mkdir azuracast

3. Enter into the directory

cd /ZimaOS-HD/AppData/azuracast

Step 4: Download and Run the AzuraCast Installer

Run the following commands:
curl -fsSL https://raw.githubusercontent.com/AzuraCast/AzuraCast/main/docker.sh > docker.sh
chmod a+x docker.sh
./docker.sh install

This will start the AzuraCast installation inside the current directory.

During installation, you’ll be asked to select several options, including port numbers.
Recommendation : Keep all default values unless you are confident about changing them.

Once the installation finishes, AzuraCast services and the web updater will be deployed.

Step 5: Fix Port Conflicts (If Any)

If any required ports are already in use, the installer will display an error showing which ports are conflicting.

1. Stop AzuraCast services

docker compose down

Wait until all services stop.

2. Edit the Docker Compose file

nano docker-compose.yml

When editing:

Change only the left-hand side ( published ports )
Do NOT change the right-hand side ( target ports )

Example:
8080:80 ← change 8080 if needed, keep 80

3. Save the file

Press:

Ctrl + X

Y

Enter

4. Redeploy AzuraCast

docker-compose up -d

You may need to repeat this process multiple times, because Docker usually reports port conflicts one at a time. After fixing one conflict, it may detect another.

Once all conflicts are resolved, AzuraCast will fully deploy.

Step 6: Access the AzuraCast Web Interface

Open your browser and go to:

http://YOUR_SERVER_IP:80

If you changed the published port, replace 80 with your chosen port number.

Important Things to Keep in Mind
There are a few limitations when using this method:

This installation cannot be managed via the ZimaOS GUI .

Editing or stopping it from the GUI may cause crashes.

ZimaOS dashboard will not display CPU or RAM usage for AzuraCast.

All management and troubleshooting must be done via the command line or third party app with GUI such as Portainer .

However, despite these limitations:

This installation method is much more stable

AzuraCast web updates work correctly

Better suited for long-term personal or home radio servers
Last updated: 2026-06-09 Prev Next
Contents
Introduction
Step 1: Enable Developer Mode and SSH Access

Step 2: Log In to the Terminal as Root

Step 3: Create the AzuraCast Installation Directory
1. Go to your AppData folder

2. Create an AzuraCast directory

3. Enter into the directory

Step 4: Download and Run the AzuraCast Installer

Step 5: Fix Port Conflicts (If Any)
1. Stop AzuraCast services

2. Edit the Docker Compose file

3. Save the file

4. Redeploy AzuraCast

Step 6: Access the AzuraCast Web Interface

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
