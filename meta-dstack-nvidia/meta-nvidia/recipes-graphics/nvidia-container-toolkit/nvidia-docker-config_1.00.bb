DESCRIPTION = "NVIDIA Docker Config"
LICENSE = "CLOSED"

SRC_URI = "file://daemon.json"

do_install() {
    install -d ${D}/etc/docker
    install -m 0644 ${WORKDIR}/daemon.json ${D}/etc/docker/daemon.json
}
