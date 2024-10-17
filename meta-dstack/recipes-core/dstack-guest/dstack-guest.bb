SUMMARY = "Guest binaries for DStack, a decentralized computing stack"
DESCRIPTION = "${SUMMARY}"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/COPYING.MIT;md5=3da9cfbcb788c80a0384361b4de20420"

inherit systemd update-rc.d

REPO_ROOT = "${THISDIR}/../../.."

SRC_URI = "file://${REPO_ROOT}/dstack \
           file://tappd.init \
           file://tappd.service \
           file://llmnr.conf \
           file://tdx-attest.conf \
           file://tboot.sh \
           file://tboot.service \
           file://app-compose.service \
           "

S = "${WORKDIR}/${REPO_ROOT}/dstack"

SYSTEMD_PACKAGES = "${@bb.utils.contains('DISTRO_FEATURES','systemd','${PN}','',d)}"
SYSTEMD_SERVICE:${PN} = "${@bb.utils.contains('DISTRO_FEATURES','systemd','tappd.service tboot.service app-compose.service','',d)}"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

INITSCRIPT_PACKAGES += "${@bb.utils.contains('DISTRO_FEATURES','systemd','','${PN}',d)}"
INITSCRIPT_NAME:${PN} = "${@bb.utils.contains('DISTRO_FEATURES','systemd','','tappd.init',d)}"
INITSCRIPT_PARAMS:${PN} = "defaults"

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
    install -m 0755 ${WORKDIR}/tboot.sh ${D}${bindir}

    install -d ${D}${sysconfdir}/
    install -m 0644 ${WORKDIR}/tdx-attest.conf ${D}${sysconfdir}/tdx-attest.conf

    if ${@bb.utils.contains('DISTRO_FEATURES', 'systemd', 'true', 'false', d)}; then
        install -d ${D}${systemd_system_unitdir} \
                   ${D}${sysconfdir}/systemd/resolved.conf.d

        install -m 0644 ${WORKDIR}/tappd.service ${D}${systemd_system_unitdir}
        install -m 0644 ${WORKDIR}/tboot.service ${D}${systemd_system_unitdir}
        install -m 0644 ${WORKDIR}/app-compose.service ${D}${systemd_system_unitdir}

        install -m 0644 ${WORKDIR}/llmnr.conf ${D}${sysconfdir}/systemd/resolved.conf.d
    else
        install -d ${D}${sysconfdir}/init.d
        install -m 0755 ${WORKDIR}/tappd.init ${D}${sysconfdir}/init.d/tappd.init
        bberror "init scripts for sysvinit is not implemented yet"
    fi
}
