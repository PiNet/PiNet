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
import errno
import grp
import logging
import os
import os.path
import pickle
import pwd
import random
import re
import shutil
import socket
import sys
import time
import traceback
import urllib.error
import urllib.request
import xml.etree.ElementTree
from logging import debug, info
from subprocess import Popen, PIPE, check_output, CalledProcessError
from xml.dom import minidom

import feedparser
import requests


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
configFileData = {}
fileLogger = None


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

    def __init__(self, name, install_type, install_commands=None, description="", install_on_server=False,
                 parameters=()):
        super(SoftwarePackage, self).__init__()
        self.name = name
        self.description = description
        self.install_type = install_type
        self.install_commands = install_commands
        self.install_on_server = install_on_server
        self.parameters = parameters

    def install_package(self):
        debug("Installing " + self.name)
        debug(self.install_commands)
        if isinstance(self.install_commands, list) and len(self.install_commands) > 0:
            programs = " ".join(self.install_commands)
        elif self.install_commands is None:
            programs = self.name
        else:
            programs = self.install_commands
        if self.install_type == "pip":
            self.marked = False
            if self.install_on_server:
                run_bash("pip install -U " + programs, ignore_errors=True)
                run_bash("pip3 install -U " + programs, ignore_errors=True)
            else:
                ltsp_chroot("pip install -U " + programs, ignoreErrors=True)
                ltsp_chroot("pip3 install -U " + programs, ignoreErrors=True)
            return
        elif self.install_type == "apt":
            self.marked = False
            install_apt_package(programs, install_on_server=self.install_on_server, parameters=self.parameters)
        elif self.install_type == "script":
            for i in self.install_commands:
                run_bash("ltsp-chroot --arch armhf " + i)
            self.marked = False
        elif self.install_type == "epoptes":
            install_epoptes()
        elif self.install_type == "scratchGPIO":
            install_scratch_gpio()
        else:
            print(_("Error in installing") + " " + self.name + " " + _("due to invalid install type."))
            self.marked = False

    def custom_apt_pip(self):
        done = False
        while done == False:
            if self.install_type == "customApt":
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
                    self.install_type = "apt"
                    self.install_commands = [package_name, ]
                    self.marked = True
                    done = True

            elif self.install_type == "customPip":
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
                    self.install_type = "pip"
                    self.install_commands = [package_name, ]
                    self.marked = True
                    done = True
            else:
                self.marked = True
                done = True


def setup_logger():
    global fileLogger
    fileLogger = logging.getLogger()
    handler = logging.FileHandler('/var/log/pinet.log')
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
            shell = True
            if run_as_sudo:
                command = "sudo " + command
            else:
                command = (["sudo"] + command)
        elif isinstance(command, list):
            shell = False
        else:
            return None
        if return_string:
            command_output = check_output(command, shell=shell)
            fileLogger.debug("Command \"" + command + "\" executed successfully.")
            return command_output.decode()
        else:
            p = Popen(command, shell=shell)
            p.wait()
            return_code = p.returncode
            if return_code != 0:
                raise CalledProcessError(return_code, str(command))
            fileLogger.debug("Command \"" + command + "\" executed successfully.")
            return True
    except CalledProcessError as c:
        fileLogger.warning("Command \"" + command + "\" failed to execute correctly with a return code of " + str(
            c.returncode) + ".")
        if ignore_errors == False:
            continue_on = whiptail_box_yes_no(_("Command failed to execute"), _(
                "Command \"" + command + "\" failed to execute correctly with a return code of " + str(
                    c.returncode) + ". Would you like to continue and ignore the error or retry the command?"),
                                              return_true_false=True, custom_yes=_("Continue"), custom_no=_("Retry"),
                                              height="11")
            if continue_on:
                fileLogger.info("Failed command \"" + command + "\" was ignored and program continued.")
                return c.returncode
            else:
                return run_bash(command, return_status=return_status, run_as_sudo=run_as_sudo,
                                return_string=return_string)
        else:
            return c.returncode


def get_users(includeRoot=False):
    users = []
    for p in pwd.getpwall():
        if (len(str(p[2])) > 3) and (str(p[5])[0:5] == "/home"):  # or (str(p[5])[0:5] == "/root"):
            users.append(p[0].lower())
    return users


def ltsp_chroot(command, return_status=True, returnString=False, ignoreErrors=False):
    run_bash("ltsp-chroot --arch armhf " + command, run_as_sudo=True, return_status=return_status,
             return_string=returnString, ignore_errors=ignoreErrors)


