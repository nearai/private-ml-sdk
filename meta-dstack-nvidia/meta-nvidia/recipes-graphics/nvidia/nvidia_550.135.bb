SUMMARY = "NVidia Graphics Driver"
LICENSE = "NVIDIA-Proprietary"
LIC_FILES_CHKSUM = "file://../LICENSE;md5=01c5e23f445259a6d1b4867efec45d22"

NVIDIA_ARCHIVE_NAME = "NVIDIA-Linux-${TARGET_ARCH}-${PV}"
NVIDIA_SRC = "${WORKDIR}/${NVIDIA_ARCHIVE_NAME}"
SRC_URI = " \
	https://us.download.nvidia.com/XFree86/Linux-x86_64/${PV}/${NVIDIA_ARCHIVE_NAME}.run \
"
SRC_URI[md5sum] = "a8c3ae0076f11e864745fac74bfdb01f"
SRC_URI[sha256sum] = "112047f5644005690e762141a55b422195ca6b90ef4024a47bad4c9e818788a9"

do_unpack() {
	chmod +x ${DL_DIR}/${NVIDIA_ARCHIVE_NAME}.run
	rm -rf ${NVIDIA_SRC}
	${DL_DIR}/${NVIDIA_ARCHIVE_NAME}.run -x --target ${NVIDIA_SRC}
}

do_make_scripts[noexec] = "1"

include nvidia-kernel-module.inc
include nvidia-libs.inc
