NVIDIA_GROUP = "acpid \
    nvidia \
    nvidia-firmware \
    nvidia-persistenced \
    nvidia-container-toolkit \
    nvidia-docker-config \
    kernel-module-video \
"
KERNEL_MODULE_AUTOLOAD:append = " nvidia nvidia-drm nvidia-modeset nvidia-uvm video"
IMAGE_INSTALL:append = " ${NVIDIA_GROUP}"
