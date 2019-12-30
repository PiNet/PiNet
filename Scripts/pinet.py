import glob
import hashlib
from typing import List, Union, Tuple
import requests

from pinet_util import *

RASPBIAN_DATA_ROOT_TAR_XZ = "/opt/PiNet/sd_images/raspbian_full_latest_root.tar.xz"
RASPBIAN_DATA_ROOT = "/opt/PiNet/sd_images/raspbian_data"


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


def install_ltsp():
    sources = glob.glob("/etc/apt/sources.list.d/ltsp-ubuntu-ppa*")
    if not sources:
        fileLogger.debug("LTSP PPA sources not currently installed, installing now.")
        run_bash("add-apt-repository ppa:ltsp -y")
        run_bash("apt update")
        run_bash("apt install -y ltsp ltsp-binaries dnsmasq nfs-kernel-server openssh-server squashfs-tools ethtool net-tools epoptes qemu binfmt-support qemu-user-static")
        fileLogger.debug("LTSP packages now installed")
    else:
        fileLogger.debug("LTSP PPA sources already found")


def install_pinet_theme():
    fileLogger.debug("Downloading PiNet theme files.")
    make_folder(PINET_THEME_LOC)
    download_file("https://raw.githubusercontent.com/PiNet/PiNet/jessie-stable/themes/raspi/bg.png", f"{PINET_THEME_FULL_LOC}/bg.png")
    download_file("https://raw.githubusercontent.com/PiNet/PiNet/jessie-stable/images/pinet-icon.png", f"{PINET_THEME_FULL_LOC}/logo.png")


def setup_pinet_theme():
    fileLogger.debug("Setting up PiNet theme.")
    if not os.path.exists(f"{PINET_THEME_FULL_LOC}/bg.png"):
        install_pinet_theme()
    find_replace_line(f"{CHROOT_LOC}/etc/lightdm/pi-greeter.conf", "wallpaper=", f"wallpaper={PINET_THEME_LOC}/bg.png")
    find_replace_line(f"{CHROOT_LOC}/etc/lightdm/pi-greeter.conf", "default-user-image=", f"default-user-image={PINET_THEME_LOC}/logo.png")
    find_replace_line(f"{CHROOT_LOC}/etc/xdg/pcmanfm/LXDE-pi/desktop-items-0.conf", "wallpaper=", f"wallpaper={PINET_THEME_LOC}/bg.png")
    find_replace_line(f"{CHROOT_LOC}/etc/xdg/pcmanfm/LXDE-pi/desktop-items-1.conf", "wallpaper=", f"wallpaper={PINET_THEME_LOC}/bg.png")


def pinet_buster_installer():
    fileLogger.debug("------")
    fileLogger.debug("------")
    fileLogger.debug("Starting PiNet Buster installation.")
    install_ltsp()
    make_folder("/opt/PiNet/sd_images/raspbian_data")
    make_folder("/opt/ltsp/armhf")
    new_file_downloaded = download_latest_raspbian_image()
    if new_file_downloaded or not os.path.exists("/opt/PiNet/sd_images/raspbian_data/var"):
        remove_file("/opt/PiNet/sd_images/raspbian_data")
        make_folder("/opt/PiNet/sd_images/raspbian_data")
        extract_tar_xz_file(RASPBIAN_DATA_ROOT_TAR_XZ, "/opt/PiNet/sd_images/raspbian_data/")
    fileLogger.debug("Copying Raspbian OS to /opt/ltsp/armhf")
    run_bash(f"rsync -a {RASPBIAN_DATA_ROOT}/* /opt/ltsp/armhf")
    fileLogger.debug("Copying Raspbian OS complete")
    fileLogger.debug("Cleaning up root directory")
    remove_file("/opt/ltsp/armhf/etc/ld.so.preload")
    run_bash("rm -f /opt/ltsp/armhf/etc/ld.so.preload")
    run_bash("touch /opt/ltsp/armhf/etc/ld.so.preload")
    fileLogger.debug("Adding qemu")
    copy_file_folder("/usr/bin/qemu-arm-static", "/opt/ltsp/armhf/usr/bin/qemu-arm-static")
    fileLogger.debug("Installing ltsp-client package")
    ltsp_chroot("apt update")
    ltsp_chroot("apt install ltsp-client -y") # This probably isn't the correct approach, should be using ltsp.img now
    ltsp_chroot("deluser pi")


def main():
    pinet_buster_installer()


main()