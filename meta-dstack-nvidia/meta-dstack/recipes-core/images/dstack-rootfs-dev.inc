include dstack-rootfs-base.inc

PACKAGE_INSTALL += "dropbear strace"
IMAGE_FEATURES = "debug-tweaks"
