DESCRIPTION = "NVIDIA CUDA Toolkit"
SECTION = "devel"
LICENSE = "CLOSED"

PV = "12.0.1"
PR = "r0"

SRC_URI = "https://developer.download.nvidia.com/compute/cuda/${PV}/local_installers/cuda_${PV}_525.85.12_linux.run"
# SRC_URI = "file://cuda_12.0.1_525.85.12_linux.run"

SRC_URI[md5sum] = "2a5b80f322151e25ed792029e4571318"
SRC_URI[sha256sum] = "1b205a06272f1463f477276fdab903f3f666917c068e520738001e69c7a1875b"

S = "${WORKDIR}"

# Depend on libcudart and any other libraries/tools your applications need

DEPENDS = "ncurses"
# Allow the recipe to fetch the CUDA Toolkit installer
LICENSE_FLAGS_ACCEPTED = "commercial"

# inherit cuda

do_fetch[noexec] = "1"
do_unpack[noexec] = "1"
do_configure[noexec] = "1"

do_compile() {
    :
}
do_custom_fetch() {
    wget -P ${DL_DIR} ${SRC_URI}
    chmod +x ${DL_DIR}/cuda_12.0.1_525.85.12_linux.run

}

do_unpack() {
    # Your existing unpack commands here

    # Debug: List the contents of WORKDIR
    ls -lah ${WORKDIR}
}

do_install() {
    # Define where we expect the CUDA toolkit to be extracted
    # export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:${D}${libdir}"
    export LD_LIBRARY_PATH="/lib:/usr/lib:/usr/local/lib:${LD_LIBRARY_PATH}"
    local cuda_extract_dir=${D}${prefix}/cuda
    
    install -d ${WORKDIR}/tmpdir
    echo "Checking CUDA installer file..."
    if [ -f ${DL_DIR}/cuda_${PV}_525.85.12_linux.run ]; then
        echo "CUDA installer found. Proceeding with installation..."

        # Ensure the CUDA installer is executable
        chmod +x ${DL_DIR}/cuda_${PV}_525.85.12_linux.run
        # Create the directory for the CUDA toolkit
        install -d ${cuda_extract_dir}

        # Install the CUDA toolkit
        # Attempt to install the CUDA toolkit
        if ${DL_DIR}/cuda_${PV}_525.85.12_linux.run --silent --installpath=${cuda_extract_dir} --tmpdir=${WORKDIR}/tmpdir --toolkit --override; then
            echo "CUDA Toolkit installation successful."
        else
            echo "Installation failed or incomplete. CUDA Toolkit did not install as expected, but continuing with the process..."
        fi
        # Check if installation was successful
        if [ "$(ls -A ${cuda_extract_dir})" ]; then
            echo "Installation successful. Copying CUDA Toolkit components..."

            # Recursively copy all contents to their respective locations
            cp -r ${cuda_extract_dir}/* ${D}${prefix}/cuda/
            rm -rf ${cuda_extract_dir}

            echo "CUDA Toolkit installation completed."
        else
            echo "Installation failed. CUDA Toolkit did not install any files."
        fi
    else
        bbfatal "CUDA installer file not found in ${DL_DIR}."
    fi
}

addtask do_custom_fetch before do_fetch
# addtask do_copy_installer_preinstall before do_install

FILES:${PN}:append= "${bindir}/* ${libdir}/* ${includedir}/*"
FILES:${PN}:append= "${prefix}/cuda ${prefix}"

COMPATIBLE_HOST = "(x86_64).*-linux"

# PROVIDES = "cuda"

do_make_scripts[noexec] = "1"
INSANE_SKIP:${PN}:append = "ldflags already-stripped dev-so"

RDEPENDS:${PN} = "\
    nvidia \
    "