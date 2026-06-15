# How to understand Docker App's paths On ZimaOS | Zimaspace Docs

Source: https://www.zimaspace.com/docs/zimaos/docker-app-paths.html

How to understand Docker App's paths On ZimaOS | Zimaspace Docs

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

How to understand Docker App's paths On ZimaOS

Docker and ZimaOS

Docker is platform that enables users to automate the deployment, scaling, and management of applications in lightweight containers. These containers bundle an application with all its dependencies, ensuring consistent performance across various environments. Docker’s efficiency lies in its ability to isolate applications, making them more portable and scalable.

ZimaOS is really impressive when we talk about Docker apps, streamlining the process with just a few clicks. ZimaOS is also a game-changer for NAS enthusiasts, pro users and studio users. Its intuitive interface simplifies data backup and management.

But do you really understand the path when using Dockers apps on ZimaOS? Can you distinguish between the ZimaOS path and the Docker apps path?

How Docker Organizes Paths

When you run a Docker container, it operates within its own filesystem, separate from the host system. Here’s a general overview of how Docker organizes paths:

Container Filesystem: Inside a Docker container, the file system is isolated from the host machine. Applications running in a container see their own root filesystem, which typically starts from /. For instance, if you have an application that stores data in /app/data within the container, this path exists solely within that container’s filesystem.

Volumes: To persist data beyond the lifecycle of a container, Docker uses volumes. Volumes are directories or files outside the container’s filesystem, usually located on the host system, and can be shared between containers. They are often mounted into containers at specific paths.

There are other data sharing modes, which you can learn here.

The Example of Plex

Let’s take plex, a popular media server application, as an example to understand how paths are organized within ZimaOS using Docker.

Docker App : Plex is distributed as a Docker app in ZimaOS’ app store. When you install Plex from ZimaOS’ app store, ZimaOS will specify several paths for various directories:

/config in container: this directory holds Plex’s configuration files. On ZimaOS, its volume path is /DATA/AppData/plex/config on ZimaOS, which is mounted to container’s /config to ensure configurations persist across container restarts.

/media in container: this is where Plex accesses your media files. Also, media files’ volume path is /DATA/Media on ZimaOS and it is mounted to containers’s /media.

Keep in mind that we want files stored in the host. This way, even if a container is stopped or recreated, the data remains intact.

You can find the detailed configuration by clicking Plex’s Settings. Besides, on this page, the volume path can be easily modified by clicking the grey icon next to the volume path.

By understanding Docker paths and how they integrate with applications like Plex, NAS enthusiasts and Homelabbers can efficiently manage their applications in a way that combines the flexibility of containerization with the reliability of persistent storage.
Last updated: 2026-06-09 Prev Next
Contents
Docker and ZimaOS

How Docker Organizes Paths

The Example of Plex
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
