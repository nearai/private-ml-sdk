"""
This script calculates the RTMR3 hash from the given docker-compose.yml file and KMS CA certificate.

Usage:
    python calc_rtmr3.py by-file --compose <docker-compose-file> --ca-cert <ca-cert-file>
    python calc_rtmr3.py by-vm --images-dir <images-dir> --vm-dir <vm-dir>

Log from a CVM:
```
FSINIT: Extending rootfs hash to RTMR, hash=bf06bf167df2d81dd54095e8a540e802dc634a31a96e1a448a20201a63d0bd21
Extended RTMR 3: bf06bf167df2d81dd54095e8a540e802dc634a31a96e1a448a20201a63d0bd2100000000000000000000000000000000
FSINIT: Extending app id to RTMR, app_id=3327603e03f5bd1f830812ca4a789277fc31f577573ed149f47e0e2f3558e99e
Extended RTMR 3: 3327603e03f5bd1f830812ca4a789277fc31f577573ed149f47e0e2f3558e99e00000000000000000000000000000000
FSINIT: Extending ca cert hash to RTMR, ca_cert_hash=663a81d65c1c749fd4ae4634fa0452553396eb9e956c90b903d47d45ae10d719
Extended RTMR 3: 663a81d65c1c749fd4ae4634fa0452553396eb9e956c90b903d47d45ae10d71900000000000000000000000000000000
ParsedReport {
    attributes: 0000001000000000,
    xfam: e702060000000000,
    mrtd: 7ba9e262ce6979087e34632603f354dd8f8a870f5947d116af8114db6c9d0d74c48bec4280e5b4f4a37025a10905bb29,
    mrconfigid: 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000,
    mrowner: 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000,
    mrownerconfig: 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000,
    rtmr0: 698a1e5764ff07840695fb46c809949cca352e6c9d26fc37dce872402adc071b3b069b0b217c1dcda68cf914253b6842,
    rtmr1: 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000,
    rtmr2: 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000,
    rtmr3: 3c30787034cd9aabff0347bc8f08b9f24a0f6ae914bbca0f9aba681e857aa57a7a7cc5b0b67231779cdc345f107707c5,
    servtd_hash: 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000,
}
```
"""

import hashlib
import argparse
import json
from pathlib import Path


INIT_MR= "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"

def rtmr_replay(history: list[str]):
    """
    Replay the RTMR history to calculate the final RTMR value.
    """
    if len(history) == 0:
        return INIT_MR
    mr = bytes.fromhex(INIT_MR)
    for content in history:
        # mr = sha384(concat(mr, content))
        # if content is shorter than 48 bytes, pad it with zeros
        content = bytes.fromhex(content)
        if len(content) < 48:
            content = content.ljust(48, b'\0')
        mr = hashlib.sha384(mr + content).digest()
    return mr.hex()


def calc_rtmr3(rootfs_hash: str, app_id: str, ca_cert_hash: str):
    """
    Calculate the RTMR3 hash from the given rootfs hash, app id and CA certificate hash.
    """
    return rtmr_replay([rootfs_hash, app_id, ca_cert_hash])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate the RTMR3 hash from the given docker-compose.yml file and KMS CA certificate.")
    parser.add_argument("mode", choices=["by-file", "by-vm"])
    parser.add_argument("--rootfs-cpio", help="The rootfs.cpio file to use.")
    parser.add_argument("--compose", help="The docker-compose.yml file to use.")
    parser.add_argument("--ca-cert", help="The KMS CA certificate to use.")
    parser.add_argument("--images-dir", type=Path, help="The directory containing the VM images to use.")
    parser.add_argument("--vm-dir", type=Path, help="The directory of a deployed VM.")
    args = parser.parse_args()

    if args.mode == "by-file":
        rootfs_hash = hashlib.sha256(open(args.rootfs_cpio, "rb").read()).hexdigest()
        app_id = hashlib.sha256(open(args.compose, "rb").read()).hexdigest()
        ca_cert_hash = hashlib.sha256(open(args.ca_cert, "rb").read()).hexdigest()
        rtmr3 = calc_rtmr3(rootfs_hash, app_id, ca_cert_hash)
        print(rtmr3)
    elif args.mode == "by-vm":
        vm_config = json.load(open(args.vm_dir / "config.json", "r"))
        image_dir = args.images_dir / vm_config["image"]
        image_metadata = json.load(open(image_dir / "metadata.json", "r"))
        rootfs_hash = image_metadata["rootfs_hash"]
        compose_file = args.vm_dir / "shared" / "docker-compose.yaml"
        ca_cert_file = args.vm_dir / "shared" / "certs" / "ca.cert"
        app_id = hashlib.sha256(open(compose_file, "rb").read()).hexdigest()
        ca_cert_hash = hashlib.sha256(open(ca_cert_file, "rb").read()).hexdigest()
        rtmr3 = calc_rtmr3(rootfs_hash, app_id, ca_cert_hash)
        print(rtmr3)
