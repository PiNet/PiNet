#! /usr/bin/env python3
# Part of PiNet https://github.com/pinet/pinet
#
# See LICENSE file for copyright and license details

#PiNet
#pinet-functions-python.py
#Written by Andrew Mulholland
#Supporting python functions for the main pinet script in BASH.
#Written for Python 3.4

#PiNet is a utility for setting up and configuring a Linux Terminal Server Project (LTSP) network for Raspberry Pi's

from logging import debug, info, warning, basicConfig, INFO, DEBUG, WARNING
basicConfig(level=WARNING)
import sys, os
import crypt
import csv
from subprocess import Popen, PIPE, check_output
import time
import shutil
import pwd, grp
import urllib.request
import xml.etree.ElementTree
import feedparser
import gettext

def _(placeholder):
    #GNU Gettext placeholder
    return(placeholder)

RepositoryBase = "https://github.com/pinet/"
RepositoryName = "pinet"
BootRepository="PiNet-Boot"
RawRepositoryBase = "https://raw.github.com/pinet/"
Repository = RepositoryBase + RepositoryName
RawRepository = RawRepositoryBase + RepositoryName
RawBootRepository=RawRepositoryBase + BootRepository
ReleaseBranch = "master"

DATA_TRANSFER_FILEPATH = "/tmp/ltsptmp"
PINET_BINPATH = "/usr/local/bin"
PINET_CONF_FILEPATH = "/etc/pinet"

CODE_DOWNLOAD_URL = RawRepository + "/" + ReleaseBranch
PINET_BINARY = "pinet"
PINET_PYTHON_BINARY = "Scripts/pinet-functions-python.py"
PINET_DOWNLOAD_URL = CODE_DOWNLOAD_URL + "/" + PINET_BINARY
PINET_PYTHON_DOWNLOAD_URL = CODE_DOWNLOAD_URL + "/" + PINET_PYTHON_BINARY

PINET_USER_GROUPS = ["adm", "dialout", "cdrom", "audio", "users", "video", "games", "plugdev", "input", "pupil"]
configFileData = {}


class softwarePackage():
    """
    Class for possible software packages.
    """

    name = ""
    description = ""
    installType = ""
    installCommands = []
    marked = False

    def __init__(self, name, description, installType, installCommands):
        super(softwarePackage, self).__init__()
        self.name = name
        self.description = description
        self.installType = installType
        self.installCommands = installCommands

    def installPackage(self):
        debug("Installing " +  self.name)
        debug(self.installCommands)
        if len(self.installCommands) > 0:
            programs = " ".join(self.installCommands)
        else:
            programs = self.installCommands
        if self.installType == "pip":
            self.marked = False
            py2 = runBash("ltsp-chroot pip install " + programs)
            py3 = runBash("ltsp-chroot pip-3.2 install " + programs)
            return
        elif self.installType == "apt":
            self.marked = False
            return runBash("ltsp-chroot apt-get install " + programs + " -y")
        elif self.installType == "script":
            for i in self.installCommands:
                runBash("ltsp-chroot --arch armhf " + i)
            self.marked = False
        elif self.installType == "epoptes":
            installEpoptes()
        elif self.installType == "scratchGPIO":
            installScratchGPIO()
        else:
            print(_("Error in installing") + " " + self.name + " " + _("due to invalid install type."))
            self.marked = False

    def customAptPip(self):
        done = False
        while done == False:
            if self.installType == "customApt":
                packageName = whiptailBox("inputbox", _("Custom package"), _("Enter the name of the name of your package from apt you wish to install."), False, returnErr = True)
                if packageName == "":
                    yesno = whiptailBox("yesno", _("Are you sure?"), _("Are you sure you want to cancel the installation of a custom apt package?"), True)
                    if yesno:
                        self.marked = False
                        done = True
                    #else:
                        #print("Setting marked to false")
                        #self.marked = False
                else:
                    self.installType = "apt"
                    self.installCommands = [packageName,]
                    self.marked = True
                    done = True

            elif self.installType == "customPip":
                packageName = whiptailBox("inputbox", _("Custom package"), _("Enter the name of the name of your python package from pip you wish to install."), False, returnErr = True)
                if packageName == "":
                    yesno = whiptailBox("yesno", _("Are you sure?"), _("Are you sure you want to cancel the installation of a custom pip package?"), True)
                    if yesno:
                        self.marked = False
                        done = True
                    else:
                        self.marked = False
                else:
                    self.installType = "pip"
                    self.installCommands = [packageName,]
                    self.marked = True
                    done = True
            else:
                self.marked = True
                done = True
        debug(self.marked, self.installType, self.installCommands, self.name)