def install_apt_package(to_install, update=False, upgrade=False, install_on_server=False, parameters=()):
    parameters = " ".join(parameters)
    if update:
        run_bash("apt-get update")
    if upgrade:
        run_bash("apt-get upgrade -y")
    if install_on_server:
        run_bash("apt-get install -y " + parameters + " " + str(to_install))
    else:
        ltsp_chroot("apt-get install -y " + parameters + " " + str(to_install))


def create_text_file(location, text):
    new_text = text.split("\n")
    new_text = strip_start_whitespaces(new_text)
    new_text = strip_end_whitespaces(new_text)
    write_test_file(new_text, location)


def make_folder(directory):
    if not os.path.exists(directory):
        fileLogger.debug("Creating directory - " + str(directory))
        os.makedirs(directory)


def get_release_channel():
    channel = "Stable"
    config_file = get_list("/etc/pinet")
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


def get_text_file(file_p):
    """
    Opens the text file and goes through line by line, appending it to the file_list list.
    Each new line is a new object in the list, for example, if the text file was
    ----
    hello
    world
    this is an awesome text file
    ----
    Then the list would be
    ["hello", "world", "this is an awesome text file"]
    Each line is a new object in the list

    """
    if not os.path.exists(file_p):
        return []
    file = open(file_p)
    file_list = []
    while 1:
        line = file.readline()
        if not line:
            break
        file_list.append(line)
    return file_list


def remove_n(file_list):
    """
    Removes the final character from every line, this is always /n, aka newline character.
    """
    for count in range(0, len(file_list)):
        file_list[count] = file_list[count][0: (len(file_list[count])) - 1]
    return file_list


def blank_line_remover(file_list):
    """
    Removes blank lines in the file.
    """
    to_remove = []
    for count in range(0, len(file_list)):  # Go through each line in the text file
        found = False
        for i in range(0, len(file_list[count])):  # Go through each char in the line
            if not (file_list[count][i] == " "):
                found = True
        if not found:
            to_remove.append(count)

    toremove1 = []
    for i in reversed(to_remove):
        toremove1.append(i)

    for r in range(0, len(to_remove)):
        file_list.pop(toremove1[r])
        debug("just removed " + str(toremove1[r]))
    return file_list


def write_test_file(file_list, name):
    """
    Writes the final list to a text file.
    Adds a newline character (\n) to the end of every sublist in the file.
    Then writes the string to the text file.
    """
    file = open(name, 'w')
    main_str = ""
    for i in range(0, len(file_list)):
        main_str = main_str + file_list[i] + "\n"
    file.write(main_str)
    file.close()
    info("")
    info("------------------------")
    info("File generated")
    info("The file can be found at " + name)
    info("------------------------")
    info("")


def get_list(file):
    """
    Creates list from the passed text file with each line a new object in the list
    """
    return remove_n(get_text_file(file))


def check_string_exists(filename, to_search_for):
    text_file = get_list(filename)
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


