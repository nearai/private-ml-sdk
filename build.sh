#!/bin/bash
set -e

THIS_DIR=$(dirname $(readlink -f $0))

export META_SUBDIR=meta-dstack-nvidia/
export IMAGE_NAME=dstack-nvidia-rootfs
export REPO_ROOT=${THIS_DIR}

${THIS_DIR}/${META_SUBDIR}/repro-build/repro-build.sh -n

for file in ${THIS_DIR}/${META_SUBDIR}/repro-build/dist/dstack-*.tar.gz; do
    # Skip files ending with -mr.tar.gz
    if [[ "$file" == *-mr.tar.gz ]]; then
        continue
    fi

    base_name=$(basename $file)
    dir_name=${base_name%.tar.gz}
    rm -rf images/${dir_name}
    tar -xzf $file -C images/
done
