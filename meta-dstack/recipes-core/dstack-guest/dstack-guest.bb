SUMMARY = "Guest binaries for DStack, a decentralized computing stack"
DESCRIPTION = "${SUMMARY}"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/COPYING.MIT;md5=3da9cfbcb788c80a0384361b4de20420"

inherit systemd

REPO_ROOT = "${THISDIR}/../../.."

SRC_DIR = '${REPO_ROOT}/dstack'
SRC_URI = 'file://${REPO_ROOT}/dstack \
           file://docker-daemon.json'
SRCREV = "${DSTACK_SRC_REV}"

S = "${WORKDIR}/${SRC_DIR}"

RDEPENDS:${PN} += "bash"

DSTACK_SERVICES = "dstack-guest-agent.service tboot.service app-compose.service"
SYSTEMD_PACKAGES = "${@bb.utils.contains('DISTRO_FEATURES','systemd','${PN}','',d)}"
SYSTEMD_SERVICE:${PN} = "${@bb.utils.contains('DISTRO_FEATURES','systemd','${DSTACK_SERVICES}','',d)}"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

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
    install -d ${D}${sysconfdir}/docker
    install -d ${D}${sysconfdir}/systemd/journald.conf.d
    install -m 0755 ${CARGO_BINDIR}/iohash ${D}${bindir}
    install -m 0755 ${CARGO_BINDIR}/tdxctl ${D}${bindir}
    install -m 0755 ${CARGO_BINDIR}/dstack-guest-agent ${D}${bindir}
    install -m 0755 ${S}/basefiles/tboot.sh ${D}${bindir}
    install -m 0755 ${S}/basefiles/app-compose.sh ${D}${bindir}
    install -m 0755 ${WORKDIR}/docker-daemon.json ${D}${sysconfdir}/docker/daemon.json
    install -m 0644 ${S}/basefiles/journald.conf ${D}${sysconfdir}/systemd/journald.conf.d/dstack.conf

    install -d ${D}${sysconfdir}/
    install -m 0644 ${S}/basefiles/tdx-attest.conf ${D}${sysconfdir}/tdx-attest.conf

    if ${@bb.utils.contains('DISTRO_FEATURES', 'systemd', 'true', 'false', d)}; then
        install -d ${D}${systemd_system_unitdir} \
                   ${D}${sysconfdir}/systemd/resolved.conf.d

        install -m 0644 ${S}/basefiles/dstack-guest-agent.service ${D}${systemd_system_unitdir}
        install -m 0644 ${S}/basefiles/tboot.service ${D}${systemd_system_unitdir}
        install -m 0644 ${S}/basefiles/app-compose.service ${D}${systemd_system_unitdir}
        install -m 0644 ${S}/basefiles/llmnr.conf ${D}${sysconfdir}/systemd/resolved.conf.d
    fi
}
