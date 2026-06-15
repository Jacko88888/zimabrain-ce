# ZimaBrain CE Quick Answer Quality Results

Review each answer for:
- Correct route
- Honest verification status
- Useful direct answer
- Safe next step
- No dangerous repair instruction without evidence

---

## 1. Should I run docker system prune to fix my containers?

### ZimaBrain Answer

## ❓ Question asked
### Should I run docker system prune to fix my containers?

#### Verification status
@@VERIFY:VERIFIED@@ ✅ VERIFIED FROM SAME-REPORT EVIDENCE
- This answer is based on evidence found in the current report.
- Active layer: Container Commands Layer
- Layer file: `app/brain/layers/container_commands.py`


#### Direct answer / severity
- This is a safe container command question.
- The answer comes from the Container Commands Layer.

### Verdict
- Use read-only Docker commands first.
- These commands check container state, names, images, health, ports, and recent logs without changing anything.
- Do not remove, recreate, prune, or restart containers until the exact container and issue are verified.

### Safe read-only commands
- Copy and paste these commands exactly as shown.
- Share the output before making any container changes.

```bash
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}'
docker compose ls
docker stats --no-stream
```

### Optional focused checks
- Use these when you already know the container name.
- Replace CONTAINER_NAME with the exact name from docker ps.

```bash
docker inspect CONTAINER_NAME --format '{{json .State}}'
docker logs --tail 120 CONTAINER_NAME
```

### What the commands verify
- `docker ps -a` shows running, exited, restarting, unhealthy, and created containers.
- `docker compose ls` shows Compose projects known to Docker.
- `docker stats --no-stream` gives a quick CPU/RAM snapshot.
- `docker inspect` shows the container state without modifying it.
- `docker logs --tail 120` shows recent logs only.

### What not to touch
- Do not run `docker system prune`.
- Do not remove containers in bulk.
- Do not recreate an app until the bind mounts and data paths are verified.
- Do not change compose files until the exact app folder is confirmed.

#### Next safest step
- Run the safe read-only Docker commands and review the output before restarting, removing, recreating, or pruning anything.

#### Forum-ready summary
Start with read-only Docker checks: docker ps -a for state, docker compose ls for projects, docker stats --no-stream for resource usage, then inspect/logs for one exact container if needed. Do not prune, remove, recreate, or restart anything until the exact container, bind mounts, and data paths are verified.

---

## 2. Can I delete the /media folders after ZimaOS made duplicate mounts?

### ZimaBrain Answer

## ❓ Question asked
### Can I delete the /media folders after ZimaOS made duplicate mounts?

#### Verification status
@@VERIFY:VERIFIED@@ ✅ VERIFIED FROM SAME-REPORT EVIDENCE
- This answer is based on evidence found in the current report.
- Active layer: Storage Mount Layer
- Layer file: `app/brain/layers/storage_mounts.py`


#### Direct answer / severity
- This is a mount / media path verification question.
- The answer comes from the Storage Mount Layer using host findmnt evidence, not from visible folders alone.

Active storage-related mounts from this report:
- /dev/nvme3n1p8 -> /DATA [ext4] rw
- /dev/nvme3n1p8[/.media] -> /media [ext4] rw
- /dev/nvme0n1 -> /media/Samsung SSD 990 PRO with Heatsink 2TB [btrfs] rw
- /dev/nvme0n1 -> /DATA/.media/Samsung SSD 990 PRO with Heatsink 2TB [btrfs] rw
- /dev/sdb -> /media/HDD-Storage-/dev/sdb [btrfs] rw
- /dev/sdb -> /DATA/.media/HDD-Storage-/dev/sdb [btrfs] rw
- /dev/nvme2n1 -> /media/Samsung SSD 980 PRO 2TB [btrfs] rw
- /dev/nvme2n1 -> /DATA/.media/Samsung SSD 980 PRO 2TB [btrfs] rw
- /dev/nvme1n1 -> /media/Samsung SSD 980 PRO 1TB [btrfs] rw
- /dev/nvme1n1 -> /DATA/.media/Samsung SSD 980 PRO 1TB [btrfs] rw
- /dev/sdd -> /media/sdc [iso9660] ro
- /dev/sdd -> /DATA/.media/sdc [iso9660] ro
- /dev/sdc1 -> /media/sdd1 [fuseblk] rw
- /dev/sdc1 -> /DATA/.media/sdd1 [fuseblk] rw
- /dev/sda -> /media/HDD-Storage [btrfs] rw
- /dev/sda -> /DATA/.media/HDD-Storage [btrfs] rw

How to interpret this:
- A visible folder under /media does not prove a disk is mounted there.
- Use active findmnt evidence before changing Docker app paths.
- Do not delete old-looking /media folders until they are confirmed not to be active mounts.

#### Next safest step
- Compare active findmnt mount paths against Docker bind paths before changing storage paths or deleting any /media folders.

