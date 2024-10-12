.PHONY: build gen-measurements

build:
	cd srcs/poky/ && bitbake dstack-initramfs

gen-measurements:
	echo "Not implemented"