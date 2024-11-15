ifeq ($(BBPATH),)
$(error BBPATH is not set. Run `source dev-setup` first)
endif

.PHONY: all dist emu clean clean-dstack images

BUILD_DIR ?= build
BUILD_IMAGES_DIR ?= ${BUILD_DIR}/tmp/deploy/images/tdx
DIST_DIR ?= ${BUILD_DIR}/dist

IMAGE_FILES = dstack-initramfs.cpio.gz \
	dstack-rootfs-tdx.cpio \
	dstack-rootfs-dev-tdx.cpio \
	bzImage \
	ovmf.fd

ABS_IMAGE_FILES = $(addprefix ${BUILD_IMAGES_DIR}/, ${IMAGE_FILES})

all: dist

dist: $(ABS_IMAGE_FILES)
	DIST_DIR=${DIST_DIR} BUILD_DIR=${BUILD_DIR} ./dist.sh

$(ABS_IMAGE_FILES):
	make images

images:
	bitbake dstack-initramfs dstack-rootfs dstack-rootfs-dev dstack-ovmf

emu:
	TD=0 ./run_td.sh

run:
	./run_td.sh

test:
	make images dist run

clean:
	git clean -xdff

clean-dstack:
	bitbake -c cleansstate dstack-guest dstack-rootfs dstack-rootfs-dev

clean-initrd:
	bitbake -c cleansstate dstack-initramfs
