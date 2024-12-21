SUMMARY = "Dstack initramfs files"

LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/COPYING.MIT;md5=3da9cfbcb788c80a0384361b4de20420"

SRC_URI = "file://init \
    file://kmfs-setup \
    file://boot-vars"

FILES:${PN} = "*"

inherit allarch

S = "${WORKDIR}"

do_install() {
    install -d ${D}/
    install -d ${D}/scripts
    install -d ${D}/${bindir}
    install -m 0755 ${S}/init ${D}/init
    install -m 0755 ${S}/kmfs-setup ${D}/scripts/kmfs-setup
    install -m 0755 ${S}/boot-vars ${D}/scripts/boot-vars
}
