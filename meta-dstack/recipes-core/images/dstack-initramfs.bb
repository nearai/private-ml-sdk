# Simple initramfs image artifact generation for tiny images.
DESCRIPTION = "Tiny image capable of booting a device. The kernel includes \
the Minimal RAM-based Initial Root Filesystem (initramfs), which finds the \
first 'init' program more efficiently. core-image-tiny-initramfs doesn't \
actually generate an image but rather generates boot and rootfs artifacts \
that can subsequently be picked up by external image generation tools such as wic."

PACKAGE_INSTALL = "\
    ${VIRTUAL-RUNTIME_base-utils} \
    ${ROOTFS_BOOTSTRAP_INSTALL} \
    base-files \
    base-passwd \
    systemd \
    netbase \
    iptables \
    dropbear \
    docker \
    docker-compose \
    dstack-prebuilt \
    kernel-module-tdx-guest \
    dstack-guest \
    curl"

INITRAMFS_MAXSIZE = "1000000"

# Do not pollute the initrd image with rootfs features
IMAGE_FEATURES = "debug-tweaks read-only-rootfs"

IMAGE_BASENAME = "dstack-initramfs"
IMAGE_NAME_SUFFIX ?= ""
IMAGE_LINGUAS = ""

LICENSE = "MIT"

# don't actually generate an image, just the artifacts needed for one
IMAGE_FSTYPES = "${INITRAMFS_FSTYPES}"

inherit core-image

IMAGE_ROOTFS_SIZE = "8192"
IMAGE_ROOTFS_EXTRA_SPACE = "0"

# Use the same restriction as initramfs-live-install
COMPATIBLE_HOST = "x86_64.*-linux"

# QB_KERNEL_CMDLINE_APPEND += "debugshell=3 init=/bin/busybox sh init"

# Remove sysvinit related files in a postprocess function
ROOTFS_POSTPROCESS_COMMAND += "remove_sysvinit_files;"

remove_sysvinit_files() {
    # Remove /etc/init.d directory and its contents
    rm -rf ${IMAGE_ROOTFS}${sysconfdir}/init.d

    # Remove /etc/rc*.d directories and their contents
    for d in ${IMAGE_ROOTFS}${sysconfdir}/rc*.d; do
        rm -rf $d
    done

    # Remove other sysvinit specific files
    rm -f ${IMAGE_ROOTFS}${sysconfdir}/inittab
}