#### Forum-ready summary
Based on the verified host mount evidence, storage paths should be trusted only when they appear as active mounts. Do not rely on visible /media folders alone, and do not change Docker bind paths until the exact active mount source is confirmed.

---

## 3. My sda has CRC errors, is the disk dying?

### ZimaBrain Answer

## ❓ Question asked
### My sda has CRC errors, is the disk dying?

#### Verification status
@@VERIFY:VERIFIED@@ ✅ VERIFIED FROM SAME-REPORT EVIDENCE
- This answer is based on evidence found in the current report.
- Active layer: Disk CRC Layer
- Layer file: `app/brain/layers/disk_crc.py`


#### Direct answer / severity
- This is a disk CRC warning question.
- The answer comes from the Disk CRC Layer using normalized dashboard evidence.

CRC-related dashboard evidence:
- 🟡 YELLOW: sda: CRC errors 8
- sda evidence: health=PASSED, temp=33°C, realloc=0, pending=0, crc=8, power_on=9325.

What CRC errors usually mean:
- CRC errors usually point to a communication/link issue between the drive and the controller, not automatic disk failure.
- The usual causes are SATA/SAS cable, loose connection, controller/HBA port, backplane path, or unstable power.
- With SMART health PASSED, reallocated sectors 0, and pending sectors 0, the current evidence points away from media/platter failure.

Most likely causes:
1. SATA/SAS data cable issue.
2. Loose connection at the drive, backplane, controller, or HBA.
3. Faulty controller/HBA/backplane port.
4. Power delivery instability.
5. Less common: drive interface issue, firmware issue, electrical noise, or connector heat/damage.

What to check:
- Monitor whether the CRC count stays at the same value or keeps increasing.
- If it stays at the same value, it may be an old link event.
- If it increases, power down, reseat the cable, try a known-good short cable, move to another port, and check power.

#### Next safest step
- Confirm whether the sda CRC count is increasing over time. If it increases, check cable, port, backplane, controller path, and power before blaming the disk.

#### Forum-ready summary
sda shows CRC errors, but SMART health still reports PASSED with no reallocated or pending sectors. This usually points to a SATA/SAS link issue such as cable, port, backplane, controller path, or power stability rather than a failing disk. Monitor whether the CRC count increases. If it does, reseat or replace the cable and try another port before considering disk replacement.

---

## 4. qBittorrent is not downloading after I changed paths

### ZimaBrain Answer

## ❓ Question asked
### qBittorrent is not downloading after I changed paths

#### Verification status
@@VERIFY:NOT VERIFIED@@ ❌ NOT VERIFIED
- The current report does not contain matching evidence to verify this answer.
- Active layer: App Runtime Diagnostics Layer
- Layer file: `app/brain/layers/app_runtime_diag.py`


#### Direct answer / severity
- This is an app runtime diagnostic question.
- Detected symptom: download failure
- Detected app: qbittorrent
- qbittorrent was not found in the current report.
- No matching local container/app evidence was found.

#### Next safest step
- Collect container status and logs for qbittorrent before giving repair steps.

#### Forum-ready summary
The qbittorrent issue is not verified because the current report does not contain matching app evidence.

---

## 5. Immich cannot see my photos on the storage drive

### ZimaBrain Answer

## ❓ Question asked
### Immich cannot see my photos on the storage drive

#### Verification status
@@VERIFY:PARTIALLY VERIFIED@@ ⚠️ PARTIALLY VERIFIED
- Some local evidence was found, but one or more key facts still need confirmation.
- Active layer: App Runtime Diagnostics Layer
- Layer file: `app/brain/layers/app_runtime_diag.py`


#### Direct answer / severity
- This is an app runtime diagnostic question.
- Detected symptom: app runtime issue
- Detected app: immich
- Matching same-report app evidence was found for immich.
- Root cause is not fully verified from same-report evidence.

### Runtime checks required
- Container running state
- Recent app/container logs
- Docker bind mounts
- Host storage path exists
- App internal path matches the host bind path

#### Next safest step
- Check immich container status, logs, bind mounts, and exact storage paths before attempting repair.

#### Forum-ready summary
immich is present in the current report, but the root cause of the app runtime issue is only partially verified until logs and bind mounts are checked.

---

## 6. ZimaOS install cannot find my SSD

### ZimaBrain Answer

## ❓ Question asked
### ZimaOS install cannot find my SSD

#### Verification status
@@VERIFY:PARTIALLY VERIFIED@@ ⚠️ PARTIALLY VERIFIED
- Some local evidence was found, but one or more key facts still need confirmation.
- Active layer: Install / Boot Diagnostics Layer
- Layer file: `app/brain/layers/install_boot_diag.py`


#### Direct answer / severity
- This is an install / boot diagnostic question.
- The layer separates installer, EFI/boot picker, disk detection, and post-install boot problems.

### Same-report evidence
- General report evidence present: yes
- Host boot/version evidence present: yes

