SUMMARY = "DStack guest binaries"
DESCRIPTION = "Guest binaries for DStack, a decentralized computing stack"
HOMEPAGE = "https://github.com/Phala-Network/dstack"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/COPYING.MIT;md5=3da9cfbcb788c80a0384361b4de20420"
DEPENDS:append = " update-rc.d-native"

SRC_URI = "git://github.com/Phala-Network/dstack;protocol=https;branch=master \
           file://tappd.init"
SRCREV = "9d5ad73d61d9c7bcacb5b2d822adbf4f62aa9631"

S = "${WORKDIR}/git"

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

    #
    # Create runlevel links
    #
    update-rc.d -r ${D} tappd start 90 2 3 4 5 .
}
