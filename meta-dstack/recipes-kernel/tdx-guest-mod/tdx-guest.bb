SUMMARY = "TDX guest kernel module for Intel Trust Domain Extensions"
DESCRIPTION = "${SUMMARY}"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/COPYING.MIT;md5=3da9cfbcb788c80a0384361b4de20420"

inherit module

REPO_ROOT = "${THISDIR}/../../.."

SRC_DIR = "${@oe.utils.conditional('DSTACK_SRC_URI', '', '${REPO_ROOT}/dstack/mod-tdx-guest', 'git/mod-tdx-guest', d)}"
SRC_URI = "${@oe.utils.conditional('DSTACK_SRC_URI', '', 'file://${REPO_ROOT}/dstack', '${DSTACK_SRC_URI}', d)}"
SRCREV = "${DSTACK_SRC_REV}"

S = "${WORKDIR}/${SRC_DIR}"

RPROVIDES:${PN} += "tdx-guest-ko"
