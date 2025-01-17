SUMMARY = "NVidia Graphics Driver"
LICENSE = "NVIDIA-Proprietary"
LIC_FILES_CHKSUM = "file://../LICENSE;md5=01c5e23f445259a6d1b4867efec45d22"

NVIDIA_ARCHIVE_NAME = "NVIDIA-Linux-${TARGET_ARCH}-${PV}"
NVIDIA_SRC = "${WORKDIR}/${NVIDIA_ARCHIVE_NAME}"
SRC_URI = " \
	https://us.download.nvidia.com/tesla/${PV}/${NVIDIA_ARCHIVE_NAME}.run \
"
SRC_URI[md5sum] = "d41045e47d511b9d0bd0c365118bcbbb"
SRC_URI[sha256sum] = "2e859ae5f912a9a47aaa9b2d40a94a14f6f486b5d3b67c0ddf8b72c1c9650385"

do_unpack() {
	chmod +x ${DL_DIR}/${NVIDIA_ARCHIVE_NAME}.run
	rm -rf ${NVIDIA_SRC}
	${DL_DIR}/${NVIDIA_ARCHIVE_NAME}.run -x --target ${NVIDIA_SRC}
}

do_make_scripts[noexec] = "1"

include nvidia-kernel-module.inc
include nvidia-libs.inc
