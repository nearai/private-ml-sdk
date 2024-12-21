# PACKAGECONFIG[glvnd] = "--enable-libglvnd,--disable-libglvnd,libglvnd"
PACKAGECONFIG[glvnd] = "-Dglvnd=true, -Dglvnd=false, libglvnd"
PACKAGECONFIG[egl] = "-Degl=enabled, -Degl=disabled"
PACKAGECONFIG:append = " glvnd"

#PACKAGES:append = " libglx-mesa libglx-mesa-dev"
# PACKAGES += "libglx-mesa libglx-mesa-dev"
PACKAGES:remove = "libgl-mesa libgl-mesa-dev libegl-mesa libegl-mesa-dev libgles1-mesa libgles1-mesa-dev libgles2-mesa libgles2-mesa-dev libgles3-mesa libgles3-mesa-dev"

PROVIDES:remove = "virtual/libgl virtual/libgles1 virtual/libgles2 virtual/libgles3 virtual/egl virtual/mesa"
PROVIDES += "virtual/egl-native virtual/libgl-native virtual/nativesdk-egl"
# PROVIDES_remove += "virtual/libgl virtual/libgles1 virtual/libgles2 virtual/libgles3 virtual/egl virtual/egl-native virtual/mesa"

# We ONLY want glx
do_install:append() {
	rm -f ${D}${includedir}/GL/gl.h
	rm -f ${D}${includedir}/GL/glext.h
	rm -f ${D}${includedir}/GL/glx.h
	rm -f ${D}${includedir}/GL/glxext.h
	
	rm -rf ${D}${includedir}/GLES
	rm -rf ${D}${includedir}/KHR
	rm -rf ${D}${includedir}/EGL
	rm -rf ${D}${includedir}/GLES2
	rm -rf ${D}${includedir}/GLES3
	rm -f ${D}${libdir}/pkgconfig/gl.pc
	rm -f ${D}${libdir}/pkgconfig/egl.pc
	rm -f ${D}${libdir}/pkgconfig/glesv1_cm.pc
	rm -f ${D}${libdir}/pkgconfig/glesv2.pc
	rm -f ${D}${libdir}/libEGL.so
	rm -f ${D}${libdir}/libGLESv1_CM.so
	rm -f ${D}${libdir}/libGLESv1_CM.so*
	rm -f ${D}${libdir}/libGLESv2.so*
}

FILES_libglx-mesa:append = " \
	${libdir}/libGLX_mesa.so.0.0.0 \
"

# FILES_libglx-mesa-dev:append = " \
#	${libdir}/libGLX_mesa.so.0 \
#	${libdir}/libGLX_mesa.so \
# "

# RDEPENDS_libglx-mesa-dev:append = " libglx-mesa"
# PACKAGECONFIG:append:pn-mesa-native = " egl"

