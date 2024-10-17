ifeq ($(BBPATH),)
$(error BBPATH is not set. Run `source dev-setup` first)
endif

# INITRAMFS_IMAGE=${BUILD_DIR}/tmp/deploy/images/tdx/dstack-initramfs.cpio.gz
# ROOTFS_IMAGE=${BUILD_DIR}/tmp/deploy/images/tdx/dstack-rootfs-tdx.cpio
# KERNEL_IMAGE=${BUILD_DIR}/tmp/deploy/images/tdx/bzImage
# OVMF_FIRMWARE=${BUILD_DIR}/tmp/deploy/images/tdx/ovmf.fd

.PHONY: all dist emu clean

BUILD_DIR ?= build
BUILD_IMAGES_DIR ?= ${BUILD_DIR}/tmp/deploy/images/tdx
DIST_DIR ?= ${BUILD_DIR}/dist

IMAGE_FILES = dstack-initramfs.cpio.gz \
	dstack-rootfs-tdx.cpio \
	bzImage \
	ovmf.fd

ABS_IMAGE_FILES = $(addprefix ${BUILD_IMAGES_DIR}, ${IMAGE_FILES})


all: dist

dist: ${ABS_IMAGE_FILES}
	DIST_DIR=${DIST_DIR} BUILD_DIR=${BUILD_DIR} ./dist.sh

${ABS_IMAGE_FILES}:
	bitbake dstack-initramfs dstack-rootfs ovmf

emu:
	TD=0 ./run_td.sh
run:
	./run_td.sh

clean:
	git clean -xdff