### Diagnostic focus
- Confirm whether the issue is installer boot, disk detection, EFI boot entry, or first boot after install.
- For Mac hardware, confirm whether EFI Boot appears in the boot picker.
- Confirm whether Linux live USB can see the internal disk.
- Confirm target disk, partition table, and whether ZimaOS installer detected any install device.

- Some local report evidence exists, but the boot/install root cause is not fully verified from same-report evidence.

#### Next safest step
- Verify boot picker result, EFI entry, installer disk detection, and live USB lsblk output before changing the disk.

#### Forum-ready summary
Install/boot evidence is partial. Confirm EFI boot visibility and disk detection before reinstalling or wiping anything.

---

## 7. MacBook only shows recovery after install

### ZimaBrain Answer

## ❓ Question asked
### MacBook only shows recovery after install

#### Verification status
@@VERIFY:PARTIALLY VERIFIED@@ ⚠️ PARTIALLY VERIFIED
- Some local evidence was found, but one or more key facts still need confirmation.
- Active layer: Install / Boot Diagnostics Layer
- Layer file: `app/brain/layers/install_boot_diag.py`


#### Direct answer / severity
- This is an install / boot diagnostic question.
- The layer separates installer, EFI/boot picker, disk detection, and post-install boot problems.

### Same-report evidence
- General report evidence present: yes
- Host boot/version evidence present: yes

### Diagnostic focus
- Confirm whether the issue is installer boot, disk detection, EFI boot entry, or first boot after install.
- For Mac hardware, confirm whether EFI Boot appears in the boot picker.
- Confirm whether Linux live USB can see the internal disk.
- Confirm target disk, partition table, and whether ZimaOS installer detected any install device.

- Some local report evidence exists, but the boot/install root cause is not fully verified from same-report evidence.

#### Next safest step
- Verify boot picker result, EFI entry, installer disk detection, and live USB lsblk output before changing the disk.

#### Forum-ready summary
Install/boot evidence is partial. Confirm EFI boot visibility and disk detection before reinstalling or wiping anything.

---

## 8. Docker daemon is failed and keeps restarting

### ZimaBrain Answer

## ❓ Question asked
### Docker daemon is failed and keeps restarting

#### Verification status
@@VERIFY:PARTIALLY VERIFIED@@ ⚠️ PARTIALLY VERIFIED
- Some local evidence was found, but one or more key facts still need confirmation.
- Active layer: Docker Daemon Diagnostics Layer
- Layer file: `app/brain/layers/docker_daemon_diag.py`


#### Direct answer / severity
- This is a Docker daemon diagnostic question.
- The layer checks same-report Docker evidence before suggesting repair steps.

### Same-report Docker evidence
- Docker ps evidence parsed: yes
- Docker inspect / bind-mount evidence parsed: yes
- Docker daemon/service error text found in report: no

- Some Docker evidence exists in the current report.
- Root cause is not fully verified from same-report evidence.
- Docker ps evidence suggests Docker was able to list containers when the report was collected.
- Docker inspect/bind-mount evidence is available and can be used to check app paths.

### Required checks before repair
- Docker service status
- Recent Docker journal logs
- Filesystem free space
- Whether /var/lib/docker or app storage is read-only
- Whether containerd is running
- Whether the issue is daemon-wide or only one app/container

### Do not do yet
- Do not run `docker system prune`.
- Do not delete `/var/lib/docker`.
- Do not reinstall ZimaOS.
- Do not recreate apps until Docker service and storage evidence are checked.

#### Next safest step
- Check Docker service status and journal logs first, then check free space and read-only mount state before restarting or repairing Docker.

#### Forum-ready summary
Docker evidence exists, but the daemon root cause is only partially verified. Check Docker service status, journal logs, free space, and read-only mount state before repair.

---

## 9. How do I enable SSH in ZimaOS?

### ZimaBrain Answer

## ❓ Question asked
### How do I enable SSH in ZimaOS?

#### Verification status
@@VERIFY:OFFICIAL MANUAL REFERENCE@@ 📘 OFFICIAL MANUAL REFERENCE
- This answer is backed by official ZimaOS documentation, but it is not a same-report diagnosis of this machine.
- Active layer: ZimaOS Manual Knowledge Engine
- Layer file: `app/brain/layers/manual_knowledge.py`


#### Direct answer / severity
This is a ZimaOS manual / how-to question.
Answer source: official ZimaOS manual pages saved locally.
This is guidance from documentation, not a same-report diagnosis.
Manual relevance confidence: high

Best matching official page:
How to Enable SSH in ZimaOS | Zimaspace Docs
Source: https://www.zimaspace.com/docs/zimaos/how-to-open-ssh-in-zimaos.html