def download_file(url, save_location):
    """
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


# def downloadFile(url, saveloc):
#    import requests
#    r = requests.get(url)
#    with open("code3.zip", "wb") as code:
#        code.write(r.content)


def strip_start_whitespaces(file_list):
    """
    Remove whitespace from start of every line in list.
    """
    for i in range(0, len(file_list)):
        file_list[i] = str(file_list[i]).lstrip()
    return file_list


def strip_end_whitespaces(file_list):
    """
    Remove whitespace from end of every line in list.
    """
    for i in range(0, len(file_list)):
        file_list[i] = str(file_list[i]).rstrip()
    return file_list


def clean_strings(file_list):
    """
    Removes \n and strips whitespace from before and after each item in the list
    """
    file_list = remove_n(file_list)
    file_list = strip_start_whitespaces(file_list)
    return strip_end_whitespaces(file_list)


def get_clean_list(filep):
    return clean_strings(get_text_file(filep))


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


def get_config_parameter(filep, search_for, break_on_first_find=False):
    text_file = get_text_file(filep)
    text_file = strip_end_whitespaces(text_file)
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
    with open("/tmp/ltsptmp", "w+") as text_file:
        text_file.write(str(data))
    return


def read_return():
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
        shutil.copytree(src, dest)
        fileLogger.debug("File/folder has been copied from " + src + " to " + dest + ".")
    except OSError as e:
        # If the error was caused because the source wasn't a directory
        if e.errno == errno.ENOTDIR:
            shutil.copy(src, dest)
        else:
            print('Directory not copied. Error: %s' % e)
            fileLogger.debug('Directory not copied. Error: %s' % e)


# ----------------Whiptail functions-----------------
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
    for x in range(0, len(items)):
        cmd.append(items[x])
        cmd.append("a")
    cmd.append("--noitem")
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


def replace_line_or_add(file, string, new_string):
    """
    Basic find and replace function for entire line.
    Pass it a text file in list form and it will search for strings.
    If it finds a string, it will replace that entire line with new_string
    """
    text_file = get_list(file)
    text_file = find_replace_any_line(text_file, string, new_string)
    write_test_file(text_file, file)


def replace_bit_or_add(file, string, new_string):
    """
    Basic find and replace function for section.
    Pass it a text file in list form and it will search for strings.
    If it finds a string, it will replace that exact string with new_string
    """
    text_file = get_list(file)
    text_file = find_replace_section(text_file, string, new_string)
    write_test_file(text_file, file)


def internet_on(timeout_limit=5, return_type=True):
    """
    Checks if there is an internet connection.
    If there is, return a 0, if not, return a 1
    # TODO: Fix try/except below to make less generic.
    """
    try:
        response = urllib.request.urlopen('http://www.google.com', timeout=int(timeout_limit))
        return_data(0)
        return True
    except:
        pass
    try:
        response = urllib.request.urlopen('http://mirrordirector.raspbian.org/', timeout=int(timeout_limit))
        return_data(0)
        return True
    except:
        pass
    try:
        response = urllib.request.urlopen('http://18.62.0.96', timeout=int(timeout_limit))
        return_data(0)
        return True
    except:
        pass
    return_data(1)
    return False


def internet_on_Requests(timeout_limit=3, return_type=True):
    try:
        response = requests.get("http://archive.raspbian.org/raspbian.public.key", timeout=timeout_limit)
        if response.status_code == requests.codes.ok:
            return_data(0)
            return True
    except (requests.ConnectionError, requests.Timeout):
        pass
    try:
        response = requests.get("http://archive.raspberrypi.org/debian/raspberrypi.gpg.key", timeout=timeout_limit)
        if response.status_code == requests.codes.ok:
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
    except:
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
    try:
        os.remove("/home/" + os.environ['SUDO_USER'] + "/pinet")
    except:
        pass
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


def checkUpdate2():
    """
    Deprecated
    Grabs the xml commit log to check for releases. Picks out most recent release and returns it.
    """

    loc = "/tmp/raspiupdate.txt"
    download_file("http://bit.ly/pinetcheckmaster", loc)
    xmldoc = minidom.parse(loc)
    version = xmldoc.getElementsByTagName('title')[1].firstChild.nodeValue
    version = clean_strings([version, ])[0]
    if version.find("Release") != -1:
        version = version[8:len(version)]
        print(version)
    else:
        print(_("ERROR"))
        print(_("No release update found!"))


def get_version_number(data):
    for i in range(0, len(data)):
        if data[i][0:7] == "Release":
            version = str(data[i][8:len(data[i])]).rstrip()
            return version


def check_update(current_version):
    if not internet_on(5, False):
        print(_("No Internet Connection"))
        return_data(0)
    download_file("http://bit.ly/pinetCheckCommits", "/dev/null")
    d = feedparser.parse(REPOSITORY + '/commits/' + RELEASE_BRANCH + '.atom')
    data = (d.entries[0].content[0].get('value'))
    data = ''.join(xml.etree.ElementTree.fromstring(data).itertext())
    data = data.split("\n")
    this_version = get_version_number(data)

    if compare_versions(current_version, this_version):
        whiptail_box("msgbox", _("Update detected"),
                     _("An update has been detected for PiNet. Select OK to view the Release History."), False)
        display_change_log(current_version)
    else:
        print(_("No PiNet software updates found"))
        # print(this_version)
        # print(current_version)
        return_data(0)


def check_kernel_file_update_web():
    # downloadFile(RAW_REPOSITORY +"/" + RELEASE_BRANCH + "/boot/version.txt", "/tmp/kernelVersion.txt")
    download_file(RAW_BOOT_REPOSITORY + "/" + RELEASE_BRANCH + "/boot/version.txt", "/tmp/kernelVersion.txt")
    user = os.environ['SUDO_USER']
    current_path = "/home/" + user + "/PiBoot/version.txt"
    if (os.path.isfile(current_path)) == True:
        current = int(get_clean_list(current_path)[0])
        new = int(get_clean_list("/tmp/kernelVersion.txt")[0])
        if new > current:
            return_data(1)
            return False
        else:
            return_data(0)
            print(_("No kernel updates found"))
            return True
    else:
        return_data(0)
        print(_("No kernel updates found"))


def check_kernel_updater():
    download_file(RAW_REPOSITORY + "/" + RELEASE_BRANCH + "/Scripts/kernelCheckUpdate.sh", "/tmp/kernelCheckUpdate.sh")

    if os.path.isfile("/opt/ltsp/armhf/etc/init.d/kernelCheckUpdate.sh"):

        current_version = int(get_config_parameter("/opt/ltsp/armhf/etc/init.d/kernelCheckUpdate.sh", "version=", True))
        new_version = int(get_config_parameter("/tmp/kernelCheckUpdate.sh", "version=", True))
        if current_version < new_version:
            install_check_kernel_updater()
            return_data(1)
            return False
        else:
            return_data(0)
            return True
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
        this_version = "Release " + get_version_number(data)
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


def previous_import():
    # TODO: Rewrite this function, is too fragile.
    items = ["passwd", "group", "shadow", "gshadow"]
    # items = ["group",]
    to_add = []
    for x in range(0, len(items)):
        # migLoc = "/Users/Andrew/Documents/Code/pinetImportTest/" + items[x] + ".mig"
        # etc_loc = "/Users/Andrew/Documents/Code/pinetImportTest/" + items[x]
        mig_loc = "/root/move/" + items[x] + ".mig"
        etc_loc = "/etc/" + items[x]
        debug("mig loc " + mig_loc)
        debug("etc loc " + etc_loc)
        mig = get_list(mig_loc)
        etc = get_list(etc_loc)
        for i in range(0, len(mig)):
            mig[i] = str(mig[i]).split(":")
        for i in range(0, len(etc)):
            etc[i] = str(etc[i]).split(":")
        for i in range(0, len(mig)):
            unfound = True
            for y in range(0, len(etc)):
                bob = mig[i][0]
                thing = etc[y][0]
                if bob == thing:
                    unfound = False
            if unfound:
                to_add.append(mig[i])
        for i in range(0, len(to_add)):
            etc.append(to_add[i])
        for i in range(0, len(etc)):
            line = ""
            for y in range(0, len(etc[i])):
                line = line + etc[i][y] + ":"
            line = line[0:len(line) - 1]
            etc[i] = line
        debug(etc)
        write_test_file(etc, etc_loc)


def open_csv_file(theFile):
    # TODO: Fix except statement
    data_list = []
    if os.path.isfile(theFile):
        with open(theFile) as csvFile:
            data = csv.reader(csvFile, delimiter=' ', quotechar='|')
            for row in data:
                try:
                    the_row = str(row[0]).split(",")
                    data_list.append(the_row)
                except:
                    whiptail_box("msgbox", _("Error!"), _("CSV file invalid!"), False)
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
                fix_group_single_user(user)
                percent_complete = int(((x + 1) / len(user_data_list)) * 100)
                print(str(percent_complete) + "% - Import of " + user + " complete.")
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


def fix_group_single_user(username):
    groups = ["adm", "dialout", "cdrom", "audio", "users", "video", "games", "plugdev", "input", "pupil"]
    for x in range(0, len(groups)):
        cmd = ["usermod", "-a", "-G", groups[x], username]
        p = Popen(cmd, stderr=PIPE)
        out, err = p.communicate()


def check_if_file_contains(file, string):
    """
    Simple function to check if a string exists in a file.
    """

    text_file = get_list(file)
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
    :return:
    """
    SoftwarePackage("epoptes", "apt", install_on_server=True).install_package()
    run_bash("gpasswd -a root staff")
    SoftwarePackage("epoptes-client", "apt", parameters=("--no-install-recommends",)).install_package()
    ltsp_chroot("epoptes-client -c")
    replace_line_or_add("/etc/default/epoptes", "SOCKET_GROUP", "SOCKET_GROUP=teacher")

    # Todo - Remove later if happy has been replaced by above.
    # runBash("apt-get install -y epoptes")
    # runBash("gpasswd -a root staff")
    # runBash("ltsp-chroot --arch armhf apt-get install -y epoptes-client --no-install-recommends")
    # runBash("ltsp-chroot --arch armhf epoptes-client -c")


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
        create_text_file("/home/" + u + "/Desktop/Install-scratchGPIO.desktop", """
        [Desktop Entry]
        Version=1.0
        Name=Install ScratchGPIO
        Comment=Install ScratchGPIO
        Exec=sudo bash /usr/local/bin/scratchSudo.sh
        Icon=scratch
        Terminal=true
        Type=Application
        Categories=Utility;Application;
        """)
        os.chown("/home/" + u + "/Desktop/Install-scratchGPIO.desktop", pwd.getpwnam(u).pw_uid, grp.getgrnam(u).gr_gid)
    make_folder("/etc/skel/Desktop")
    create_text_file("/etc/skel/Desktop/Install-scratchGPIO.desktop",
                     """[Desktop Entry]
    Version=1.0
    Name=Install ScratchGPIO
    Comment=Install ScratchGPIO
    Exec=sudo bash /usr/local/bin/scratchSudo.sh
    Icon=scratch
    Terminal=true
    Type=Application
    Categories=Utility;Application;""")


