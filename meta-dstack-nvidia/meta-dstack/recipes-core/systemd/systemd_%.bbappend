FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"

SRC_URI += "file://blacklist-autofs4.conf"

do_install:append() {
    # Disable systemd-vconsole-setup.service
    rm -f ${D}${systemd_system_unitdir}/sysinit.target.wants/systemd-vconsole-setup.service

    # Install modprobe blacklist for autofs4
    install -d ${D}${sysconfdir}/modprobe.d
    install -m 0644 ${WORKDIR}/blacklist-autofs4.conf ${D}${sysconfdir}/modprobe.d/
}

SYSTEMD_SERVICE:${PN}-vconsole-setup = ""

FILES:${PN} += "${sysconfdir}/modprobe.d/blacklist-autofs4.conf"
