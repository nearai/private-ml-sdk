#!/bin/bash
SCRIPT_DIR=$(
    cd $(dirname $0)
    pwd
)
ACTION=$1

META_DIR=$SCRIPT_DIR
DSTACK_DIR=$SCRIPT_DIR/dstack
CERTS_DIR=$(pwd)/certs
IMAGES_DIR=$(pwd)/images
RUN_DIR=$(pwd)/run
RUST_BUILD_DIR=$(pwd)/rust-target
CERBOT_WORKDIR=$RUN_DIR/certbot
KMS_UPGRADE_REGISTRY_DIR=$RUN_DIR/kms/upgrade_registry
KMS_CERT_LOG_DIR=$RUN_DIR/kms/cert_log/

CONFIG_FILE=./build-config.sh

check_config() {
    local template_file=$1
    local config_file=$2

    # extract all variables in template file
    local variables=$(grep -oE '^\s*[A-Z_]+=' $template_file | sort)

    # check if each variable is set in config file
    local var missing=0
    for var in $variables; do
        if ! grep -qE "^\s*$var" $config_file; then
            echo "Variable $var is not set in $config_file"
            missing=1
        fi
    done
    if [ $missing -ne 0 ]; then
        return 1
    fi
    return 0
}

require_config() {
    cat <<'EOF' >build-config.sh.tpl
# DNS domain of kms rpc and tproxy rpc
# *.1022.kvin.wang resolves to 10.0.2.2 which is the IP of the host system
# from CVMs point of view
KMS_DOMAIN=kms.1022.kvin.wang
TPROXY_DOMAIN=tproxy.1022.kvin.wang

# CIDs allocated to VMs start from this number of type unsigned int32
TEEPOD_CID_POOL_START=20000
# CID pool size
TEEPOD_CID_POOL_SIZE=1000

# Base port for RPC services
BASE_PORT=13000

TEEPOD_RPC_LISTEN_PORT=$BASE_PORT
# Whether port mapping from host to CVM is allowed
TEEPOD_PORT_MAPPING_ENABLED=false
# Host API configuration, type of uint32
TEEPOD_VSOCK_LISTEN_PORT=$BASE_PORT

KMS_RPC_LISTEN_PORT=$(($BASE_PORT + 1))
TPROXY_RPC_LISTEN_PORT=$(($BASE_PORT + 2))

TPROXY_WG_INTERFACE=tproxy-$USER
TPROXY_WG_LISTEN_PORT=$(($BASE_PORT + 3))
TPROXY_WG_IP=10.3.3.1
TPROXY_SERVE_PORT=$(($BASE_PORT + 4))

BIND_PUBLIC_IP=0.0.0.0

TPROXY_PUBLIC_DOMAIN=app.kvin.wang

# for certbot
CF_API_TOKEN=
CF_ZONE_ID=
ACME_URL=https://acme-staging-v02.api.letsencrypt.org/directory
EOF
    if [ -f $CONFIG_FILE ]; then
        source $CONFIG_FILE
        # check if any variable in build-config.sh.tpl is not set in build-config.sh.
        # This might occur if the build-config.sh is generated from and old repo.
        check_config build-config.sh.tpl $CONFIG_FILE
        if [ $? -ne 0 ]; then
            exit 1
        fi
        rm -f build-config.sh.tpl

        if [ -z "$TPROXY_SERVE_PORT" ]; then
            TPROXY_SERVE_PORT=${TPROXY_LISTEN_PORT1}
        fi
        TAPPD_PORT=8090
    else
        mv build-config.sh.tpl $CONFIG_FILE
        echo "Config file $CONFIG_FILE created, please edit it to configure the build"
        exit 1
    fi
}

# Step 1: build binaries
build_host() {
    echo "Building binaries"
    (cd $DSTACK_DIR && cargo build --release --target-dir ${RUST_BUILD_DIR})
    cp ${RUST_BUILD_DIR}/release/{tproxy,kms,teepod,certbot,ct_monitor,supervisor} .
}

