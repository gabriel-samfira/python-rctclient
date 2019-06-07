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

import logging
import requests

LOG = logging

CHUNK_SIZE = 10 * 1024 * 1024


def get_disk_info(base_url, auth_key, disk_path, verify):
    url = "%s/vdisk/%s/info" % (base_url, disk_path)
    r = requests.get(
        url, headers={"auth_key": auth_key}, verify=verify)
    r.raise_for_status()
    return r.json()


def get_rct_info(base_url, auth_key, disk_path, verify):
    url = "%s/vdisk/%s/rct" % (base_url, disk_path)
    r = requests.get(
        url, headers={"auth_key": auth_key}, verify=verify)
    r.raise_for_status()
    return r.json()


def set_rct_info(base_url, auth_key, disk_path, enabled, verify):
    url = "%s/vdisk/%s/rct?enabled=%s" % (
        base_url, disk_path, str(enabled).lower())
    r = requests.put(
        url, headers={"auth_key": auth_key}, verify=verify)
    r.raise_for_status()


def query_disk_changes(base_url, auth_key, disk_path, rct_id, verify):
    url = "%s/vdisk/%s/rct/%s/changes" % (base_url, disk_path, rct_id)
    r = requests.get(
        url, headers={"auth_key": auth_key}, verify=verify)
    r.raise_for_status()
    return r.json()


def get_disk_content(base_url, auth_key, disk_path, out_file, ranges, verify):
    if not ranges:
        return

    url = "%s/vdisk/%s/content" % (base_url, disk_path)
    with requests.post(
            url, headers={"auth_key": auth_key}, stream=True, json=ranges,
            verify=verify) as r:
        r.raise_for_status()

        current_range_index = 0
        range_bytes_written = 0
        current_range = ranges[current_range_index]
        length = current_range["length"]
        out_file.seek(current_range["offset"])
        total_bytes_written = 0

        for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
            while True:
                # The loop is needed in case the chunk includes data from
                # multiple ranges
                if not chunk:
                    break
                else:
                    buf = chunk[0:length - range_bytes_written]
                    out_file.write(buf)
                    range_bytes_written += len(buf)
                    total_bytes_written += len(buf)

                    if (length == range_bytes_written and
                            current_range_index + 1 < len(ranges)):
                        current_range_index += 1
                        range_bytes_written = 0
                        current_range = ranges[current_range_index]
                        length = current_range["length"]
                        out_file.seek(current_range["offset"])

                    chunk = chunk[len(buf):]

        expected_bytes = sum([v["length"] for v in ranges])
        if total_bytes_written != expected_bytes:
            raise Exception(
                "Incomplete response. Bytes expected: "
                "%d, received: %d" % (expected_bytes, total_bytes_written))


def download_disk(base_url, auth_key, disk_path, rct_id, out_file,
                  max_bytes_per_request, verify, progress_cb=None):
    disk_info = get_disk_info(
        base_url, auth_key, disk_path, verify=verify)
    LOG.info("Virtual disk info: %s" % disk_info)
    virtual_disk_size = disk_info["virtual_size"]

    if rct_id:
        rct_info = get_rct_info(base_url, auth_key, disk_path, verify=verify)
        LOG.info("RCT status: %s" % rct_info)

        if not rct_info["enabled"]:
            raise Exception("RCT not enabled for this disk")

        disk_changes = query_disk_changes(
            base_url, auth_key, disk_path, rct_id, verify=verify)
        LOG.info("Disk changes: %d" % len(disk_changes))
        LOG.info("Total bytes: %d" % sum(d["length"] for d in disk_changes))
    else:
        # Get the entire disk
        LOG.info("Retrieving entire disk content. Total bytes: %d" %
                 virtual_disk_size)
        disk_changes = [{"offset": 0, "length": virtual_disk_size}]

    out_file.truncate(virtual_disk_size)
    tot_size = 0
    total_transferred = 0
    total_length = sum([change["length"] for change in disk_changes])
    ranges = []
    for i, disk_change in enumerate(disk_changes):
        LOG.info("Requesting disk data %d/%d. Offset: %d, length: %d" %
                 (i + 1, len(disk_changes), disk_change["offset"],
                  disk_change["length"]))

        offset = disk_change["offset"]
        length = disk_change["length"]
        get_data = (max_bytes_per_request == 0 or
                    tot_size + length >= max_bytes_per_request)

        while True:
            if not max_bytes_per_request:
                range_length = length
            else:
                range_length = min(
                    length, max_bytes_per_request - tot_size)

            tot_size += range_length
            ranges.append({"offset": offset, "length": range_length})

            if get_data:
                get_disk_content(base_url, auth_key, disk_path, out_file,
                                 ranges, verify=verify)
                total_transferred += tot_size
                if progress_cb is not None:
                    progress_cb(total_transferred, total_length)
                ranges = []
                tot_size = 0

            length -= range_length
            if not length:
                break
            offset += range_length
            get_data = True
            LOG.info("Range split due to transfer size limit. "
                     "Remaining length: %d" % length)

    if ranges:
        get_disk_content(base_url, auth_key, disk_path, out_file, ranges,
                         verify=verify)
        total_transferred += sum([d["length"] for d in ranges])
        if progress_cb is not None:
            progress_cb(total_transferred, total_length)
