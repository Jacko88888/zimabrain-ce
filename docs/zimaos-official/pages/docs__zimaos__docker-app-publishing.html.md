# Build Apps | Zimaspace Docs

Source: https://www.zimaspace.com/docs/zimaos/docker-app-publishing.html

Build Apps | Zimaspace Docs

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

Build Apps

ZimaOS Docker Application Adaptation Manual

How to publish applications to ZimaOS

Docker App publishing and adaptation tutorial

PC application compilation and online tutorial

Cloud application migration tutorial

ZimaOS Docker App Checklist and recommended configuration

Modular milestone: Prioritize application upgrades without restarting

Application tendency judgment

Preliminarily predict the application adaptation workload, whether it can be adapted directly, whether it is necessary to build the image yourself, etc.

Generally speaking, the official website of the application can be roughly divided into the following three tendencies:

Docker self-deployment

Difficulty: 🌟

Features: The official website or GitHub gives priority to providing self-deployment options.

For example: LocalAI, OpenWebUI and Nextcloud, etc.

It means that the developer of this application is likely to develop and test in a self-deployment environment. It also means that this application has self-deployment experience from the original developer and the community, and is generally easier to adapt.

It is very likely that an AIO image with minimal configuration will be provided directly, and then we can directly configure it.

PC self-deployment

Difficulty: 🌟🌟🌟

Features: The official website or GitHub gives priority to providing downloads to Win/Mac/Linux, but the main interface is provided through WebUI.

For example: AUTOMATIC1111/stable-diffusion-webui

Represents the installation process of this application, which will be verified by developers and the community. But there may not be a suitable Docker image, because this is not a priority when the project starts.

If there is no ready-made docker image available, it will be relatively easy for us to package it as a Docker image ourselves, because there is almost no need to worry about errors in the installation process. Just configure the required environment and pre-install the dependencies.

Cloud Service

Difficulty: 🌟🌟🌟🌟🌟

Features: The official website or GitHub recommends that you use the cloud services they provide, and also provides a way to self-deploy. Usually the application is also described as an all-round XX platform that can solve a variety of needs.

For example: Dify, TaskingAI, etc.

The developers of this application generally give priority to the deployment environment of the cloud cluster, and they are likely to give priority to development based on container orchestration environments such as K8s. The self-deployment options provided are usually built through docker compose or k8s. The startup of a complete application involves multiple container services and multiple images. At the same time, a large number of environment variables and even external files are required to enable the application to start normally.

This type of application requires a lot of effort to learn the various service relationships required for the application startup process, as well as the meaning and setting methods of a large number of environment variables. At the same time, if it exceeds the application capabilities of ZimaOS, it will be relatively difficult to build an image by yourself, because you need to understand the specific configuration methods of the various technology stacks used by this program.

Understand the application components

Analyze which duplicate services the application depends on, the impact of different configurations, and what users need to care about.

Analyze service requirements

Usually, each application has its own independent front-end and back-end, and may rely on some common services such as

Various databases: mysql, redis, pg, etc.

Various shared APIs:

LLMs: Ollama, LocalAI, LM Studio

……

Since shared services and pre-installed/recommended dependencies are not supported at this stage,
For App Developer / Adaptor:
Consider giving priority to AIO out-of-the-box images when adapting or consider packaging the required services in an image or compose
For ZimaOS Developer:
Consider supporting pre-installed and recommended dependencies

Analyze data storage requirements

Temporary file directories generated when the application is running

Persistent file directories required when the application is restored/migrated

File directories that users need to manage/use

After understanding clearly, perform corresponding initialization mapping according to the data directory structure defined by ZimaOS, and inform users of the directories they need to care about through appropriate tips.

Analyze port requirements

What are the WebUI service ports, HTTP/HTTPS

Usually they can be freely allocated by the system, and changes will not affect normal use

Some applications may have specific requirements for such ports, which need to be identified

API ports

Many application ports that expose APIs are conventional, and the original ports need to be used first, and then automatic allocation should be considered

When necessary, users need to be informed through tips

For example, 113114 of Ollama

What are the ports that have special purposes and must exist, such as DNS

Some ports have specific purposes and must be allocated, otherwise the core functions will fail

For example, the DNS port used by adguard, etc.

Application-specific auxiliary function ports

Some ports that should have their own special purpose ports, used for intranet discovery, etc.