Relevant manual excerpt:
How to Enable SSH in ZimaOS | Zimaspace Docs
How to Enable SSH in ZimaOS
Based on feedback from our community, we’ve made it easier to enable SSH in ZimaOS. To simplify the process and make it more accessible, we’ve integrated this functionality directly into the UI. Now, it’s quicker and simpler to access SSH and use the terminal.
In the ZimaOS v1.2.5, enabling SSH is now easier than ever. Follow these steps to access SSH:
1. Open Settings.
2. Navigate to Developer Mode.
3. Toggle the SSH Access switch to “On”.
Once you’ve done this, you can use SSH to access your ZimaOS system directly without any additional configurations.
Additionally, you can enable the Web-based Terminal with a single toggle.
This simple update provides a more straightforward approach for developers and advanced users who require SSH access.
Please download the lastet version of ZimaOS: Releases · IceWhaleTech/ZimaOS · GitHub
1. Open Settings.
2. Navigate to Developer Mode.
3. Toggle the SSH Access switch to “On”.

Other possible manual matches:
- SSH Setting | Zimaspace Docs | https://www.zimaspace.com/docs/zimaos/ssh-setup.html
- Enable AI search | Zimaspace Docs | https://www.zimaspace.com/docs/zimaos/enable-ai.html
- How to Enable the Intel AX210 Wi-Fi Module on ZimaOS？ | Zimaspace Docs | https://www.zimaspace.com/docs/zimaos/enable-intel-ax210.html

Next safest step:
Follow the official manual page first. If the user has an error or failed step, collect evidence and route back to the diagnostic layers.

#### Next safest step
- Follow the official ZimaOS manual page first. If the user has an error, collect evidence and route back to diagnostics.

#### Forum-ready summary
This is official ZimaOS manual guidance, not a same-report diagnosis.

---

## 10. How do I find my Network ID?

### ZimaBrain Answer

## ❓ Question asked
### How do I find my Network ID?

#### Verification status
@@VERIFY:OFFICIAL MANUAL REFERENCE@@ 📘 OFFICIAL MANUAL REFERENCE
- This answer is backed by official ZimaOS documentation, but it is not a same-report diagnosis of this machine.
- Active layer: ZimaOS Manual Knowledge Engine
- Layer file: `app/brain/layers/manual_knowledge.py`


#### Direct answer / severity
This is a ZimaOS manual / how-to question.
Answer source: official ZimaOS manual pages saved locally.
This is guidance from documentation, not a same-report diagnosis.
Manual relevance confidence: high

Best matching official page:
Get Network ID | Zimaspace Docs
Source: https://www.zimaspace.com/docs/zimaos/remote-id.html

Relevant manual excerpt:
Get Network ID | Zimaspace Docs
Get Network ID
The NetworkID is one of the ways to uniquely identify a Zima device and connect to it.
You can find the device’s NetworkID in ZimaOS at the following location:
Click “Settings” in the top-left corner of the system.
Click and switch to the “Network” tab.
Obtain and copy the current device’s NetworkID here.
Notes on NetworkID security:
If the NetworkID is leaked, your shared folders may be exposed, so please keep the NetworkID secure.
If you confirm it has been leaked, please click “…” to reset the NetworkID. The leak will be terminated, while existing connections and shares will become invalid.
The NetworkID is one of the ways to uniquely identify a Zima device and connect to it.
You can find the device’s NetworkID in ZimaOS at the following location:
Notes on NetworkID security:

Other possible manual matches:
- Reset Network Settings | Zimaspace Docs | https://www.zimaspace.com/docs/zimaos/resetnetworksettings.html
- 文章标题 | Zimaspace Docs | https://www.zimaspace.com/docs/zimaos/networking.html

Next safest step:
Follow the official manual page first. If the user has an error or failed step, collect evidence and route back to the diagnostic layers.

#### Next safest step
- Follow the official ZimaOS manual page first. If the user has an error, collect evidence and route back to diagnostics.

#### Forum-ready summary
This is official ZimaOS manual guidance, not a same-report diagnosis.

---

## 11. How do I create a bootable USB for ZimaOS?

### ZimaBrain Answer

## ❓ Question asked
### How do I create a bootable USB for ZimaOS?

#### Verification status
@@VERIFY:OFFICIAL MANUAL REFERENCE@@ 📘 OFFICIAL MANUAL REFERENCE
- This answer is backed by official ZimaOS documentation, but it is not a same-report diagnosis of this machine.
- Active layer: ZimaOS Manual Knowledge Engine
- Layer file: `app/brain/layers/manual_knowledge.py`


#### Direct answer / severity
This is a ZimaOS manual / how-to question.
Answer source: official ZimaOS manual pages saved locally.
This is guidance from documentation, not a same-report diagnosis.
Manual relevance confidence: high

Best matching official page:
How to Install ZimaOS | Zimaspace Docs
Source: https://www.zimaspace.com/docs/zimaos/how-to-install-zimaos.html

