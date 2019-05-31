Hyper-V RCT Service Client
==========================

A Python client and CLI for the https://github.com/cloudbase/rct-service
REST API.

Command-line API
----------------

To display the current RCT status for a virtual disk::

    rct --auth-key swordfish \
    --base-url https://hypervhost:6677 \
    --remote-vhd-path "C:\VHDS\mydisk.vhdx" \
    --show-rct-info \
    --cert-path C:\path\to\cert.pem

To enable RCT for a virtual disk::

    rct --auth-key swordfish \
    --base-url https://hypervhost:6677 \
    --remote-vhd-path "C:\VHDS\mydisk.vhdx" \
    --enable-rct \
    --cert-path C:\path\to\cert.pem

To disable RCT for a virtual disk::

    rct --auth-key swordfish \
    --base-url https://hypervhost:6677 \
    --remote-vhd-path "C:\VHDS\mydisk.vhdx" \
    --disable-rct \
    --cert-path C:\path\to\cert.pem

To download the changed sectors since a given RCT ID into a local RAW disk
(useful for incremental backups)::

    rct --auth-key swordfish \
    --base-url https://hypervhost:6677 \
    --remote-vhd-path "C:\VHDS\mydisk.vhdx" \
    --local-disk-path mydisk.raw \
    --rct-id "rctX:5bfde23b:ce75:4303:b54f:6c18394f105c:00000001" \
    --cert-path C:\path\to\cert.pem

The RCT ID is optional, if not provided the entire disk content is retrieved.
The local disk path contains the data obtained from the RCT service, in RAW
format (it can be converted to other formats with e.g. qemu-img if needed).

The certificate path is needed to verify the service's TLS identity, if omitted
the verification is disabled.