def install_software_list(hold_off_install=False):
    """
    Replacement for ExtraSoftware function in bash.
    Builds a list of possible software to install (using SoftwarePackage class) then displays the list using checkbox Whiptail menu.
    Checks what options the user has collected, then saves the packages list to file (using pickle). If hold_off_install is False, then runs installSoftwareFromFile().
    """
    software = [
        SoftwarePackage("Arduino-IDE", "apt", description=_("Programming environment for Arduino microcontrollers"),
                        install_commands=["arduino", ]),
        SoftwarePackage("Scratch-gpio", "scratchGPIO", description=_("A special version of scratch for GPIO work")),
        SoftwarePackage("Epoptes", "epoptes", description=_("Free and open source classroom management software")),
        SoftwarePackage("Custom-package", "customApt",
                        description=_(
                             "Allows you to enter the name of a package from Raspbian repository")),
        SoftwarePackage("Custom-python", "customPip",
                        description=_("Allows you to enter the name of a Python library from pip."))]

    software_list = []
    for i in software:
        software_list.append([i.name, i.description])
    done = False
    if (shutil.get_terminal_size()[0] < 105) or (shutil.get_terminal_size()[0] < 30):
        print("\x1b[8;30;105t")
        time.sleep(0.05)
        # print("Resizing")
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
    packages = []
    packages.append(SoftwarePackage("idle", "apt"))
    packages.append(SoftwarePackage("idle3", "apt"))
    packages.append(SoftwarePackage("python-dev", "apt"))
    packages.append(SoftwarePackage("nano", "apt"))
    packages.append(SoftwarePackage("python3-dev", "apt"))
    packages.append(SoftwarePackage("scratch", "apt"))
    packages.append(SoftwarePackage("python3-tk", "apt"))
    packages.append(SoftwarePackage("git", "apt"))
    packages.append(SoftwarePackage("debian-reference-en", "apt"))
    packages.append(SoftwarePackage("dillo", "apt"))
    packages.append(SoftwarePackage("python", "apt"))
    packages.append(SoftwarePackage("python-pygame", "apt"))
    packages.append(SoftwarePackage("python3-pygame", "apt"))
    packages.append(SoftwarePackage("python-tk", "apt"))
    packages.append(SoftwarePackage("sudo", "apt"))
    packages.append(SoftwarePackage("sshpass", "apt"))
    packages.append(SoftwarePackage("pcmanfm", "apt"))
    packages.append(SoftwarePackage("python3-numpy", "apt"))
    packages.append(SoftwarePackage("wget", "apt"))
    packages.append(SoftwarePackage("xpdf", "apt"))
    packages.append(SoftwarePackage("gtk2-engines", "apt"))
    packages.append(SoftwarePackage("alsa-utils", "apt"))
    packages.append(SoftwarePackage("wpagui", "apt"))
    packages.append(SoftwarePackage("omxplayer", "apt"))
    packages.append(SoftwarePackage("lxde", "apt"))
    packages.append(SoftwarePackage("net-tools", "apt"))
    packages.append(SoftwarePackage("mpg123", "apt"))
    packages.append(SoftwarePackage("ssh", "apt"))
    packages.append(SoftwarePackage("locales", "apt"))
    packages.append(SoftwarePackage("less", "apt"))
    packages.append(SoftwarePackage("fbset", "apt"))
    packages.append(SoftwarePackage("sudo", "apt"))
    packages.append(SoftwarePackage("psmisc", "apt"))
    packages.append(SoftwarePackage("strace", "apt"))
    packages.append(SoftwarePackage("module-init-tools", "apt"))
    packages.append(SoftwarePackage("ifplugd", "apt"))
    packages.append(SoftwarePackage("ed", "apt"))
    packages.append(SoftwarePackage("ncdu", "apt"))
    packages.append(SoftwarePackage("console-setup", "apt"))
    packages.append(SoftwarePackage("keyboard-configuration", "apt"))
    packages.append(SoftwarePackage("debconf-utils", "apt"))
    packages.append(SoftwarePackage("parted", "apt"))
    packages.append(SoftwarePackage("unzip", "apt"))
    packages.append(SoftwarePackage("build-essential", "apt"))
    packages.append(SoftwarePackage("manpages-dev", "apt"))
    packages.append(SoftwarePackage("python", "apt"))
    packages.append(SoftwarePackage("bash-completion", "apt"))
    packages.append(SoftwarePackage("gdb", "apt"))
    packages.append(SoftwarePackage("pkg-config", "apt"))
    packages.append(SoftwarePackage("python-rpi.gpio", "apt"))
    packages.append(SoftwarePackage("v4l-utils", "apt"))
    packages.append(SoftwarePackage("lua5.1", "apt"))
    packages.append(SoftwarePackage("luajit", "apt"))
    packages.append(SoftwarePackage("hardlink", "apt"))
    packages.append(SoftwarePackage("ca-certificates", "apt"))
    packages.append(SoftwarePackage("curl", "apt"))
    packages.append(SoftwarePackage("fake-hwclock", "apt"))
    packages.append(SoftwarePackage("ntp", "apt"))
    packages.append(SoftwarePackage("nfs-common", "apt"))
    packages.append(SoftwarePackage("usbutils", "apt"))
    packages.append(SoftwarePackage("libraspberrypi-dev", "apt"))
    packages.append(SoftwarePackage("libraspberrypi-doc", "apt"))
    packages.append(SoftwarePackage("libfreetype6-dev", "apt"))
    packages.append(SoftwarePackage("python3-rpi.gpio", "apt"))
    packages.append(SoftwarePackage("python-rpi.gpio", "apt"))
    packages.append(SoftwarePackage("python-pip", "apt"))
    packages.append(SoftwarePackage("python3-pip", "apt"))
    packages.append(SoftwarePackage("python-picamera", "apt"))
    packages.append(SoftwarePackage("python3-picamera", "apt"))
    packages.append(SoftwarePackage("x2x", "apt"))
    packages.append(SoftwarePackage("wolfram-engine", "apt"))
    packages.append(SoftwarePackage("xserver-xorg-video-fbturbo", "apt"))
    packages.append(SoftwarePackage("netsurf-common", "apt"))
    packages.append(SoftwarePackage("netsurf-gtk", "apt"))
    packages.append(SoftwarePackage("rpi-update", "apt"))
    packages.append(SoftwarePackage("ftp", "apt"))
    packages.append(SoftwarePackage("libraspberrypi-bin", "apt"))
    packages.append(SoftwarePackage("python3-pifacecommon", "apt"))
    packages.append(SoftwarePackage("python3-pifacedigitalio", "apt"))
    packages.append(SoftwarePackage("python3-pifacedigital-scratch-handler", "apt"))
    packages.append(SoftwarePackage("python-pifacecommon", "apt"))
    packages.append(SoftwarePackage("python-pifacedigitalio", "apt"))
    packages.append(SoftwarePackage("i2c-tools", "apt"))
    packages.append(SoftwarePackage("man-db", "apt"))
    packages.append(SoftwarePackage("cifs-utils", "apt", parameters=("--no-install-recommends",)))
    packages.append(SoftwarePackage("midori", "apt", parameters=("--no-install-recommends",)))
    packages.append(SoftwarePackage("lxtask", "apt", parameters=("--no-install-recommends",)))
    packages.append(SoftwarePackage("epiphany-browser", "apt", parameters=("--no-install-recommends",)))
    packages.append(SoftwarePackage("minecraft-pi", "apt"))
    packages.append(SoftwarePackage("python-smbus", "apt"))
    packages.append(SoftwarePackage("python3-smbus", "apt"))
    packages.append(SoftwarePackage("dosfstools", "apt"))
    packages.append(SoftwarePackage("ruby", "apt"))
    packages.append(SoftwarePackage("iputils-ping", "apt"))
    packages.append(SoftwarePackage("scrot", "apt"))
    packages.append(SoftwarePackage("gstreamer1.0-x", "apt"))
    packages.append(SoftwarePackage("gstreamer1.0-omx", "apt"))
    packages.append(SoftwarePackage("gstreamer1.0-plugins-base", "apt"))
    packages.append(SoftwarePackage("gstreamer1.0-plugins-good", "apt"))
    packages.append(SoftwarePackage("gstreamer1.0-plugins-bad", "apt"))
    packages.append(SoftwarePackage("gstreamer1.0-alsa", "apt"))
    packages.append(SoftwarePackage("gstreamer1.0-libav", "apt"))
    packages.append(
        SoftwarePackage("raspberrypi-sys-mods", "apt", parameters=("-o", 'Dpkg::Options::="--force-confold"',)))
    packages.append(
        SoftwarePackage("raspberrypi-net-mods", "apt", parameters=("-o", 'Dpkg::Options::="--force-confnew"',)))
    packages.append(
        SoftwarePackage("raspberrypi-ui-mods", "apt", parameters=("-o", 'Dpkg::Options::="--force-confnew"',)))
    packages.append(SoftwarePackage("java-common", "apt"))
    packages.append(SoftwarePackage("oracle-java8-jdk", "apt"))
    packages.append(SoftwarePackage("apt-utils", "apt"))
    packages.append(SoftwarePackage("wpasupplicant", "apt"))
    packages.append(SoftwarePackage("wireless-tools", "apt"))
    packages.append(SoftwarePackage("firmware-atheros", "apt"))
    packages.append(SoftwarePackage("firmware-brcm80211", "apt"))
    packages.append(SoftwarePackage("firmware-libertas", "apt"))
    packages.append(SoftwarePackage("firmware-ralink", "apt"))
    packages.append(SoftwarePackage("firmware-realtek", "apt"))
    packages.append(SoftwarePackage("libpng12-dev", "apt"))
    packages.append(SoftwarePackage("linux-image-3.18.0-trunk-rpi", "apt"))
    packages.append(SoftwarePackage("linux-image-3.18.0-trunk-rpi2", "apt"))
    # packages.append(SoftwarePackage("linux-image-3.12-1-rpi", "apt"))
    # packages.append(SoftwarePackage("linux-image-3.10-3-rpi", "apt"))
    # packages.append(SoftwarePackage("linux-image-3.2.0-4-rpi", "apt"))
    packages.append(SoftwarePackage("linux-image-rpi-rpfv", "apt"))
    packages.append(SoftwarePackage("linux-image-rpi2-rpfv", "apt"))
    packages.append(SoftwarePackage("libreoffice", "apt", parameters=("--no-install-recommends",)))
    packages.append(SoftwarePackage("libreoffice-gtk", "apt", parameters=("--no-install-recommends",)))
    packages.append(SoftwarePackage("myspell-en-gb", "apt"))
    packages.append(SoftwarePackage("mythes-en-us", "apt"))
    # packages.append(SoftwarePackage("chromium", "apt"))
    packages.append(SoftwarePackage("smartsim", "apt"))
    packages.append(SoftwarePackage("penguinspuzzle", "apt"))
    packages.append(SoftwarePackage("alacarte", "apt"))
    packages.append(SoftwarePackage("rc-gui", "apt"))
    packages.append(SoftwarePackage("claws-mail", "apt"))
    packages.append(SoftwarePackage("tree", "apt"))
    packages.append(SoftwarePackage("greenfoot", "apt"))
    packages.append(SoftwarePackage("bluej", "apt"))
    packages.append(SoftwarePackage("raspi-gpio", "apt"))
    packages.append(SoftwarePackage("libreoffice", "apt"))
    packages.append(SoftwarePackage("nuscratch", "apt"))
    packages.append(SoftwarePackage("iceweasel", "apt"))
    packages.append(SoftwarePackage("mu", "apt"))

    ltsp_chroot("touch /boot/config.txt")  # Required due to bug in sense-hat package installer
    packages.append(SoftwarePackage("libjpeg-dev", "apt"))
    packages.append(SoftwarePackage("pillow", "pip"))
    packages.append(SoftwarePackage("sense-hat", "apt"))
    packages.append(SoftwarePackage("nodered", "apt"))
    packages.append(SoftwarePackage("libqt4-network", "apt"))  # Remove when Sonic-Pi update fixes dependency issue.

    packages.append(SoftwarePackage("gpiozero", "pip"))
    packages.append(SoftwarePackage("pgzero", "pip"))
    packages.append(SoftwarePackage("pibrella", "pip"))
    packages.append(SoftwarePackage("skywriter", "pip"))
    packages.append(SoftwarePackage("unicornhat", "pip"))
    packages.append(SoftwarePackage("piglow", "pip"))
    packages.append(SoftwarePackage("pianohat", "pip"))
    packages.append(SoftwarePackage("explorerhat", "pip"))
    packages.append(SoftwarePackage("twython", "pip"))

    packages.append(SoftwarePackage("bindfs", "apt", install_on_server=True))
    packages.append(SoftwarePackage("python3-feedparser", "apt", install_on_server=True))
    packages.append(SoftwarePackage("ntp", "apt", install_on_server=True))

    for package in packages:
        package.install_package()

    if not os.path.exists("/opt/ltsp/armhf/usr/local/bin/raspi2png"):
        download_file("https://github.com/AndrewFromMelbourne/raspi2png/blob/master/raspi2png?raw=true",
                      "/tmp/raspi2png")
        copy_file_folder("/tmp/raspi2png", "/opt/ltsp/armhf/usr/local/bin/raspi2png")
        os.chmod("/opt/ltsp/armhf/usr/local/bin/raspi2png", 0o755)

    ltsp_chroot("easy_install --upgrade pip")  # Fixes known "cannot import name IncompleteRead" error
    ltsp_chroot("sudo apt-get -y purge clipit")  # Remove clipit application as serves no purpose on Raspbian
    run_bash("sudo DEBIAN_FRONTEND=noninteractive ltsp-chroot --arch armhf apt-get install -y sonic-pi")


