import hashlib
from typing import List, Union, Tuple
import requests

from pinet_util import *

RASPBIAN_DATA_ROOT_TAR_XZ = "/opt/PiNet/sd_images/raspbian_full_latest_root.tar.xz"


def locate_raspbian_download() -> Tuple[str, str]:
    fileLogger.debug("Downloading NOOBS OS list")
    os_list = requests.get("https://downloads.raspberrypi.org/os_list_v3.json").json()
    for os_item in os_list["os_list"]:
        if os_item["os_name"].lower() == "raspbian full":
            raspbian_os_entry = os_item
            fileLogger.debug("Found OS entry from NOOBS OS list")
            break
    else:
        fileLogger.error("Unable to find Raspbian full entry in NOOBS OS list...")
        return None, None

    fileLogger.debug(f"Downloading NOOBS OS partiton list from {raspbian_os_entry['partitions_info']}")
    partition_info = requests.get(raspbian_os_entry['partitions_info']).json()["partitions"]
    for partition_id, partition in enumerate(partition_info):
        if partition['filesystem_type'] == "ext4":
            main_data_partition_record = partition
            main_data_partition_id = partition_id
            fileLogger.debug("Found Raspbian partition")
            break
    else:
        fileLogger.error(f"Unable to find Raspbian full data partition entry in NOOBS OS partiton list from {raspbian_os_entry['partitions_info']}...")
        return None, None
    
    return raspbian_os_entry["tarballs"][main_data_partition_id], main_data_partition_record["sha256sum"]


def download_latest_raspbian_image():
    data_tar_url, data_tar_sha256_hash = locate_raspbian_download()
    if os.path.exists(RASPBIAN_DATA_ROOT_TAR_XZ):
        fileLogger.debug("Raspbian download already exists, checking hash.")
        hash_sum = get_sha256_hash(RASPBIAN_DATA_ROOT_TAR_XZ)
        fileLogger.debug(f"New Raspbian download hash is {data_tar_sha256_hash} vs current hash of {hash_sum}.")
        if hash_sum != data_tar_sha256_hash:
            download_file(data_tar_url, RASPBIAN_DATA_ROOT_TAR_XZ)
            return True
    else:
        download_file(data_tar_url, RASPBIAN_DATA_ROOT_TAR_XZ)
        return True
    return False




def pinet_buster_installer():
    make_folder("/opt/PiNet/sd_images/raspbian_data")
    new_file_downloaded = download_latest_raspbian_image()
    if new_file_downloaded or not os.path.exists("/opt/PiNet/sd_images/raspbian_data/var"):
        remove_file("/opt/PiNet/sd_images/raspbian_data")
        make_folder("/opt/PiNet/sd_images/raspbian_data")
        extract_tar_xz_file(RASPBIAN_DATA_ROOT_TAR_XZ, "/opt/PiNet/sd_images/raspbian_data/")


def main():
    pinet_buster_installer()


main()