Relevant manual excerpt:
How to Install ZimaOS | Zimaspace Docs
How to Install ZimaOS
What you’ll learn
This guide provides a complete step-by-step process to help you download, flash, and install ZimaOS quickly and successfully.
What you’ll need
A Zima device or a generic x86-64 with at least 25GB of storage space.
A flash drive (4GB or above recommended).
Getting Started
To boot ZimaOS, the BIOS needs to have UEFI boot mode enabled and Secure Boot disabled.
Step 1: Download the ZimaOS Installation Image
To get started, download the latest ZimaOS .img file from the official GitHub release page:
👉 ZimaOS GitHub Releases
Step 2: Create a Bootable USB Drive
You need to flash the ZimaOS image to a USB drive. The easiest tool for this is Balena Etcher .
Download and install Balena Etcher
Open Etcher and select the ZimaOS .img file.
Insert your USB drive and select it as the target.
Click Flash to start writing the image.
Step 3: Boot your device from USB
Insert the bootable USB drive into your device.
Enter the BIOS/boot menu and choose Boot from USB .
Step 4: Complete ZimaOS Installation
Follow the on-screen instructions to install ZimaOS.
When the system prompts, remove the USB drive and restart the device.
It will now automatically boot into ZimaOS .
Step 5: Access ZimaOS
After reboot, the easiest way to

Other possible manual matches:
- Install ZimaOS on Proxmox VE Using the ISO Image | Zimaspace Docs | https://www.zimaspace.com/docs/zimaos/install-zimaos-on-proxmox-ve.html
- A Comprehensive Guide to Installing AzuraCast on ZimaOS via the Command Line | Zimaspace Docs | https://www.zimaspace.com/docs/zimaos/azuracast-install.html
- A Comprehensive Guide to Installing Paperless-ngx on ZimaOS | Zimaspace Docs | https://www.zimaspace.com/docs/zimaos/paperless-ngx-install.html
- A Comprehensive Guide to Installing Paperless‑AI on ZimaOS | Zimaspace Docs | https://www.zimaspace.com/docs/zimaos/paperless-ai-install.html

Next safest step:
Follow the official manual page first. If the user has an error or failed step, collect evidence and route back to the diagnostic layers.

#### Next safest step
- Follow the official ZimaOS manual page first. If the user has an error, collect evidence and route back to diagnostics.

#### Forum-ready summary
This is official ZimaOS manual guidance, not a same-report diagnosis.

---

## 12. How do I migrate my data to another drive?

### ZimaBrain Answer

## ❓ Question asked
### How do I migrate my data to another drive?

#### Verification status
@@VERIFY:OFFICIAL MANUAL REFERENCE@@ 📘 OFFICIAL MANUAL REFERENCE
- This answer is backed by official ZimaOS documentation, but it is not a same-report diagnosis of this machine.
- Active layer: ZimaOS Manual Knowledge Engine
- Layer file: `app/brain/layers/manual_knowledge.py`


#### Direct answer / severity
This is a ZimaOS manual / how-to question.
Answer source: official ZimaOS manual pages saved locally.
This is guidance from documentation, not a same-report diagnosis.
Manual relevance confidence: medium

Best matching official page:
From Synology to ZimaCube，migrate all files! | Zimaspace Docs
Source: https://www.zimaspace.com/docs/zimaos/synology-to-zimacube-migration.html

Relevant manual excerpt:
From Synology to ZimaCube，migrate all files! | Zimaspace Docs
From Synology to ZimaCube，migrate all files!
Welcome to the world of ZimaOS! I mean new friends who have come from other brand camps such as Synology, hello!
We are honored that you have chosen ZimaCube as the first hardware to experience ZimaOS. In order to help everyone quickly transfer files from Synology devices to ZimaCube, we have prepared this tutorial.
Of course, transferring files to ZimaCube is very easy. Let’s get started.
This tutorial is also applicable to other devices with ZimaOS installed.
SMB/SAMBA will be our method
SMB (Server Message Block) is a protocol built into the Windows system for sharing files and other services over the network. SAMBA implements the SMB protocol, which enriches the file sharing methods of * nix-like systems.
Both ZimaOS and Synology DSM are well-implemented/compatible with SMB, whether through SAMBA or self-implementation, making file sharing and transfer very convenient.
Mount shares from DSM in ZimaOS
At the beginning of Synology setup, many users set up sharing when creating directories; some users did not give sharing function when creating directories. Therefore, before migrating, you may need to create a new shared directory and then move the data you want to migrate

Other possible manual matches:
- Migrate from CasaOS to ZimaOS | Zimaspace Docs | https://www.zimaspace.com/docs/zimaos/casaos-to-zimaos-migration.html
- Data Migration Guide | Zimaspace Docs | https://www.zimaspace.com/docs/zimaos/data-migration.html

Next safest step:
Follow the official manual page first. If the user has an error or failed step, collect evidence and route back to the diagnostic layers.

#### Next safest step
- Follow the official ZimaOS manual page first. If the user has an error, collect evidence and route back to diagnostics.

#### Forum-ready summary
This is official ZimaOS manual guidance, not a same-report diagnosis.

---

## 13. Show me the disk inventory

### ZimaBrain Answer

## ❓ Question asked
### Show me the disk inventory

