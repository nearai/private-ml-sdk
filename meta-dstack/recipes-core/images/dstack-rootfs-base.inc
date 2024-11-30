IMAGE_BASENAME = "${PN}"

IMAGE_INSTALL = "\
    ${VIRTUAL-RUNTIME_base-utils} \
    ${ROOTFS_BOOTSTRAP_INSTALL} \
    base-files \
    base-passwd \
    systemd \
    netbase \
    iptables \
    docker \
    docker-compose \
    dstack-prebuilt \
    tdx-guest-ko \
    dstack-guest \
    wireguard-tools \
    curl \
    jq \
"

# Do not pollute the initrd image with rootfs features
IMAGE_FEATURES = ""

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
ROOTFS_POSTPROCESS_COMMAND += "symlink_lib64;"
IMAGE_FEATURES[validitems] += "nologin"
ROOTFS_POSTPROCESS_COMMAND += '${@bb.utils.contains_any("IMAGE_FEATURES", [ 'nologin' ], "disable_getty_services", "",d)}'

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

symlink_lib64() {
    ln -s lib ${IMAGE_ROOTFS}/lib64
}

disable_getty_services() {
    for srv in getty getty-pre; do
        rm -f ${IMAGE_ROOTFS}/etc/systemd/system/${srv}.target
        rm -f ${IMAGE_ROOTFS}/usr/lib/systemd/system/${srv}.target
    done
    for srv in autovt container-getty console-getty getty-generator serial-getty getty; do
        rm -f ${IMAGE_ROOTFS}/etc/systemd/system/${srv}.service
        rm -f ${IMAGE_ROOTFS}/etc/systemd/system/${srv}@.service
        rm -f ${IMAGE_ROOTFS}/usr/lib/systemd/system/${srv}.service
        rm -f ${IMAGE_ROOTFS}/usr/lib/systemd/system/${srv}@.service
    done
}

