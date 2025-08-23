SUMMARY = "NVidia Graphics Driver"
LICENSE = "NVIDIA-Proprietary"
LIC_FILES_CHKSUM = "file://../LICENSE;md5=92aa2e2af6aa0bcba1c3fe49da021937"

NVIDIA_ARCHIVE_NAME = "NVIDIA-Linux-${TARGET_ARCH}-${PV}"
NVIDIA_SRC = "${WORKDIR}/${NVIDIA_ARCHIVE_NAME}"
SRC_URI = " \
    https://us.download.nvidia.com/tesla/${PV}/${NVIDIA_ARCHIVE_NAME}.run \
"
SRC_URI[md5sum] = "4d0264e320d09f614b086c3ad99a75c5"
SRC_URI[sha256sum] = "0256867e082caf93d7b25fa7c8e69b316062a9c6c72c6e228fad7b238c6fa17d"

RDEPENDS:${PN} = "nvidia-modprobe-config"

do_unpack() {
	chmod +x ${DL_DIR}/${NVIDIA_ARCHIVE_NAME}.run
	rm -rf ${NVIDIA_SRC}
	${DL_DIR}/${NVIDIA_ARCHIVE_NAME}.run -x --target ${NVIDIA_SRC}
}

do_make_scripts[noexec] = "1"

include nvidia-kernel-module.inc
include nvidia-libs.inc
