MAINTAINER = "Nauman Shakir <nshakir@kopernikusauto.com>"
SUMMARY = "The GL Vendor-Neutral Dispatch library"
SECTION = "Libraries"

FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI = "https://github.com/NVIDIA/libglvnd/archive/v${PV}.tar.gz;downloadfilename=${BP}.tar.gz \
           file://0000-egl-pkgconfig.patch \
		   file://0001-glvnd-header.patch"
SRC_URI[md5sum] = "390f7934a22a17c9542621b727fc5908"
SRC_URI[sha256sum] = "baca5e1a78b96a112650cdc597be3f856d4754eb73a7bf3f6629e78a7e9f2b5a"

LICENSE = "MIT & BSD"
LIC_FILES_CHKSUM = "file://README.md;beginline=309;md5=f98ec0fbe6c0d2fbbd0298b5d9e664d3"

#S = "${WORKDIR}/${PN}"

DEPENDS = "python libx11 libxext xorgproto"
REQUIRED_DISTRO_FEATURES = "x11 opengl"

inherit autotools pkgconfig

PROVIDES = "virtual/libgl virtual/libgles1 virtual/libgles2 virtual/egl virtual/mesa"
RPROVIDES:${PN} = "libgl libgles1 libgles2 libegl egl xserver-xorg-extension-glx"

do_install:append() {
        mkdir -p ${D}${includedir}
        cp -rf ${S}/include/GL ${D}${includedir}/
        cp -rf ${S}/include/KHR ${D}${includedir}/
        cp -rf ${S}/include/EGL ${D}${includedir}/
        cp -rf ${S}/include/GLES ${D}${includedir}/
		cp -rf ${S}/include/GLES2 ${D}${includedir}/
		cp -rf ${S}/include/GLES3 ${D}${includedir}/
        cp -rf ${S}/include/glvnd ${D}${includedir}/
        cp -rf ${S}/include/glheader.h ${D}${includedir}/

		ln -sf libOpenGL.so.0 ${D}${libdir}/libOpenGL.so
		ln -sf libGLESv1_CM.so.1.2.0 ${D}${libdir}/libGLESv1_CM.so.1
		ln -sf libGLESv1_CM.so.1 ${D}${libdir}/libGLESv1_CM.so
		ln -sf libGLESv2.so.2.1.0 ${D}${libdir}/libGLESv2.so.2
		ln -sf libGLESv2.so.2 ${D}${libdir}/libGLESv2.so
		ln -sf libGLX.so.0 ${D}${libdir}/libGLX.so
		ln -sf libGL.so.1.7.0 ${D}${libdir}/libGL.so.1
		ln -sf libGL.so.1 ${D}${libdir}/libGL.so
		ln -sf libEGL.so.1.1.0 ${D}${libdir}/libEGL.so.1
		ln -sf libEGL.so.1 ${D}${libdir}/libEGL.so
}

FILES:${PN} = " \
	${libdir} \
"

FILES:${PN}-dev = " \
    ${includedir} \
"

INHIBIT_PACKAGE_DEBUG_SPLIT = "1"
INHIBIT_PACKAGE_STRIP = "1"
INSANE_SKIP:${PN}:append = "ldflags already-stripped dev-so"
INSANE_SKIP_libgl-nvidia:append = "ldflags"