def nbd_run():
    """
    Runs NBD compression tool. Clone of version in main pinet script
    """
    if get_config_parameter("/etc/pinet", "NBD=") == "true":
        if get_config_parameter("/etc/pinet", "NBDuse=") == "true":
            print("--------------------------------------------------------")
            print(_("Compressing the image, this will take roughly 5 minutes"))
            print("--------------------------------------------------------")
            run_bash("ltsp-update-image /opt/ltsp/armhf")
            set_config_parameter("NBDBuildNeeded", "false")
        else:
            whiptail_box("msgbox", _("WARNING"), _(
                "Auto NBD compressing is disabled, for your changes to push to the Raspberry Pis, run NBD-recompress from main menu."),
                         False)


def generate_server_id():
    """
    Generates random server ID for use with stats system.
    """
    ID = random.randint(10000000000, 99999999999)
    set_config_parameter("ServerID", str(ID))


def get_ip_address():
    """
    Get the PiNet server external IP address using the dnsdynamic.org IP address checker.
    If there is any issues, defaults to returning 0.0.0.0.
    """
    # TODO: Fix broad except.
    try:
        with urllib.request.urlopen("http://myip.dnsdynamic.org/") as url:
            ip_address = url.read().decode()
            socket.inet_aton(ip_address)
    except:
        ip_address = "0.0.0.0"
    return ip_address