#### Verification status
@@VERIFY:VERIFIED@@ ✅ VERIFIED FROM SAME-REPORT EVIDENCE
- This answer is based on evidence found in the current report.
- Active layer: Disk Inventory / Drive Count Layer
- Layer file: `app/brain/layers/disk_inventory.py`


#### Direct answer / severity
- This is a disk inventory / drive count question.
- The answer comes from the Disk Inventory Layer using parsed dashboard disk evidence.

### Disk count
- Total disks/devices parsed: 8
- NVMe devices: 4
- SATA / USB disk devices: 3
- USB / removable devices: 1
- Mounted: 6
- Not mounted: 2
- SMART passed: 7
- SMART unknown / not available: 1

### Disk list
- sda: type=SATA / USB disk, model=WDC WD40EFPX-68C6CN0, size=3.6T, health=PASSED, temp=33, crc=8, pending=0, realloc=0, mount=/host/var/lib/casaos_data/.media/HDD-Storage
- sdb: type=SATA / USB disk, model=WDC WD40EFPX-68C6CN0, size=3.6T, health=PASSED, temp=34, crc=0, pending=0, realloc=0, mount=/host/var/lib/casaos_data/.media/HDD-Storage-/dev/sdb
- sdc: type=SATA / USB disk, model=WDC WD10JMVW-11AJGS2, size=931.5G, health=PASSED, temp=31, crc=0, pending=0, realloc=0, mount=not mounted
- sdd: type=USB / removable, model=Flash Drive, size=59.8G, health=UNKNOWN, temp=N/A, crc=-, pending=-, realloc=-, mount=/host/var/lib/casaos_data/.media/sdc
- nvme0n1: type=NVMe, model=Samsung SSD 990 PRO with Heatsink 2TB, size=1.8T, health=PASSED, temp=38, crc=N/A, pending=N/A, realloc=N/A, mount=/host/var/lib/casaos_data/.media/Samsung SSD 990 PRO with Heatsink 2TB
- nvme1n1: type=NVMe, model=Samsung SSD 980 PRO 1TB, size=931.5G, health=PASSED, temp=38, crc=N/A, pending=N/A, realloc=N/A, mount=/host/var/lib/casaos_data/.media/Samsung SSD 980 PRO 1TB
- nvme2n1: type=NVMe, model=Samsung SSD 980 PRO 2TB, size=1.8T, health=PASSED, temp=39, crc=N/A, pending=N/A, realloc=N/A, mount=/host/var/lib/casaos_data/.media/Samsung SSD 980 PRO 2TB
- nvme3n1: type=NVMe, model=KINGSTON OM8PGP4256Q-A0, size=238.5G, health=PASSED, temp=35, crc=N/A, pending=N/A, realloc=N/A, mount=not mounted

### How to interpret this
- NVMe and SATA disks are your main storage candidates.
- Flash/ISO-style devices may be installer, recovery, or removable media.
- A disk showing `not mounted` is detected by the system but not currently mounted as storage.
- A `PASSED` SMART result is good, but CRC/pending/reallocated values still matter.

#### Next safest step
- Use this disk inventory as the baseline, then inspect any disk with CRC errors, unknown SMART, not mounted state, or unexpected media path.

#### Forum-ready summary
The disk inventory layer lists all parsed disks, counts them, separates NVMe/SATA/removable devices, and shows health, mount path, CRC, pending, and reallocated values. This is the first check before changing storage paths or troubleshooting apps.

---

## 14. Which disks are healthy?

### ZimaBrain Answer

## ❓ Question asked
### Which disks are healthy?

#### Verification status
@@VERIFY:VERIFIED@@ ✅ VERIFIED FROM SAME-REPORT EVIDENCE
- This answer is based on evidence found in the current report.
- Active layer: Disk Health Layer
- Layer file: `app/brain/layers/disk_health.py`


#### Direct answer / severity
- This is a disk health summary question.

Disks needing attention from real values:
- sda: CRC errors 8. SMART health still reports PASSED, so check the connection path first.
- sdd: filesystem usage 100%, health=UNKNOWN, model=Flash Drive, size=59.8G, mount=/host/var/lib/casaos_data/.media/sdc. Verify the mount and contents before deleting anything.

Info only / unavailable SMART fields:
- ℹ️ INFO: nvme0n1: pending sectors N/A (SMART value unavailable, not confirmed failure)
- ℹ️ INFO: nvme0n1: reallocated sectors N/A (SMART value unavailable, not confirmed failure)
- ℹ️ INFO: nvme0n1: CRC errors N/A (SMART value unavailable, not confirmed failure)
- ℹ️ INFO: nvme1n1: pending sectors N/A (SMART value unavailable, not confirmed failure)
- ℹ️ INFO: nvme1n1: reallocated sectors N/A (SMART value unavailable, not confirmed failure)
- ℹ️ INFO: nvme1n1: CRC errors N/A (SMART value unavailable, not confirmed failure)
- ℹ️ INFO: nvme2n1: pending sectors N/A (SMART value unavailable, not confirmed failure)
- ℹ️ INFO: nvme2n1: reallocated sectors N/A (SMART value unavailable, not confirmed failure)
- ℹ️ INFO: nvme2n1: CRC errors N/A (SMART value unavailable, not confirmed failure)
- ℹ️ INFO: nvme3n1: pending sectors N/A (SMART value unavailable, not confirmed failure)
- ℹ️ INFO: nvme3n1: reallocated sectors N/A (SMART value unavailable, not confirmed failure)
- ℹ️ INFO: nvme3n1: CRC errors N/A (SMART value unavailable, not confirmed failure)

