include dstack-rootfs-base.inc

IMAGE_INSTALL += "packagegroup-core-ssh-dropbear strace tcpdump gdb gdbserver"
IMAGE_FEATURES = "debug-tweaks"
