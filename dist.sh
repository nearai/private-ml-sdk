#!/bin/sh
set -e

BUILD_DIR=${BUILD_DIR:-build}
DIST_DIR=${DIST_DIR:-${BUILD_DIR}/dist}

INITRAMFS_IMAGE=${BUILD_DIR}/tmp/deploy/images/tdx/dstack-initramfs.cpio.gz
ROOTFS_IMAGE=${BUILD_DIR}/tmp/deploy/images/tdx/dstack-rootfs-tdx.cpio
ROOTFS_IMAGE_DEV=${BUILD_DIR}/tmp/deploy/images/tdx/dstack-rootfs-dev-tdx.cpio
KERNEL_IMAGE=${BUILD_DIR}/tmp/deploy/images/tdx/bzImage
OVMF_FIRMWARE=${BUILD_DIR}/tmp/deploy/images/tdx/ovmf.fd

echo "Copying initramfs..."
rm -rf ${DIST_DIR}/
mkdir -p ${DIST_DIR}/
cp $INITRAMFS_IMAGE ${DIST_DIR}/initramfs.cpio.gz

echo "Copying kernel..."
cp $KERNEL_IMAGE ${DIST_DIR}/

echo "Copying OVMF firmware..."
cp $OVMF_FIRMWARE ${DIST_DIR}/

echo "Making rootfs.iso..."
mkdir -p ${BUILD_DIR}/rootfs/
mkdir -p ${BUILD_DIR}/rootfs-dev/
cp $ROOTFS_IMAGE ${BUILD_DIR}/rootfs/rootfs.cpio
cp $ROOTFS_IMAGE ${DIST_DIR}/rootfs.cpio
cp $ROOTFS_IMAGE_DEV ${BUILD_DIR}/rootfs-dev/rootfs.cpio
cp $ROOTFS_IMAGE_DEV ${DIST_DIR}/rootfs-dev.cpio
mkisofs -o ${DIST_DIR}/rootfs.iso --max-iso9660-filenames -input-charset utf-8 ${BUILD_DIR}/rootfs/
mkisofs -o ${DIST_DIR}/rootfs-dev.iso --max-iso9660-filenames -input-charset utf-8 ${BUILD_DIR}/rootfs-dev/
