#! /usr/bin/env python3
# Part of PiNet https://github.com/pinet/pinet
#
# See LICENSE file for copyright and license details

# PiNet
# pinet_functions_python.py
# Written by Andrew Mulholland
# Supporting python functions for the main pinet script in BASH.
# Written for Python 3.4

# PiNet is a utility for setting up and configuring a Linux Terminal Server Project (LTSP) network for Raspberry Pi's

import crypt
import csv
import datetime
import errno
import feedparser
import grp
import logging
import os
import os.path
import pickle
import pwd
import random
import re
import requests
import shutil
import socket
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.request
import xml.etree.ElementTree
from collections import OrderedDict
from logging import debug
from subprocess import Popen, PIPE, check_output, CalledProcessError

try:
    import netifaces
except ImportError:
    print("Unable to import netifaces. Please run sudo pip3 install netifaces")
    netifaces = None


# basicConfig(level=WARNING)


# from gettext import gettext as _
# gettext.textdomain(pinetPython)


# Set up message catalog access
# t = gettext.translation('pinetPython', 'locale', fallback=True)
# _ = t.ugettext

def _(placeholder):
    # GNU Gettext placeholder
    return (placeholder)


REPOSITORY_BASE = "https://github.com/pinet/"
REPOSITORY_NAME = "pinet"
BOOT_REPOSITORY = "PiNet-Boot"
RAW_REPOSITORY_BASE = "https://raw.github.com/pinet/"
REPOSITORY = REPOSITORY_BASE + REPOSITORY_NAME
RAW_REPOSITORY = RAW_REPOSITORY_BASE + REPOSITORY_NAME
RAW_BOOT_REPOSITORY = RAW_REPOSITORY_BASE + BOOT_REPOSITORY
RELEASE_BRANCH = "master"
CONFIG_FILE_LOCATION = "/etc/pinet"
PINET_LOG_DIRPATH = "/var/log"
DATA_TRANSFER_FILEPATH = "/tmp/ltsptmp"
configFileData = {}
fileLogger = None

APT, PIP, SCRIPT, EPOPTES, SCRATCH_GPIO, CUSTOM_APT, CUSTOM_PIP = 1, 2, 3, 4, 5, 6, 7
RASPBIAN_RELEASE = "jessie"
STABLE, BETA, ALPHA = RASPBIAN_RELEASE + "-stable", RASPBIAN_RELEASE + "-beta", RASPBIAN_RELEASE + "-alpha"

# Groups every user should be added to.
PINET_UNRESTRICTED_GROUPS = {"adm": None,
                             "dialout": None,
                             "cdrom": None,
                             "audio": None,
                             "users": None,
                             "sudo": None,
                             "video": None,
                             "games": None,
                             "plugdev": None,
                             "input": None,
                             "netdev": None,
                             "gpio": 625,
                             "spi": 626,
                             "i2c": 627,
                             "pupil": 628}

# Groups that not all users should be added to.
PINET_RESTRICTED_GROUPS = {"teacher": 629, }

PINET_GROUPS = {}
PINET_GROUPS.update(PINET_UNRESTRICTED_GROUPS)
PINET_GROUPS.update(PINET_RESTRICTED_GROUPS)


class SoftwarePackage():
    """
    Class for software packages.
    """

    name = ""
    description = ""
    install_type = ""
    install_commands = None
    marked = False
    install_on_server = False
    parameters = ()
    version = None

    def __init__(self, name, install_type, install_commands=None, description="", install_on_server=False,
                 parameters=(), version = None):
        super(SoftwarePackage, self).__init__()
        self.name = name
        self.description = description
        self.install_type = install_type
        self.install_commands = install_commands
        self.install_on_server = install_on_server
        self.parameters = parameters
        if version:
            self.version = version
        else:
            self.version = get_package_version_to_install(self.name)

    def install_package(self):
        fileLogger.debug("Installing - {}".format(self.name))
        fileLogger.debug("Install commands - {}".format(self.install_commands))
        if isinstance(self.install_commands, list) and len(self.install_commands) > 0:
            programs = " ".join(self.install_commands)
        elif self.install_commands is None:
            programs = self.name
        else:
            programs = self.install_commands
        if self.install_type == PIP:
            self.marked = False
            if self.install_on_server:
                run_bash("pip2 install -U " + programs, ignore_errors=True)
                run_bash("pip3 install -U " + programs, ignore_errors=True)
            else:
                ltsp_chroot("pip2 install -U " + programs, ignore_errors=True)
                ltsp_chroot("pip3 install -U " + programs, ignore_errors=True)
            return
        elif self.install_type == APT:
            self.marked = False
            install_apt_package(programs, install_on_server=self.install_on_server, parameters=self.parameters, version=self.version)
        elif self.install_type == SCRIPT:
            for i in self.install_commands:
                run_bash("ltsp-chroot --arch armhf " + i)
            self.marked = False
        elif self.install_type == EPOPTES:
            install_epoptes()
        elif self.install_type == SCRATCH_GPIO:
            install_scratch_gpio()
        else:
            print(_("Error in installing {} due to invalid install type.").format(self.name))
            self.marked = False

    def custom_apt_pip(self):
        done = False
        while done == False:
            if self.install_type == CUSTOM_APT:
                package_name = whiptail_box("inputbox", _("Custom package"),
                                            _(
                                                "Enter the name of the name of your package from apt you wish to install."),
                                            False, return_err=True)
                if package_name == "":
                    yes_no = whiptail_box("yesno", _("Are you sure?"),
                                          _(
                                              "Are you sure you want to cancel the installation of a custom apt package?"),
                                          True)
                    if yes_no:
                        self.marked = False
                        done = True
                        # else:
                        # print("Setting marked to false")
                        # self.marked = False
                else:
                    self.install_type = APT
                    self.install_commands = [package_name, ]
                    self.marked = True
                    done = True

            elif self.install_type == CUSTOM_PIP:
                package_name = whiptail_box("inputbox", _("Custom Python package"), _(
                    "Enter the name of the name of your python package from pip you wish to install."), False,
                                            return_err=True)
                if package_name == "":
                    yes_no = whiptail_box("yesno", _("Are you sure?"),
                                          _(
                                              "Are you sure you want to cancel the installation of a custom pip package?"),
                                          True)
                    if yes_no:
                        self.marked = False
                        done = True
                    else:
                        self.marked = False
                else:
                    self.install_type = PIP
                    self.install_commands = [package_name, ]
                    self.marked = True
                    done = True
            else:
                self.marked = True
                done = True


def setup_logger():
    global fileLogger
    fileLogger = logging.getLogger()
    handler = logging.FileHandler(PINET_LOG_DIRPATH + '/pinet.log')
    formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    fileLogger.addHandler(handler)
    fileLogger.setLevel(logging.DEBUG)


def runBashOld(command, checkFailed=False):
    # Deprecated in favor of new runBash
    if type(command) == str:
        p = Popen("sudo " + command, shell=True)
        p.wait()
        returnCode = p.returncode
    else:
        p = Popen(command)
        p.wait()
        returnCode = p.returncode
    if checkFailed:
        if int(returnCode) != 0:
            fileLogger.warning("Command \"" + command + "\" failed to execute correctly with a return code of " + str(
                returnCode) + ".")
            continueOn = whiptail_box_yes_no(_("Command failed to execute"), _(
                "Command \"" + command + "\" failed to execute correctly with a return code of " + str(
                    returnCode) + ". Would you like to continue and ignore the error or retry the command?"),
                                             return_true_false=True, custom_yes=_("Continue"), custom_no=_("Retry"),
                                             height="9")
            if continueOn:
                fileLogger.info("Failed command \"" + command + "\" was ignored and program continued.")
                return returnCode
            else:
                run_bash(command, True)
    else:
        fileLogger.debug("Command \"" + command + "\" executed successfully.")
        return returnCode


def runBashOutput(command):
    # Deprecated in favor of new runBash
    output = check_output("sudo " + command, shell=True)
    return output


def run_bash(command, return_status=True, run_as_sudo=True, return_string=False, ignore_errors=False):
    """
    Run a Bash command from Python and get back its return code or returned string.

    :param command: Bash command to be executed in a string or list form.
    :param return_status: Whether to return the status (as boolean).
    :param run_as_sudo: Should sudo be prefixed onto the command.
    :param return_string: Whether the actual command response string should be returned.
    :param ignore_errors: Set to True to ignore a non 0 return code.
    :return: Return code or returned string.
    """
    try:
        if isinstance(command, str):
            # If is a string, set shell parameter to True to tell Popen to interpret as a single string.
            shell = True
            if run_as_sudo:
                command = "sudo " + command

        elif isinstance(command, list):
            # If is a list, make sure Popen is expecting a list by setting shell to False.
            shell = False
            if run_as_sudo:
                command = (["sudo"] + command)

        else:
            return None

        if return_string:
            # If returning the text output.
            command_output = check_output(command, shell=shell)
            fileLogger.debug("Command \"" + str(command) + "\" executed successfully.")
            return command_output.decode()
        else:
            # Otherwise, can run with Popen to get the return code.
            p = Popen(command, shell=shell)
            p.wait()
            return_code = p.returncode
            if return_code != 0:
                # If process exited with an error (non 0 return code).
                raise CalledProcessError(return_code, str(command))
            fileLogger.debug("Command \"" + str(command) + "\" executed successfully.")
            return True
    except CalledProcessError as c:
        # If reaching this section, the process failed to execute correctly.
        fileLogger.warning("Command \"" + str(command) + "\" failed to execute correctly with a return code of " + str(
            c.returncode) + ".")
        if not ignore_errors:
            # If should be alerting the user to errors.
            continue_on = whiptail_box_yes_no(_("Command failed to execute"), _(
                "Command \"" + str(command) + "\" failed to execute correctly with a return code of " + str(
                    c.returncode) + ". Would you like to continue and ignore the error or retry the command?"),
                                              return_true_false=True, custom_yes=_("Continue"), custom_no=_("Retry"),
                                              height="11")
            if continue_on:
                # If the user selects Continue
                fileLogger.info("Failed command \"" + str(command) + "\" was ignored and program continued.")
                return c.returncode
            else:
                # If user Retry
                return run_bash(command, return_status=return_status, run_as_sudo=False,
                                return_string=return_string)
        else:
            return c.returncode


def get_users(includeRoot=False):
    users = []
    for p in pwd.getpwall():
        if (len(str(p[2])) > 3) and (str(p[5])[0:5] == "/home"):  # or (str(p[5])[0:5] == "/root"):
            users.append(p[0].lower())
    return users


def ltsp_chroot(command, return_status=True, return_string=False, ignore_errors=False):
    if isinstance(command, str):
        ltsp_prefix = "ltsp-chroot --arch armhf "
    elif isinstance(command, list):
        ltsp_prefix = ["ltsp-chroot", "--arch", "armhf"]
    else:
        return None
    return run_bash(ltsp_prefix + command, run_as_sudo=True, return_status=return_status,
                    return_string=return_string, ignore_errors=ignore_errors)


def install_apt_package(to_install, update=False, upgrade=False, install_on_server=False, parameters=(), version=""):
    parameters = " ".join(parameters)
    if update:
        run_bash("apt-get update")
    if upgrade:
        run_bash("apt-get upgrade -y")
    if install_on_server:
        if version:
            run_bash("apt-get install -y --force-yes {} {}={}".format(parameters, to_install, version))
            run_bash("apt-mark hold {}".format(to_install))
        else:
            run_bash("apt-get install -y {} {}".format(parameters, to_install))
    else:
        if version:
            ltsp_chroot("apt-get install -y --force-yes {} {}={}".format(parameters, to_install, version))
            ltsp_chroot("apt-mark hold {}".format(to_install))
        else:
            ltsp_chroot("apt-get install -y {} {}".format(parameters, to_install))


def group_apt_installer(packages):
    packages_to_install = []
    for package in packages:
        if not package.version and not package.parameters and not package.install_on_server:
            packages_to_install.append(package.name)
        else:
            if packages_to_install:
                print("Going to install {}".format(" ".join(packages_to_install)))
                returned = ltsp_chroot("apt-get install -y {}".format(" ".join(packages_to_install)), ignore_errors=True)
                if returned != True:
                    for single_package in packages_to_install:
                        install_apt_package(single_package)
                packages_to_install = []
            install_apt_package(package.name, install_on_server=package.install_on_server, parameters=package.parameters, version=package.version)



