# How does ZimaOS-Search work | Zimaspace Docs

Source: https://www.zimaspace.com/docs/zimaos/zimaos-search.html

How does ZimaOS-Search work | Zimaspace Docs

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

How does ZimaOS-Search work

System Architecture Overview

Three-Layer Design

Real-Time File Monitoring Layer

Real-time detection of file system changes (creation/renaming/deletion)
Filename indexing (milisecond-level response)
File content indexing (processed uniformly during off-peak hours at midnight)

Asynchronous batch processing for index updates (separate coroutines for read, write, and delete operations)

Full audit at 12:00 AM daily to ensure eventual consistency

Intelligent Indexing Layer

Snowflake algorithm for generating document IDs (capable of generating 400,000+ IDs per second)

Automatic format recognition supporting over 70 file types

Multimodal Search Layer

Four-dimensional combined search:
Full-text search (name/content/tags/summary)
Filename fuzzy matching
Filename exact matching
Semantic search (currently supports images only)

Core Advantages

🚀Ultra-Fast Index Building

Test data: Total size 65.5GB, 200,000 files

Hardware configuration: 4-core N100 CPU, 500GB HDD
Metric Traditional Solution (Similar System) This system Improvement Multiple Notes File name indexing time 18 minutes 1.4 senconds 771x - File content indexing time (Office & PDF documents only) 1hour 23minutes 2 minutes 21 seconds 35.2x - Index memory usage 176MB 26MB 6.77x Reduces to 17MB after 1 minute of inactivity, releasing one service Index disk usage 156MB 28MB 5.6x - Number of background services 7 2 3.5x Reduces to 1 service after 1 minute of inactivity

💡Intelligent Resource Scheduling

On-demand loading mechanism : Model files are downloaded based on actual usage needs, enabling lightweight and fast startup

Dynamic throttling strategy :
Maximum documents processed per session: 100,000 per type
Maximum processing time: 5 minutes per type

Write barrier protection : Prevents CPU spikes caused by high-frequency writes

Use Cases

Knowledge Base Management : Quickly locate documents

Multimedia Archiving : Search for images/videos vy content

Compliance Auditing : Accurately track file change history

Team collaboration : Cross-format content association retrieval
Full-Text Search Supported Formats and Processing Methods Table
Category File Extensions Processing Method Notes Text Files .txt .md .log .htm .html .mht .mhtml .xml 1. Direct reading 2. HTML based on text density extraction Code files not indexed by default PDF Documents .pdf 1. Direct parsing with pdfium 2. Scanned copies use tesseract OCR Limit: ≤ 200 pages, OCR result ≤ 800KB E-books .epub .fb2 .djvu Convert to txt via doconverter djvu treated as scanned document Word Documents .doc .docm .docx .docxf .dot .dotm .dotx .fodt .odt .ott .oxps .rtf .stw .sxw .wps .wpt .xps Convert to docx via doconverter, then parse Supports all WPS formats Spreadsheet Documents .csv .et .ett .fods .ods .ots .sxc .xls .xlsb .xlsm .xlsx .xlt .xltm .xltx Convert to CSV via doconverter, then read - Presentation Documents .dps .dpt .fodp .odp .otp .pot .potm .potx .pps .ppsm .ppsx .ppt .pptm .pptx .sxi Convert to pptx via doconverter, then parse - IWork Documents .pages .numbers .key Convert via iwork2text (supports OCR recognition) - Images★ .bmp .raw .jpg .jpeg .jpe .jfif .png .gif .tif .tiff .webp .mat .pbm .pgm .ppm .pfm .pnm .fits .fit .fts .exr .hdr .v .vips OCR recognition using MiniCPM-o-2.6 model Limit: ≤20MB per image Videos★ .mp4 .wmv .mkv .avi .mov .webm .flv .mpeg .mpg .3gp .asf .rm .rmv .rmvb .m4v .swf Subtitle extraction using faster-whisper-large-v3 - Audio★ .mp3 .aac .wav .flac .ogg .m4a .aiff .wma .ape Speech-to-text using faster-whisper-large-v3 - CAD Document .dwg .dxf Metadata indexing only (content parsing not supported) - Compressed Files .zip .rar .7z .sz .xz .gz .tar .bz2 .br .zz .zst .lz4 Metadata indexing only (content decompression not supported) -
Note: Formats marked with ★ require the ZimaOS-AI module to be enabled. Full processing capability depends on hardware configuration. The system continuously updates the supported format list; refer to official documentation for the latest support.

🌐 AI-Enhanced Search

Image processing: MiniCPM-o-2.6 OCR + tag recognition

Audio/video processing: Whisper-large-v3 subtitle generation

Semantic analysis: MiniLM-L6 semantic vectorization

Reference document: Enable AI search for ZimaOS
Last updated: 2026-06-09 Prev Next
Contents
System Architecture Overview
Three-Layer Design

Core Advantages
🚀Ultra-Fast Index Building

💡Intelligent Resource Scheduling

Use Cases
🌐 AI-Enhanced Search

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