# Step 2: build guest images
build_guest() {
    echo "Building guest images"
    if [ -z "$BBPATH" ]; then
        source $SCRIPT_DIR/dev-setup $1
    fi
    make -C $META_DIR dist DIST_DIR=$IMAGES_DIR BB_BUILD_DIR=${BBPATH}
}

# Step 4: generate config files

build_cfg() {
    echo "Building config files"
    TPROXY_WG_KEY=$(wg genkey)
    TPROXY_WG_PUBKEY=$(echo $TPROXY_WG_KEY | wg pubkey)
    # kms
    cat <<EOF >kms.toml
log_level = "info"

[rpc]
address = "127.0.0.1"
port = $KMS_RPC_LISTEN_PORT

[rpc.tls]
key = "$CERTS_DIR/rpc.key"
certs = "$CERTS_DIR/rpc.crt"

[rpc.tls.mutual]
ca_certs = "$CERTS_DIR/tmp-ca.crt"
mandatory = false

[core]
cert_dir = "$CERTS_DIR"

[core.auth_api]
type = "dev"

[core.onboard]
quote_enabled = false
address = "127.0.0.1"
port = $KMS_RPC_LISTEN_PORT
auto_bootstrap_domain = "$KMS_DOMAIN"
EOF

    # tproxy
    cat <<EOF >tproxy.toml
log_level = "info"
address = "127.0.0.1"
port = $TPROXY_RPC_LISTEN_PORT

[tls]
key = "$CERTS_DIR/tproxy-rpc.key"
certs = "$CERTS_DIR/tproxy-rpc.cert"

[tls.mutual]
ca_certs = "$CERTS_DIR/tproxy-ca.cert"
mandatory = false

[core]
kms_url = "https://localhost:$KMS_RPC_LISTEN_PORT"
rpc_domain = "$TPROXY_DOMAIN"
run_as_tapp = false

[core.sync]
enabled = false

[core.certbot]
enabled = true
# Path to the working directory
workdir = "$CERBOT_WORKDIR"
# ACME server URL
acme_url = "$ACME_URL"
# Cloudflare API token
cf_api_token = "$CF_API_TOKEN"
# Cloudflare zone ID
cf_zone_id = "$CF_ZONE_ID"
# Auto set CAA record
auto_set_caa = true
# Domain to issue certificates for
domain = "*.$TPROXY_PUBLIC_DOMAIN"
# Check renewal interval
renew_interval = "30m"
# Number of days before expiration to trigger renewal
renew_days_before = "10d"
# Renew timeout
renew_timeout = "10m"

[core.wg]
private_key = "$TPROXY_WG_KEY"
public_key = "$TPROXY_WG_PUBKEY"
listen_port = $TPROXY_WG_LISTEN_PORT
ip = "$TPROXY_WG_IP/24"
reserved_net = "$TPROXY_WG_IP/31"
client_ip_range = "$TPROXY_WG_IP/24"
config_path = "$RUN_DIR/wg.conf"
interface = "$TPROXY_WG_INTERFACE"
endpoint = "10.0.2.2:$TPROXY_WG_LISTEN_PORT"

[core.proxy]
cert_chain = "$CERBOT_WORKDIR/live/cert.pem"
cert_key = "$CERBOT_WORKDIR/live/key.pem"
base_domain = "$TPROXY_PUBLIC_DOMAIN"
listen_addr = "$BIND_PUBLIC_IP"
listen_port = $TPROXY_SERVE_PORT
tappd_port = $TAPPD_PORT
EOF

    # teepod
    cat <<EOF >teepod.toml
log_level = "info"
address = "127.0.0.1"
port = $TEEPOD_RPC_LISTEN_PORT
image_path = "$IMAGES_DIR"
run_path = "$RUN_DIR/vm"
kms_url = "https://localhost:$KMS_RPC_LISTEN_PORT"

[cvm]
kms_urls = ["https://$KMS_DOMAIN:$KMS_RPC_LISTEN_PORT"]
tproxy_urls = ["https://$TPROXY_DOMAIN:$TPROXY_RPC_LISTEN_PORT"]
cid_start = $TEEPOD_CID_POOL_START
cid_pool_size = $TEEPOD_CID_POOL_SIZE
[cvm.port_mapping]
enabled = $TEEPOD_PORT_MAPPING_ENABLED
address = "127.0.0.1"
range = [
    { protocol = "tcp", from = 1, to = 20000 },
    { protocol = "udp", from = 1, to = 20000 },
]

[gateway]
base_domain = "$TPROXY_PUBLIC_DOMAIN"
port = $TPROXY_SERVE_PORT
tappd_port = $TAPPD_PORT

[host_api]
port = $TEEPOD_VSOCK_LISTEN_PORT
EOF

    mkdir -p $RUN_DIR
    mkdir -p $CERBOT_WORKDIR/backup/preinstalled
}

