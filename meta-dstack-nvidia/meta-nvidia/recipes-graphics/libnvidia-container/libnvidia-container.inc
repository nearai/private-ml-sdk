DESCRIPTION = "libnvidia-container"
HOMEPAGE = "https://github.com/NVIDIA/libnvidia-container"
LICENSE = "Apache-2.0"
# LIC_FILES_CHKSUM = "file://LICENSE;md5=3b83ef96387f14655fc854ddc3c6bd57"

LIC_FILES_CHKSUM = "\
    file://LICENSE;md5=3b83ef96387f14655fc854ddc3c6bd57 \
    file://deps/src/nvidia-modprobe-${NVIDIA_MODPROBE_VERSION}/modprobe-utils/nvidia-modprobe-utils.c;endline=22;md5=b6a3106a81660c726888d006853ada63 \
    file://deps/src/nvidia-modprobe-${NVIDIA_MODPROBE_VERSION}/modprobe-utils/pci-enum.h;endline=29;md5=ca948b6fabc48e616fccbf17247feebf \
    file://deps/src/nvidia-modprobe-${NVIDIA_MODPROBE_VERSION}/modprobe-utils/pci-sysfs.c;endline=25;md5=0449248350efd54938e7f8d25af965cb \
"

ELF_TOOLCHAIN_VERSION = "0.7.1"
NVIDIA_MODPROBE_VERSION = "550.40.07"
LIBTIRPC_VERSION = "1.3.4"

SRC_URI = "git://github.com/NVIDIA/libnvidia-container.git;protocol=https;name=libnvidia;branch=release-1.14 \
           git://github.com/NVIDIA/nvidia-modprobe.git;protocol=https;branch=main;name=modprobe;destsuffix=git/deps/src/nvidia-modprobe-${NVIDIA_MODPROBE_VERSION} \
           file://0001-build-fix.patch \
           file://0002-secomp-fix.patch \
           file://0003-fix-remove-buildpath-for-package-qa.patch \
           "

# SRCREV = "a4ef85ebc86688eeef667271abbc7cd4f1110cf6"
SRCREV_libnvidia = "d2eb0afe86f0b643e33624ee64f065dd60e952d4"
# Nvidia modprobe version 495.44
SRCREV_modprobe = "d6bce304f30b6661c9ab6a993f49340eafca7a7e"
SRCREV_FORMAT = "libnvidia_modprobe"

DEPENDS = " \
            curl-native ca-certificates-native go-native \
            coreutils-native \
            pkgconfig-native \
            libcap \
            elfutils \
            libtirpc134 \
            ldconfig-native \        
            "
RDEPENDS:${PN}:append= " ldconfig-compatibility-symlink containerd-config"


S = "${WORKDIR}/git"