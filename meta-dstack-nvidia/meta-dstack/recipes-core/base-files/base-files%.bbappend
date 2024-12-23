do_install:append() {
    # Remove the motd file from poky so we can use our own
    rm -rf ${D}${sysconfdir}/motd
}
