SUMMARY = "NVIDIA NSCQ library"
DESCRIPTION = "NVIDIA NSCQ (NVIDIA System Communication Queue) library for NVIDIA GPU systems"
HOMEPAGE = "https://developer.nvidia.com/"
LICENSE = "NVIDIA-Proprietary"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2cc00be68c1227a7c42ff3620ef75d05"

SRC_URI = "https://developer.download.nvidia.cn/compute/nvidia-driver/redist/libnvidia_nscq/linux-x86_64/libnvidia_nscq-linux-x86_64-${PV}-archive.tar.xz"
SRC_URI[md5sum] = "e749f6745d1cae3fd490afe79b5678f2"
SRC_URI[sha256sum] = "a4fdb36783499ae3df283ccc539e6ca5c9f29289c3263662cd91b9d24d777260"

S = "${WORKDIR}/libnvidia_nscq-linux-x86_64-${PV}-archive"

INSANE_SKIP:${PN} = "already-stripped ldflags"

do_configure[noexec] = "1"
do_compile[noexec] = "1"

do_install() {
    # Create directories
    install -d ${D}${libdir}
    install -d ${D}${bindir}

    # Install libraries
    install -m 0755 ${S}/lib/libnvidia-nscq.so.${PV} ${D}${libdir}
    ln -sf libnvidia-nscq.so.${PV} ${D}${libdir}/libnvidia-nscq.so.2.0
    ln -sf libnvidia-nscq.so.2.0 ${D}${libdir}/libnvidia-nscq.so.2
    ln -sf libnvidia-nscq.so.2 ${D}${libdir}/libnvidia-nscq.so

    # Install binaries
    install -m 0755 ${S}/bin/nscq-cli ${D}${bindir}
}

FILES:${PN} = "\
    ${libdir}/libnvidia-nscq.so.${PV} \
    ${libdir}/libnvidia-nscq.so.2.0 \
    ${libdir}/libnvidia-nscq.so.2 \
    ${libdir}/libnvidia-nscq.so \
    ${bindir}/nscq-cli \
"
