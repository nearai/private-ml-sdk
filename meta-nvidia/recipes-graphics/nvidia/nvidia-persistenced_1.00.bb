SUMMARY = "NVidia Persistenced systemd service"
LICENSE = "CLOSED"

SRC_URI += "\
    file://nvidia-persistenced.service \
    file://nvidia-lkca.conf \
"

inherit systemd

SYSTEMD_PACKAGES = "${PN}"
SYSTEMD_SERVICE:${PN} = "nvidia-persistenced.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

do_install() {
    install -d ${D}${systemd_unitdir}/system
    install -m 0644 ${WORKDIR}/nvidia-persistenced.service ${D}${systemd_unitdir}/system
    install -d ${D}${sysconfdir}/modprobe.d
    install -m 0644 ${WORKDIR}/nvidia-lkca.conf ${D}${sysconfdir}/modprobe.d/
}
