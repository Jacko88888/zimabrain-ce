# How to setup an emby server on ZimaOS? | Zimaspace Docs

Source: https://www.zimaspace.com/docs/zimaos/setup-emby-server.html

How to setup an emby server on ZimaOS? | Zimaspace Docs

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

How to setup an emby server on ZimaOS?

John, a movie enthusiast, wanted to build his dream home theater. However, he struggled to organize his growing collection of films and TV shows across multiple devices.
He found existing solutions either too complex to set up or lacking the performance needed for smooth playback. That’s when he discovered Emby, a powerful media server that not only simplified his setup but also enhanced his viewing experience.
However, like many users, John faced challenges with certain configurations and features. This article explores how pairing Emby with ZimaOS or CasaOS can solve these challenges. It shows how users like John can build a seamless and efficient home theater system.

About Emby Media Server

Emby Media Server is a powerful tool for managing personal video, audio, TV shows, and movie content. It organizes local and online media into easy-to-browse libraries, supporting multi-device access and streaming.
Emby allows you to share content across devices and ensures smooth playback with its powerful transcoding features. It also supports add-ons for automatic downloads, metadata updates, and subtitles.
As a home theater solution, Emby offers flexible options and an easy streaming experience.

Deployment convenience: from installation to use

In today’s home theater environment, the convenience of deploying and using a media server is essential. For ZimaOS, users can install and deploy it in a simple way. ZimaOS makes installation easy by allowing you to download and install directly from the App Store. Unlike other complex server software, it eliminates the need for tedious configuration steps.

Quick Deployment Guide

Search for Emby
We provide two versions of the app:
Normal version : This version lacks support for discrete graphics cards (GPU).
GPU version : This version is designed to work with dedicated GPUs. Its offering enhanced performance for demanding tasks and smoother media processing.

You can choose to download and install the corresponding version according to your personal needs. Here we choose the normal version.

Set Language

Create a User and set a Password

Configure Remote Access and check Enable automatic port mapping

Complete the Configuration

Content management through Files

Import your film and television resources into the corresponding folder (here we use media/movies as an example)

In emby, click Settings in the upper right corner and scroll down to find Library

Click New Library and follow the steps below to configure our media library

Click Add to add a media library folder

Select the appropriate folder as the media library folder in Folder

Select the appropriate Language and country, and Enable real-time monitoring of changes to files by default.

Enable Import collection information from metadata downloaders , it will import collection information from enabled metadata downloader.

Choose the Option that best suits your needs.

Note:
The above options are the best configurations we recommend based on various requirements. You can choose the configuration options that suit you according to your specific needs.
Here are three options for managing media images:

Save media images to media folder : Places images next to the media files, allowing easy access outside Emby.
2.** Keep a cached copy in the metadata folder**: Stores images in a server folder for quick access.

Pre-download images from the internet : Downloads images before displaying the media in Emby.

This completes the creation of the media library

Now we have created our own media library. Click Home on the left to enter the homepage and watch our film and television resources.

If you have an external storage device that you want to use on ZimaCube, you can refer to the following method:

Connect and mount the external disk to ZimaCube
First, connect your external disk to ZimaCube. Make sure the device can recognize the disk and mount it correctly. Use the ZimaOS management interface or command line to confirm the successful connection of the external disk.

Configure Emby to use an external disk

Find the target folder in the external disk and check the address

Configure this address to Emby

After re-entering Emby, click Add to create a media library folder. This will allow you to locate and select the address of the external storage.

Transcoding performance

Transcoding in Emby Server is resource-intensive, especially for high-quality videos. Despite hardware-accelerated transcoding (e.g., Intel Quick Sync, NVIDIA NVENC), challenges include:

Compatibility : Some GPUs may not work with Emby.

Resources : High-resolution videos need strong CPU/GPU power, risking slowdowns or crashes.

Efficiency : Speed varies with GPU, drivers, and settings.

Improving Performance

Enable hardware acceleration in Emby settings.

Optimize settings like video quality and resolution.

Monitor usage with tools like intel-gpu-top.

ZimaBlade vs. ZimaCube

ZimaCube excels in high-resolution transcoding with its powerful GPU, while ZimaBlade is better for basic video playback.
ZimaCube

ZimaBlade

Summarize

In this tutorial, you’ve installed and configured Emby, enabling you to manage and play your media content. To enhance your experience, you can pair Emby with tools like:

Sonarr : Automatically finds, downloads, and updates TV episodes.

Radarr : Manages and updates your movie collection.
These tools keep your library up to date, saving time and effort.

You can access your media on multiple devices:

On TV : Download the Emby app from your smart TV app store. Connect it using your server’s IP address, then start watching.

On mobile : Download the Emby app for Android or iOS. Connect using your server’s IP or the auto-search feature to start enjoying your media.
Emby helps you create a private multimedia cloud, offering easy access to your content anytime, anywhere.
Last updated: 2026-06-09 Prev Next
Contents
About Emby Media Server

Deployment convenience: from installation to use
Quick Deployment Guide

Content management through Files

Transcoding performance
Improving Performance

ZimaBlade vs. ZimaCube

Summarize
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
