DESCRIPTION = "NVIDIA Container Toolkit"
HOMEPAGE = "https://github.com/NVIDIA/nvidia-container-toolkit"
LICENSE = "Apache-2.0"
LIC_FILES_CHKSUM = "file://src/${GO_IMPORT}/LICENSE;md5=3b83ef96387f14655fc854ddc3c6bd57"

SRC_URI = "git://github.com/NVIDIA/nvidia-container-toolkit.git;protocol=https;branch=release-1.14"
SRCREV = "4668c511de4b311c96bc3dd0310bff40b75083bd"

SRC_URI += "file://config.toml"
SRC_URI += "file://daemon.json"
SRC_URI += "file://0001-Fix-cgo-LDFLAGS-for-go-1.21-and-later.patch;patchdir=src/${GO_IMPORT}"
GO_IMPORT = "github.com/NVIDIA/nvidia-container-toolkit"

DEPENDS = " \
            curl-native ca-certificates-native go-native \
            coreutils-native \
            "

S = "${WORKDIR}/git"
