#!/usr/bin/env python
# Copyright 2019 Cloudbase Solutions Srl
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import argparse
import logging
import requests
from requests.packages.urllib3 import exceptions
import sys

from rct import client

DEFAULT_MAX_BYTES_PER_REQUEST = 20 * 1024 * 1024
LOG = logging


def _parse_arguments():
    def _get_long_type():
        if sys.version_info >= (3, 0):
            return int
        else:
            return long

    parser = argparse.ArgumentParser(
        description='Backup a Hyper-V virtual disk using RCT', add_help=True)
    parser.add_argument(
        '--base-url', type=str, default="https://localhost:6677",
        help='Base RCT service URL')
    parser.add_argument(
        '--auth-key', type=str, required=True,
        help='Auth key for the RCT service')
    parser.add_argument(
        '--remote-vhd-path', type=str, required=True,
        help='Path of the Hyper-V virtual disk (VHD or VHDX)')
    parser.add_argument(
        '--cert-path', type=str,
        help="X509 server certificate to be verified")
    parser.add_argument(
        '--rct-id', type=str,
        help="RCT id, retrieves the entire disk's content if not provided")
    parser.add_argument(
        '--max-bytes-per-request', type=_get_long_type(),
        default=DEFAULT_MAX_BYTES_PER_REQUEST,
        help="Max virtual disk bytes requested at once, aggregating multiple "
             "disk ranges. Set to 0 to perform one request for each virtual "
             "disk range. Default value is: %d" %
             DEFAULT_MAX_BYTES_PER_REQUEST)

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--show-rct-info', action='store_true',
        help='Show the current RCT info for this virtual disk')
    group.add_argument(
        '--enable-rct', action='store_true', dest="enable_rct",
        help='Enable RCT for this virtual disk')
    group.add_argument(
        '--disable-rct', action='store_false', dest="enable_rct",
        help='Disable RCT for this virtual disk')
    group.add_argument(
        '--local-disk-path', type=str, help='Local RAW disk path')

    args = parser.parse_args()
    return args


def _show_rct_info(base_url, auth_key, disk_path, verify):
    disk_info = client.get_disk_info(
        base_url, auth_key, disk_path, verify=verify)
    LOG.info("Virtual disk info: %s" % disk_info)
    rct_info = client.get_rct_info(
        base_url, auth_key, disk_path, verify=verify)
    LOG.info("RCT status: %s" % rct_info)


def _enable_rct(base_url, auth_key, disk_path, enable_rct, verify):
    client.set_rct_info(
        base_url, auth_key, disk_path, enabled=enable_rct, verify=verify)
    rct_info = client.get_rct_info(
        base_url, auth_key, disk_path, verify=verify)
    LOG.info("New RCT status: %s" % rct_info)


def _download_to_local_raw_disk(base_url, auth_key, disk_path, rct_id,
                                local_filename, max_bytes_per_request,
                                verify):
    with open(local_filename, 'wb') as f:
        client.download_disk(base_url, auth_key, disk_path, rct_id, f,
                             max_bytes_per_request, verify)


def main():
    requests.packages.urllib3.disable_warnings(
        exceptions.InsecureRequestWarning)
    requests.packages.urllib3.disable_warnings(
        exceptions.SubjectAltNameWarning)

    LOG.basicConfig(format="%(message)s", level=logging.INFO)

    args = _parse_arguments()
    verify = args.cert_path or False

    if args.local_disk_path:
        _download_to_local_raw_disk(
            args.base_url, args.auth_key, args.remote_vhd_path, args.rct_id,
            args.local_disk_path, args.max_bytes_per_request, verify)
    elif args.show_rct_info:
        _show_rct_info(
            args.base_url, args.auth_key, args.remote_vhd_path, verify)
    else:
        _enable_rct(
            args.base_url, args.auth_key, args.remote_vhd_path,
            args.enable_rct, verify)


if __name__ == "__main__":
    main()