def send_status():
    """
    Upload anonymous stats to the secure PiNet server (over encrypted SSL).
    """
    disable_metrics = str(get_config_parameter("/etc/pinet", "DisableMetrics="))
    server_id = str(get_config_parameter("/etc/pinet", "ServerID="))
    if server_id == "None":
        generate_server_id()
        server_id = str(get_config_parameter("/etc/pinet", "ServerID="))
    if disable_metrics.lower() == "true":
        pinet_version = "0.0.0"
        users = "0"
        kernel_version = "000"
        release_channel = "0"
        city = "Blank"
        organisation_type = "Blank"
        organisation_name = "Blank"
    else:
        pinet_version = str(get_config_parameter("/usr/local/bin/pinet", "version=", True))
        users = str(len(get_users()))
        if os.path.exists("/home/" + os.environ['SUDO_USER'] + "/PiBoot/version.txt"):
            kernel_version = str(get_clean_list("/home/" + os.environ['SUDO_USER'] + "/PiBoot/version.txt")[0])
        else:
            kernel_version = "000"
        city = str(get_config_parameter("/etc/pinet", "City="))
        organisation_type = str(get_config_parameter("/etc/pinet", "OrganisationType="))
        organisation_name = str(get_config_parameter("/etc/pinet", "OrganisationName="))
        release_channel = str(get_config_parameter("/etc/pinet", "ReleaseChannel="))

    ip_address = get_ip_address()

    command = 'curl --connect-timeout 2 --data "ServerID=' + server_id + "&" + "PiNetVersion=" + pinet_version + "&" + "Users=" + users + "&" + "KernelVersion=" + kernel_version + "&" + "ReleaseChannel=" + release_channel + "&" + "IPAddress=" + ip_address + "&" + "City=" + city + "&" + "OrganisationType=" + organisation_type + "&" + "OrganisationName=" + organisation_name + '"  https://secure.pinet.org.uk/pinetstatsv1.php -s -o /dev/null 2>&1'
    run_bash(command, ignore_errors=True)


