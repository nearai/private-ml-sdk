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
    curl jq"

# Do not pollute the initrd image with rootfs features
IMAGE_FEATURES = "debug-tweaks read-only-rootfs"

IMAGE_BASENAME = "dstack-rootfs"
IMAGE_NAME_SUFFIX ?= ""
IMAGE_LINGUAS = ""
INITRAMFS_MAXSIZE = "1000000"

LICENSE = "MIT"

IMAGE_FSTYPES = "cpio"

inherit core-image

IMAGE_ROOTFS_SIZE = "8192"
IMAGE_ROOTFS_EXTRA_SPACE = "0"

# Use the same restriction as initramfs-live-install
COMPATIBLE_HOST = "x86_64.*-linux"

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
