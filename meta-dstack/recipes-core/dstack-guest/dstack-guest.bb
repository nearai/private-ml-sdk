SUMMARY = "Guest binaries for DStack, a decentralized computing stack"
DESCRIPTION = "${SUMMARY}"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/COPYING.MIT;md5=3da9cfbcb788c80a0384361b4de20420"

DEPENDS:append = " update-rc.d-native"

REPO_ROOT = "${THISDIR}/../../.."

SRC_URI = "file://${REPO_ROOT}/dstack \
           file://tappd.init"

S = "${WORKDIR}/${REPO_ROOT}/dstack"

inherit cargo_bin

do_configure() {
    cargo_bin_do_configure
}

do_compile() {
    cargo_bin_do_compile
}

do_compile[network] = "1"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${CARGO_BINDIR}/iohash ${D}${bindir}
    install -m 0755 ${CARGO_BINDIR}/tdxctl ${D}${bindir}
    install -m 0755 ${CARGO_BINDIR}/tappd ${D}${bindir}
    install -d ${D}${sysconfdir}/init.d
    install -m 0755 ${WORKDIR}/tappd.init ${D}${sysconfdir}/init.d/tappd

    install -d ${D}$/mnt/host-shared

    #
    # Create runlevel links
    #
    update-rc.d -r ${D} tappd start 90 2 3 4 5 .
}
