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
    ENCFS=0
    IS_DEV=true
else
    ENCFS=1
    IS_DEV=false
fi

BB_BUILD_DIR=$(realpath ${BB_BUILD_DIR:-build})
DIST_DIR=$(realpath ${DIST_DIR:-${BB_BUILD_DIR}/dist})

ROOTFS_IMAGE_NAME=${DIST_NAME}-rootfs
WORK_DIR=${BB_BUILD_DIR}/${ROOTFS_IMAGE_NAME}.tmp
INITRAMFS_IMAGE=${BB_BUILD_DIR}/tmp/deploy/images/tdx/dstack-initramfs.cpio.gz
ROOTFS_IMAGE=${BB_BUILD_DIR}/tmp/deploy/images/tdx/${ROOTFS_IMAGE_NAME}-tdx.cpio
KERNEL_IMAGE=${BB_BUILD_DIR}/tmp/deploy/images/tdx/bzImage
OVMF_FIRMWARE=${BB_BUILD_DIR}/tmp/deploy/images/tdx/ovmf.fd
ROOTFS_HASH=$(sha256sum "$ROOTFS_IMAGE" | awk '{print $1}')
DSTACK_VERSION=$(bitbake-getvar --value DISTRO_VERSION)
OUTPUT_DIR=${OUTPUT_DIR:-"${DIST_DIR}/${DIST_NAME}-${DSTACK_VERSION}"}

mkdir -p ${WORK_DIR}

verbose() {
    echo "$@"
    $@
}

Q=verbose

makeiso() {
    export SOURCE_DATE_EPOCH="$(date -d20010101 -u +%s)"
    folder="$1"
    output_filename="$2"
    file_mode=0444

    list="$(mktemp)"
    (cd "$folder"; for f in *; do printf "%s\n" "$f=$PWD/$f"; done) | LC_ALL=C sort >"$list"

    xorriso \
        -preparer_id xorriso \
        -volume_date 'all_file_dates' "=$SOURCE_DATE_EPOCH" \
        -as mkisofs \
        -iso-level 3 \
        -graft-points \
        -full-iso9660-filenames \
        -joliet \
        -file-mode $file_mode \
        -uid 0 \
        -gid 0 \
        -path-list "$list" \
        -output "$output_filename"

    rm -f "$list"
}

$Q rm -rf ${OUTPUT_DIR}/
$Q mkdir -p ${OUTPUT_DIR}/
$Q cp $INITRAMFS_IMAGE ${OUTPUT_DIR}/initramfs.cpio.gz
$Q cp $KERNEL_IMAGE ${OUTPUT_DIR}/
$Q cp $OVMF_FIRMWARE ${OUTPUT_DIR}/

$Q mkdir -p ${WORK_DIR}/rootfs/
$Q cp $ROOTFS_IMAGE ${WORK_DIR}/rootfs/rootfs.cpio
$Q cp $ROOTFS_IMAGE ${OUTPUT_DIR}/rootfs.cpio
$Q makeiso ${WORK_DIR}/rootfs/ ${OUTPUT_DIR}/rootfs.iso

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
    echo "Archiving the output directory to ${OUTPUT_DIR}.tar.gz"
    if [ x$DSTACK_TAR_EXCLUDE_ROOTFS_CPIO = x1 ]; then
        TAR_ARGS=--exclude=rootfs.cpio
    fi
    (cd ${OUTPUT_DIR} && tar -czf ${OUTPUT_DIR}.tar.gz ${TAR_ARGS} .)
    echo
fi