def runBash(command):
    if type(command) == str:
        p = Popen("sudo " + command, shell=True)
        p.wait()
        return p.returncode
    else:
        p = Popen(command)
        p.wait()
        return p.returncode

def runBashOutput(command):
    output = check_output("sudo " + command, shell=True)
    return output

def getUsers(includeRoot=False):
    users = []
    for p in pwd.getpwall():
        if (len(str(p[2])) > 3) and (str(p[5])[0:5] == "/home"): #or (str(p[5])[0:5] == "/root"):
            users.append(p[0].lower())
    return users

def ltspChroot(command):
    runBash("ltsp-chroot --arch armhf " + command)

def installPackage(toInstall, update=False, upgrade=False, InstallOnServer=False):
    toInstall = toInstall.split(" ")
    totalPackages = ""
    for i in range(0, len(toInstall)):
        totalPackages = totalPackages + " " + toInstall[i]
    if update:
        runBash("apt-get update")
    if update:
        runBash("apt-get upgrade -y")
    if InstallOnServer:
        runBash("apt-get install -y " + str(totalPackages))
    else:
        ltspChroot("apt-get install -y " + str(totalPackages))


def createTextFile(location, text):
    newText = text.split("\n")
    newText = stripStartWhitespaces(newText)
    newText = stripEndWhitespaces(newText)
    writeTextFile(newText, location)