def get_package_version_to_install(package_name):
    """
    Check if package being installed should have a specific version installed, so can be held on that version
    :param package_name: Name of package to check.
    :return: Package version to be installed, or None.
    """
    current_time = time.time()
    pinet_package_versions_path = "/opt/PiNet/pinet-package-versions.txt"
    pinet_bootfiles_versions_path = "/opt/PiNet/PiBootBackup/apt_version.txt"
    pinet_bootfiles_versions_path_reserve = "/tmp/apt_version.txt"

    # Check first if the package is included in /opt/PiNet/PiBootBackup/boot/apt_version.txt. If not, then fall back to general package list at /opt/PiNet/pinet-package-versions.txt.
    if os.path.isfile(pinet_bootfiles_versions_path):
        bootfile_package_version = get_config_file_parameter(package_name, config_file_path=pinet_bootfiles_versions_path)
    else:
        # If the apt version list doesn't exist, then download
        if not os.path.isfile(pinet_bootfiles_versions_path_reserve):
            download_file(build_download_url("PiNet/PiNet-Boot", "boot/apt_version.txt"), pinet_bootfiles_versions_path_reserve)
        bootfile_package_version = get_config_file_parameter(package_name, config_file_path=pinet_bootfiles_versions_path_reserve)

    # If the file doesn't exist or is over 12 hours old, get the newest copy off the web.
    if not os.path.isfile(pinet_package_versions_path) or ((current_time - os.path.getctime(pinet_package_versions_path)) / 3600 > 12):
        make_folder("/opt/PiNet") # In case folder doesn't exist yet.
        for download_attempts in range(1, 4): # Attempt downloading 3 times with a 30s gap between each if fails first time.
            remove_file(pinet_package_versions_path)
            if download_file(build_download_url("PiNet/PiNet-Configs", "packages/package_versions.txt"), pinet_package_versions_path):
                break
            fileLogger.warning("Now able to download package_versions.txt file from {}. Already attempted {} time.".format(build_download_url("PiNet/PiNet-Configs", "packages/package_versions.txt"), download_attempts))
            if download_attempts == 3:
                # Not able to get the file correctly downloaded. Going to give up and return None after deleting the file.
                remove_file(pinet_package_versions_path)
                if bootfile_package_version:
                    return bootfile_package_version
            time.sleep(30) # Wait for 30s to allow for any issues with web connectivity.

    if bootfile_package_version:
        return bootfile_package_version
    else:
        return get_config_file_parameter(package_name, config_file_path=pinet_package_versions_path)


def make_folder(directory):
    if not os.path.exists(directory):
        fileLogger.debug("Creating directory - " + str(directory))
        os.makedirs(directory)


def get_release_channel_old():
    channel = "Stable"
    config_file = read_file("/etc/pinet")
    for i in range(0, len(config_file)):
        if config_file[i][0:14] == "ReleaseChannel":
            channel = config_file[i][15:len(config_file[i])]
            break

    global RELEASE_BRANCH
    channel = channel.lower()
    if channel == "stable":
        RELEASE_BRANCH = "master"
    elif channel == "dev":
        RELEASE_BRANCH = "dev"
    elif len(channel) > 7 and channel[0:7].lower() == "custom:":
        RELEASE_BRANCH = channel[7:len(channel)]
    else:
        RELEASE_BRANCH = "master"


def get_release_channel():
    global RELEASE_BRANCH
    release_channel = get_config_file_parameter("ReleaseChannel")
    if release_channel:
        release_channel = release_channel.lower()
    else:
        # No ReleaseChannel config value found, assuming Stable.
        RELEASE_BRANCH = STABLE
        return
    if release_channel == "stable":
        RELEASE_BRANCH = STABLE
    elif release_channel == "beta":
        RELEASE_BRANCH = BETA
    elif release_channel == "alpha":
        RELEASE_BRANCH = ALPHA
    elif release_channel == "dev":
        # Legacy from older version of PiNet, replaced by beta now
        set_config_parameter("ReleaseChannel", "beta")
    elif len(release_channel) > 7 and release_channel[0:7] == "custom:":
        RELEASE_BRANCH = release_channel[7:len(release_channel)]
    else:
        RELEASE_BRANCH = STABLE


def build_download_url(repo, path):
    if RELEASE_BRANCH in [STABLE, BETA, ALPHA]:
        # Convert for example https://raw.githubusercontent.com/PiNet/PiNet/scripts/test.txt to https://links.pinet.org.uk/PiNet--PiNet---jessie-stable---scripts--test
        url = "https://links.pinet.org.uk/{}---{}---{}".format(repo.replace("/", "--"), RELEASE_BRANCH, os.path.splitext(path)[0].replace("/", "--"))
    else:
        url = "https://raw.githubusercontent.com/{}/{}/{}".format(repo, RELEASE_BRANCH, path)
    return url



def read_file(file_path):
    """
    :param file_path: Full path to the file to be read.
    :return: A list containing an item for each line with newlines and whitespace (before and after) removed.
    """
    if not os.path.exists(file_path):
        return []
    with open(file_path) as f:
        file_contents = f.read().splitlines()
    cleaned_file_contents = [line.strip() for line in file_contents]
    return cleaned_file_contents


def write_file(file_path, file_contents):
    """

    :param file_path: Full path to the file to be read.
    :param file_contents: Contents of the file as a list of strings (with no newline characters).
    :return: Status of the file write
    """
    try:
        with open(file_path, 'w') as f:
            f.write('\n'.join(file_contents) + '\n')
        return True
    except IOError as e:
        print(e)
        return False


def check_string_exists(filename, to_search_for):
    text_file = read_file(filename)
    unfound = True
    for i in range(0, len(text_file)):
        found = text_file[i].find(to_search_for)
        if (found != -1):
            unfound = False
            break
    if unfound:
        return False

    return True


def find_replace_any_line(text_file, string, new_string):
    """
    Basic find and replace function for entire line.
    Pass it a text file in list form and it will search for strings.
    If it finds a string, it will replace the entire line with new_string
    """
    unfound = True
    for i in range(0, len(text_file)):
        found = text_file[i].find(string)
        if (found != -1):
            text_file[i] = new_string
            unfound = False
    if unfound:
        text_file.append(new_string)

    return text_file


def find_replace_section(text_file, string, new_string):
    """
    Basic find and replace function for section.
    Pass it a text file in list form and it will search for strings.
    If it finds a string, it will replace that exact string with new_string
    """
    for i in range(0, len(text_file)):
        found = text_file[i].find(string)
        if found != -1:
            before = text_file[i][0:found]
            after = text_file[i][found + len(string):len(text_file[i])]
            text_file[i] = before + new_string + after
    return text_file


def download_file_urllib(url, save_location):
    """
    Deprecated in favor of Requests library.

    Downloads a file from the internet using a standard browser header.
    Custom header is required to allow access to all pages.
    """
    try:
        req = urllib.request.Request(url)
        req.add_header('User-agent', 'Mozilla 5.10')
        f = urllib.request.urlopen(req)
        text_file = open(save_location, "wb")
        text_file.write(f.read())
        text_file.close()
        fileLogger.debug("Downloaded file from " + url + " to " + save_location + ".")
        return True
    except urllib.error.URLError as e:
        fileLogger.debug("Failed to download file from " + url + " to " + save_location + ". Error was " + e.reason)
    except:
        print(traceback.format_exc())
        fileLogger.debug("Failed to download file from " + url + " to " + save_location + ".")
        return False


def download_file(url, save_location):
    try:
        response = requests.get(url, headers={'User-agent': 'Mozilla 5.10'}, timeout=5)
        if response.status_code == requests.codes.ok:
            with open(save_location, 'wb') as f:
                f.write(response.content)
            fileLogger.debug("Downloaded file from " + url + " to " + save_location + ".")
            return True
        else:
            response.raise_for_status()
    except requests.RequestException as e:
        fileLogger.debug("Failed to download file from {} to {}. Error was {}.".format(url, save_location, e))
        return False


def compare_versions(local, web):
    """
    Compares 2 version numbers to decide if an update is required.
    """
    web = str(web).split(".")
    local = str(local).split(".")
    if int(web[0]) > int(local[0]):
        return_data(1)
        return True
    else:
        if int(web[1]) > int(local[1]):
            return_data(1)
            return True
        else:
            if int(web[2]) > int(local[2]):
                return_data(1)
                return True
            else:
                return_data(0)
                return False


def parse_config_file(config_file, read_first_use_only=False):
    """
    :param config_file: List of lines from config file.
    :param read_first_use_only: Only read the first copy of the value in the file. Default False.
    :return: Dictionary of keys and their values.
    """
    parsed = {}
    for line in config_file:
        if line.strip().startswith("#") or "=" not in line:
            # If a comment or missing an equals sign in the line, skip the line.
            continue
        key = line.split("=")[0].strip()
        if read_first_use_only and key in parsed:
            continue
        value = line.split("=")[1].strip()
        parsed[key] = value
    return parsed


def get_config_file_parameter(parameter_key, read_first_use_only=False, config_file_path=CONFIG_FILE_LOCATION):
    """
    :param parameter_key: Parameter key to search for in the config file.
    :param read_first_use_only: Only read the first copy of the value in the file. Default False.
    :param config_file_path: The full path of the config file. Default CONFIG_FILE_LOCATION variable.
    :return: Key or if not found, None.
    """
    config_file = read_file(config_file_path)

    parsed_config_file = parse_config_file(config_file, read_first_use_only=read_first_use_only)
    if parameter_key in parsed_config_file:
        return parsed_config_file[parameter_key]
    return None


def get_config_parameter(filep, search_for, break_on_first_find=False):
    text_file = read_file(filep)
    value = ""
    for i in range(0, len(text_file)):
        found = text_file[i].find(search_for)
        if found != -1:
            value = text_file[i][found + len(search_for):len(text_file[i])]
            if break_on_first_find:
                break

    if value == "":
        value = "None"

    return value


def set_config_parameter(option, value, filep="/etc/pinet"):
    new_value = option + "=" + value
    replace_line_or_add(filep, option, new_value)


def return_data(data):
    # TODO: Switch to use write_file
    with open(DATA_TRANSFER_FILEPATH, "w+") as text_file:
        text_file.write(str(data))
    return


def read_return():
    # TODO: Switch to use read_file
    with open("/tmp/ltsptmp", "r") as text_file:
        print(text_file.read())


def remove_file(file):
    try:
        shutil.rmtree(file)
        fileLogger.debug("File at " + file + " has been deleted.")
    except (OSError, IOError):
        pass


def copy_file_folder(src, dest):
    try:
        shutil.copytree(src, dest, symlinks=True)
        fileLogger.debug("File/folder has been copied from " + src + " to " + dest + ".")
    except OSError as e:
        # If the error was caused because the source wasn't a directory
        if e.errno == errno.ENOTDIR:
            shutil.copy(src, dest)
        else:
            print('Directory not copied. Error: %s' % e)
            fileLogger.debug('Directory not copied. Error: %s' % e)


def change_owner_file_folder(path, user_id, group_id):
    user_id = int(user_id)
    group_id = int(group_id)
    item_path = ""
    # Taken from http://stackoverflow.com/questions/2853723/whats-the-python-way-for-recursively-setting-file-permissions
    fileLogger.debug("Changing ownership of folder {} to user ID of {} and group ID of {}".format(path, user_id, group_id))
    try:
        for root, dirs, files in os.walk(path):
            for directory in dirs:
                item_path = os.path.join(root, directory)
                os.chown(item_path, user_id, group_id)
            for file in files:
                item_path = os.path.join(root, file)
                os.chown(item_path, user_id, group_id)
    except FileNotFoundError:
        fileLogger.debug("Unable to change owner on {} as it can't be found.".format(item_path))


def set_current_user_to_owner(path):
    """
    Sets provided owner of file/folder provided to the SUDO_USER. Leaves group same as was previously.
    :param path: File path to file/folder to set owner
    """
    uid = pwd.getpwnam(os.getenv("SUDO_USER")).pw_uid
    current_gid = os.stat(path).st_gid
    os.chown(path, uid, current_gid)


# ----------------Whiptail functions-----------------

#
# A general-purpose whiptail function. This can be used in the implementation
# of the other whiptail_... functions, allowing it to be overridden
# or nulled out in tests.
#
def whiptail(*args):
    """General purpose simple whiptail interface routine
    
    Take a list of argument and throw them at the whiptail command. Depending
    on the result from the whiptail call, set up a true or a false result
    in the result datafile and return True or False accordingly.
    """
    cmd = ["whiptail"] + list(args)
    p = Popen(cmd, stderr=PIPE)
    out, err = p.communicate()
    if p.returncode == 0:
        update_PiNet()
        return_data(1)
        return True
    elif p.returncode == 1:
        return_data(0)
        return False
    else:
        return "ERROR"


def whiptail_box(whiltailType, title, message, return_true_false, height="8", width="78", return_err=False, other=""):
    cmd = ["whiptail", "--title", title, "--" + whiltailType, message, height, width, other]
    p = Popen(cmd, stderr=PIPE)
    out, err = p.communicate()

    if return_true_false:
        if p.returncode == 0:
            return True
        elif p.returncode == 1:
            return False
        else:
            return "ERROR"
    elif return_err:
        return err.decode()
    else:
        return p.returncode