Disks that look OK from available fields:
- sda: health=PASSED, temp=33°C, realloc=0, pending=0, crc=8. CRC is the attention item.
- sdb: health=PASSED, temp=34°C, model=WDC WD40EFPX-68C6CN0.
- sdc: health=PASSED, temp=31°C, model=WDC WD10JMVW-11AJGS2.
- nvme0n1: health=PASSED, temp=38°C, model=Samsung SSD 990 PRO with Heatsink 2TB.
- nvme1n1: health=PASSED, temp=38°C, model=Samsung SSD 980 PRO 1TB.
- nvme2n1: health=PASSED, temp=39°C, model=Samsung SSD 980 PRO 2TB.
- nvme3n1: health=PASSED, temp=35°C, model=KINGSTON OM8PGP4256Q-A0.

#### Next safest step
- Handle real disk warnings first: confirm whether sda CRC errors are increasing, then verify the active sdd mount and contents. Treat NVMe N/A SMART values as unavailable data, not failures.

#### Forum-ready summary
Based on the verified dashboard evidence, the real disk attention items are sda CRC errors and sdd filesystem usage at 100%. NVMe N/A SMART values are informational only. Confirm whether sda CRC is increasing and verify the sdd mount before deleting or replacing anything.

---

## 15. What containers are exited?

### ZimaBrain Answer

## ❓ Question asked
### What containers are exited?

#### Verification status
@@VERIFY:VERIFIED@@ ✅ VERIFIED FROM SAME-REPORT EVIDENCE
- This answer is based on evidence found in the current report.
- Active layer: Containers Layer
- Layer file: `app/brain/layers/containers.py`


#### Direct answer / severity
- This is a container state question.
- The answer comes from the Containers Layer using dashboard-parsed Docker state.

Exited containers parsed from the dashboard layer:
- mailcowdockerized-watchdog-mailcow-1 (ghcr.io/mailcow/watchdog:2.11)
- mailcowdockerized-postfix-mailcow-1 (ghcr.io/mailcow/postfix:3.7.11-2)
- mailcowdockerized-dovecot-mailcow-1 (ghcr.io/mailcow/dovecot:2.3.21.1-1)
- mailcowdockerized-netfilter-mailcow-1 (ghcr.io/mailcow/netfilter:1.64)
- netdata-fixed (netdata/netdata:latest)
- netdata-full (netdata/netdata:latest)

#### Next safest step
- Inspect only the affected exited container logs/status. Do not remove containers in bulk.

#### Forum-ready summary
Based on the verified dashboard evidence, several containers are exited. Inspect only the affected container logs and status one by one. Do not remove containers in bulk or run Docker prune commands.

---

## 16. Can I expose port 8601 publicly?

### ZimaBrain Answer

## ❓ Question asked
### Can I expose port 8601 publicly?

#### Verification status
@@VERIFY:PARTIALLY VERIFIED@@ ⚠️ PARTIALLY VERIFIED
- Some local evidence was found, but one or more key facts still need confirmation.
- Active layer: Network Exposure / Firewall Layer
- Layer file: `app/brain/layers/network_exposure.py`


#### Direct answer / severity
- This is a network exposure / firewall verification question.
- The answer comes from the Network Exposure / Firewall Layer using same-report Docker and firewall evidence.

