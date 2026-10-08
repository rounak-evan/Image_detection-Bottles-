#!/bin/bash
# Copy the running Orange Pi system onto the eMMC module, so the Pi can boot
# from the eMMC alone (no SD card / USB pen drive). Does what Orange Pi's
# menu-driven `nand-sata-install` does, step by step, with safety checks.
# ERASES EVERYTHING ON THE eMMC. Run with: sudo bash install_to_emmc.sh
set -euo pipefail

DEV=/dev/mmcblk0
UBOOT_DIR=$(ls -d /usr/lib/linux-u-boot-*/ | head -1)
MNT=/mnt/emmc_install

echo "== 1. Safety checks"
# The eMMC is the only storage with hardware "boot0" partitions.
[[ -b ${DEV}boot0 ]] || { echo "STOP: $DEV is not an eMMC"; exit 1; }
SIZE_GB=$(( $(blockdev --getsize64 $DEV) / 1000000000 ))
[[ $SIZE_GB -ge 16 && $SIZE_GB -le 128 ]] || { echo "STOP: unexpected size ${SIZE_GB} GB"; exit 1; }
ROOT_DISK=$(lsblk -no PKNAME "$(findmnt -no SOURCE /)")
[[ "/dev/$ROOT_DISK" != "$DEV" ]] || { echo "STOP: the running system is on $DEV"; exit 1; }
echo "Target $DEV (${SIZE_GB} GB). Running system is on /dev/$ROOT_DISK. Bootloader from $UBOOT_DIR"
umount ${DEV}p* 2>/dev/null || true

echo "== 2. Fresh partition table sized to the whole eMMC (same layout as the image)"
wipefs -a ${DEV}p* 2>/dev/null || true
sgdisk --zap-all $DEV >/dev/null
# Partition 1: 1 GiB boot (FAT) at sector 61440; partition 2: the rest, for the system.
# Everything before sector 61440 is left free for the bootloader.
sgdisk -n 1:61440:2158591 -t 1:EA00 -c 1:bootfs -n 2:2158592:0 -t 2:8300 -c 2:rootfs $DEV >/dev/null
partprobe $DEV; sleep 2
sgdisk -v $DEV | tail -1

echo "== 3. Bootloader (same positions as Orange Pi's own installer)"
dd if=${UBOOT_DIR}idbloader.img of=$DEV seek=64 conv=notrunc status=none
dd if=${UBOOT_DIR}u-boot.itb of=$DEV seek=16384 conv=notrunc status=none

echo "== 4. Format both partitions (new, unique IDs)"
mkfs.vfat -F 32 -n BOOT ${DEV}p1 >/dev/null
mkfs.ext4 -F -q -L opi_root ${DEV}p2
BOOT_UUID=$(blkid -s UUID -o value ${DEV}p1)
ROOT_UUID=$(blkid -s UUID -o value ${DEV}p2)
echo "New boot UUID $BOOT_UUID, root UUID $ROOT_UUID"

echo "== 5. Copy the running system (takes a few minutes)"
mkdir -p $MNT
mount ${DEV}p2 $MNT
# --one-file-system: copy only the real disk, not /proc, /sys, /tmp, the zram /var/log, or /boot.
rsync -aAXH --one-file-system / $MNT/
mkdir -p $MNT/boot
mount ${DEV}p1 $MNT/boot
# /boot is FAT, which can't store Linux owners/permissions, so copy without them.
rsync -rtD --modify-window=2 /boot/ $MNT/boot/

echo "== 6. Point the eMMC copy at its own partitions"
OLD_ROOT=$(findmnt -no UUID /)
OLD_BOOT=$(findmnt -no UUID /boot)
sed -i "s/$OLD_ROOT/$ROOT_UUID/; s/$OLD_BOOT/$BOOT_UUID/" $MNT/etc/fstab
sed -i "s/^rootdev=.*/rootdev=UUID=$ROOT_UUID/" $MNT/boot/orangepiEnv.txt
echo "--- eMMC fstab:"; grep -v '^#' $MNT/etc/fstab
echo "--- eMMC orangepiEnv.txt rootdev:"; grep ^rootdev $MNT/boot/orangepiEnv.txt

sync
umount $MNT/boot $MNT
echo "== DONE. Shut down, remove the SD card and USB drive, then power on."
