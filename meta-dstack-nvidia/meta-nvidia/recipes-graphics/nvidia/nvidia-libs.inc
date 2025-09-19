DESCRIPTION = "Linker and Installer of Nvidia Kernel modules, libs and binaries"
SECTION = "Installer Tools"
MAINTAINER = "Nauman Shakir <nshakir@kopernikusauto.com>"

RDEPENDS:${PN} += "${PN}-firmware ${PN}-private-libs"

addlib() {
    cp ${NVIDIA_SRC}/${1}.so.${PV} ${D}${libdir}/
    ln -sf ${1}.so.${PV} ${D}${libdir}/${1}.so.1
    ln -sf ${1}.so.1 ${D}${libdir}/${1}.so
}

# Function to add library if it exists
addlib_if_exists() {
    if [ -f ${NVIDIA_SRC}/${1}.so.${PV} ]; then
        addlib ${1}
        return 0
    fi
    return 1
}

addbin() {
    install -m 755 -D ${NVIDIA_SRC}/${1} ${D}${bindir}/${1}
}

# Function to add binary if it exists
addbin_if_exists() {
    if [ -f ${NVIDIA_SRC}/${1} ]; then
        addbin ${1}
        return 0
    fi
    return 1
}

do_install:append() {
	install -d ${D}${libdir}
	install -d ${D}${bindir}

    addlib libnvidia-ml
    addlib libnvidia-allocator
    addlib libnvidia-eglcore
    addlib libnvidia-encode
    addlib libnvidia-glcore
    addlib libnvidia-gpucomp
    addlib libnvidia-ngx
    addlib libnvidia-nvvm
    addlib libnvidia-opencl
    addlib libnvidia-rtcore
    addlib libnvidia-tls
    addlib libnvidia-cfg
    addlib libnvidia-opticalflow
    addlib libnvidia-glsi
    addlib libnvidia-glvkspirv
    addlib libcuda
    addlib libnvcuvid
    addlib libnvidia-pkcs11-openssl3
    addlib libnvidia-pkcs11
    
    # CUDA Toolkit libraries
    addlib_if_exists libnvidia-ptxjitcompiler
    
    # Check for libnvptxcompiler (may be static library)
    if [ -f ${NVIDIA_SRC}/libnvptxcompiler_static.a ]; then
        cp ${NVIDIA_SRC}/libnvptxcompiler_static.a ${D}${libdir}/
    fi
    
    # CUDA Runtime and compiler libraries  
    if addlib_if_exists libnvrtc; then
        ln -sf libnvrtc.so.${PV} ${D}${libdir}/libnvrtc.so.12
    fi
    
    if addlib_if_exists libnvrtc-builtins; then
        ln -sf libnvrtc-builtins.so.${PV} ${D}${libdir}/libnvrtc-builtins.so.12
    fi
    
    # Additional CUDA libraries
    addlib_if_exists libcudadebugger
    addlib_if_exists libnvidia-nvjitlink

    cp ${NVIDIA_SRC}/libnvidia-api.so.1 ${D}${libdir}/
    ln -sf libnvidia-api.so.1 ${D}${libdir}/libnvidia-api.so
    ln -sf libnvidia-nvvm.so.${PV} ${D}${libdir}/libnvidia-nvvm.so.4

    addbin nvidia-smi
    addbin nvidia-debugdump
    addbin nvidia-persistenced
    addbin nvidia-modprobe
    
    # CUDA toolkit binaries if present
    addbin_if_exists nvidia-cuda-mps-control
    addbin_if_exists nvidia-cuda-mps-server

    # Copy the firmware to the target directory
	install -d ${D}${libdir}/firmware/nvidia/${PV}
    cp ${NVIDIA_SRC}/firmware/* ${D}${libdir}/firmware/nvidia/${PV}/
}

FILES:${PN}:append= " ${libdir} ${bindir}"


INHIBIT_PACKAGE_DEBUG_SPLIT = "1"
INHIBIT_PACKAGE_STRIP = "1"

INSANE_SKIP:${PN}:append = " ldflags already-stripped dev-so"
INSANE_SKIP_libgl-nvidia:append = " ldflags"
INSANE_SKIP_:append = " ldflags"

# Create a separate package for GSP firmware files
PACKAGES =+ "${PN}-firmware"
FILES:${PN}-firmware = "${libdir}/firmware/nvidia/${PV}/*"
FILES:${PN}:remove = "${libdir}/firmware/nvidia/${PV}/*"
INSANE_SKIP:${PN}-firmware += "arch"

PACKAGES =+ "${PN}-private-libs"
FILES:${PN}-private-libs = "${libdir}/libnvidia-pkcs11.so*"
INSANE_SKIP:${PN}-private-libs:append = " ldflags already-stripped dev-so"
EXCLUDE_PACKAGES_FROM_SHLIBS = "${PN}-private-libs"
SKIP_FILEDEPS:${PN}-private-libs = "1"