These ports must use the original ports, otherwise the auxiliary functions will fail

Since ZimaOS does not support flexible port allocation at this stage,
For App Developer / Adaptor:
Consider configuring ports and tips according to application characteristics during adaptation
For ZimaOS Developer:
Consider supporting a defined port allocation mechanism

Analyze device requirements

GPU requirements

CPU requirements

USB device requirements

…

Consider setting the required devices when adapting, and consider whether you can fallback to the CPU when the GPU is unavailable.

Since ZimaOS does not support flexible device allocation at this stage,
For App Developer / Adaptor:
Consider configuring devices and tips according to application characteristics during adaptation
For ZimaOS Developer:
Consider supporting a defined device allocation mechanism, as well as a detection and feedback mechanism for device requirements.

Analyze runtime requirements

nvidia

…

This type is rare, but it is recommended to understand the corresponding runtime requirements when adapting, configure them, and write them in the tips appropriately

Read the official self-deployment solution

Prioritize learning the official best practices when adapting

The official self-deployment solutions and documents usually contain some excellent practical cases and deployment techniques, which can be read in advance to speed up adaptation.

Adapted to ZimaOS Docker App

Now you can integrate the information you learned before and adapt it to the ZimaOS App.

When you start writing, you can refer to the previously applied files to start writing:
https://github.com/IceWhaleTech/CasaOS-AppStore/tree/main/Apps

Write docker-compose.yaml

According to the definition, add application metadata in the x-casaos field

The multi-language field has at least en_us, because this is the fallback field.

Prepare icons and screenshots, and fill in the corresponding links in the x-casaos field.

Test the installation

Submit to GitHub

x-casaos Field Definition
x-casaos:
architectures: # List of architectures supported by the application
- amd64
- arm
- arm64
main: syncthing # The name of the main service under `services`
author: CasaOS team
category: Backup
description: # Support multiple languages
en_us: Syncthing is a continuous file synchronization program. It synchronizes files between two or more computers in real time, safely protecting your data from prying eyes. Your data belongs only to you, and you have the right to choose where to store it, whether to share it with third parties, and how to transfer it over the Internet.
developer: Syncthing
icon: https://cdn.jsdelivr.net/gh/IceWhaleTech/CasaOS-AppStore@main/Apps/Syncthing/icon.png
tagline: # Support multiple languages
en_us: Free, secure and distributed file synchronization tool.
thumbnail: https://cdn.jsdelivr.net/gh/IceWhaleTech/CasaOS-AppStore@main/Apps/Jellyfin/thumbnail.jpg
title: # Support multiple languages
en_us: Syncthing
tips:
before_install:
en_us: |
(Some notes that users need to read before installation, such as the default `user name` and `password` - support markdown format!)
index: / # The index page of the web interface, for exampleindex.html
port_map: "8384" # Port for the web interface

Field Description

Descriptions

Detailed description

Tagline

Try to express the essence in one line.

Icon and screenshot requirements

Icon

Give priority to using the SVG image of the official logo

Usually in the header of the official website

Secondary use of PNG images

If there is no Icon, find a designer to draw it

Screenshot

Give priority to using the screenshot provided by the official

Secondary use of the screenshot taken during runtime

Design intervention

The designer decides whether to intervene in the modification

Other tips

The container needs to access other host ports

If you run other services on the host (that is, localhost), such as Chroma, LocalAi, or LMStudio, you need to use http://host.docker.internal:xxxx to access the host service from the docker container, because localhost:xxxx will not be able to resolve the host system.
You can add an extra_hosts in docker-compose.yaml
services:
theapp: #Services that need to access other services on the host
······
······
······
extra_hosts:
- "host.docker.internal:host-gateway"

Using graphics card and nvidia runtime

If you need to use an external Nvidia graphics card inside Docker, you need runtime, ipc and env.
services:
open-webui-ollama:
image: ghcr.io/open-webui/open-webui:ollama
runtime: nvidia
ipc: host
environment:
CPU_FALLBACK: "true"
NVIDIA_VISIBLE_DEVICES: all

Runtime:
Runtime refers to where the container runs. The default is runc. There are several common ones.

kata-runtime, runs containers with virtual machines

Windows Container Runtime runs windows containers

NVIDIA allows external GPUs to be used in containers
IPC

