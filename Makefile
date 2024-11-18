ifeq ($(BBPATH),)
$(error BBPATH is not set. Run `source dev-setup` first)
endif

.PHONY: all dist emu clean clean-dstack images

BUILD_DIR ?= bb-build
BUILD_IMAGES_DIR ?= ${BUILD_DIR}/tmp/deploy/images/tdx
DIST_DIR ?= ${BUILD_DIR}/dist

IMAGE_FILES = dstack-initramfs.cpio.gz \
	dstack-rootfs-tdx.cpio \
	dstack-rootfs-dev-tdx.cpio \
	bzImage \
	ovmf.fd

ABS_IMAGE_FILES = $(addprefix ${BUILD_IMAGES_DIR}/, ${IMAGE_FILES})

all: dist

dist: images
	DIST_DIR=${DIST_DIR} BUILD_DIR=${BUILD_DIR} ./dist.sh

images:
	bitbake dstack-initramfs dstack-rootfs dstack-rootfs-dev dstack-ovmf

test:
	make images dist

clean:
	git clean -xdff

clean-dstack:
	bitbake -c cleansstate dstack-guest dstack-rootfs dstack-rootfs-dev

clean-initrd:
	bitbake -c cleansstate dstack-initramfs
