#!/bin/bash
set -e

# Parse command line arguments
while [ $# -gt 0 ]; do
    case "$1" in
        --dist-name)
            DIST_NAME="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 --image-name NAME --dist-name NAME [--dev]"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$DIST_NAME" ]; then
    echo "Error: --dist-name is required"
    exit 1
fi


if [[ "$DIST_NAME" == *-dev ]]; then
    ENCFS=0
else
    ENCFS=1
fi

BUILD_DIR=${BUILD_DIR:-build}
DIST_DIR=${DIST_DIR:-${BUILD_DIR}/dist}

ROOTFS_IMAGE_NAME=${DIST_NAME}-rootfs
WORK_DIR=${BUILD_DIR}/${ROOTFS_IMAGE_NAME}.tmp
INITRAMFS_IMAGE=${BUILD_DIR}/tmp/deploy/images/tdx/dstack-initramfs.cpio.gz
ROOTFS_IMAGE=${BUILD_DIR}/tmp/deploy/images/tdx/${ROOTFS_IMAGE_NAME}-tdx.cpio
KERNEL_IMAGE=${BUILD_DIR}/tmp/deploy/images/tdx/bzImage
OVMF_FIRMWARE=${BUILD_DIR}/tmp/deploy/images/tdx/ovmf.fd
ROOTFS_HASH=$(sha256sum "$ROOTFS_IMAGE" | awk '{print $1}')
DSTACK_VERSION=$(bitbake-getvar --value DISTRO_VERSION)
OUTPUT_DIR=${OUTPUT_DIR:-"${DIST_DIR}/${DIST_NAME}-${DSTACK_VERSION}"}

mkdir -p ${WORK_DIR}

verbose() {
    echo "$@"
    $@
}

Q=verbose

$Q rm -rf ${OUTPUT_DIR}/
$Q mkdir -p ${OUTPUT_DIR}/
$Q cp $INITRAMFS_IMAGE ${OUTPUT_DIR}/initramfs.cpio.gz
$Q cp $KERNEL_IMAGE ${OUTPUT_DIR}/
$Q cp $OVMF_FIRMWARE ${OUTPUT_DIR}/

$Q mkdir -p ${WORK_DIR}/rootfs/
$Q cp $ROOTFS_IMAGE ${WORK_DIR}/rootfs/rootfs.cpio
$Q cp $ROOTFS_IMAGE ${OUTPUT_DIR}/rootfs.cpio
$Q mkisofs -o ${OUTPUT_DIR}/rootfs.iso --max-iso9660-filenames -input-charset utf-8 ${WORK_DIR}/rootfs/

GIT_REVISION=$(git rev-parse HEAD)
echo "Generating metadata.json to ${OUTPUT_DIR}/metadata.json"
cat <<EOF > ${OUTPUT_DIR}/metadata.json
{
    "bios": "ovmf.fd",
    "kernel": "bzImage",
    "cmdline": "console=ttyS0 init=/init dstack.fde=${ENCFS} panic=1 systemd.unified_cgroup_hierarchy=0",
    "initrd": "initramfs.cpio.gz",
    "rootfs": "rootfs.iso",
    "rootfs_hash": "$ROOTFS_HASH",
    "git_revision": "$GIT_REVISION"
}
EOF
