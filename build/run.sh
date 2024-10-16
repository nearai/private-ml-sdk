#!/bin/bash

VMDIR=${1:-./mock}

PROCESS_NAME=qemu

KERNEL=./tmp/deploy/images/tdx/bzImage
INITRD=./tmp/deploy/images/tdx/dstack-initramfs-tdx.cpio.gz
VDA=${VMDIR}/vda.qcow2
VDA_SIZE=10G
CMDLINE="console=ttyS0"
CONFIG_DIR=${VMDIR}/shared
TD=${TD:-1}
TDVF_FIRMWARE=/usr/share/ovmf/OVMF.fd
RO=${RO:-off}
CID=$(( ( RANDOM % 10000 )  + 3 ))

ARGS="${ARGS} -kernel ${KERNEL}"
ARGS="${ARGS} -initrd ${INITRD}"

if [ "${TD}" == "1" ]; then
	MACHINE_ARGS=",confidential-guest-support=tdx,hpet=off"
	PROCESS_NAME=td
	TDX_ARGS="-device vhost-vsock-pci,guest-cid=${CID} -object tdx-guest,id=tdx"
	BIOS="-bios ${TDVF_FIRMWARE}"
fi

echo INITRD=${INITRD}
echo ARGS=${ARGS}
echo VDA=${VDA}
echo CMDLINE=${CMDLINE}
echo TD=${TD}
echo TDX_ARGS=${TDX_ARGS}
echo BIOS=${BIOS}

sleep 2

if [ ! -f ${VDA} ]; then
    qemu-img create -f qcow2 ${VDA} ${VDA_SIZE}
fi
qemu-system-x86_64 \
		   -accel kvm \
		   -m 8G -smp 16 \
		   -name ${PROCESS_NAME},process=${PROCESS_NAME},debug-threads=on \
		   -cpu host \
		   -machine q35,kernel_irqchip=split${MACHINE_ARGS} \
		   ${BIOS} \
		   ${TDX_ARGS} \
		   -nographic \
		   -nodefaults \
		   -chardev stdio,id=ser0,signal=on -serial chardev:ser0 \
		   -device virtio-net-pci,netdev=nic0_td -netdev user,id=nic0_td \
		   -drive file=${VDA},if=none,id=virtio-disk0 -device virtio-blk-pci,drive=virtio-disk0 \
		   -virtfs local,path=${CONFIG_DIR},mount_tag=host-shared,readonly=${RO},security_model=mapped,id=virtfs0 \
		   ${ARGS} \
		   -append "${CMDLINE}"