def makeFolder(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def getReleaseChannel(filepath=PINET_CONF_FILEPATH):
    Channel = "Stable"
    configFile = getList(filepath)
    for i in range(0, len(configFile)):
        if configFile[i][0:14] == "ReleaseChannel":
            Channel = configFile[i][15:len(configFile[i])]
            break

    global ReleaseBranch
    if Channel == "Stable":
        ReleaseBranch = "master"
    elif Channel == "Dev":
        ReleaseBranch = "dev"
    else:
        ReleaseBranch = "master"


def getTextFile(filep):
    """
    Opens the text file and goes through line by line, appending it to the filelist list.
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
    if not os.path.exists(filep):
        return []
    file = open(filep)
    filelist = []
    while 1:
        line = file.readline()
        if not line:
            break
        filelist.append(line) #Go through entire SVG file and import it into a list
    return filelist

def removeN(filelist):
    """
    Removes the final character from every line, this is always /n, aka newline character.
    """
    for count in range(0, len(filelist)):
        filelist[count] = filelist[count][0: (len(filelist[count]))-1]
    return filelist

def blankLineRemover(filelist):
    """
    Removes blank lines in the file.
    """
    toremove = [ ]
    #toremove.append(len(filelist))
    for count in range(0, len(filelist)): #Go through each line in the text file
        found = False
        for i in range(0, len(filelist[count])): #Go through each char in the line
            if not (filelist[count][i] == " "):
                found = True
        if found == False:
            toremove.append(count)

    #toremove.append(len(filelist))
    toremove1 = []
    for i in reversed(toremove):
        toremove1.append(i)


    for r in range(0, len(toremove)):
        filelist.pop(toremove1[r])
        debug("just removed " + str(toremove1[r]))
    return filelist

def writeTextFile(filelist, name):
    """
    Writes the final list to a text file.
    Adds a newline character (\n) to the end of every sublist in the file.
    Then writes the string to the text file.
    """
    file = open(name, 'w')
    mainstr = ""
    for i in range(0, len(filelist)):
        mainstr = mainstr + filelist[i] + "\n"
    file.write(mainstr)
    file.close()
    info("")
    info("------------------------")
    info("File generated")
    info("The file can be found at " + name)
    info("------------------------")
    info("")

def getList(file):
    """
    Creates list from the passed text file with each line a new object in the list
    """
    return removeN(getTextFile(file))

def checkStringExists(filename, toSearchFor):
    textFile = getList(filename)
    unfound = True
    for i in range(0,len(textFile)):
        found = textFile[i].find(toSearchFor)
        if (found != -1):
            unfound = False
            break
    if unfound:
        return False

    return True

def findReplaceAnyLine(textFile, string, newString):
    """
    Basic find and replace function for entire line.
    Pass it a text file in list form and it will search for strings.
    If it finds a string, it will replace the entire line with newString
    If it doesn't find the string, it will add the new string to the end
    """
    unfound = True
    for i in range(0,len(textFile)):
        found = textFile[i].find(string)
        if (found != -1):
            textFile[i] = newString
            unfound = False
    if unfound:
        textFile.append(newString)

    return textFile

def findReplaceSection(textFile, string, newString):
    """
    Basic find and replace function for section.
    Pass it a text file in list form and it will search for strings.
    If it finds a string, it will replace that exact string with newString
    """
    for i in range(0, len(textFile)):
        found = textFile[i].find(string)
        if (found != -1):
            before = textFile[i][0:found]
            after = textFile[i][found+len(string):len(textFile[i])]
            textFile[i] = before+newString+after
    return textFile


def downloadFile(url, saveloc):
    """
    Downloads a file from the internet using a standard browser header.
    Custom header is required to allow access to all pages.
    """
    import traceback
    try:
        req = urllib.request.Request(url)
        req.add_header('User-agent', 'Mozilla 5.10')
        f = urllib.request.urlopen(req)
        text_file = open(saveloc, "wb")
        text_file.write(f.read())
        text_file.close()
        return True
    except:
        print (traceback.format_exc())
        return False

def stripStartWhitespaces(filelist):
    """
    Remove whitespace from start of every line in list.
    """
    for i in range(0, len(filelist)):
        filelist[i] = str(filelist[i]).lstrip()
    return filelist

def stripEndWhitespaces(filelist):
    """
    Remove whitespace from end of every line in list.
    """
    for i in range(0, len(filelist)):
        filelist[i] = str(filelist[i]).rstrip()
    return filelist

def cleanStrings(filelist):
    """
    Removes \n and strips whitespace from before and after each item in the list
    """
    filelist = removeN(filelist)
    filelist = stripStartWhitespaces(filelist)
    return stripEndWhitespaces(filelist)

def getCleanList(filep):
    return cleanStrings(getTextFile(filep))

def compareVersions(local, web):
    """
    Compares 2 version numbers to decide if an update is required.
    """
    web = str(web).split(".")
    local = str(local).split(".")
    if int(web[0]) > int(local[0]):
        returnData(1)
        return True
    else:
        if int(web[1]) > int(local[1]):
            returnData(1)
            return True
        else:
            if int(web[2]) > int(local[2]):
                returnData(1)
                return True
            else:
                returnData(0)
                return False

def getConfigParameter(filep, searchfor):
    textFile = getTextFile(filep)
    textFile = stripEndWhitespaces(textFile)
    value = ""
    for i in range(0,len(textFile)):
        found = textFile[i].find(searchfor)
        if (found != -1):
            value = textFile[i][found+len(searchfor):len(textFile[i])]

    if value == "":
        value = "None"

    return value

def setConfigParameter(option, value, filep = "/etc/pinet"):
    newValue = option + "=" + value
    replaceLineOrAdd(filep, option, newValue)

#def selectFile(start = "/home/"+os.environ['SUDO_USER']+"/"):
#    pass
def returnData(data):
    with open(DATA_TRANSFER_FILEPATH, "w+") as text_file:
        text_file.write(str(data))
    return
    #return fileLoc

def readReturn():
    with open(DATA_TRANSFER_FILEPATH, "r") as text_file:
        print(text_file.read())

def removeFile(file):
    try:
        shutil.rmtree(file)
    except (OSError, IOError):
        pass

def copyFile(src, dest):
    shutil.copy(src, dest)

#----------------Whiptail functions-----------------
def whiptail(*args):
    cmd = ["whiptail"] + list(args)
    p = Popen(cmd,  stderr=PIPE)
    out, err = p.communicate()
    if p.returncode == 0:
        updatePiNet()
        returnData(1)
        return True
    elif p.returncode == 1:
        returnData(0)
        return False
    else:
        return "ERROR"

def whiptailBox(whiltailType, title, message, returnTrueFalse ,height = "8", width= "78", returnErr = False, other=""):
    cmd = ["whiptail", "--title", title, "--"+whiltailType, message, height, width, other]
    p = Popen(cmd,  stderr=PIPE)
    out, err = p.communicate()

    if returnTrueFalse:
        if p.returncode == 0:
            return True
        elif p.returncode == 1:
            return False
        else:
            return "ERROR"
    elif returnErr:
        return err.decode()
    else:
        return p.returncode

def whiptailSelectMenu(title, message, items, height = "16", width = "78", other = "5"):
    cmd = ["whiptail", "--title", title, "--menu", message ,height, width, other]
    itemsList = ""
    for x in range(0, len(items)):
        cmd.append(items[x])
        cmd.append("a")
    cmd.append("--noitem")
    p = Popen(cmd,  stderr=PIPE)
    out, err = p.communicate()
    returnCode = p.returncode
    if str(returnCode) == "0":
        return(err)
    else:
        return("Cancel")

def whiptailCheckList(title, message, items):
    height, width, other = "20", "100", str(len(items)) #"16", "78", "5"
    cmd = ["whiptail", "--title", title, "--checklist", message ,height, width, other]
    itemsList = ""
    for x in range(0, len(items)):
        cmd.append(items[x][0])
        cmd.append(items[x][1])
        cmd.append("OFF")
    p = Popen(cmd,  stderr=PIPE)
    out, err = p.communicate()
    returnCode = p.returncode
    if str(returnCode) == "0":
        return(err)
    else:
        return("Cancel")

#------------------ Utility functions ---------------

def create_user(username, password):
    subprocess.call(["useradd", "-m", "-s", "/bin/bash", "-p", password, username])

def add_user_to_group(username, group):
    subprocess.call(["usermod", "-a", "-G", group, username])

def encrypted_password(password):
    return crypt.crypt(password, "22")

#---------------- Main functions -------------------


def replaceLineOrAdd(file, string, newString):
    """
    Basic find and replace function for entire line.
    Pass it a text file in list form and it will search for strings.
    If it finds a string, it will replace that entire line with newString
    """
    textfile = getList(file)
    textfile = findReplaceAnyLine(textfile, string, newString)
    writeTextFile(textfile, file)

def replaceBitOrAdd(file, string, newString):
    """
    Basic find and replace function for section.
    Pass it a text file in list form and it will search for strings.
    If it finds a string, it will replace that exact string with newString
    """
    textfile = getList(file)
    textfile = findReplaceSection(textfile, string, newString)
    writeTextFile(textfile, file)

def internet_on(timeoutLimit = 5, returnType = True):
    """
    Checks if there is an internet connection.
    If there is, return a 0, if not, return a 1
    """
    #print("Checking internet")
    try:
        response=urllib.request.urlopen('http://www.google.com',timeout=int(timeoutLimit))
        returnData(0)
        #print("returning 0")
        return True
    except:  pass
    try:
        response=urllib.request.urlopen('http://mirrordirector.raspbian.org/',timeout=int(timeoutLimit))
        returnData(0)
        #print("returning 0")
        return True
    except:  pass
    try:
        response=urllib.request.urlopen('http://18.62.0.96',timeout=int(timeoutLimit))
        returnData(0)
        #print("returning 0")
        return True
    except:  pass
    #print("Reached end, no internet")
    returnData(1)
    return False

def updatePiNet():
    """
    Fetches most recent PiNet and PiNet-functions-python.py
    """
    #
    # TODO: TJG not sure why this is here; my guess is that, at
    # some point, the main pinet script ran from the user's home
    # directory. If the policy is now to run from /usr/local/bin/pinet
    # then we need to remove the copy in the home directory.
    #
    try:
        os.remove("/home/" + os.environ['SUDO_USER'] + "/pinet")
        #
        # FIXME: TJG Don't use a bare except
        #
    except: 
        pass
    
    print("")
    print("----------------------")
    print(_("Installing update"))
    print("----------------------")
    print("")
    download = True
    #
    # FIXME: TJG This if download... logic almost certainly doesn't do
    # what's intended.
    #
    if not downloadFile(PINET_DOWNLOAD_URL, os.path.join(PINET_BINPATH, PINET_BINARY)):
        download = False
    if not downloadFile(PINET_PYTHON_DOWNLOAD_URL, os.path.join(PINET_BINPATH, PINET_PYTHON_BINARY)):
        download = False
    if download:
        print("----------------------")
        print(_("Update complete"))
        print("----------------------")
        print("")
        returnData(0)
    else:
        print("")
        print("----------------------")
        print(_("Update failed..."))
        print("----------------------")
        print("")
        returnData(1)


def checkUpdate2():
    """
    Grabs the xml commit log to check for releases. Picks out most recent release and returns it.
    """

    loc = "/tmp/raspiupdate.txt"
    downloadFile("http://bit.ly/pinetcheckmaster", loc)
    from xml.dom import minidom
    xmldoc = minidom.parse(loc)
    version = xmldoc.getElementsByTagName('title')[1].firstChild.nodeValue
    version = cleanStrings([version,])[0]
    if version.find("Release") != -1:
        version = version[8:len(version)]
        print(version)
    else:
        print(_("ERROR"))
        print(_("No release update found!"))

def GetVersionNum(data):
    for i in range(0, len(data)):
        bob = data[i][0:8]
        if data[i][0:7] == "Release":
            bob = data[i]
            version = str(data[i][8:len(data[i])]).rstrip()
            return version


def checkUpdate(currentVersion):
    if not internet_on(5, False):
        print(_("No Internet Connection"))
        returnData(0)
        return
    downloadFile("http://bit.ly/pinetCheckCommits", "/dev/null")
    d = feedparser.parse(Repository +'/commits/' +ReleaseBranch + '.atom')
    releases = []
    data = (d.entries[0].content[0].get('value'))
    data = ''.join(xml.etree.ElementTree.fromstring(data).itertext())
    data = data.split("\n")
    thisVersion = GetVersionNum(data)
    #thisVersion = data[0].rstrip()
    #thisVersion = thisVersion[8:len(thisVersion)]

    if compareVersions(currentVersion, thisVersion):
        whiptailBox("msgbox", _("Update detected"), _("An update has been detected for PiNet. Select OK to view the Release History."), False)
        displayChangeLog(currentVersion)
    else:
        print(_("No PiNet software updates found"))
        #print(thisVersion)
        #print(currentVersion)
        returnData(0)



def checkKernelFileUpdateWeb():
    #downloadFile(RawRepository +"/" + ReleaseBranch + "/boot/version.txt", "/tmp/kernelVersion.txt")
    downloadFile(RawBootRepository +"/" + ReleaseBranch + "/boot/version.txt", "/tmp/kernelVersion.txt")
    import os.path
    user=os.environ['SUDO_USER']
    currentPath="/home/"+user+"/PiBoot/version.txt"
    if (os.path.isfile(currentPath)) == True:
        current = int(getCleanList(currentPath)[0])
        new = int(getCleanList("/tmp/kernelVersion.txt")[0])
        if new > current:
            returnData(1)
            return False
        else:
            returnData(0)
            print(_("No kernel updates found"))
            return True
    else:
        returnData(0)
        print(_("No kernel updates found"))

def checkKernelUpdater():
    downloadFile(RawRepository +"/" + ReleaseBranch + "/Scripts/kernelCheckUpdate.sh", "/tmp/kernelCheckUpdate.sh")

    import os.path
    if os.path.isfile("/opt/ltsp/armhf/etc/init.d/kernelCheckUpdate.sh"):

        currentVersion = int(getConfigParameter("/opt/ltsp/armhf/etc/init.d/kernelCheckUpdate.sh", "version="))
        newVersion = int(getConfigParameter("/tmp/kernelCheckUpdate.sh", "version="))
        if currentVersion < newVersion:
            installCheckKernelUpdater()
            returnData(1)
            return False
        else:
            returnData(0)
            return True
    else:
        installCheckKernelUpdater()
        returnData(1)
        return False

def installCheckKernelUpdater():
    import shutil
    from subprocess import Popen, PIPE, STDOUT
    shutil.copy("/tmp/kernelCheckUpdate.sh", "/opt/ltsp/armhf/etc/init.d/kernelCheckUpdate.sh")
    Popen(['ltsp-chroot', '--arch', 'armhf', 'chmod', '755', '/etc/init.d/kernelCheckUpdate.sh'], stdout=PIPE, stderr=PIPE, stdin=PIPE)
    process = Popen(['ltsp-chroot', '--arch', 'armhf', 'update-rc.d', 'kernelCheckUpdate.sh', 'defaults'], stdout=PIPE, stderr=PIPE, stdin=PIPE)
    process.communicate()

#def importUsers():

def displayChangeLog(version):
    version = "Release " + version
    d = feedparser.parse(Repository +'/commits/' +ReleaseBranch + '.atom')
    releases = []
    for x in range(0, len(d.entries)):
        data = (d.entries[x].content[0].get('value'))
        data = ''.join(xml.etree.ElementTree.fromstring(data).itertext())
        data = data.split("\n")
        thisVersion = "Release " + GetVersionNum(data)
        #thisVersion = data[0].rstrip()
        if thisVersion == version:
            break
        elif x == 10:
            break
        if data[0][0:5] == "Merge":
            continue
        releases.append(data)
    output=[]
    for i in range(0, len(releases)):
        output.append(releases[i][0])
        for z in range(0, len(releases[i])):
            if not z == 0:
                output.append(" - " +releases[i][z])
        output.append("")
    thing = ""
    for i in range(0, len(output)):
        thing = thing + output[i] + "\n"
    whiptail_cmd = ["whiptail", "--title", _("Release history (Use arrow keys to scroll)") + " - " + version, "--scrolltext", "--"+"yesno", "--yes-button", _("Install") + output[0], "--no-button", _("Cancel"), thing, "24", "78"]
    result = whiptail(*whiptail_cmd)
    if result:
        updatePiNet()
    return result

def previousImport(migration_dirpath="/root/move"):
    #
    # Before this is run, four files will have been unpacked into /root/move:
    # passwd.mig, group.mig, shadow.mig, gshadow.mig
    #
    # Take each of these files and add their contents into the
    # corresponding /etc file, skipping those which already exist
    #
    items = ["passwd", "group", "shadow", "gshadow"]
    #items = ["group",]
    toAdd = []
    for x in range(0, len(items)):
        #migLoc = "/Users/Andrew/Documents/Code/pinetImportTest/" + items[x] + ".mig"
        #etcLoc = "/Users/Andrew/Documents/Code/pinetImportTest/" + items[x]
        migLoc = os.path.join(migration_dirpath, items[x] + ".mig")
        etcLoc = "/etc/" + items[x]
        debug("mig loc " + migLoc)
        debug("etc loc " + etcLoc)
        mig = getList(migLoc)
        etc = getList(etcLoc)
        for i in range(0, len(mig)):
            mig[i] = str(mig[i]).split(":")
        for i in range(0, len(etc)):
            etc[i] = str(etc[i]).split(":")
        for i in range(0, len(mig)):
            unFound = True
            for y in range(0, len(etc)):
                bob = mig[i][0]
                thing = etc[y][0]
                if bob == thing:
                    unFound = False
            if unFound:
                toAdd.append(mig[i])
        for i in range(0, len(toAdd)):
            etc.append(toAdd[i])
        for i in range(0, len(etc)):
            etc[i] = ":".join(etc[i])
        debug(etc)
        writeTextFile(etc, etcLoc)

def importFromCSV(theFile, defaultPassword, test = True):
    """Import users from a space-delimited, pipe-quoted .csv file
    
    FIXME TJG except that it seems to be loading from a conventional,
    comma-separated file.
    """
    userData=[]
    if test == "True" or True:
        test = True
    else:
        test = False
    if os.path.isfile(theFile):
        with open(theFile) as csvFile:
            data = csv.reader(csvFile, delimiter=' ', quotechar='|')
            for row in data:
                try:
                    theRow=str(row[0]).split(",")
                except:
                    raise RuntimeError("Invalid data in CSV file %s" % theFile)
                user=theRow[0]
                if " " in user:
                    whiptailBox("msgbox", _("Error!"), _("CSV file names column (1st column) contains spaces in the usernames! This isn't supported."), False)
                    returnData("1")
                    raise RuntimeError("Usernames with spaces are unsupported")
                if len(theRow) >= 2:
                    if theRow[1] == "":
                        password=defaultPassword
                    else:
                        password=theRow[1]
                else:
                    password=defaultPassword
                userData.append([user, password])
            
            #
            # FIXME TJG Not sure this "if test:" logic is doing what it
            # should be
            #
            if test:
                thing = ""
                for i in range(0, len(userData)):
                    thing = thing + _("Username") + " - " + userData[i][0] + " : " + _("Password - ") + userData[i][1] + "\n"
                whiptail_cmd = ["whiptail", "--title", _("About to import (Use arrow keys to scroll)") ,"--scrolltext", "--"+"yesno", "--yes-button", _("Import") , "--no-button", _("Cancel"), thing, "24", "78"]
                result = whiptail(*whiptail_cmd)
                if result == 0:
                    for x in range(0, len(userData)):
                        user = userData[x][0]
                        password = userData[x][1]
                        encPass = encrypted_password(password)
                        create_user(user, encPass)
                        fixGroupSingle(user)
                        print("Import of " + user + " complete.")
                    whiptailBox("msgbox", _("Complete"), _("Importing of CSV data has been complete."), False)
                else:
                    raise RuntimeError("Some Problem")
    else:
        print(_("Error! CSV file not found at") + " " + theFile)

def fixGroupSingle(username):
    groups = PINET_USER_GROUPS
    for x in range(0, len(groups)):
        add_user_to_group(username, groups[x])

def checkIfFileContains(file, string):
    """
    Simple function to check if a string exists in a file.
    """

    textfile = getList(file)
    unfound = True
    for i in range(0,len(textfile)):
        found = textfile[i].find(string)
        #print("Searching line number " + str(i) + ". Found status is " + str(found))
        #print(textfile[i])
        #print("")
        if (found != -1):
            unfound = False

    if unfound:
        returnData(0)
    else:
        returnData(1)

def savePickled(toSave, path = "/tmp/pinetSoftware.dump"):
    """
    Saves list of softwarePackage objects.
    """
    import pickle
    with open(path, "wb") as output:
        pickle.dump(toSave, output, pickle.HIGHEST_PROTOCOL)

def loadPickled(path= "/tmp/pinetSoftware.dump", deleteAfter = True):
    """
    Loads list of softwarePackage objects ready to be used.
    """
    import pickle
    try:
        with open(path, "rb") as input:
            obj = pickle.load(input)
        if deleteAfter:
            removeFile(path)
        return obj
    except (OSError, IOError):
        if deleteAfter:
            removeFile(path)
        return []

def installEpoptes():
    """
    Install Epoptes classroom management software. Key is making sure groups are correct.
    :return:
    """
    runBash("apt-get install -y epoptes")
    runBash("gpasswd -a root staff")
    runBash("ltsp-chroot --arch armhf apt-get install -y epoptes-client --no-install-recommends")
    runBash("ltsp-chroot --arch armhf epoptes-client -c")
    replaceLineOrAdd("/etc/default/epoptes", "SOCKET_GROUP", "SOCKET_GROUP=teacher")

def installScratchGPIO():
    """
    ScratchGPIO installation process. Includes creating the desktop icon in all users and /etc/skel
    """
    removeFile("/tmp/isgh7.sh")
    removeFile("/opt/ltsp/armhf/usr/local/bin/isgh5.sh")
    removeFile("/opt/ltsp/armhf/usr/local/bin/scratchSudo.sh")
    removeFile("/opt/ltsp/armhf/usr/local/bin/isgh7.sh")
    downloadFile("http://bit.ly/1wxrqdp", "/tmp/isgh7.sh")
    copyFile("/tmp/isgh7.sh", "/opt/ltsp/armhf/usr/local/bin/isgh7.sh")
    replaceLineOrAdd("/opt/ltsp/armhf/usr/local/bin/scratchSudo.sh", "bash /usr/local/bin/isgh7.sh $SUDO_USER", "bash /usr/local/bin/isgh7.sh $SUDO_USER")
    users = getUsers()
    for u in users:
        createTextFile("/home/" + u + "/Desktop/Install-scratchGPIO.desktop", """
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
    makeFolder("/etc/skel/Desktop")
    createTextFile("/etc/skel/Desktop/Install-scratchGPIO.desktop",
    """[Desktop Entry]
    Version=1.0
    Name=Install ScratchGPIO
    Comment=Install ScratchGPIO
    Exec=sudo bash /usr/local/bin/scratchSudo.sh
    Icon=scratch
    Terminal=true
    Type=Application
    Categories=Utility;Application;""")


def installSoftwareList(holdOffInstall = False):
    """
    Replacement for ExtraSoftware function in bash.
    Builds a list of possible software to install (using softwarePackage class) then displays the list using checkbox Whiptail menu.
    Checks what options the user has collected, then saves the packages list to file (using pickle). If holdOffInstall is False, then runs installSoftwareFromFile().
    """
    software = []
    software.append(softwarePackage("Libreoffice", _("A free office suite, similar to Microsoft office"), "script", ["apt-get purge -y openjdk-6-jre-headless openjdk-7-jre-headless ca-certificates-java", "apt-get install -y libreoffice gcj-4.7-jre gcj-jre gcj-jre-headless libgcj13-awt"]))
    software.append(softwarePackage("Arduino-IDE", _("Programming environment for Arduino microcontrollers"), "apt", ["arduino",]))
    software.append(softwarePackage("Scratch-gpio", _("A special version of scratch for GPIO work") , "scratchGPIO", ["",]))
    software.append(softwarePackage("Python-hardware", _("Python libraries for a number of additional addon boards"), "pip", ["pibrella skywriter unicornhat piglow pianohat explorerhat microstacknode twython"]))
    software.append(softwarePackage("Epoptes", _("Free and open source classroom management software"), "epoptes", ["",]))
    software.append(softwarePackage("BlueJ", _("A Java IDE for developing programs quickly and easily"), "script", ["rm -rf /tmp/bluej-314a.deb", "rm -rf /opt/ltsp/armhf/tmp/bluej-314a.deb", "wget http://bluej.org/download/files/bluej-314a.deb -O /tmp/bluej-314a.deb", "dpkg -i /tmp/bluej-314a.deb"]))
    software.append(softwarePackage("Custom-package", _("Allows you to enter the name of a package from Raspbian repository"), "customApt", ["",]))
    software.append(softwarePackage("Custom-python", _("Allows you to enter the name of a Python library from pip."), "customPip", ["",]))
    softwareList = []
    for i in software:
        softwareList.append([i.name, i.description])
    done = False
    if (shutil.get_terminal_size()[0] < 105) or (shutil.get_terminal_size()[0] < 30):
        print("\x1b[8;30;105t")
        time.sleep(0.05)
        #print("Resizing")
    while done == False:
        whiptailBox("msgbox", _("Additional Software"), _("In the next window you can select additional software you wish to install. Use space bar to select applications and hit enter when you are finished."), False)
        result = (whiptailCheckList(_("Extra Software Submenu"), _("Select any software you want to install. Use space bar to select then enter to continue."), softwareList))
        try:
            result = result.decode("utf-8")
        except AttributeError:
            return
        result = result.replace('"', '')
        if result != "Cancel":
            if result == "":
                yesno = whiptailBox("yesno", _("Are you sure?"), _("Are you sure you don't want to install any additional software?"), True)
                if yesno:
                    savePickled(software)
                    done = True
            else:
                resultList = result.split(" ")
                yesno = whiptailBox("yesno", _("Are you sure?"), _("Are you sure you want to install this software?") + " \n" + (result.replace(" ", "\n")), True, height=str(7+len(result.split(" "))))
                if yesno:
                    for i in software:
                        if i.name in resultList:
                            i.customAptPip()
                            #i.marked = True
                    done = True
                    savePickled(software)

    if holdOffInstall == False:
        installSoftwareFromFile()

def installSoftwareFromFile(packages = None):
    """
    Second part of installSoftwareList().
    Loads the pickle encoded list of softwarePackage objects then if they are marked to be installed, installs then.
    """
    needCompress = False
    if packages == None:
        packages = loadPickled()
    for i in packages:
        if i.marked == True:
            print(_("Installing") + " " + str(i.name))
            if needCompress == False:
                ltspChroot("apt-get update")
            i.installPackage()
            i.marked = False
            setConfigParameter("NBDBuildNeeded", "true")
            needCompress = True
        else:
            debug("Not installing " + str(i.name))
    if needCompress:
        nbdRun()




def nbdRun():
    """
    Runs NBD compression tool. Clone of version in main pinet script
    """
    if getConfigParameter("/etc/pinet", "NBD=") == "true":
        if getConfigParameter("/etc/pinet", "NBDuse=") == "true":
            print("--------------------------------------------------------")
            print(_("Compressing the image, this will take roughly 5 minutes"))
            print("--------------------------------------------------------")
            runBash("ltsp-update-image /opt/ltsp/armhf")
            setConfigParameter("NBDBuildNeeded", "false")
        else:
            whiptailBox("msgbox", _("WARNING"), _("Auto NBD compressing is disabled, for your changes to push to the Raspberry Pis, run NBD-recompress from main menu."), False)



#------------------------------Main program-------------------------
if __name__ == '__main__':

    if len(sys.argv) == 1:
        print(_("This python script does nothing on its own, it must be passed stuff"))

    else:
        getReleaseChannel()
        if sys.argv[1] == "replaceLineOrAdd":
            replaceLineOrAdd(sys.argv[2], sys.argv[3], sys.argv[4])
        elif sys.argv[1] == "replaceBitOrAdd":
            replaceBitOrAdd(sys.argv[2], sys.argv[3], sys.argv[4])
        elif sys.argv[1] == "CheckInternet":
            internet_on(sys.argv[2])
        elif sys.argv[1] == "CheckUpdate":
            checkUpdate(sys.argv[2])
        elif sys.argv[1] == "CompareVersion":
            compareVersions(sys.argv[2], sys.argv[3])
        elif sys.argv[1] == "updatePiNet":
            updatePiNet()
        elif sys.argv[1] == "triggerInstall":
            downloadFile("http://bit.ly/pinetinstall1", "/dev/null")
        elif sys.argv[1] == "checkKernelFileUpdateWeb":
            checkKernelFileUpdateWeb()
        elif sys.argv[1] == "checkKernelUpdater":
            checkKernelUpdater()
        elif sys.argv[1] == "installCheckKernelUpdater":
            installCheckKernelUpdater()
        elif sys.argv[1] == "previousImport":
            previousImport()
        elif sys.argv[1] == "importFromCSV":
            importFromCSV(sys.argv[2], sys.argv[3])
        elif sys.argv[1] == "checkIfFileContainsString":
            checkIfFileContains(sys.argv[2], sys.argv[3])
        elif sys.argv[1] == "initialInstallSoftwareList":
            installSoftwareList(True)
        elif sys.argv[1] == "installSoftwareList":
            installSoftwareList(False)
        elif sys.argv[1] == "installSoftwareFromFile":
            installSoftwareFromFile()
