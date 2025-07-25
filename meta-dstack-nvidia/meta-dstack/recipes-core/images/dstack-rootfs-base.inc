inherit core-image

IMAGE_BASENAME = "${PN}"

IMAGE_INSTALL = "\
    ${VIRTUAL-RUNTIME_base-utils} \
    ${ROOTFS_BOOTSTRAP_INSTALL} \
    base-files \
    base-passwd \
    systemd \
    netbase \
    iptables \
    docker-moby \
    docker-compose \
    tdx-guest-ko \
    dstack-guest \
    wireguard-tools \
    cryptsetup \
    curl \
    jq \
    chrony \
    chronyc \
    dstack-zfs \
    kernel-module-tun \
    kernel-module-fuse \
    fuse3 \
    fuse3-utils \
"

IMAGE_NAME_SUFFIX ?= ""
IMAGE_LINGUAS = ""
INITRAMFS_MAXSIZE = "1000000"

LICENSE = "MIT"

IMAGE_CLASSES += "dm-verity-img"

DM_VERITY_IMAGE = "${PN}"
DM_VERITY_IMAGE_TYPE = "squashfs"
DM_VERITY_SEPARATE_HASH = "0"
DM_VERITY_REPRODUCIBLE = "1"

IMAGE_FSTYPES = "cpio squashfs"
CONVERSIONTYPES += "verity"
IMAGE_TYPES += "squashfs.verity"

EXTRA_IMAGE_FEATURES = "read-only-rootfs"

IMAGE_ROOTFS_SIZE = "8192"
IMAGE_ROOTFS_EXTRA_SPACE = "0"

# Use the same restriction as initramfs-live-install
COMPATIBLE_HOST = "x86_64.*-linux"

# Remove sysvinit related files in a postprocess function
ROOTFS_POSTPROCESS_COMMAND += "remove_sysvinit_files;"
ROOTFS_POSTPROCESS_COMMAND += "symlink_lib64;"
IMAGE_FEATURES[validitems] += "nologin"
ROOTFS_POSTPROCESS_COMMAND += '${@bb.utils.contains_any("IMAGE_FEATURES", [ 'nologin' ], "disable_login", "",d)}'
ROOTFS_POSTPROCESS_COMMAND += "mkdirs;"


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

disable_login() {
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

    # Login/console related
    rm -rf ${IMAGE_ROOTFS}/usr/sbin/getty
    rm -rf ${IMAGE_ROOTFS}/usr/sbin/agetty
    rm -rf ${IMAGE_ROOTFS}/usr/bin/login
    rm -rf ${IMAGE_ROOTFS}/usr/bin/loginctl
    rm -rf ${IMAGE_ROOTFS}/etc/systemd/system/getty.target.wants

    # Console fonts and keymaps
    rm -rf ${IMAGE_ROOTFS}/usr/share/consolefonts
    rm -rf ${IMAGE_ROOTFS}/usr/share/keymaps

    # Systemd components we don't need
    rm -rf ${IMAGE_ROOTFS}/usr/bin/systemd-tty-ask-password-agent
    rm -rf ${IMAGE_ROOTFS}/usr/lib/systemd/system/debug-shell.service
    rm -rf ${IMAGE_ROOTFS}/usr/lib/systemd/system/suspend.target
    rm -rf ${IMAGE_ROOTFS}/usr/lib/systemd/system/systemd-hibernate.service
    rm -rf ${IMAGE_ROOTFS}/usr/lib/systemd/system/systemd-suspend-then-hibernate.service
    rm -rf ${IMAGE_ROOTFS}/usr/lib/systemd/systemd-hibernate-resume
    rm -rf ${IMAGE_ROOTFS}/usr/lib/systemd/system-generators/systemd-getty-generator
    rm -rf ${IMAGE_ROOTFS}/usr/lib/systemd/systemd-logind
    rm -rf ${IMAGE_ROOTFS}/usr/lib/systemd/system/systemd-logind.service
    rm -rf ${IMAGE_ROOTFS}/usr/lib/systemd/system/multi-user.target.wants/systemd-logind.service
    rm -rf ${IMAGE_ROOTFS}/usr/lib/systemd/logind.conf.d
    rm -rf ${IMAGE_ROOTFS}/usr/lib/systemd/system/graphical.target.wants
    rm -rf ${IMAGE_ROOTFS}/usr/lib/systemd/user/graphical-session.target
    rm -rf ${IMAGE_ROOTFS}/usr/lib/systemd/user/graphical-session-pre.target
    rm -rf ${IMAGE_ROOTFS}/usr/lib/systemd/user/bluetooth.target

    # Polkit
    rm -rf ${IMAGE_ROOTFS}/usr/share/polkit-1

    # Factory defaults
    rm -rf ${IMAGE_ROOTFS}/usr/share/factory

    > ${IMAGE_ROOTFS}/etc/securetty
}

mkdirs() {
    mkdir -p ${IMAGE_ROOTFS}/dev
    mkdir -p ${IMAGE_ROOTFS}/proc
    mkdir -p ${IMAGE_ROOTFS}/sys
    mkdir -p ${IMAGE_ROOTFS}/run
    mkdir -p ${IMAGE_ROOTFS}/dstack
    mkdir -p ${IMAGE_ROOTFS}/etc/wireguard
    mkdir -p ${IMAGE_ROOTFS}/var/lib/docker
    ln -sf dstack ${IMAGE_ROOTFS}/tapp

    # Aliases passwd files to a subdirectory
    mkdir -p ${IMAGE_ROOTFS}/etc/users
    mv ${IMAGE_ROOTFS}/etc/passwd ${IMAGE_ROOTFS}/etc/users/
    mv ${IMAGE_ROOTFS}/etc/shadow ${IMAGE_ROOTFS}/etc/users/
    ln -s users/passwd ${IMAGE_ROOTFS}/etc/passwd
    ln -s users/shadow ${IMAGE_ROOTFS}/etc/shadow
}
