import logging
import subprocess
from subprocess import CalledProcessError, Popen, check_output
from typing import List, Union

fileLogger: logging.Logger

def setup_logger():
    global fileLogger
    fileLogger = logging.getLogger()
    handler = logging.FileHandler(PINET_LOG_DIRPATH + '/pinet.log')
    formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    fileLogger.addHandler(handler)
    fileLogger.setLevel(logging.DEBUG)


def _(placeholder):
    # GNU Gettext placeholder
    return (placeholder)

def run_bash(command:Union[str, List[str]], run_as_sudo: bool=True, ignore_errors:bool=False) -> subprocess.CompletedProcess:
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
        fileLogger.debug(f'Command \"{" ".join(command)}\" failed to execute correctly with return code of {result.returncode}!')
        if not ignore_errors:
            # If should be alerting the user to errors.
            # TODO : Finish error detection here
            continue_on = dialog_box_yes_no(_("Command failed to execute"), _(""))
            
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
            return result


def _base_dialog_box(dialog_box_type:str, title:str, message:str, height:int, width:int, content:List[str]=[]) -> subprocess.CompletedProcess:
    command = ["whiptail", "--title", title, f"--{dialog_box_type}", message, height , width]
    command = command + content
    output = run_bash(command=command, run_as_sudo=False)
    return output


def dialog_box_yes_no(title:str, message:str, yes_button_text:str="Yes", no_button_text:str="No", height:int=8, width:int=78):
    content = ["--yes-button", yes_button_text, "--no-button",yes_button_text]
    output = _base_dialog_box("yesno", title, message, height, width, content=content)