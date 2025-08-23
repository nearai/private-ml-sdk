SUMMARY = "NVIDIA Fabric Manager for NVSwitch systems"
DESCRIPTION = "NVIDIA Fabric Manager provides NVSwitch management for NVIDIA HGX and DGX systems"
HOMEPAGE = "https://developer.nvidia.com/"
LICENSE = "NVIDIA-Proprietary"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2cc00be68c1227a7c42ff3620ef75d05"

SRC_URI = "https://developer.download.nvidia.com/compute/nvidia-driver/redist/fabricmanager/linux-x86_64/fabricmanager-linux-x86_64-${PV}-archive.tar.xz"
SRC_URI[md5sum] = "a71788f11f6edabf69df32a7b9dcfa68"
SRC_URI[sha256sum] = "8d24cacde4554d471899ad426f46a349d5ca0a2e8acd45c2a76381c8f496491e"

S = "${WORKDIR}/fabricmanager-linux-x86_64-${PV}-archive"

DEPENDS = ""
RDEPENDS:${PN} = "bash zlib"

INSANE_SKIP:${PN} = "already-stripped ldflags"

do_configure[noexec] = "1"
do_compile[noexec] = "1"

inherit systemd

SYSTEMD_AUTO_ENABLE = "enable"
SYSTEMD_SERVICE:${PN} = "nvidia-fabricmanager.service"

do_install() {
    # Create directories
    install -d ${D}${bindir}
    install -d ${D}${libdir}
    install -d ${D}${datadir}/nvidia/nvswitch
    install -d ${D}${systemd_system_unitdir}

    # Install binaries
    install -m 0755 ${S}/bin/nv-fabricmanager ${D}${bindir}
    install -m 0755 ${S}/bin/nvidia-fabricmanager-start.sh ${D}${bindir}
    install -m 0755 ${S}/bin/nvswitch-audit ${D}${bindir}

    # Install libraries
    install -m 0644 ${S}/lib/libnvfm.so.1 ${D}${libdir}
    ln -sf libnvfm.so.1 ${D}${libdir}/libnvfm.so

    # Install config files
    install -m 0644 ${S}/etc/fabricmanager.cfg ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/etc/fabricmanager_multinode.cfg ${D}${datadir}/nvidia/nvswitch/

    # Install topology files
    install -m 0644 ${S}/share/nvidia/nvswitch/dgx2_hgx2_topology ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/dgxa100_hgxa100_topology ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/dgxh100_hgxh100_topology ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/dgxh800_hgxh800_topology ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/mgxh20_nvl16_topology ${D}${datadir}/nvidia/nvswitch/

    # Install multi-node topology files
    install -m 0644 ${S}/share/nvidia/nvswitch/dgxgh200_hgxgh200_8gpus_topology ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/dgxgh200_hgxgh200_16gpus_topology ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/dgxgh200_hgxgh200_16gpus_trunk_connections.csv ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/dgxgh200_hgxgh200_16gpus_osfp_connections.csv ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/dgxgh200_hgxgh200_16gpus_osfp_cable_connections.csv ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/dgxgh200_hgxgh200_32gpus_topology ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/dgxgh200_hgxgh200_32gpus_trunk_connections.csv ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/dgxgh200_hgxgh200_32gpus_osfp_connections.csv ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/dgxgh200_hgxgh200_32gpus_osfp_cable_connections.csv ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/gh200_nvlink_32gpus_topology ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/gb200_nvl36r1_c2g4_topology ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/gb200_nvl36r1_c2g2_topology ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/gb200_nvl72r1_c2g4_topology ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/gb200_nvl72r2_c2g4_topology ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/gb200_nvl72r2_c2g2_topology ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/gb200_nvl576r16_c2g4_topology ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/gb200_nvl8r1_c2g4_etf_topology ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/gb200_nvl8r1_c2g4_etf_nso_topology ${D}${datadir}/nvidia/nvswitch/
    install -m 0644 ${S}/share/nvidia/nvswitch/gb200_nvl4r1_c2g2_etf_topology ${D}${datadir}/nvidia/nvswitch/

    # Install systemd service
    install -m 0644 ${S}/systemd/nvidia-fabricmanager.service ${D}${systemd_system_unitdir}
}

FILES:${PN} = "\
    ${bindir}/nv-fabricmanager \
    ${bindir}/nvidia-fabricmanager-start.sh \
    ${bindir}/nvswitch-audit \
    ${libdir}/libnvfm.so.1 \
    ${libdir}/libnvfm.so \
    ${datadir}/nvidia/nvswitch/* \
    ${systemd_system_unitdir}/nvidia-fabricmanager.service \
"
