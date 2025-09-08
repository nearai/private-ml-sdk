FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

LINUX_VERSION_EXTENSION = "-dstack"

SRC_URI += "file://dstack-docker.cfg \
            file://dstack-docker.scc \
            file://dstack-tdx.cfg \
            file://dstack-tdx.scc \
            file://dstack.cfg \
            file://dstack.scc"

KERNEL_FEATURES:append = " features/cgroups/cgroups.scc \
                          features/overlayfs/overlayfs.scc \
                          features/netfilter/netfilter.scc \
                          features/fuse/fuse.scc \
                          cfg/fs/squashfs.scc \
                          dstack-docker.scc \
                          dstack.scc"

KERNEL_FEATURES:append = " ${@bb.utils.contains("DISTRO_FEATURES", "dm-verity", " features/device-mapper/dm-verity.scc", "" ,d)}"

KERNEL_FEATURES:append:tdx = " dstack-tdx.scc"

# Enable BTF
KERNEL_DEBUG = "True"

do_deploy:append() {
    install -m 0644 ${B}/.config ${DEPLOYDIR}/kernel-config
}