def whiptail_select_menu(title, message, items, height="16", width="78", other="5"):
    cmd = ["whiptail", "--title", title, "--menu", message, height, width, other]
    if isinstance(items, list):
        for x in range(0, len(items)):
            cmd.append(items[x])
            cmd.append("a")
        cmd.append("--noitem")
    elif isinstance(items, OrderedDict):
        for item, item_value in items.items():
            cmd.append(item)
            cmd.append(item_value)
    p = Popen(cmd, stderr=PIPE)
    out, err = p.communicate()
    if str(p.returncode) == "0":
        return err
    else:
        return "Cancel"


def whiptail_check_list(title, message, items):
    height, width, other = "20", "100", str(len(items))  # "16", "78", "5"
    cmd = ["whiptail", "--title", title, "--checklist", message, height, width, other]
    for x in range(0, len(items)):
        cmd.append(items[x][0])
        cmd.append(items[x][1])
        cmd.append("OFF")
    p = Popen(cmd, stderr=PIPE)
    out, err = p.communicate()
    if str(p.returncode) == "0":
        return (err)
    else:
        return ("Cancel")


def whiptail_box_yes_no(title, message, return_true_false, height="8", width="78", return_error=False, custom_yes="",
                        custom_no=""):
    cmd = ["whiptail", "--yesno", "--title", title, message, height, width,
           "--yes-button", custom_yes,
           "--no-button", custom_no]
    p = Popen(cmd, stderr=PIPE)
    out, err = p.communicate()

    if return_true_false:
        if p.returncode == 0:
            return True
        elif p.returncode == 1:
            return False
        else:
            return "ERROR"
    elif return_error:
        return err.decode()
    else:
        return p.returncode


# ---------------- Main functions -------------------

def replace_in_text_file(file_path, string_to_search_for, new_string, replace_all_uses=False, add_if_not_exists=True, replace_entire_line = True):
    """
    Simple string replacer for text files. Allows replacing a line in a text file if that line contains the
    provided string. If the line does not exist, add it.
    :param file_path: File path to file being edited..
    :param string_to_search_for: String to search for in the file.
    :param new_string: String to replace the line with if found.
    :param replace_all_uses: Replace all uses in the file or just first found use.
    :param add_if_not_exists: Add line if it doesn't exist in the file
    :param replace_entire_line: If found, replace the entire line. If false, does an inplace replace.
    :return: If string was found in file and replaced, return True. If appended on end of file, return False.
    """
    text_file = read_file(file_path)
    found = False
    for index, line in enumerate(text_file):
        if string_to_search_for in line:
            if replace_entire_line:
                text_file[index] = new_string
            else:
                text_file[index] = text_file[index].replace(string_to_search_for, new_string)
            found = True
            if not replace_all_uses:
                break
    if found:
        write_file(file_path, text_file)
        return True
    if add_if_not_exists:
        text_file.append(new_string)
        write_file(file_path, text_file)
    return False


def replace_line_or_add(file, string, new_string):
    """
    Basic find and replace function for entire line.
    Pass it a text file in list form and it will search for strings.
    If it finds a string, it will replace that entire line with new_string
    """
    text_file = read_file(file)
    text_file = find_replace_any_line(text_file, string, new_string)
    write_file(file, text_file)


def replace_bit_or_add(file, string, new_string):
    """
    Basic find and replace function for section.
    Pass it a text file in list form and it will search for strings.
    If it finds a string, it will replace that exact string with new_string
    """
    text_file = read_file(file)
    text_file = find_replace_section(text_file, string, new_string)
    write_file(file, text_file)


def internet_on_urllib(timeout_limit=5, return_type=True):
    """
    Checks if there is an internet connection.
    If there is, return a 0, if not, return a 1
    """
    try:
        response = urllib.request.urlopen('http://www.google.com', timeout=int(timeout_limit))
        return_data(0)
        return True
    except urllib.error.URLError:
        pass
    try:
        response = urllib.request.urlopen('http://mirrordirector.raspbian.org/', timeout=int(timeout_limit))
        return_data(0)
        return True
    except urllib.error.URLError:
        pass
    try:
        response = urllib.request.urlopen('http://18.62.0.96', timeout=int(timeout_limit))
        return_data(0)
        return True
    except urllib.error.URLError:
        pass
    return_data(1)
    return False


