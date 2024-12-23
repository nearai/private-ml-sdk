#!/bin/bash
set -e

THIS_DIR=$(dirname $(readlink -f $0))

export META_SUBDIR=meta-dstack-nvidia/
export IMAGE_NAME=dstack-nvidia-rootfs
export REPO_ROOT=${THIS_DIR}

${THIS_DIR}/${META_SUBDIR}/repro-build/repro-build.sh -n

for file in ${THIS_DIR}/${META_SUBDIR}/repro-build/dist/*; do
    base_name=$(basename $file)
    dir_name=${base_name%.tar.gz}
    rm -rf images/${dir_name}
    mkdir -p images/${dir_name}
    tar -xzf $file -C images/${dir_name}
done

