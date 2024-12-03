# How Dstack CVM boot

Phala's Dstack provides generic base CVM images to run Applications, where an Application is defined in a manifest file.
The manifest is a JSON file that looks like this:

```json
{
  // Version of the manifest format
  "manifest_version": 1,
  // Name of the Application
  "name": "Example",
  // Brief information about the Application
  "description": "This is an example Application",
  // Version of the Application
  "version": "1.0.0",
  // Features required by the Application
  "features": ["kms", "tproxy-net"],
  // Operator that allowed to upgrade the Application
  "operator": "eee5eae48e79b2e75178328c7c585b89d676eaae616f03f9a1813aaed820745",
  // Runner to use to run the Application
  "runner": "docker-compose",
  // Content of the docker compose file to use if the runner is docker-compose
  "docker_compose_file": "services:\\n  nginx:\\n    image: nginx@sha256:eee5eae48e79b2e75178328c7c585b89d676eaae616f03f9a1813aaed820745a\\n    ports:\\n      - \\"80:80\\"\\n"
}
```

where the field `docker_compose_file` is the entire content of the docker compose file defines what services to run.

The features field defines which features the Application requires, where available features are:

- kms: Enable external KMS as key provider. If not enabled, the CVM will clear all data on disk at each reboot.
- `tproxy-net`: the CVM connects to tproxy when started so that user can access the Application services through the tproxy's TLS reverse proxy server or SOCKS5 proxy server.

We define `app_id` as `sha256(app_manifest_json)[0:20]`, which serves as a unique identifier for each Application.

Notable qemu config to run the CVM:

| Component | Configuration |
| --- | --- |
| Machine Type | tdx |
| Hard Drive | a blank disk `hda.qcow2` |
| CDROM | rootfs.iso (containing rootfs.cpio) |
| Shared Folder | Host folder in CVM mounted to `/mnt/host-shared` containing:
- app-manifest.json
- env.json
- kms-ca.crt |
| Kernel | `bzImage` |
| Initrd | `initramfs.cpio.gz` |

The configurations above are measured to RTMR0~2 in the CVM by the ovmf firmware.

The `env.json` contains the following self-describing content:

```json
{
  "kms_url": "https://kms.<operation domain>",
  "tproxy_url": "https://tproxy.<operation domain>",
  "rootfs_hash": "<hash of the rootfs.cpio>"
}
```

## The CVM boot process

When booting into the initrd, the system executes the following steps:

1. mount shared folder `host-shared` to `/mnt/host-shared` in the initrd.
2. copy files from `/mnt/host-shared` to `/host-shared` in the initrd to avoid host modification during the initrd boot.
3. calculate `app_id` from `app-manifest.json`, `kms_ca_hash` from `kms-ca.crt`, and read `rootfs_hash` from `env.json`.
4. extend the `rootfs_hash`, `app_id` and `kms_ca_hash` to `RTMR3`.
5. Generate a temporary RA-TLS certificate which contains the TDX quote inside.
6. App keys provisioning:
6.1 If KMS is enabled, request keys from KMS via curl(HTTPS) with the RA-TLS certificate as client certificate and the `kms-ca.crt` as TLS authority anchor.
6.2 If KMS is not enabled, the CVM will generate one-time random keys for the Application. The keys will be dropped after the CVM reboots.
7. KMS handles the request in the following steps:
    - Verify the TDX quote inside the RA-TLS certificate, abort if failed.
    - Extract the `app_id`, `rootfs_hash` from the RA-TLS certificate.
    - Derive the `app_root_key` by `HKDF(["app-root-key", kms_root_key, app_id])`.
    - Derive the `disk_encrypt_key` by:
        - `KDF(["app-disk-crypt-key", kms_root_key, rootfs_hash, app_id])`
    - Return the keys to the CVM.
8. After the keys are received, the CVM will do steps `8.x` if `/mnt/host-shared/.bootstraped` does not exist, or goto `9` otherwise.
    - `8.1`: mount /dev/sr0 to /mnt/cdrom.
    - `8.2`: format `/dev/sda` using luks with the `disk_encrypt_key`.
    - `8.3`: luks open `/dev/sda` and mount it to `/root`.
    - `8.4`: extract `/mnt/cdrom/rootfs.cpio` to `/root` and **calculate the rootfs hash in the extracting command**.
    - `8.5`: compare the calculated rootfs hash with the `rootfs_hash` in `env.json`, abort if not match.
    - `8.6`: copy `/host-shared/app-manifest.json` to `/root/tapp/app-manifest.json` and extract the inner docker compose file to `/root/tapp/docker-compose.yaml`.
    - `8.7`: copy app keys to `/root/tapp/app-keys.json`.
    - `8.8`: create `/root/.bootstraped`.
    - `8.9`: create `/mnt/host-shared/.bootstraped`.
9. luks open `/dev/sda` and mount it to `/root` if not mounted.
10. ensure `/root/.bootstraped` exists, abort if not to avoid to boot from an incomplete rootfs extraction.
11. switch root to `/root` so it continues to systemd boot process.
12. in the `tboot.service`, it connects to the tproxy via RA-TLS if `tproxy-net` feature is set, and setup encrypted networking between the CVM and the tproxy.
13. in the `app-compose.service`, it starts the docker compose services defined in the `docker-compose.yaml` file.
14. in the `tappd.service`, it starts `tappd` which provides RPC for containers to get TDX quote and derive keys.


## The KMS API

When the App enables the `kms` feature, in its compose file, it will request keys from KMS via curl(HTTPS) with the RA-TLS certificate as client certificate and the `kms-ca.crt` as TLS authority anchor.

The KMS API is defined as an HTTP endpoint at `/prpc/Kms.GetAppKeys` without any parameters or body. All information about the Application is embedded in the RA-TLS certificate. The KMS verifies the TDX quote, and issues keys, certificates to the CVM if the quote is valid. The keys include:

- `app_root_key`: The root key for the Application.
- `app_root_cert`: The root certificate for the Application. This certificate is signed by the KMS root certificate. App can use this certificate to issue certificates for the Application usage, such as end-to-end TLS connections.
- `disk_crypt_key`: The key to setup Full Disk Encryption for the rootfs.
- `env_crypt_key`: The key to encrypt/decrypt the environment variables.