### Published Docker ports
- zimabrain-ce-flask-8601: 8601/tcp=>0.0.0.0:8601,:::8601,;
- zimabrain-ce-8600: 8512/tcp=>0.0.0.0:8600,:::8600,;
- zimacube-dashboard-brain: 8501/tcp=>0.0.0.0:8514,:::8514,;
- zimacube-dashboard: 8501/tcp=>0.0.0.0:8513,:::8513,;
- zimabrain-ce: 8512/tcp=>0.0.0.0:8512,:::8512,;
- casadrop: 8080/tcp=>0.0.0.0:8080,:::8080,;
- zima-brain-v2: 8510/tcp=>0.0.0.0:8511,:::8511,;
- zima-brain: 8510/tcp=>0.0.0.0:8510,:::8510,;
- borg-web-ui: 8081/tcp=>0.0.0.0:8081,:::8081,;
- portainer: 8000/tcp=>0.0.0.0:8000,:::8000,;9000/tcp=>0.0.0.0:9000,:::9000,;9443/tcp=>0.0.0.0:9446,:::9446,;
- homepage: 3000/tcp=>0.0.0.0:3333,:::3333,;
- big-bear-tugtainer: 80/tcp=>0.0.0.0:9412,:::9412,;
- brain-host-tools: 8099/tcp=>127.0.0.1:8099,;
- big-bear-composetoolbox: 3000/tcp=>0.0.0.0:3002,:::3002,;
- pdf-ai: 8501/tcp=>0.0.0.0:8502,:::8502,;
- open-webui: 8080/tcp=>0.0.0.0:3000,:::3000,;
- ollama: 11434/tcp=>0.0.0.0:11434,:::11434,;
- mailcowdockerized-nginx-mailcow-1: 80/tcp=>;8085/tcp=>0.0.0.0:8085,:::8085,;8445/tcp=>0.0.0.0:8445,:::8445,;
- mailcowdockerized-php-fpm-mailcow-1: 9000/tcp=>;
- mailcowdockerized-mysql-mailcow-1: 3306/tcp=>127.0.0.1:13306,;
- mailcowdockerized-redis-mailcow-1: 6379/tcp=>127.0.0.1:7654,;
- mailcowdockerized-unbound-mailcow-1: 53/tcp=>;53/udp=>;
- mailcowdockerized-memcached-mailcow-1: 11211/tcp=>;
- rsync-ssh: 22/tcp=>0.0.0.0:2223,:::2223,;
- big-bear-btop: 7681/tcp=>0.0.0.0:7682,:::7682,;
- big-bear-ntfy-app-1: 80/tcp=>0.0.0.0:7200,:::7200,;
- big-bear-scrutiny: 8080/tcp=>0.0.0.0:38080,:::38080,;8086/tcp=>0.0.0.0:38086,:::38086,;
- immich-server: 2283/tcp=>0.0.0.0:2283,:::2283,;
- immich-postgres: 5432/tcp=>;
- immich-redis: 6379/tcp=>;

### High-risk exposure checks
- Containers with full `/DATA` read-write access and published ports:
  - casadrop: /DATA rw with published ports: 8080/tcp=>0.0.0.0:8080,:::8080,;
  - zima-brain-v2: /DATA rw with published ports: 8510/tcp=>0.0.0.0:8511,:::8511,;
  - zima-brain: /DATA rw with published ports: 8510/tcp=>0.0.0.0:8510,:::8510,;

### Remote access / tunnel indicators
- mailcowdockerized-nginx-mailcow-1: 80/tcp=>;8085/tcp=>0.0.0.0:8085,:::8085,;8445/tcp=>0.0.0.0:8445,:::8445,;
- cloudflared: no parsed published port
- mailcowdockerized-nginx-mailcow-1: 0.0.0.0:8085->8085/tcp, :::8085->8085/tcp, 80/tcp, 0.0.0.0:8445->8445/tcp, :::8445->8445/tcp
- cloudflared: Up 3 weeks

### DOCKER-USER firewall chain
- No DOCKER-USER firewall evidence was parsed from the current report.

### How to interpret this
- Published Docker ports are reachable from the LAN unless another firewall or router rule blocks them.
- A tunnel container can expose services externally even when router port-forwarding is not used.
- A container with `/DATA` write access and a published port deserves extra attention.
- Do not change firewall rules until the service, port, and access path are confirmed.

#### Next safest step
- Review the listed published ports and any tunnel/proxy containers, then confirm authentication and firewall restrictions before exposing services further.

#### Forum-ready summary
Network exposure should be verified from Docker published ports, tunnel/proxy containers, and DOCKER-USER firewall evidence. Do not assume a service is safe just because it is local. Confirm the exact port, service, authentication, and firewall path before exposing it.

---

## 17. What should I do next?

### ZimaBrain Answer

## ❓ Question asked
### What should I do next?

#### Verification status
@@VERIFY:VERIFIED@@ ✅ VERIFIED FROM SAME-REPORT EVIDENCE
- This answer is based on evidence found in the current report.
- Active layer: Final Recommendation / Repair Planner Layer
- Layer file: `app/brain/layers/repair_planner.py`


#### Direct answer / severity
- This is a final recommendation / repair planner question.
- The layer does not repair directly. It orders the next checks from safest to riskiest.

### Same-report evidence
- Report text present: yes
- Evidence groups present: 12
- Disk inventory parsed: yes

- Evidence exists, but final repair action is not fully verified until the affected layer confirms the root cause.

### Safe order
1. Identify the affected layer.
2. Confirm same-report evidence.
3. Use read-only commands first.
4. Back up important data before repair.
5. Apply only the smallest repair step.
6. Re-test and compare evidence.

#### Next safest step
- Use the active diagnostic layer first, then apply the smallest safe repair step only after evidence is confirmed.

#### Forum-ready summary
Repair plan should follow verified evidence, read-only checks first, backup before repair, and smallest-change-first action.