def check_stats_notification():
    """
    Displays a one time notification to the user only once on the metrics.
    """
    shown_stats_notification = str(get_config_parameter("/etc/pinet", "ShownStatsNotification="))
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
            print("Copy complete.")
            whiptail_box("msgbox", _("Backup complete"), _("Backup has been complete"), False)
            return True
        except:
            print("Backup failed!")
            whiptail_box("msgbox", _("Error!"), _("Backup failed!"), False)
            return False
    else:
        print("Space issue...")
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
        "Would you like to proceed with Raspbian Jessie update? It will take 1-2 hours as Raspbian will be fully rebuilt. Note PiNet Wheezy support will be officially discontinued on 1st July 2016."),
                         True)
    if yesno and internet_full_status_check():
        backupName = "RaspbianWheezyBackup" + str(time.strftime("-%d-%m-%Y"))
        whiptail_box("msgbox", _("Backup chroot"), _(
            "Before proceeding with the update, a backup of the Raspbian chroot will be performed. You can revert to this later if need be. It will be called " + backupName),
                     False, height="10")
        if backup_chroot(backupName):
            return_data(1)
            return

    return_data(0)


# ------------------------------Main program-------------------------

get_release_channel()
setup_logger()

if __name__ == "__main__":
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
        elif sys.argv[1] == "previousImport":
            previous_import()
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