build_wg() {
    echo "Setting up wireguard interface"
    # Step 6: setup wireguard interface
    # Check if the WireGuard interface exists
    if ! ip link show $TPROXY_WG_INTERFACE &>/dev/null; then
        sudo ip link add $TPROXY_WG_INTERFACE type wireguard
        sudo ip address add $TPROXY_WG_IP dev $TPROXY_WG_INTERFACE
        sudo ip link set $TPROXY_WG_INTERFACE up
        echo "created and configured WireGuard interface $TPROXY_WG_INTERFACE"
    else
        echo "WireGuard interface $TPROXY_WG_INTERFACE already exists"
    fi
    # sudo ip route add $TPROXY_WG_CLIENT_IP_RANGE dev $TPROXY_WG_INTERFACE
}

download_image() {
    local VERSION=""
    local IS_DEV=""

    # Parse arguments to support both formats
    if [[ "$1" == "-dev" ]]; then
        IS_DEV=1
        VERSION=$2
    else
        VERSION=$1
    fi

    echo "Downloading image $VERSION${IS_DEV:+ (dev)}"

    TAG=v$VERSION
    if [ x"$IS_DEV" = x"1" ]; then
        BASENAME=dstack-dev-$VERSION
    else
        BASENAME=dstack-$VERSION
    fi
    URL=https://github.com/Dstack-TEE/meta-dstack/releases/download/$TAG/$BASENAME.tar.gz
    if [ -d $IMAGES_DIR/$BASENAME ]; then
        echo "Image already exists"
    else
        mkdir -p $IMAGES_DIR/$BASENAME.tmp
        curl -L $URL -o $IMAGES_DIR/$BASENAME.tar.gz
        tar -xvf $IMAGES_DIR/$BASENAME.tar.gz -C $IMAGES_DIR/$BASENAME.tmp
        rm -f $IMAGES_DIR/$BASENAME.tar.gz
        if [ -d $IMAGES_DIR/$BASENAME.tmp/$BASENAME ]; then
            mv $IMAGES_DIR/$BASENAME.tmp/$BASENAME $IMAGES_DIR/$BASENAME
            rm -rf $IMAGES_DIR/$BASENAME.tmp
        else
            mv $IMAGES_DIR/$BASENAME.tmp $IMAGES_DIR/$BASENAME
        fi
    fi
}

case $ACTION in
host)
    build_host
    ;;
guest)
    build_guest $2
    ;;
cfg)
    require_config
    build_cfg
    ;;
certs)
    require_config
    ;;
wg)
    require_config
    build_wg
    ;;
dl)
    download_image $2 $3
    ;;
"")
    # If no action specified, build everything
    require_config
    build_host
    build_guest
    build_cfg
    build_wg
    ;;
*)
    echo "Invalid action: $ACTION"
    echo "Valid actions are: host, guest, cfg, certs, wg, dl"
    exit 1
    ;;
esac
