# More RAID Options | Zimaspace Docs

Source: https://www.zimaspace.com/docs/zimaos/raid-options.html

More RAID Options | Zimaspace Docs

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

More RAID Options

RAID Array Setup

RAID (Redundant Array of Independent Disks) is a technology that combines multiple hard drives to improve both data storage reliability and performance . It distributes data across multiple drives to achieve higher read and write speeds, and can maintain data integrity even if some drives fail.
JBOD simply combines multiple disks into one continuous logical volume, thereby maximizing the use of total capacity.

In ZimaOS, complex RAID configurations are simplified into an intuitive user experience.
Whether creating or maintaining a RAID array, you don’t need cumbersome commands or configurations — the setup can be completed in just three steps .

Supported Storage Combination Options:

Currently, ZimaOS supports the following RAID levels and JBOD configuration. Each option has unique advantages and ideal use cases:

RAID 0 (Fast) : Focuses on maximum speed and capacity, but offers low security.

RAID 1 (Safe) : Provides high redundancy through mirroring, suitable for critical data.

RAID 5 (Balanced) : Offers a good balance of performance, capacity, and single-disk failure tolerance.

RAID 6 (Stability) : Enhances RAID 5 with dual parity, providing better protection against two-disk failures.

JBOD (Flexible) : Treats disks as independent units or concatenates them to maximize flexibility and capacity, with no redundancy.

For easier comparison, the table below summarizes the key features of each option (speed and capacity percentages are relative to using individual disks; actual performance depends on hardware configuration):

Detailed Steps to Create RAID 5:

RAID 5 is ideal for users seeking a balance of storage efficiency, performance, and single-drive failure protection. It requires at least three disks. Below is a step-by-step guide for creating a RAID 5 array using the updated ZimaOS UI.

Navigate to Storage Settings Open the Settings interface. Go to the Storage tab. Here, you will see a list of current disks and available operations.

Click the “Combine” button to enter the disk combination menu.

Select the RAID 5 option , then click “Next.”

Select three available disks . The system will calculate the estimated capacity, then click “Next.”

Configure and name the array : Enter a name for the array (e.g., “RAID5”), check the desired protocols, then click “Create” to begin initialization.

Creation complete : The system will perform data striping, monitor the progress until finished, and display the array status as “Healthy.”

You can now use RAID 5! After creation, parity will be enabled automatically. During this process, disk read speeds may be affected, but normal usage will not be interrupted.

Others:

Other RAID creation : The steps for RAID 0, 1, and 6 are similar, differing only in the selected option and minimum number of disks. For example, RAID 6 requires at least four disks and provides dual-failure tolerance.

ZFS support : For users whose needs are not met by the default RAID options, ZimaOS also supports the ZFS file system. Please refer to the ZFS section in the official ZimaOS documentation or use command-line tools for setup: https://www.zimaspace.com/docs/zimaos/ZFS-Setup .

FAQ:

Why does creating a RAID take a long time?

It is affected by the capacity and performance of the hard drives.

How should I choose?

Choosing the right RAID level depends on your storage needs: RAID 0 prioritizes speed, RAID 1 emphasizes safety, RAID 5 offers a balance of performance and protection, while RAID 6 is suitable for high-reliability scenarios. For quick comparison, the table below summarizes the descriptions, best uses, and key features of these levels to help you make an informed decision.

Conclusion

With the new visual RAID wizard in ZimaOS, you can achieve the optimal storage solution with minimal effort—just three clicks to easily complete RAID configuration, without complex commands, and enjoy high-performance, highly reliable storage.

We strongly recommend pairing this with the 3-2-1 backup strategy (keeping three copies of your data, using two different media types, and ensuring at least one copy is stored offline) to further guard against accidental data loss and keep your valuable files safe. Learn more here .

If you encounter any questions, technical issues, or need further guidance during use, feel free to reach out to our official support team via direct message: X platform or Facebook . We promise a quick response within 48 hours, along with professional, personalized assistance.

Thank you for using ZimaOS! If this guide has been helpful, please share your feedback to help us improve.
Last updated: 2026-06-09 Prev Next
Contents
RAID Array Setup
Supported Storage Combination Options:

Detailed Steps to Create RAID 5:

Others:

FAQ:

How should I choose?

Conclusion

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