Allows containers to use the host system’s IPC mechanisms, such as shared memory, semaphores, and message queues.

Containers can perform IPC communications with other processes on the host system.

Ref

https://developer.nvidia.com/container-runtime

How to handle the default configuration file
Reference: https://docs.docker.com/compose/compose-file/08-configs/

Use $$xxx instead of $xxx to avoid the file content being recognized as an environment variable
Reference: https://docs.docker.com/compose/compose-file/12-interpolation/

Use self-built images for pre-configuration

For apps that require more configuration files or more environment variables, self-built images can easily and conveniently mount the required configuration files to the host for use by other images, avoiding the situation where the image cannot obtain the correct configuration due to mounting the file as a directory or the loss of environment variables, resulting in startup failure or abnormal operation.

Reference: https://github.com/Ns2Kracy/dify-config

Create a configuration file and place it in the configs directory

Create and write entrypoint.sh
#!/bin/sh

CONFIG_PATH="/configs"
RAW_CONFIG_PATH="/raw_configs"
CONFIGED_FLAG="/configs/.configed"

if [ ! -f $CONFIGED_FLAG ]; then
if [ ! -d $CONFIG_PATH ]; then
echo "Creating config directory"
mkdir -p $CONFIG_PATH
fi

# Copy the raw config files to the config path
echo "Copying $RAW_CONFIG_PATH to $CONFIG_PATH"
cp -r $RAW_CONFIG_PATH/* $CONFIG_PATH

# Create the flag file
echo "Creating configed flag"
touch $CONFIGED_FLAG
else
echo "Config directory already exists"
fi;

tail -f /dev/null

Write a Dockerfile FROM alpine:latest

COPY entrypoint.sh /entrypoint.sh
COPY configs /raw_configs

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

Build the image docker build -t yourname/yourimage:yourtag .

Local testing docker run

Release the image docker login
docker push docker.io/yourname/yourimage:yourtag

Add a self-built image to the Docker App and make other images depend on this image version: '3.8'

services:
initservice:
image: yourname/yourimage:yourtag
container_name: initservice
volumes:
- type: bind
source: /path/on/host
target: /configs

otherservice:
image: otherimage:latest
depends_on:
- initservice

Magic Values

Note : These features are only available in CasaOS 0.4.4 and newer. To solve some situations, CasaOS provides some magic values ​​to enhance your application:

Environment variables Your application can read environment variables set by the user, such as reading OPENAI_API_KEY from the environment variable. These variables are stored in /etc/casaos/env . Users only need to set it once and use it everywhere. It can be changed through the API, and after the change, all applications will be restarted to inject the new environment variables. Note: Changing the configuration will not change the environment variables of the current container. To set the environment variables, you should use the command line interface (CLI) to set it.

WEBUI_PORT Your docker-compose.yml can use WEBUI_PORT to set the Web UI port. CasaOS will assign an available port to your application. You can use it like this:
...
ports:
- target: 5230
published: ${WEBUI_PORT}
protocol: tcp
...
x-casaos:
architectures:
- amd64
- arm64
- arm
...
port_map: ${WEBUI_PORT}

or
...
ports:
- target: 5230
published: ${WEBUI_PORT:-5230}
protocol: tcp
...
x-casaos:
architectures:
- amd64
- arm64
- arm
...
port_map: ${WEBUI_PORT:-5230}

Note : WEBUI_PORT is only allocated once. It guarantees that the port is available when it is allocated. If the port is used by other applications, it will not reallocate a new port.
Two special features in CasaOS are explained here: the use of environment variables and the dynamic allocation of WEBUI_PORT. These features can help developers configure their applications more flexibly, especially when dealing with port allocation and sensitive information (such as API keys).
Last updated: 2026-06-09 Prev Next
Contents
ZimaOS Docker Application Adaptation Manual
Application tendency judgment
Docker self-deployment

PC self-deployment

Cloud Service

Understand the application components
Analyze service requirements

Analyze data storage requirements

Analyze port requirements

Analyze device requirements

Analyze runtime requirements

Read the official self-deployment solution

Adapted to ZimaOS Docker App
x-casaos Field Definition

Field Description
Descriptions

Tagline

Icon and screenshot requirements
Icon

Screenshot

Design intervention

Other tips

The container needs to access other host ports

Using graphics card and nvidia runtime

Use self-built images for pre-configuration

Magic Values

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
