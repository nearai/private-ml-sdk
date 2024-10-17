#!/bin/sh
set -e

INITRAMFS_IMAGE=tmp/deploy/images/tdx/dstack-initramfs.cpio.gz
ROOTFS_IMAGE=tmp/deploy/images/tdx/dstack-rootfs-tdx.cpio

echo "Copying initramfs..."
mkdir -p dist/
cp $INITRAMFS_IMAGE dist/

echo "Copying rootfs..."
mkdir -p rootfs/
cp $ROOTFS_IMAGE rootfs/rootfs.cpio
mkisofs -o dist/rootfs.iso --max-iso9660-filenames -input-charset utf-8 rootfs/