def internet_on(timeout_limit=3, return_type=True):
    last_checked_str = get_config_file_parameter("InternetConnectionLastCheckSuccess")
    if last_checked_str:
        last_checked = datetime.datetime.strptime(last_checked_str, "%Y-%m-%d-%H:%M:%S")
        current_date_time = datetime.datetime.now()
        if (current_date_time - last_checked).seconds / 60 < 20:
            return_data(0)
            return True

    try:
        response = requests.get("http://archive.raspbian.org/raspbian.public.key", timeout=int(timeout_limit))
        if response.status_code == requests.codes.ok:
            set_config_parameter("InternetConnectionLastCheckSuccess", datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S"))
            return_data(0)
            return True
    except (requests.ConnectionError, requests.Timeout):
        pass
    try:
        response = requests.get("http://archive.raspberrypi.org/debian/raspberrypi.gpg.key", timeout=int(timeout_limit))
        if response.status_code == requests.codes.ok:
            set_config_parameter("InternetConnectionLastCheckSuccess", datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S"))
            return_data(0)
            return True
    except (requests.ConnectionError, requests.Timeout):
        pass
    return_data(1)
    return False


def test_site_connection(site_url, timeout_limit=5):
    """
    Tests to see if can access the given website.
    """
    try:
        response = urllib.request.urlopen(site_url, timeout=int(timeout_limit))
        return True
    except urllib.error:
        return False


def internet_full_status_report(timeout_limit=5, whiptail=False, return_status=False):
    """
    Full check of all sites used by PiNet. Only needed on initial install
    """
    sites = []
    sites.append(
        [_("Main Raspbian repository"), "http://archive.raspbian.org/raspbian.public.key", ("Critical"), False])
    sites.append([_("Raspberry Pi Foundation repository"), "http://archive.raspberrypi.org/debian/raspberrypi.gpg.key",
                  ("Critical"), False])
    sites.append([_("Github"), "https://github.com", ("Critical"), False])
    sites.append([_("Bit.ly"), "http://bit.ly", ("Highly recommended"), False])
    sites.append([_("Bitbucket (Github mirror, not active yet)"), "https://bitbucket.org", ("Recommended"), False])
    # sites.append([_("BlueJ"), "http://bluej.org", ("Recommended"), False])
    sites.append([_("PiNet metrics"), "https://secure.pinet.org.uk", ("Recommended"), False])
    for website in range(0, len(sites)):
        sites[website][3] = test_site_connection(sites[website][1])
    if return_status:
        return sites
    if whiptail:
        message = ""
        for website in sites:
            if sites[3]:
                status = "Success"
            else:
                status = "Failed"
            message = message + status + " - " + website[2] + " - " + website[0] + " (" + website[1] + ")\n"
            if (shutil.get_terminal_size()[0] < 105) or (shutil.get_terminal_size()[0] < 30):
                print("\x1b[8;30;105t")
                time.sleep(0.05)
        whiptail_box("msgbox", "Web filtering test results", message, True, height="14", width="100")
    else:
        for website in range(0, len(sites)):
            print(str(sites[website][2] + " - "))


def internet_full_status_check(timeoutLimit=5):
    results = internet_full_status_report(timeout_limit=timeoutLimit, return_status=True)
    for site in results:
        if site[2] == "Critical":
            if not site[3]:
                whiptail_box("msgbox", _("Unable to proceed"), _(
                    "The requested action is unable to proceed as PiNet is not able to access a critical site. Perhaps your internet connection is not active or a proxy or web filtering system may be blocking access. The critical domain that is unable to be accessed is - " +
                    site[1]), False, height="11")
                return_data(1)
                return False
        elif site[2] == "Highly recommended":
            if not site[3]:
                answer = whiptail_box("yesno", _("Proceeding not recommended"), _(
                    "A highly recommended site is inaccessible. Perhaps a proxy or web filtering system may be blockeing access. Would you like to proceed anyway? (not recommended). The domain that is unable to be accessed is - " +
                    site[1]), True, height="11")
                if not answer:
                    return_data(1)
                    return False
        elif site[2] == "Recommended":
            if not site[3]:
                answer = whiptail_box("yesno", _("Proceeding not recommended"), _(
                    "A recommended site is inaccessible. Perhaps a proxy or web filtering system may be blockeing access. Would you like to proceed anyway? (not recommended). The domain that is unable to be accessed is - " +
                    site[1]), True, height="11")
                if answer == False:
                    return_data(1)
                    return False
        else:
            print("Unknown site type...")
    return_data(0)
    return True


def update_PiNet():
    """
    Fetches most recent PiNet and PiNet_functions_python.py
    """
    remove_file("/home/" + os.environ['SUDO_USER'] + "/pinet")
    print("")
    print("----------------------")
    print(_("Installing update"))
    print("----------------------")
    print("")
    download = True
    if not download_file(RAW_REPOSITORY + "/" + RELEASE_BRANCH + "/pinet", "/usr/local/bin/pinet"):
        download = False
    if not download_file(RAW_REPOSITORY + "/" + RELEASE_BRANCH + "/Scripts/pinet_functions_python.py",
                         "/usr/local/bin/pinet_functions_python.py"):
        download = False
    if download:
        print("----------------------")
        print(_("Update complete"))
        print("----------------------")
        print("")
        return_data(0)
    else:
        print("")
        print("----------------------")
        print(_("Update failed..."))
        print("----------------------")
        print("")
        return_data(1)


def get_version_number(data):
    for i in range(0, len(data)):
        if data[i][0:7] == "Release":
            version = str(data[i][8:len(data[i])]).rstrip()
            return version


def check_update(current_version):
    if not internet_on(5, False):
        print(_("No Internet Connection"))
        return_data(0)
        return
    download_file("http://bit.ly/pinetCheckCommits", "/dev/null")
    pinet_software_update_url = "{}/commits/{}.atom".format(REPOSITORY, RELEASE_BRANCH)
    debug("Checking for updates from {}.".format(pinet_software_update_url))
    d = feedparser.parse(pinet_software_update_url)
    try:
        for index, entries in enumerate(d.entries): #Iterate over each line in the .atom file up to x5 times to find a line with a version number
            data = entries.content[0].get('value')
            data = ''.join(xml.etree.ElementTree.fromstring(data).itertext())
            data = data.split("\n")
            this_version = get_version_number(data)
            if this_version:  # If a valid version number was found on the line.
                if compare_versions(current_version, this_version):
                    whiptail_box("msgbox", _("Update detected"), _("An update has been detected for PiNet. Select OK to view the Release History."), False)
                    display_change_log(current_version)
                    return
                else:
                    print(_("No PiNet software updates found"))
                    return_data(0)
                    return
            elif index > 5:  # Only check x5 lines before giving up.
                print(_("Unable to perform automatic update checks on this branch as the standard release format isn't followed. To update, use the manual Update-PiNet option."))
                debug("Unable to perform automatic update check on the currently selected branch - {}. Current version is {} and attempt to get new version returned {}".format(RELEASE_BRANCH, current_version, this_version))
                return_data(0)
                return
    except IndexError:
        print(_("Unable to check for PiNet updates, unable to download {}.".format(pinet_software_update_url)))
        return_data(0)


def check_kernel_file_update_web():
    # downloadFile(RAW_REPOSITORY +"/" + RELEASE_BRANCH + "/boot/version.txt", "/tmp/kernelVersion.txt")
    kernel_version_url = "{}/{}/boot/version.txt".format(RAW_BOOT_REPOSITORY, RELEASE_BRANCH)
    download_file(kernel_version_url, "/tmp/kernelVersion.txt")
    user = os.environ['SUDO_USER']
    current_path = "/home/" + user + "/PiBoot/version.txt"
    raspbian_boot_fiels_copy_path = "/opt/ltsp/armhf/bootfiles/version.txt"
    if os.path.isfile(current_path):
        current = int(read_file(current_path)[0])
        if os.path.isfile(raspbian_boot_fiels_copy_path):
            raspbian_current = int(read_file(raspbian_boot_fiels_copy_path)[0])
        else:
            raspbian_current = None
        try:
            new = int(read_file("/tmp/kernelVersion.txt")[0])
            if new > current or (raspbian_current and new > raspbian_current):
                return_data(1)
                return False
            else:
                return_data(0)
                print(_("No kernel updates found"))
                return True
        except (ValueError, TypeError):  # If can't find the update data
            print(_("Unable to check for kernel updates, unable to download {}.".format(kernel_version_url)))

    else:
        return_data(0)
        print(_("No kernel updates found"))


def check_kernel_updater():
    kernel_updater_version_url = "{}/{}/Scripts/kernelCheckUpdate.sh".format(RAW_REPOSITORY, RELEASE_BRANCH)
    download_file(kernel_updater_version_url, "/tmp/kernelCheckUpdate.sh")

    if os.path.isfile("/opt/ltsp/armhf/etc/init.d/kernelCheckUpdate.sh"):
        try:
            current_version = int(get_config_file_parameter("version", True,
                                                            config_file_path="/opt/ltsp/armhf/etc/init.d/kernelCheckUpdate.sh"))
            new_version = int(get_config_file_parameter("version", True, config_file_path="/tmp/kernelCheckUpdate.sh"))
            if current_version < new_version:
                install_check_kernel_updater()
                return_data(1)
                return False
            else:
                return_data(0)
                return True
        except (ValueError, TypeError): #If can't find the update data
            print(_("Unable to check for kernel updater updates, unable to download {}.".format(kernel_updater_version_url)))
    else:
        install_check_kernel_updater()
        return_data(1)
        return False


def install_check_kernel_updater():
    shutil.copy("/tmp/kernelCheckUpdate.sh", "/opt/ltsp/armhf/etc/init.d/kernelCheckUpdate.sh")
    Popen(['ltsp-chroot', '--arch', 'armhf', 'chmod', '755', '/etc/init.d/kernelCheckUpdate.sh'], stdout=PIPE,
          stderr=PIPE, stdin=PIPE)
    process = Popen(['ltsp-chroot', '--arch', 'armhf', 'update-rc.d', 'kernelCheckUpdate.sh', 'defaults'], stdout=PIPE,
                    stderr=PIPE, stdin=PIPE)
    process.communicate()


# def importUsers():

def display_change_log(version):
    version = "Release " + version
    d = feedparser.parse(REPOSITORY + '/commits/' + RELEASE_BRANCH + '.atom')
    releases = []
    for x in range(0, len(d.entries)):
        data = (d.entries[x].content[0].get('value'))
        data = ''.join(xml.etree.ElementTree.fromstring(data).itertext())
        data = data.split("\n")
        this_version = get_version_number(data)
        if not this_version:
            continue
        this_version = "Release " + this_version
        if this_version == version:
            break
        elif x == 10:
            break
        if data[0][0:5] == "Merge":
            continue
        releases.append(data)
    output = []
    for i in range(0, len(releases)):
        output.append(releases[i][0])
        for z in range(0, len(releases[i])):
            if not z == 0:
                output.append(" - " + releases[i][z])
        output.append("")
    thing = ""
    for i in range(0, len(output)):
        thing = thing + output[i] + "\n"
    cmd = ["whiptail", "--title", _("Release history (Use arrow keys to scroll)") + " - " + version, "--scrolltext",
           "--" + "yesno", "--yes-button", _("Install ") + output[0], "--no-button", _("Cancel"), thing, "24", "78"]
    p = Popen(cmd, stderr=PIPE)
    out, err = p.communicate()
    if p.returncode == 0:
        update_PiNet()
        return_data(1)
        return True
    elif p.returncode == 1:
        return_data(0)
        return False
    else:
        return "ERROR"


def open_csv_file(theFile):
    data_list = []
    if os.path.isfile(theFile):
        with open(theFile) as csvFile:
            data = csv.reader(csvFile, delimiter=' ', quotechar='|')
            for row in data:
                try:
                    the_row = str(row[0]).split(",")
                    data_list.append(the_row)
                except csv.Error as e:
                    whiptail_box("msgbox", _("Error!"), _("CSV file invalid! Error was - " + str(e)), False)
                    return_data("1")
                    sys.exit()
            return data_list

    else:
        print(_("Error! CSV file not found at") + " " + theFile)


def import_users_csv(theFile, default_password, dry_run=False):
    user_data_list = []
    data_list = open_csv_file(theFile)
    if dry_run == "True" or dry_run == True:
        dry_run = True
    else:
        dry_run = False
    for user_line in data_list:
        user = user_line[0]
        if " " in user:
            whiptail_box("msgbox", _("Error!"), _(
                "CSV file names column (1st column) contains spaces in the usernames! This isn't supported."), False)
            return_data("1")
            sys.exit()
        if len(user_line) >= 2:
            if user_line[1] == "":
                password = default_password
            else:
                password = user_line[1]
        else:
            password = default_password
        user_data_list.append([user, password])
    all_user_data_string = ""
    for i in range(0, len(user_data_list)):
        all_user_data_string = all_user_data_string + _("Username") + " - " + user_data_list[i][0] + " : " + _(
            "Password - ") + \
                               user_data_list[i][1] + "\n"
    cmd = ["whiptail", "--title", _("About to import (Use arrow keys to scroll)"), "--scrolltext", "--" + "yesno",
           "--yes-button", _("Import"), "--no-button", _("Cancel"), all_user_data_string, "24", "78"]
    p = Popen(cmd, stderr=PIPE)
    out, err = p.communicate()
    if not dry_run:
        if p.returncode == 0:
            for x in range(0, len(user_data_list)):
                user = user_data_list[x][0]
                password = user_data_list[x][1]
                encrypted_password = crypt.crypt(password, "22")
                cmd = ["useradd", "-m", "-s", "/bin/bash", "-p", encrypted_password, user]
                p = Popen(cmd, stderr=PIPE)
                out, err = p.communicate()
                percent_complete = int(((x + 1) / len(user_data_list)) * 100)
                print(str(percent_complete) + "% - Import of " + user + " complete.")
            verify_correct_group_users()
            whiptail_box("msgbox", _("Complete"), _("Importing of CSV data has been complete."), False)
        else:
            sys.exit()


def users_csv_delete(theFile, dry_run):
    user_data_list = []
    data_list = open_csv_file(theFile)
    if dry_run == "True" or dry_run == True:
        dry_run = True
    else:
        dry_run = False
    for user_line in data_list:
        user = user_line[0]
        if " " in user:
            whiptail_box("msgbox", _("Error!"),
                         _(
                             "CSV file names column (1st column) contains spaces in the usernames! This isn't supported."),
                         False)
            return_data("1")
            sys.exit()
        user_data_list.append([user, ])
    all_user_data_string = ""
    for i in range(0, len(user_data_list)):
        all_user_data_string = all_user_data_string + _("Username") + " - " + user_data_list[i][0] + "\n"
    cmd = ["whiptail", "--title", _("About to attempt to delete (Use arrow keys to scroll)"), "--scrolltext",
           "--" + "yesno", "--yes-button", _("Delete"), "--no-button", _("Cancel"), all_user_data_string, "24", "78"]
    p = Popen(cmd, stderr=PIPE)
    out, err = p.communicate()
    if not dry_run:
        if p.returncode == 0:
            for x in range(0, len(user_data_list)):
                user = user_data_list[x][0]
                cmd = ["userdel", "-r", "-f", user]
                p = Popen(cmd, stderr=PIPE)
                out, err = p.communicate()
                percent_complete = int(((x + 1) / len(user_data_list)) * 100)
                print(str(percent_complete) + "% - Delete of " + user + " complete.")
            whiptail_box("msgbox", _("Complete"), _("Delete of users from CSV file complete"), False)
        else:
            sys.exit()


def check_if_file_contains(file, string):
    """
    Simple function to check if a string exists in a file.
    """

    text_file = read_file(file)
    unfound = True
    for i in range(0, len(text_file)):
        found = text_file[i].find(string)
        if found != -1:
            unfound = False

    if unfound:
        return_data(0)
    else:
        return_data(1)


def save_pickled(toSave, path="/tmp/pinetSoftware.dump"):
    """
    Saves list of SoftwarePackage objects.
    """
    with open(path, "wb") as output:
        pickle.dump(toSave, output, pickle.HIGHEST_PROTOCOL)


def load_pickled(path="/tmp/pinetSoftware.dump", delete_after=True):
    """
    Loads list of SoftwarePackage objects ready to be used.
    """
    try:
        with open(path, "rb") as input:
            obj = pickle.load(input)
        if delete_after:
            remove_file(path)
        return obj
    except (OSError, IOError):
        if delete_after:
            remove_file(path)
        return []


def install_epoptes():
    """
    Install Epoptes classroom management software. Key is making sure groups are correct.
    """
    SoftwarePackage("epoptes", APT, install_on_server=True).install_package()
    run_bash("gpasswd -a root staff")
    SoftwarePackage("epoptes-client", APT, parameters=("--no-install-recommends",)).install_package()
    ltsp_chroot("epoptes-client -c")
    replace_line_or_add("/etc/default/epoptes", "SOCKET_GROUP", "SOCKET_GROUP=teacher")


def install_scratch_gpio():
    """
    ScratchGPIO installation process. Includes creating the desktop icon in all users and /etc/skel
    """
    remove_file("/tmp/isgh7.sh")
    remove_file("/opt/ltsp/armhf/usr/local/bin/isgh5.sh")
    remove_file("/opt/ltsp/armhf/usr/local/bin/scratchSudo.sh")
    remove_file("/opt/ltsp/armhf/usr/local/bin/isgh7.sh")
    download_file("http://bit.ly/1wxrqdp", "/tmp/isgh7.sh")
    copy_file_folder("/tmp/isgh7.sh", "/opt/ltsp/armhf/usr/local/bin/isgh7.sh")
    replace_line_or_add("/opt/ltsp/armhf/usr/local/bin/scratchSudo.sh", "bash /usr/local/bin/isgh7.sh $SUDO_USER",
                        "bash /usr/local/bin/isgh7.sh $SUDO_USER")
    users = get_users()
    for u in users:
        write_file("/home/" + u + "/Desktop/Install-scratchGPIO.desktop", """
        [Desktop Entry]
        Version=1.0
        Name=Install ScratchGPIO
        Comment=Install ScratchGPIO
        Exec=sudo bash /usr/local/bin/scratchSudo.sh
        Icon=scratch
        Terminal=true
        Type=Application
        Categories=Utility;Application;
        """.split("\n"))
        os.chown("/home/" + u + "/Desktop/Install-scratchGPIO.desktop", pwd.getpwnam(u).pw_uid, grp.getgrnam(u).gr_gid)
    make_folder("/etc/skel/Desktop")
    write_file("/etc/skel/Desktop/Install-scratchGPIO.desktop",
               """[Desktop Entry]
Version=1.0
Name=Install ScratchGPIO
Comment=Install ScratchGPIO
Exec=sudo bash /usr/local/bin/scratchSudo.sh
Icon=scratch
Terminal=true
Type=Application
Categories=Utility;Application;""".split("\n"))


def install_software_list(hold_off_install=False):
    """
    Replacement for ExtraSoftware function in bash.
    Builds a list of possible software to install (using SoftwarePackage class) then displays the list using checkbox Whiptail menu.
    Checks what options the user has collected, then saves the packages list to file (using pickle). If hold_off_install is False, then runs installSoftwareFromFile().
    """
    software = [
        SoftwarePackage("Arduino-IDE", APT, description=_("Programming environment for Arduino microcontrollers"),
                        install_commands=["arduino", ]),
        SoftwarePackage("Scratch-gpio", SCRATCH_GPIO, description=_("A special version of scratch for GPIO work")),
        SoftwarePackage("Epoptes", EPOPTES, description=_("Free and open source classroom management software")),
        SoftwarePackage("Custom-package", CUSTOM_APT,
                        description=_(
                            "Allows you to enter the name of a package from Raspbian repository")),
        SoftwarePackage("Custom-python", CUSTOM_PIP,
                        description=_("Allows you to enter the name of a Python library from pip."))]

    software_list = []
    for i in software:
        software_list.append([i.name, i.description])
    done = False
    if (shutil.get_terminal_size()[0] < 105) or (shutil.get_terminal_size()[0] < 30):
        print("\x1b[8;30;105t")
        time.sleep(0.05)
    while not done:
        whiptail_box("msgbox", _("Additional Software"), _(
            "In the next window you can select additional software you wish to install. Use space bar to select applications and hit enter when you are finished."),
                     False)
        result = (whiptail_check_list(_("Extra Software Submenu"), _(
            "Select any software you want to install. Use space bar to select then enter to continue."), software_list))
        try:
            result = result.decode("utf-8")
        except AttributeError:
            return
        result = result.replace('"', '')
        if result != "Cancel":
            if result == "":
                yesno = whiptail_box("yesno", _("Are you sure?"),
                                     _("Are you sure you don't want to install any additional software?"), True)
                if yesno:
                    save_pickled(software)
                    done = True
            else:
                result_list = result.split(" ")
                yesno = whiptail_box("yesno", _("Are you sure?"),
                                     _("Are you sure you want to install this software?") + " \n" + (
                                         result.replace(" ", "\n")), True, height=str(7 + len(result.split(" "))))
                if yesno:
                    for i in software:
                        if i.name in result_list:
                            i.custom_apt_pip()
                            # i.marked = True
                    done = True
                    save_pickled(software)

    if hold_off_install == False:
        install_software_from_file()


def install_software_from_file(packages=None):
    """
    Second part of installSoftwareList().
    Loads the pickle encoded list of SoftwarePackage objects then if they are marked to be installed, installs then.
    """
    need_compress = False
    if packages is None:
        packages = load_pickled()
    for i in packages:
        if i.marked == True:
            print(_("Installing") + " " + str(i.name))
            if not need_compress:
                ltsp_chroot("apt-get update")
            i.install_package()
            i.marked = False
            set_config_parameter("NBDBuildNeeded", "true")
            need_compress = True
        else:
            debug("Not installing " + str(i.name))
    if need_compress:
        nbd_run()


def install_chroot_software():
    ltsp_chroot("apt-get autoremove -y")
    packages = []
    packages.append(SoftwarePackage("idle", APT))
    packages.append(SoftwarePackage("idle3", APT))
    packages.append(SoftwarePackage("python-dev", APT))
    packages.append(SoftwarePackage("nano", APT))
    packages.append(SoftwarePackage("python3-dev", APT))
    packages.append(SoftwarePackage("scratch", APT))
    packages.append(SoftwarePackage("python3-tk", APT))
    packages.append(SoftwarePackage("git", APT))
    packages.append(SoftwarePackage("debian-reference-en", APT))
    packages.append(SoftwarePackage("dillo", APT))
    packages.append(SoftwarePackage("python", APT))
    packages.append(SoftwarePackage("python-pygame", APT))
    packages.append(SoftwarePackage("python3-pygame", APT))
    packages.append(SoftwarePackage("python-tk", APT))
    packages.append(SoftwarePackage("sudo", APT))
    packages.append(SoftwarePackage("sshpass", APT))
    packages.append(SoftwarePackage("pcmanfm", APT))
    packages.append(SoftwarePackage("python3-numpy", APT))
    packages.append(SoftwarePackage("wget", APT))
    packages.append(SoftwarePackage("xpdf", APT))
    packages.append(SoftwarePackage("gtk2-engines", APT))
    packages.append(SoftwarePackage("alsa-utils", APT))
    packages.append(SoftwarePackage("wpagui", APT))
    packages.append(SoftwarePackage("omxplayer", APT))
    packages.append(SoftwarePackage("lxde", APT))
    packages.append(SoftwarePackage("net-tools", APT))
    packages.append(SoftwarePackage("mpg123", APT))
    packages.append(SoftwarePackage("ssh", APT))
    packages.append(SoftwarePackage("locales", APT))
    packages.append(SoftwarePackage("less", APT))
    packages.append(SoftwarePackage("fbset", APT))
    packages.append(SoftwarePackage("sudo", APT))
    packages.append(SoftwarePackage("psmisc", APT))
    packages.append(SoftwarePackage("strace", APT))
    packages.append(SoftwarePackage("module-init-tools", APT))
    packages.append(SoftwarePackage("ifplugd", APT))
    packages.append(SoftwarePackage("ed", APT))
    packages.append(SoftwarePackage("ncdu", APT))
    packages.append(SoftwarePackage("console-setup", APT))
    packages.append(SoftwarePackage("keyboard-configuration", APT))
    packages.append(SoftwarePackage("debconf-utils", APT))
    packages.append(SoftwarePackage("parted", APT))
    packages.append(SoftwarePackage("unzip", APT))
    packages.append(SoftwarePackage("build-essential", APT))
    packages.append(SoftwarePackage("manpages-dev", APT))
    packages.append(SoftwarePackage("python", APT))
    packages.append(SoftwarePackage("bash-completion", APT))
    packages.append(SoftwarePackage("gdb", APT))
    packages.append(SoftwarePackage("pkg-config", APT))
    packages.append(SoftwarePackage("python-rpi.gpio", APT))
    packages.append(SoftwarePackage("v4l-utils", APT))
    packages.append(SoftwarePackage("lua5.1", APT))
    packages.append(SoftwarePackage("luajit", APT))
    packages.append(SoftwarePackage("hardlink", APT))
    packages.append(SoftwarePackage("ca-certificates", APT))
    packages.append(SoftwarePackage("curl", APT))
    packages.append(SoftwarePackage("fake-hwclock", APT))
    packages.append(SoftwarePackage("ntp", APT))
    packages.append(SoftwarePackage("nfs-common", APT))
    packages.append(SoftwarePackage("usbutils", APT))
    packages.append(SoftwarePackage("libfreetype6-dev", APT))
    packages.append(SoftwarePackage("python3-rpi.gpio", APT))
    packages.append(SoftwarePackage("python-rpi.gpio", APT))
    packages.append(SoftwarePackage("python-pip", APT))
    packages.append(SoftwarePackage("python3-pip", APT))
    packages.append(SoftwarePackage("python-picamera", APT))
    packages.append(SoftwarePackage("python3-picamera", APT))
    packages.append(SoftwarePackage("x2x", APT))
    packages.append(SoftwarePackage("wolfram-engine", APT))
    packages.append(SoftwarePackage("xserver-xorg-video-fbturbo", APT))
    packages.append(SoftwarePackage("netsurf-common", APT))
    packages.append(SoftwarePackage("netsurf-gtk", APT))
    packages.append(SoftwarePackage("rpi-update", APT))
    packages.append(SoftwarePackage("ftp", APT))
    packages.append(SoftwarePackage("raspberrypi-kernel", APT))
    packages.append(SoftwarePackage("raspberrypi-bootloader", APT))
    packages.append(SoftwarePackage("libraspberrypi0", APT))
    packages.append(SoftwarePackage("libraspberrypi-dev", APT))
    packages.append(SoftwarePackage("libraspberrypi-doc", APT))
    packages.append(SoftwarePackage("libraspberrypi-bin", APT))
    packages.append(SoftwarePackage("python3-pifacecommon", APT))
    packages.append(SoftwarePackage("python3-pifacedigitalio", APT))
    packages.append(SoftwarePackage("python3-pifacedigital-scratch-handler", APT))
    packages.append(SoftwarePackage("python-pifacecommon", APT))
    packages.append(SoftwarePackage("python-pifacedigitalio", APT))
    packages.append(SoftwarePackage("i2c-tools", APT))
    packages.append(SoftwarePackage("man-db", APT))
    packages.append(SoftwarePackage("cifs-utils", APT, parameters=("--no-install-recommends",)))
    packages.append(SoftwarePackage("midori", APT, parameters=("--no-install-recommends",)))
    packages.append(SoftwarePackage("lxtask", APT, parameters=("--no-install-recommends",)))
    packages.append(SoftwarePackage("epiphany-browser", APT, parameters=("--no-install-recommends",)))
    packages.append(SoftwarePackage("minecraft-pi", APT))
    packages.append(SoftwarePackage("python-smbus", APT))
    packages.append(SoftwarePackage("python3-smbus", APT))
    packages.append(SoftwarePackage("dosfstools", APT))
    packages.append(SoftwarePackage("ruby", APT))
    packages.append(SoftwarePackage("iputils-ping", APT))
    packages.append(SoftwarePackage("scrot", APT))
    packages.append(SoftwarePackage("gstreamer1.0-x", APT))
    packages.append(SoftwarePackage("gstreamer1.0-omx", APT))
    packages.append(SoftwarePackage("gstreamer1.0-plugins-base", APT))
    packages.append(SoftwarePackage("gstreamer1.0-plugins-good", APT))
    packages.append(SoftwarePackage("gstreamer1.0-plugins-bad", APT))
    packages.append(SoftwarePackage("gstreamer1.0-alsa", APT))
    packages.append(SoftwarePackage("gstreamer1.0-libav", APT))
    packages.append(
        SoftwarePackage("raspberrypi-sys-mods", APT, parameters=("-o", 'Dpkg::Options::="--force-confold"',)))
    packages.append(
        SoftwarePackage("raspberrypi-net-mods", APT, parameters=("-o", 'Dpkg::Options::="--force-confnew"',)))
    packages.append(
        SoftwarePackage("raspberrypi-ui-mods", APT, parameters=("-o", 'Dpkg::Options::="--force-confnew"',)))
    packages.append(SoftwarePackage("java-common", APT))
    packages.append(SoftwarePackage("oracle-java8-jdk", APT))
    packages.append(SoftwarePackage("apt-utils", APT))
    packages.append(SoftwarePackage("wpasupplicant", APT))
    packages.append(SoftwarePackage("wireless-tools", APT))
    packages.append(SoftwarePackage("firmware-atheros", APT))
    packages.append(SoftwarePackage("firmware-brcm80211", APT))
    packages.append(SoftwarePackage("firmware-libertas", APT))
    packages.append(SoftwarePackage("firmware-ralink", APT))
    packages.append(SoftwarePackage("firmware-realtek", APT))
    packages.append(SoftwarePackage("libpng12-dev", APT))
    packages.append(SoftwarePackage("linux-image-3.18.0-trunk-rpi", APT))
    packages.append(SoftwarePackage("linux-image-3.18.0-trunk-rpi2", APT))
    # packages.append(SoftwarePackage("linux-image-3.12-1-rpi", APT))
    # packages.append(SoftwarePackage("linux-image-3.10-3-rpi", APT))
    # packages.append(SoftwarePackage("linux-image-3.2.0-4-rpi", APT))
    packages.append(SoftwarePackage("linux-image-rpi-rpfv", APT))
    packages.append(SoftwarePackage("linux-image-rpi2-rpfv", APT))
    packages.append(SoftwarePackage("libreoffice", APT, parameters=("--no-install-recommends",)))
    packages.append(SoftwarePackage("libreoffice-gtk", APT, parameters=("--no-install-recommends",)))
    packages.append(SoftwarePackage("myspell-en-gb", APT))
    packages.append(SoftwarePackage("mythes-en-us", APT))
    packages.append(SoftwarePackage("smartsim", APT))
    packages.append(SoftwarePackage("penguinspuzzle", APT))
    packages.append(SoftwarePackage("alacarte", APT))
    packages.append(SoftwarePackage("rc-gui", APT))
    packages.append(SoftwarePackage("claws-mail", APT))
    packages.append(SoftwarePackage("tree", APT))
    packages.append(SoftwarePackage("greenfoot", APT))
    packages.append(SoftwarePackage("bluej", APT))
    packages.append(SoftwarePackage("raspi-gpio", APT))
    packages.append(SoftwarePackage("libreoffice", APT))
    packages.append(SoftwarePackage("nuscratch", APT))
    packages.append(SoftwarePackage("iceweasel", APT))
    packages.append(SoftwarePackage("mu", APT))
    packages.append(SoftwarePackage("python-twython", APT))
    packages.append(SoftwarePackage("python3-twython", APT))
    packages.append(SoftwarePackage("python-flask", APT))
    packages.append(SoftwarePackage("python3-flask", APT))
    packages.append(SoftwarePackage("python-picraft", APT))
    packages.append(SoftwarePackage("python3-picraft", APT))
    packages.append(SoftwarePackage("python3-codebug-tether", APT))
    packages.append(SoftwarePackage("python3-codebug-i2c-tether", APT))

    ltsp_chroot("touch /boot/config.txt")  # Required due to bug in sense-hat package installer
    packages.append(SoftwarePackage("libjpeg-dev", APT))
    #packages.append(SoftwarePackage("pillow", PIP))
    packages.append(SoftwarePackage("sense-hat", APT))
    packages.append(SoftwarePackage("nodered", APT))
    packages.append(SoftwarePackage("libqt4-network", APT))  # Remove when Sonic-Pi update fixes dependency issue.
    packages.append((SoftwarePackage("python-sense-emu", APT)))
    packages.append((SoftwarePackage("python3-sense-emu", APT)))
    packages.append((SoftwarePackage("sense-emu-tools", APT)))
    packages.append((SoftwarePackage("python-sense-emu-doc", APT)))
    packages.append((SoftwarePackage("gvfs", APT)))
    packages.append((SoftwarePackage("cups", APT)))

    packages.append(SoftwarePackage("bindfs", APT, install_on_server=True))
    packages.append(SoftwarePackage("python3-feedparser", APT, install_on_server=True))
    packages.append(SoftwarePackage("ntp", APT, install_on_server=True))
    packages.append(SoftwarePackage("python-pip", APT, install_on_server=True))
    packages.append(SoftwarePackage("python3-pip", APT, install_on_server=True))
    packages.append(SoftwarePackage("curl", APT, install_on_server=True))

    #for package in packages:
    #    package.install_package()

    # Unhold all packages
    pinet_package_versions_path = "/opt/PiNet/pinet-package-versions.txt"
    pinet_bootfiles_versions_path = "/opt/PiNet/PiBootBackup/apt_version.txt"
    held_packages = list(parse_config_file(read_file(pinet_package_versions_path)).keys()) + list(parse_config_file(read_file(pinet_bootfiles_versions_path)).keys())
    for package in held_packages:
        ltsp_chroot("apt-mark unhold {}".format(package), ignore_errors=True)
        fileLogger.debug("Marking {} to be unheld for updates.".format(package))


    group_apt_installer(packages)

    ltsp_chroot("easy_install --upgrade pip")  # Fixes known "cannot import name IncompleteRead" error
    ltsp_chroot("easy_install3 --upgrade pip")  # Fixes known "cannot import name IncompleteRead" error

    python_packages = []

    python_packages.append(SoftwarePackage("gpiozero", PIP))
    python_packages.append(SoftwarePackage("pgzero", PIP))
    python_packages.append(SoftwarePackage("pibrella", PIP))
    python_packages.append(SoftwarePackage("skywriter", PIP))
    python_packages.append(SoftwarePackage("unicornhat", PIP))
    python_packages.append(SoftwarePackage("piglow", PIP))
    python_packages.append(SoftwarePackage("pianohat", PIP))
    python_packages.append(SoftwarePackage("explorerhat", PIP))
    python_packages.append(SoftwarePackage("twython", PIP))
    python_packages.append(SoftwarePackage("python-sonic", PIP))


    for python_package in python_packages:
        python_package.install_package()

    if not os.path.exists("/opt/ltsp/armhf/usr/local/bin/raspi2png"):
        download_file("https://github.com/AndrewFromMelbourne/raspi2png/blob/master/raspi2png?raw=true",
                      "/tmp/raspi2png")
        copy_file_folder("/tmp/raspi2png", "/opt/ltsp/armhf/usr/local/bin/raspi2png")
        os.chmod("/opt/ltsp/armhf/usr/local/bin/raspi2png", 0o755)

    ltsp_chroot("sudo apt-get -y purge clipit")  # Remove clipit application as serves no purpose on Raspbian
    run_bash("sudo DEBIAN_FRONTEND=noninteractive ltsp-chroot --arch armhf apt-get install -y sonic-pi")
    run_bash(
        "sudo DEBIAN_FRONTEND=noninteractive ltsp-chroot --arch armhf apt-get install -y chromium-browser rpi-chromium-mods")
    run_bash("apt-get upgrade -y")
    ltsp_chroot("apt-get upgrade -y")
    ltsp_chroot("apt-get autoremove -y")


def nbd_run():
    """
    Runs NBD compression tool. Clone of version in main pinet script
    """
    if get_config_file_parameter("NBD") == "true":
        if get_config_file_parameter("NBDuse=") == "true":
            print("--------------------------------------------------------")
            print(_("Compressing the image, this will take roughly 5 minutes"))
            print("--------------------------------------------------------")
            run_bash("ltsp-update-image /opt/ltsp/armhf")
            set_config_parameter("NBDBuildNeeded", "false")
        else:
            print(_("Auto recompression of Raspbian OS is disabled. To enable, run NBD-recompress from the Other menu."))


def generate_server_id():
    """
    Generates random server ID for use with stats system.
    """
    ID = random.randint(10000000000, 99999999999)
    set_config_parameter("ServerID", str(ID))


def get_external_ip_address():
    """
    Get the PiNet server external IP address using an external server.
    If there is any issues, defaults to returning 0.0.0.0.
    """
    try:
        response = requests.get("http://links.pinet.org.uk/external_ip", timeout=5).text.strip()
        if len(response) > 16: # Verify isn't a blocked site page etc.
            return "0.0.0.0"
        return response
    except requests.RequestException:
        return "0.0.0.0"


def send_status():
    """
    Upload anonymous stats to the secure PiNet server (over encrypted SSL).
    """
    disable_metrics = str(get_config_file_parameter("DisableMetrics"))
    server_id = str(get_config_file_parameter("ServerID"))
    if server_id == "None":
        generate_server_id()
        server_id = str(get_config_file_parameter("ServerID"))
    if disable_metrics.lower() == "true":
        pinet_version = "0.0.0"
        users = "0"
        kernel_version = "000"
        release_channel = "0"
        city = "Blank"
        organisation_type = "Blank"
        organisation_name = "Blank"
    else:
        pinet_version = str(get_config_file_parameter("version", True, config_file_path="/usr/local/bin/pinet"))
        users = str(len(get_users()))
        if os.path.exists("/home/" + os.environ['SUDO_USER'] + "/PiBoot/version.txt"):
            kernel_version = str(read_file("/home/" + os.environ['SUDO_USER'] + "/PiBoot/version.txt")[0])
        else:
            kernel_version = "000"
        city = str(get_config_file_parameter("City"))
        organisation_type = str(get_config_file_parameter("OrganisationType"))
        organisation_name = str(get_config_file_parameter("OrganisationName"))
        release_channel = str(get_config_file_parameter("ReleaseChannel"))

    ip_address = get_external_ip_address()

    command = 'curl --connect-timeout 2 --data "ServerID=' + server_id + "&" + "PiNetVersion=" + pinet_version + "&" + "Users=" + users + "&" + "KernelVersion=" + kernel_version + "&" + "ReleaseChannel=" + release_channel + "&" + "IPAddress=" + ip_address + "&" + "City=" + city + "&" + "OrganisationType=" + organisation_type + "&" + "OrganisationName=" + organisation_name + '"  https://secure.pinet.org.uk/pinetstatsv1.php -s -o /dev/null 2>&1'
    run_bash(command, ignore_errors=True)


def check_stats_notification():
    """
    Displays a one time notification to the user only once on the metrics.
    """
    shown_stats_notification = str(get_config_file_parameter("ShownStatsNotification"))
    if shown_stats_notification == "true":
        pass  # Don't display anything
    else:
        whiptail_box("msgbox", _("Stats"), _(
            "Please be aware PiNet now collects very basic usage stats. These stats are uploaded to the secure PiNet metrics server over an encrypted 2048 bit SSL/TLS connection. The stats logged are PiNet version, Raspbian kernel version, number of users, development channel (stable or dev), external IP address, a randomly generated unique ID and any additional information you choose to add. These stats are uploaded in the background when PiNet checks for updates. Should you wish to disable the stats, see - http://pinet.org.uk/articles/advanced/metrics.html"),
                     False, height="14")
        set_config_parameter("ShownStatsNotification", "true", "/etc/pinet")
        ask_extra_stats_info()


def ask_extra_stats_info():
    """
    Ask the user for additional stats information.
    """
    whiptail_box("msgbox", _("Additional information"), _(
        "It is really awesome to see and hear from users across the world using PiNet. So we can start plotting schools/organisations using PiNet on a map, feel free to add any extra information to your PiNet server. It hugely helps us out also for internationalisation/localisation of PiNet. If you do not want to attach any extra information, please simply leave the following prompts blank."),
                 False, height="13")
    city = whiptail_box("inputbox", _("Nearest major city"), _(
        "To help with putting a dot on the map for your server, what is your nearest major town or city? Leave blank if you don't want to answer."),
                        False, return_err=True)
    organisation_type = whiptail_select_menu(_("Organisation type"), _(
        "What type of organisation are you setting PiNet up for? Leave on blank if you don't want to answer."),
                                             ["Blank", "School", "Non Commercial Organisation",
                                              "Commercial Organisation", "Raspberry Jam/Club", "N/A"])
    organisation_name = whiptail_box("inputbox", _("School/organisation name"), _(
        "What is the name of your organisation? Leave blank if you don't want to answer."), False, return_err=True)
    whiptail_box("msgbox", _("Additional information"), _(
        'Thanks for taking the time to read through (and if possible fill in) additional information. If you ever want to edit your information supplied, you can do so by selecting the "Other" menu and selecting "Edit-Information".'),
                 False, height="11")
    try:
        organisation_type = organisation_type.decode("utf-8")
    except:
        organisation_type = "Blank"
    if city == "":
        city = "Blank"
    if organisation_type == "":
        organisation_type = "Blank"
    if organisation_name == "":
        organisation_name = "Blank"
    city = re.sub('[^0-9a-zA-Z]+', '_', city)
    organisation_type = re.sub('[^0-9a-zA-Z]+', '_', organisation_type)
    organisation_name = re.sub('[^0-9a-zA-Z]+', '_', organisation_name)
    set_config_parameter("City", city)
    set_config_parameter("OrganisationType", organisation_type)
    set_config_parameter("OrganisationName", organisation_name)
    send_status()


def decode_bash_output(input_data, decode=False, remove_n=False):
    if decode:
        try:
            input_data = input_data.decode("utf-8")
        except:
            pass
    if remove_n:
        input_data = input_data.rstrip('\n')

    return input_data


def backup_chroot(name=None, override=False):
    make_folder("/opt/PiNet/chrootBackups")
    chroot_size = int(
        decode_bash_output(run_bash("""sudo du -s /opt/ltsp/armhf | awk '{print $1}' """, return_string=True),
                           decode=True,
                           remove_n=True))
    remaining_space = int(
        decode_bash_output(run_bash("""sudo df | grep /dev/ | sed -n 1p | awk '{print $4}' """, return_string=True),
                           decode=True,
                           remove_n=True))
    if ((remaining_space - chroot_size) > 1000000) or override:
        if name == None:
            waiting_for_name = True
            while waiting_for_name:
                name = whiptail_box("inputbox", _("Backup Chroot name"),
                                    _("Please enter a name to store the backup chroot under. Do not include spaces."),
                                    False, return_err=True)
                if (' ' in name) or (name == ""):
                    whiptail_box("msgbox", _("Invalid name"),
                                 _("Please do not include spaces in the filename or leave the filename blank."), False)
                else:
                    waiting_for_name = False
                    # print("Starting copy. This may take up to 10 minutes.")
        try:
            # for i in os.listdir("/opt/ltsp/armhf"):
            #    if (not i == "proc") and (not i == "dev"):
            #        print("Copying " + "/opt/ltsp/armhf/" + i)
            #        #makeFolder("/opt/PiNet/chrootBackups/" + backupName + "/" + i)
            #        copyFileFolder("/opt/ltsp/armhf/" + i, "/opt/PiNet/chrootBackups/" + backupName + "/" + i)
            print("-------------------------------------------------------------")
            print("Backing up Raspbian Chroot... This may take up to 20 minutes.")
            print("-------------------------------------------------------------")
            run_bash("sudo cp -rp /opt/ltsp/armhf/ /opt/PiNet/chrootBackups/" + name)
            print("Backup complete.")
            whiptail_box("msgbox", _("Backup complete"), _("Raspbian chroot backup is now complete."), False)
            return True
        except:
            print("Backup failed!")
            whiptail_box("msgbox", _("Error!"), _("Backup failed!"), False)
            return False
    else:
        print("Unable to allocate enough hard drive space for a backup.")
        chroot_size_readable = int(
            decode_bash_output(run_bash("""sudo du -s /opt/ltsp/armhf | awk '{print $1}' """, return_string=True),
                               decode=True,
                               remove_n=True))
        remaining_spacechroot_size_readable = int(
            decode_bash_output(run_bash("""sudo df | grep /dev/ | sed -n 1p | awk '{print $4}' """, return_string=True),
                               decode=True,
                               remove_n=True))
        print(remaining_spacechroot_size_readable, chroot_size_readable)
        override = whiptail_box_yes_no("Not enough space",
                                       "PiNet has detected not enough space is left to store the backup. " + str(
                                           chroot_size_readable) + " is required, but only " + str(
                                           remaining_spacechroot_size_readable) + " is available. You can choose to override this check.",
                                       custom_yes="Override", custom_no="Cancel", return_true_false=True, height="11")
        if override:
            backup_chroot(name, True)
            return True
        return False


def restore_chroot():
    options = []
    for i in os.listdir("/opt/PiNet/chrootBackups/"):
        options.append(i)
    if len(options) == 0:
        whiptail_box("msgbox", _("No backups"), _("No Raspbian chroots found "), False)
    else:
        name = decode_bash_output(
            whiptail_select_menu(_("Select backup"), _("Select your Raspbian chroot backup to restore"), options), True,
            False)
        if os.path.isdir("/opt/PiNet/chrootBackups/" + name) and name != "" and name != None and os.path.isdir(
                                "/opt/PiNet/chrootBackups/" + name + "/boot"):
            answer = whiptail_box("yesno", _("Are you sure?"), _(
                "The old Raspbian chroot will now be deleted and your chosen one copied into its place. There is no way to undo this process. Are you sure you wish to proceed?"),
                                  True, height="9")
            if answer:
                run_bash("rm -rf /opt/ltsp/armhf")
                print("Starting restore...")
                run_bash("cp -rp /opt/PiNet/chrootBackups/" + name + " /opt/ltsp/armhf")
                print("Restore complete")
                nbd_run()
        else:
            whiptail_box("msgbox", _("Unable to restore"), _(
                "Unable to restore backup chroot. The Raspbian chroot being restored is corrupt or damaged. Your previous Rabpain chroot has been left untouched."),
                         False)


def check_debian_version():
    wheezy = check_string_exists("/opt/ltsp/armhf/etc/apt/sources.list",
                                 "deb http://mirrordirector.raspbian.org/raspbian/ wheezy")
    if wheezy:
        debian_wheezy_to_jessie_update()
    else:
        return_data(0)


def debian_wheezy_to_jessie_update(try_backup=True):
    whiptail_box("msgbox", _("Raspbian Jessie update"), _(
        "A major update for your version of Raspbian is available. You are currently running Raspbian Wheezy, although the next big release (Raspbian Jessie) has now been released by the Raspberry Pi Foundation. As they have officially discontinued support for Raspbian Wheezy, it is highly recommended you proceed with the automatic update. Note that any custom configurations or changes you have made with Raspbian will be reset on installation of this update. Future updates for PiNet will only support Raspbian Jessie."),
                 False, height="14")
    yesno = whiptail_box("yesno", _("Proceed"), _(
        "Would you like to proceed with Raspbian Jessie update? It will take 1-2 hours as Raspbian will be fully rebuilt. Note PiNet Wheezy support will be officially discontinued on 1st July 2017."),
                         True, height="10")
    if yesno and internet_full_status_check():
        backupName = "RaspbianWheezyBackup" + str(time.strftime("-%d-%m-%Y"))
        whiptail_box("msgbox", _("Backup chroot"), _(
            "Before proceeding with the update, a backup of the Raspbian chroot will be performed. You can revert to this later if need be. It will be called {} and stored at {}.".format(backupName, "/opt/PiNet/chrootBackups/" + backupName)),
                     False, height="10")
        if backup_chroot(backupName):
            return_data(1)
            return

    return_data(0)


def custom_config_txt():
    """
    Allow users to build a custom config.txt file which will be appended onto the main config.txt file.
    Very useful if need to use custom values in the config.txt file, such as display settings.
    Custom config file isn't actually pushed out though till update_sd() is run.
    """
    additional_config_path = "/opt/PiNet/additional_config.txt"
    additional_config = read_file(additional_config_path)
    whiptail_box("msgbox", _("Custom config.txt values"), _("Custom config.txt values can be added in the following text file. Any changes made in this file will be added onto the end of the default config.txt file"), False, height="10")
    information_lines = []
    information_lines.append("You are now editing a temp file. This program is called Nano and is a very")
    information_lines.append("simple text editor in a terminal. Use arrow keys to move around and when you")
    information_lines.append("are finished, hit ctrl+x, followed by y, finally followed by hitting enter.")
    information_lines.append("Note - Any changes you make above the line below will not be saved!")
    information_lines.append("----------------------------------------------------------------------------")
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_config_file:
        additional_config = information_lines + additional_config
        temp_config_file.write('\n'.join(additional_config) + '\n')
    run_bash(["nano", temp_config_file.name])
    write_file(additional_config_path, read_file(temp_config_file.name)[5:])
    if whiptail_box("yesno", _("Update-SD"), _("Config file has been updated. To push this update out, Update-SD needs run. Would you like to run Update-SD?"), True, height="10"):
        update_sd()



def add_linux_group(group_name, group_id=None, in_chroot=False, ignore_errors=False):
    """
    Add new Linux group.
    :param group_name: Name of group to add
    :param group_id: Unique ID. If None, will default to system picking next available ID
    :param in_chroot: Create the group in the Raspbian chroot or just on Ubuntu system.
    """
    if group_id:
        cmd = ["groupadd", group_name, "-g", str(group_id)]
    else:
        cmd = ["groupadd", group_name]

    if in_chroot:
        fileLogger.info("Adding new group to the Raspbian chroot - " + group_name)
        ltsp_chroot(cmd, ignore_errors=ignore_errors)
    else:
        fileLogger.info("Adding new group to the Server - " + group_name)
        run_bash(cmd, ignore_errors=ignore_errors)


def modify_linux_group(group_name, group_id, in_chroot=False):
    """
    Modify a Linux group.
    :param group_name: Name of group to add.
    :param group_id: Unique group ID to modify.
    :param in_chroot: Modify the group in the Raspbian chroot or just on Ubuntu system.
    """
    cmd = ["groupmod", group_name, "-g", str(group_id)]

    if in_chroot:
        fileLogger.info("Modifying group to the Raspbian chroot - " + group_name)
        ltsp_chroot(cmd)
    else:
        fileLogger.info("Modifying group to the Server - " + group_name)
        run_bash(cmd)


def add_linux_user_to_group(username, group_name, ignore_errors=False):
    """
    Add a Linux user to a group.
    :param username: The username of the user to add to the group.
    :param group_name: The group the user is to be added to.
    :return:
    """
    fileLogger.info("Adding " + username + " to group " + group_name)
    cmd = ["usermod", "-a", "-G", group_name, username]
    run_bash(cmd, ignore_errors=ignore_errors)


def add_linux_user(username, user_id, group_id, encrypted_password, ignore_errors=False):
    """
    :param username: The linux username
    :param user_id: The user ID
    :param group_id: The default group ID for user
    :param encrypted_password: Pre-encrypted password for user
    :return:
    """
    fileLogger.info("Creating username {} with ID of {} and group_id of {}".format(username, user_id, group_id))
    cmd = ["useradd", username, "--password", encrypted_password, "--uid", user_id, "--gid", group_id]
    run_bash(cmd, ignore_errors=ignore_errors)


def parse_group_file(lines):
    """
    Parse a /etc/group file returning a dictionary with name:ID
    :param lines: Group file with in list with with new item for each line
    """
    groups = {}
    for line in lines:
        group_line = line.split(":")
        groups[group_line[0]] = int(group_line[2])
    return groups


def verify_groups():
    """
    Verify that all groups are correctly set up in the chroot and also on the server OS
    """

    server_groups = parse_group_file(read_file("/etc/group"))
    pi_groups = parse_group_file(read_file("/opt/ltsp/armhf/etc/group"))

    for group in PINET_GROUPS:
        if group in server_groups:
            if PINET_GROUPS[group] and PINET_GROUPS[group] != server_groups[group]:
                fileLogger.warning("The group with name {} on server has an ID mismatch. It is currently using {} and should be using {}. This has been corrected.".format(group, server_groups[group], PINET_GROUPS[group]))
                modify_linux_group(group, PINET_GROUPS[group], in_chroot=False)
                set_config_parameter("NBDBuildNeeded", "true")
        else:
            # If required group doesn't exist on the server, add it.
            add_linux_group(group, PINET_GROUPS[group])

        if PINET_GROUPS[group]:
            if group in pi_groups:
                if PINET_GROUPS[group] != pi_groups[group]:
                    fileLogger.warning("The group with name {} on the Raspbian chroot has an ID mismatch. It is currently using {} and should be using {}. This has been corrected.".format(group, pi_groups[group], PINET_GROUPS[group]))
                    modify_linux_group(group, PINET_GROUPS[group], in_chroot=True)
                    set_config_parameter("NBDBuildNeeded", "true")
            else:
                # If required group doesn't exist on the Raspbian chroot, add it.
                add_linux_group(group, PINET_GROUPS[group], in_chroot=True)
                set_config_parameter("NBDBuildNeeded", "true")


def get_users_linux_groups(username):
    """
    Get the groups a user is part of.
    (from http://stackoverflow.com/questions/9323834/python-how-to-get-group-ids-of-one-username-like-id-gn)
    """
    groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
    gid = pwd.getpwnam(username).pw_gid
    groups.append(grp.getgrgid(gid).gr_name)
    return groups


def verify_correct_group_users():
    """
    Verify all users are in the correct groups. If not, fix the group allocations.
    """
    verify_groups()
    non_system_users = []
    for user in pwd.getpwall():
        if 1000 <= user.pw_uid < 65534:
            non_system_users.append(user)
    for user in non_system_users:
        verify_correct_group_single_user(user.pw_name)


def verify_correct_group_single_user(user):
    """
    Verify single provided user is in the correct groups. If not, add to the correct groups.
    """
    missing_groups = set(PINET_UNRESTRICTED_GROUPS.keys()) - set(get_users_linux_groups(user))
    for missing_group in missing_groups:
        add_linux_user_to_group(user, missing_group)


def select_release_channel():
    whiptail_box("msgbox", _("Release channel selection"), _("There are a number of different release channels (branches) for PiNet. The default is stable which is suitable for production use. There is also Beta if you like testing new features, but are happy to accept the risk it could be buggy. Finally, there is Alpha. Alpha is the expermiental versions if you want to help test early copies of PiNet."), return_true_false=False, height="11")
    current_channel = get_config_file_parameter("ReleaseChannel")
    if not current_channel:
        current_channel = _("no channel selected, defaulting to stable")
    release = decode_bash_output(whiptail_select_menu(_("Release Channel"), _("Select a release channel to use. If in doubt, select Stable. Your current selected channel is \"{}\".".format(current_channel)), OrderedDict([("Stable", _("Extensively tested. Recommended for production use.")), ("Beta", _("Partially tested. Suitable in non production environment.")), ("Alpha", _("Experimental & untested. Use only for testing bleeding edge features."))]), width="80"), True, False)
    if release in ["Stable", "Beta", "Alpha"]:
        set_config_parameter("ReleaseChannel", str(release).lower())
        return_data(1)
    elif not get_config_file_parameter("ReleaseChannel"):
        # Isn't anything in the config file under ReleaseChannel, default to stable
        set_config_parameter("ReleaseChannel", "stable")
        return_data(1)
    else:
        # No change needed
        return_data(0)



def get_internal_ip_address():
    # Using netiface, grab the current internal IP address. If 2 network cards, pick alphabetically
    try:
        interfaces = netifaces.interfaces()
        for interface in interfaces:
            if str(interface).lower().startswith("e"):
                addr = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]["addr"]
                if addr:
                    return addr
    except KeyError:
        pass
    return "0.0.0.0"


def update_sd_card_ip_address():
    local_ip_address = get_internal_ip_address()
    continue_on = whiptail_box_yes_no(_("IP Address"), _("Your detected local IP address is {}. This will be added to the SD card boot files. If it has been detected incorrectly, select change below. Otherwise, select continue.".format(local_ip_address)), return_true_false = True, custom_yes=_("Continue"), custom_no=_("Change"), height="9")
    if not continue_on:
        local_ip_address = str(whiptail_box("inputbox", _("Custom IP address"),_("Enter the IP address you plan to use for your PiNet server below."),False, return_err=True))
        if not local_ip_address:
            return
    pass # Some sort of check in case they hit cancel?
    home_folder_path = os.path.expanduser("~")
    remove_file("{}/PiBoot/".format(home_folder_path))
    copy_file_folder("/opt/PiNet/PiBootBackup/", "{}/PiBoot/".format(home_folder_path))
    if get_config_file_parameter("NBD") == "true":
        remove_file("{}/PiBoot/cmdline.txt".format(home_folder_path))
        copy_file_folder("{}/PiBoot/cmdlineNBD.txt".format(home_folder_path), "{}/PiBoot/cmdline.txt".format(home_folder_path))
    replace_in_text_file("{}/PiBoot/cmdline.txt".format(home_folder_path), "1.1.1.1", str(local_ip_address), replace_entire_line=False)
    # Build a customised config.txt file and replace current one.
    write_file("{}/PiBoot/config.txt".format(home_folder_path), build_custom_config_txt_file())
    set_current_user_to_owner("{}/PiBoot/".format(home_folder_path))
    run_bash("nautilus ~/PiBoot > /dev/null 2>&1 &", run_as_sudo=False)
    create_sd_card_image_file()


def update_sd():
    if internet_on():
        make_folder("/opt/PiNet")
        remove_file("/tmp/PiBoot")
        run_bash("git clone --no-single-branch --depth 1 {}.git /tmp/PiBoot".format(REPOSITORY_BASE + BOOT_REPOSITORY), run_as_sudo=False)
        run_bash("(cd \"/tmp/PiBoot\"; git checkout \"{}\")".format(RELEASE_BRANCH), run_as_sudo=False)
        if os.path.isfile("/tmp/PiBoot/boot/config.txt"):
            remove_file("/opt/PiNet/PiBootBackup/")
            make_folder("/opt/PiNet/PiBootBackup")
            run_bash("cp -r /tmp/PiBoot/boot/* /opt/PiNet/PiBootBackup/")
            update_sd_card_ip_address()
        else:
            print("Error - Download failed or PiNet was unable to locate boot files, which should be located in /tmp/PiBoot/boot")
            fileLogger.warning("Error - Download failed or PiNet was unable to locate boot files, which should be located in /tmp/PiBoot/boot")
    elif os.path.isdir("/opt/PiNet/PiBootBackup"):
        # If not connected to the internet, but is a backup of boot files in /opt/PiNet/PiBootBackup
        whiptail_box("msgbox", _("Internet connection unavailable"), _("Unable to download new boot files as unable to detect an active internet connection. Previous backup copy will be used."), False)
        update_sd_card_ip_address()
    else:
        # If not connected to the internet and no local backup copy of boot files is available.
        whiptail_box("msgbox", _("Internet connection unavailable"), _("Unable to download boot files as unable to detect an active internet connection. Please connect to the internet to proceed."), False)
        return False

    if os.path.isdir("/opt/ltsp/armhf/bootfiles"):
        user = os.environ['SUDO_USER']
        current_path = "/home/" + user + "/PiBoot/version.txt"
        raspbian_boot_files_copy_path = "/opt/ltsp/armhf/bootfiles/version.txt"
        if os.path.isfile(current_path):
            current = int(read_file(current_path)[0])
            raspbian_current = int(read_file(raspbian_boot_files_copy_path)[0])
            # Check if there is a new version of the version.txt file, or if the config.txt files don't exactly match.
            if current > raspbian_current or read_file("/home/" + user + "/PiBoot/config.txt") != read_file("/opt/ltsp/armhf/bootfiles/config.txt"):
                remove_file("/opt/ltsp/armhf/bootfiles")
                copy_file_folder("/opt/PiNet/PiBootBackup/", "/opt/ltsp/armhf/bootfiles")
                copy_file_folder("/home/" + user + "/PiBoot/config.txt", "/opt/ltsp/armhf/bootfiles/config.txt")
                remove_file("/opt/ltsp/armhf/bootfiles/cmdline.txt")
                set_config_parameter("NBDBuildNeeded", "true")

    elif os.path.isdir("/opt/ltsp/armhf") and os.path.isdir("/opt/PiNet/PiBootBackup/"):
        copy_file_folder("/opt/PiNet/PiBootBackup/", "/opt/ltsp/armhf/bootfiles")
        set_config_parameter("NBDBuildNeeded", "true")

def build_custom_config_txt_file():
    base_config = read_file("/opt/PiNet/PiBootBackup/config.txt")
    custom_config_info = ["", "[all]", "# Below contains any custom user provided configuration.", ""]
    append_config = read_file("/opt/PiNet/additional_config.txt")
    if append_config:
        return base_config + custom_config_info + append_config
    return base_config


def create_sd_card_image_file():
    sd_card_image_path = "/tmp/pinet.img"
    run_bash("dd if=/dev/zero of={} bs=512 count=208845".format(sd_card_image_path))
    create_partition_table(sd_card_image_path)
    run_bash("mkdosfs -n PINET -S 512 -s 16 -v {}".format(sd_card_image_path))
    make_folder("/mnt/sdimage")
    run_bash("mount {} /mnt/sdimage".format(sd_card_image_path))
    run_bash("cp -r {}/PiBoot/* /mnt/sdimage/".format(os.path.expanduser("~")))
    run_bash("umount /mnt/sdimage")
    remove_file("/mnt/sdimage")
    copy_file_folder(sd_card_image_path, "{}/pinetSDImage.img".format(os.path.expanduser("~")))
    set_current_user_to_owner("{}/pinetSDImage.img".format(os.path.expanduser("~")))


def create_partition_table(sd_card_image_path):
    run_bash("""parted {} <<EOF
    unit b
    mklabel msdos
    mkpart primary fat32 $(expr 4 \* 1024 \* 1024) $(expr 60 \* 1024 \* 1024 - 1)
    print
    quit
    EOF""".format(sd_card_image_path))


def parse_mig_file(path):
    """
    Parse mig(ration) files. These are copied versions of passwd, shadow etc files.
    :param path: Path to mig file
    :return: Dictionary of mig file values
    """
    mig_raw = read_file(path)
    mig_parsed = {}
    for line in mig_raw:
        mig_parsed_single = line.split(":")
        for index, section in enumerate(mig_parsed_single):
            if "," in section:
                mig_parsed_single[index] = section.split(",")
        mig_parsed[mig_parsed_single[0]] = mig_parsed_single[1:]
    return mig_parsed


def import_migration_create_users(base_path = "/tmp/pinet_unpack/root/move/"):
    """
    Import tool for importing users/groups after a PiNet server migration.
    Recreates the groups, then the users and finally adds the users to the correct groups.
    :param base_path: Path that the unzipped user/group files are held.
    """

    # Parse migration files
    passwd = parse_mig_file("{}passwd.mig".format(base_path))
    shadow = parse_mig_file("{}shadow.mig".format(base_path))

    gpasswd = parse_mig_file("{}group.mig".format(base_path))
    gshadow = parse_mig_file("{}gshadow.mig".format(base_path))

    # Add the Linux groups
    for group in gpasswd:
        add_linux_group(group, gpasswd[group][1], ignore_errors=True)

    # Add the Linux user accounts
    for username in passwd:
        add_linux_user(username, passwd[username][1], passwd[username][2], shadow[username][0], ignore_errors=True)

        # Check if the user has a home folder, if not create one from /etc/skel
        if not os.path.exists("/home/{}".format(username)):
            fileLogger.warning("User {} does not have a home folder at /home/{} as part of import. Creating from /etc/skel.".format(username, username))
            copy_file_folder("/etc/skel/", "/home/{}".format(username))
            # Set home folder owner to the user/group if new coming from /etc/skel
            change_owner_file_folder("/home/{}".format(username), passwd[username][1], passwd[username][2])

    # Add the users into correct groups
    for group in gpasswd:
        if len(gpasswd[group]) > 2 and isinstance(gpasswd[group][2], list):
            for username in gpasswd[group][2]:
                add_linux_user_to_group(username, group, ignore_errors=True)


def import_migration_unpack_home_folders(migration_file_path):
    """
    Unpack the migration tar.gz, then move home folders into correct locations with correct permissions
    :param migration_file_path: Path to the toMove.tar.gz migration blob
    :return: Status of migration as True/False
    """
    # First verify that the migration tar.gz exists
    if os.path.isfile(migration_file_path):
        unpack_path = "/tmp/pinet_unpack/"
        home_files_path_tar = "{}root/move/home.tar.gz".format(unpack_path)
        if os.path.isdir(unpack_path):
            remove_file(unpack_path)
        make_folder(unpack_path)
        print(_("Extracting main migration archive."))
        # Unpack the main migration tar.gz
        run_bash("tar -zxvf {} -C {}".format(migration_file_path, unpack_path))
        # Verify all the key files are included in the main migration tar.gz
        if os.path.isfile(home_files_path_tar) and os.path.isfile("{}root/move/group.mig".format(unpack_path)) and os.path.isfile("{}root/move/passwd.mig".format(unpack_path)) and os.path.isfile("{}root/move/shadow.mig".format(unpack_path)):
            print(_("Extracting home folder archive."))
            # Extract the sub-tar.gz file containing the home folders
            run_bash("tar -zxvf {} -C {}".format(home_files_path_tar, "{}".format(unpack_path)))
            ignored_users = []
            for folder in os.listdir("{}home/".format(unpack_path)): # Get all files/folders in folder of home folders
                full_folder_path = "{}home/{}".format(unpack_path, folder)
                if os.path.isdir(full_folder_path):
                    if not os.path.exists("/home/{}".format(folder)):
                        # If it is a folder and the folder doesn't already exist in /home, then copy it from the import.
                        remove_file("{}.pulse".format(full_folder_path)) # Remove pulse audio files which can cause login issues.
                        print(_("Importing {} home folder.".format(folder)))
                        # Copy the home folders back into /home using -p to maintain the initial owner/permissions.
                        run_bash(["cp", "-r", "-p", full_folder_path, "/home/{}".format(folder)], ignore_errors=True) # Needed to maintain file permissions/owners
                    else: # If the home folder already exists in /home, so is ignored
                        ignored_users.append(folder)

            print(_("Home folders import complete. The following home folders were ignored as already existed - {}".format(", ".join(ignored_users))))
            remove_file("{}home/".format(unpack_path)) # Clean up home folders from /tmp
            return True
        else:
            print(_("Key files missing from {}root/move/ ! It should include home.tar.gz, group.mig, passwd.mig and shadow.mig.".format(unpack_path)))
            return False
    else:
        return False


def reset_theme_cache_for_all_users():
    """
    Delete cache files for desktop theme for provided user.
    This is needed for the migration to Pixel, to bring in the new theme configuration files.
    """
    non_system_users = []
    for user in pwd.getpwall():
        if 1000 <= user.pw_uid < 65534:
            non_system_users.append(user)
    for user in non_system_users:
        fileLogger.debug("Deleting theme cache for {}.".format(user.pw_name))
        files_folders_to_delete = [".config/Trolltech.conf", ".config/lxsession", ".config/openbox", ".config/pcmanfm", ".config/lxpanel", ".config/gtk-3.0", ".themes/PiX"]
        for file_folder in files_folders_to_delete:
            remove_file("/home/{}/{}".format(user.pw_name, file_folder))



def import_migration(migration_file_path):
    if import_migration_unpack_home_folders(migration_file_path):
        import_migration_create_users()


def verify_chroot_integrity():
    """
    Verify that Raspbian chroot integrity in correct by checking for key folders.
    """
    to_be_verified = {"/usr": False, "/opt": False, "/lib": False, "/bin": False, "/home": False, "/etc": False}

    for file_folder in to_be_verified:
        to_be_verified[file_folder] = os.path.exists("/opt/ltsp/armhf{}".format(file_folder))
    if False in to_be_verified.values():
        print("------------------------------------")
        print(_("PiNet integrity check has failed!"))
        print("------------------------------------")
        print("")
        print(_("The following files/folders are missing."))
        for file_folder in to_be_verified:
            if not to_be_verified[file_folder]:
                print("/opt/ltsp/armhf{} - Missing".format(file_folder))
        print("")
        print(_("The most likely cause of the missing files/folders above is issues with the PiNet installation process, which is common if used on a filtered internet connection."))
        print(_("If you are seeing this a long period of time after an installation, it may be that your PiNet Raspbian chroot has become corrupt is some way."))
        print(_("If you have just installed PiNet, perhaps retry (after fresh full Ubuntu reinstall) using a different internet connection."))
        print(_("Otherwise, visit http://pinet.org.uk/articles/support.html to get in touch. Include a screenshot of this error message."))
        print("")
        print(_("Press enter to continue..."))
        input()
        return_data(1)
        return

    return_data(0)
    return



# ------------------------------Main program-------------------------

if __name__ == "__main__":
    get_release_channel()
    setup_logger()

    if len(sys.argv) == 1:
        print(_("This python script does nothing on its own, it must be passed stuff"))
    else:
        if sys.argv[1] == "replaceLineOrAdd":
            replace_line_or_add(sys.argv[2], sys.argv[3], sys.argv[4])
        elif sys.argv[1] == "replaceBitOrAdd":
            replace_bit_or_add(sys.argv[2], sys.argv[3], sys.argv[4])
        elif sys.argv[1] == "CheckInternet":
            internet_on(sys.argv[2])
        elif sys.argv[1] == "CheckUpdate":
            check_update(sys.argv[2])
        elif sys.argv[1] == "CompareVersion":
            compare_versions(sys.argv[2], sys.argv[3])
        elif sys.argv[1] == "updatePiNet":
            update_PiNet()
        elif sys.argv[1] == "triggerInstall":
            download_file("http://bit.ly/pinetinstall1", "/dev/null")
        elif sys.argv[1] == "checkKernelFileUpdateWeb":
            check_kernel_file_update_web()
        elif sys.argv[1] == "checkKernelUpdater":
            check_kernel_updater()
        elif sys.argv[1] == "installCheckKernelUpdater":
            install_check_kernel_updater()
        elif sys.argv[1] == "importFromCSV":
            import_users_csv(sys.argv[2], sys.argv[3])
        elif sys.argv[1] == "usersCSVDelete":
            users_csv_delete(sys.argv[2], sys.argv[3])
        elif sys.argv[1] == "checkIfFileContainsString":
            check_if_file_contains(sys.argv[2], sys.argv[3])
        elif sys.argv[1] == "initialInstallSoftwareList":
            install_software_list(True)
        elif sys.argv[1] == "installSoftwareList":
            install_software_list(False)
        elif sys.argv[1] == "installSoftwareFromFile":
            install_software_from_file()
        elif sys.argv[1] == "sendStats":
            send_status()
        elif sys.argv[1] == "checkStatsNotification":
            check_stats_notification()
        elif sys.argv[1] == "askExtraStatsInfo":
            ask_extra_stats_info()
        elif sys.argv[1] == "internetFullStatusCheck":
            internet_full_status_check()
        elif sys.argv[1] == "checkDebianVersion":
            check_debian_version()
        elif sys.argv[1] == "setConfigParameter":
            set_config_parameter(sys.argv[2], sys.argv[3])
        elif sys.argv[1] == "installChrootSoftware":
            install_chroot_software()
        elif sys.argv[1] == "verifyCorrectGroupUsers":
            verify_correct_group_users()
        elif sys.argv[1] == "verifyCorrectGroupSingleUser":
            verify_correct_group_single_user(sys.argv[2])
        elif sys.argv[1] == "selectReleaseChannel":
            select_release_channel()
        elif sys.argv[1] == "buildDownloadURL":
            return_data(build_download_url(sys.argv[2], sys.argv[3]))
        elif sys.argv[1] == "updateSD":
            update_sd()
        elif sys.argv[1] == "importMigration":
            import_migration(sys.argv[2])
        elif sys.argv[1] == "resetThemeCacheForAllUsers":
            reset_theme_cache_for_all_users()
        elif sys.argv[1] == "getInternalIPAddress":
            return_data(get_internal_ip_address())
        elif sys.argv[1] == "customConfig":
            custom_config_txt()
        elif sys.argv[1] == "verifyChrootIntegrity":
            verify_chroot_integrity()
