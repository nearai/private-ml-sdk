FILESEXTRAPATHS:prepend := "${THISDIR}/cfg:"

SRC_URI += "file://dstack-docker.cfg \
            file://dstack-docker.scc \
            file://dstack-tdx.cfg \
            file://dstack-tdx.scc \
            file://dstack.cfg \
            file://dstack.scc"

KERNEL_FEATURES:append = " features/cgroups/cgroups.scc \
                          features/overlayfs/overlayfs.scc \
                          features/netfilter/netfilter.scc \
                          dstack-docker.scc \
                          dstack.scc"

KERNEL_FEATURES:append:tdx = " dstack-tdx.scc"
