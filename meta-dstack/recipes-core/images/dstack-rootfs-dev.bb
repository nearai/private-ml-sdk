require ${THISDIR}/dstack-rootfs.bb

PACKAGE_INSTALL += "dropbear"
IMAGE_FEATURES = "debug-tweaks"
IMAGE_BASENAME = "dstack-rootfs-dev"
