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
            echo "Usage: $0 --dist-name NAME"
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
    IS_DEV=true
else
    IS_DEV=false
fi

BB_BUILD_DIR=$(realpath ${BB_BUILD_DIR:-build})
DIST_DIR=$(realpath ${DIST_DIR:-${BB_BUILD_DIR}/dist})

IMG_DIR=${BB_BUILD_DIR}/tmp/deploy/images/tdx
ROOTFS_IMAGE_NAME=${DIST_NAME}-rootfs

INITRAMFS_IMAGE=${IMG_DIR}/dstack-initramfs.cpio.gz
ROOTFS_IMAGE=${IMG_DIR}/${ROOTFS_IMAGE_NAME}-tdx.ext4.verity
KERNEL_IMAGE=${IMG_DIR}/bzImage
OVMF_FIRMWARE=${IMG_DIR}/ovmf.fd
# Always use the work-shared directory which has the correct verity env
VERITY_ENV_FILE=${BB_BUILD_DIR}/tmp/work-shared/tdx/dm-verity/${ROOTFS_IMAGE_NAME}.ext4.verity.env
echo "Loading verity env from ${VERITY_ENV_FILE}"
source ${VERITY_ENV_FILE}

DSTACK_VERSION=$(bitbake-getvar --value DISTRO_VERSION)
OUTPUT_DIR=${OUTPUT_DIR:-"${DIST_DIR}/${DIST_NAME}-${DSTACK_VERSION}"}

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
$Q cp $ROOTFS_IMAGE ${OUTPUT_DIR}/rootfs.img.verity

GIT_REVISION=$(git rev-parse HEAD)
echo "Generating metadata.json to ${OUTPUT_DIR}/metadata.json"

KARG0="console=ttyS0 init=/init panic=1 systemd.unified_cgroup_hierarchy=0 net.ifnames=0 biosdevname=0"
KARG1="mce=off oops=panic pci=noearly pci=nommconf random.trust_cpu=y random.trust_bootloader=n tsc=reliable no-kvmclock"
KARG2="dstack.rootfs_hash=$ROOT_HASH dstack.rootfs_size=$DATA_SIZE"

cat <<EOF > ${OUTPUT_DIR}/metadata.json
{
    "bios": "ovmf.fd",
    "kernel": "bzImage",
    "cmdline": "$KARG0 $KARG1 $KARG2",
    "initrd": "initramfs.cpio.gz",
    "rootfs": "rootfs.img.verity",
    "version": "$DSTACK_VERSION",
    "git_revision": "$GIT_REVISION",
    "shared_ro": true,
    "is_dev": ${IS_DEV}
}
EOF

echo "Generating md5sum.txt and sha256sum.txt to ${OUTPUT_DIR}/"
pushd ${OUTPUT_DIR}/
find . -type f -not -name md5sum.txt -not -name sha256sum.txt -exec md5sum {} + | sort -k 2 > md5sum.txt
find . -type f -not -name md5sum.txt -not -name sha256sum.txt -exec sha256sum {} + | sort -k 2 > sha256sum.txt
popd

if [ x$DSTACK_TAR_RELEASE = x1 ]; then
    OUTPUT_DIR=$(realpath ${OUTPUT_DIR})
    echo "Archiving the output directory to ${OUTPUT_DIR}.tar.gz"
    (cd $(dirname ${OUTPUT_DIR}) && tar -czvf ${OUTPUT_DIR}.tar.gz ${TAR_ARGS} $(basename $OUTPUT_DIR))
    echo
fi
