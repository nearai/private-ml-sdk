FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI += "file://dstack-motd"

do_install:append() {
    if [ -f ${WORKDIR}/dstack-motd ];then
        bbnote "Installing custom dstack motd file"
        install -m 0644 ${WORKDIR}/dstack-motd ${D}${sysconfdir}/motd
    else
        bbwarn "Custom dstack-motd file not found in ${WORKDIR}"
        ls -la ${WORKDIR}
    fi
}
