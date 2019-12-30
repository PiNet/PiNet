import errno
import hashlib
import logging
import lzma
import os
import shutil
import subprocess
import tarfile
from subprocess import CalledProcessError
from typing import List, Union

import requests

fileLogger: logging.Logger

PINET_LOG_DIRPATH = "/var/log"
CHROOT_LOC = "/srv/ltsp/armhf"
PINET_THEME_LOC = "/usr/share/pinet-theme"
PINET_THEME_FULL_LOC = f"{CHROOT_LOC}/usr/share/pinet-theme"

def _(placeholder):
    # GNU Gettext placeholder
    return (placeholder)

def setup_logger():
    global fileLogger
    fileLogger = logging.getLogger()
    handler = logging.FileHandler(PINET_LOG_DIRPATH + '/pinet.log')
    formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    fileLogger.addHandler(handler)
    fileLogger.setLevel(logging.DEBUG)


setup_logger()


def make_folder(directory):
    if not os.path.exists(directory):
        fileLogger.debug("Creating directory - " + str(directory))
        os.makedirs(directory)


def _(placeholder):
    # GNU Gettext placeholder
    return (placeholder)


def run_bash(command: Union[str, List[str]], run_as_sudo: bool = True, ignore_errors: bool = False) -> subprocess.CompletedProcess:
    """
    Run a Bash command from Python and get back its return code or returned string.

    :param command: Bash command to be executed in a string or list form.
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
                command = f"sudo {command}"
            fileLogger.debug(f'Executing the following command \"{command}\"')

        elif isinstance(command, list):
            command = [str(section) for section in command]
            # If is a list, make sure Popen is expecting a list by setting shell to False.
            shell = False
            if run_as_sudo:
                command = (["sudo"] + command)
            fileLogger.debug(f'Executing the following command \"{" ".join(command)}\"')

        else:
            raise TypeError("No valid type passed to run_bash(), should be str or list.")
        result = subprocess.run(command, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        fileLogger.debug(f"Command executed and completed with {result.returncode}")
        result.check_returncode()
        return result

    except CalledProcessError as c:
        # If reaching this section, the process failed to execute correctly.
        if isinstance(command, str):
            fileLogger.debug(f'Command \"{command}\" failed to execute correctly with return code of {result.returncode}!')
        elif isinstance(command, list):
            fileLogger.debug(f'Command \"{" ".join(command)}\" failed to execute correctly with return code of {result.returncode}!')
        if not ignore_errors:
            # If should be alerting the user to errors.
            # TODO : Finish error detection here
            continue_on = dialog_box_yes_no(title=_("Command failed to execute"),
                                            message=_("Would you like to continue and ignore the error or retry the command?"),
                                            yes_button_text="Continue",
                                            no_button_text="Retry",
                                            height=11)

            # continue_on = whiptail_box_yes_no(_("Command failed to execute"), _(
            #   "Command \"" + str(command) + "\" failed to execute correctly with a return code of " + str(
            #        c.returncode) + ". Would you like to continue and ignore the error or retry the command?"),
            #                                  return_true_false=True, custom_yes=_("Continue"), custom_no=_("Retry"),
            #                                  height="11")
            if continue_on:
                # If the user selects Continue
                fileLogger.info("Failed command \"" + str(command) + "\" was ignored and program continued.")
                return c.returncode
            else:
                # If user Retry
                return run_bash(command, run_as_sudo=False, ignore_errors=ignore_errors)
        else:
            return result


def _base_dialog_box(dialog_box_type: str, title: str, message: str, height: int, width: int, content: List[str] = ()) -> subprocess.CompletedProcess:
    command = ["whiptail", "--title", title, f"--{dialog_box_type}", message, height, width]
    command = command + content
    output = run_bash(command=command, run_as_sudo=False)
    return output


def dialog_box_yes_no(title: str, message: str, yes_button_text: str = "Yes", no_button_text: str = "No", height: int = 8, width: int = 78):
    content = ["--yes-button", yes_button_text, "--no-button", no_button_text]
    output = _base_dialog_box("yesno", title, message, height, width, content=content)
    return output


def download_file(url, save_location):
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(save_location, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)
        fileLogger.debug("Downloaded file from " + url + " to " + save_location + ".")
        return True
    except requests.RequestException as e:
        fileLogger.debug("Failed to download file from {} to {}. Error was {}.".format(url, save_location, e))
        return False


def get_sha256_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


def extract_tar_xz_file(file_path_to_xz, extract_to_path):
    with lzma.open(file_path_to_xz) as f:
        with tarfile.open(fileobj=f) as tar:
            content = tar.extractall(extract_to_path)


def remove_file(file):
    try:
        shutil.rmtree(file)
        fileLogger.debug("File at " + file + " has been deleted.")
    except (OSError, IOError):
        fileLogger.debug("File at " + file + " was unable to be deleted!.")


def ltsp_chroot(command, ignore_errors=False):
    if isinstance(command, str):
        ltsp_command = f"chroot {CHROOT_LOC} /bin/bash -c '{command}'"
    elif isinstance(command, list):
        ltsp_command = ["chroot", CHROOT_LOC, "/bin/bash", "-c", "\'"] + command + ["\'",]
    else:
        return None
    return run_bash(ltsp_command, run_as_sudo=True, ignore_errors=ignore_errors)


def copy_file_folder(src, dest):
    try:
        shutil.copytree(src, dest, symlinks=True)
        fileLogger.debug(f"File/folder has been copied from {src} to {dest}.")
    except OSError as e:
        # If the error was caused because the source wasn't a directory
        if e.errno == errno.ENOTDIR:
            shutil.copy(src, dest)
        else:
            fileLogger.debug(f"Directory not copied. Error: {e}")


def find_replace_line(path, search_for, new_line):
    fileLogger.debug(f"Searching through {path} for {search_for}.")
    new_file = []
    found = False
    with open(path, 'r') as f:
        for line in f.readlines():
            if search_for in line:
                fileLogger.debug(f"Replaced {line} with {new_file} in {path}")
                new_file.append(f"{new_line}\n")
                found = True
            else:
                new_file.append(line)
    with open(path, 'w') as f:
        f.writelines(new_file)
    return found