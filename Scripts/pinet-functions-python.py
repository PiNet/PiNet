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
from subprocess import Popen, PIPE, check_output
import time
import shutil
import pwd, grp
from copy import deepcopy
import random
#from gettext import gettext as _
#gettext.textdomain(pinetPython)
import gettext
# Set up message catalog access
#t = gettext.translation('pinetPython', 'locale', fallback=True)
#_ = t.ugettext

def _(placeholder):
    #GNU Gettext placeholder
    return(placeholder)

RepositoryBase="https://github.com/pinet/"
RepositoryName="pinet"
BootRepository="PiNet-Boot"
RawRepositoryBase="https://raw.github.com/pinet/"
Repository=RepositoryBase + RepositoryName
RawRepository=RawRepositoryBase + RepositoryName
RawBootRepository=RawRepositoryBase + BootRepository
ReleaseBranch = "master"
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
            py2 = runBash("ltsp-chroot pip install -U " + programs)
            py3 = runBash("ltsp-chroot pip3 install -U " + programs)
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


def getReleaseChannel():
    """
    Gets the PiNet release chanel (branch) from /etc/pinet and also allows overwriting RepositoryBase and RawRepositoryBase.
    """
    Channel = "Stable"
    configFile = getList("/etc/pinet")
    for i in range(0, len(configFile)):
        if configFile[i][0:14] == "ReleaseChannel":
            Channel = configFile[i][15:len(configFile[i])]
            break

    global ReleaseBranch, RepositoryBase, Repository, RawRepository, RawBootRepository, RawRepositoryBase
    Channel = Channel.lower()
    if Channel == "stable":
        ReleaseBranch = "master"
    elif Channel == "dev":
        ReleaseBranch = "dev"
    elif len(Channel) > 7 and Channel[0:7].lower() == "custom:":
        ReleaseBranch = Channel[7:len(Channel)]
    else:
        ReleaseBranch = "master"

    RepositoryBaseCustom=""
    RawRepositoryBaseCustom=""

    needUpdateRepoVariables = False

    for i in range(0, len(configFile)):  # Check if overwriting RepositoryBase
        if configFile[i][0:14] == "RepositoryBase":
            RepositoryBaseCustom = configFile[i][15:len(configFile[i])]
            if RepositoryBaseCustom != "":
                RepositoryBase = RepositoryBaseCustom
                needUpdateRepoVariables = True
            break

    for i in range(0, len(configFile)):  # Check if overwriting RawRepositoryBase
        if configFile[i][0:17] == "RawRepositoryBase":
            RawRepositoryBaseCustom = configFile[i][18:len(configFile[i])]
            if RawRepositoryBaseCustom != "":
                RawRepositoryBase = RawRepositoryBaseCustom
                needUpdateRepoVariables = True
            break

    if needUpdateRepoVariables:
        Repository=RepositoryBase + RepositoryName
        RawRepository=RawRepositoryBase + RepositoryName
        RawBootRepository=RawRepositoryBase + BootRepository



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
        import urllib.request
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
    with open("/tmp/ltsptmp", "w+") as text_file:
        text_file.write(str(data))
    return
    #return fileLoc

def readReturn():
    with open("/tmp/ltsptmp", "r") as text_file:
        print(text_file.read())

def removeFile(file):
    try:
        shutil.rmtree(file)
    except (OSError, IOError):
        pass

def copyFile(src, dest):
    shutil.copy(src, dest)

#----------------Whiptail functions-----------------
def whiptailBox(whiltailType, title, message, returnTrueFalse ,height = "8", width= "78", returnErr = False, other = ""):
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

def whiptailBoxYesNo(title, message, returnTrueFalse ,height = "8", width= "78", returnErr = False, customYes = "", customNo = ""):
    cmd = ["whiptail", "--title " + title,  "--yesno", message, height, width, "--yes-button " + customYes, "--no-button " + customNo]
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
    import urllib.request
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

def testSiteConnection(siteURL, timeoutLimit = 5):
    """
    Tests to see if can access the given website.
    """
    import urllib.request
    try:
        response=urllib.request.urlopen(siteURL,timeout=int(timeoutLimit))
        return True
    except:
        return False

def internetFullStatusReport(timeoutLimit = 5, whiptail = False, returnStatus = False):
    """
    Full check of all sites used by PiNet. Only needed on initial install
    """
    sites = []
    sites.append([_("Main Raspbian repository"), "http://archive.raspbian.org/raspbian.public.key", ("Critical"), False])
    sites.append([_("Raspberry Pi Foundation repository"), "http://archive.raspberrypi.org/debian/raspberrypi.gpg.key", ("Critical"),False])
    sites.append([_("Github"), "https://github.com", ("Critical"), False])
    sites.append([_("Bit.ly"), "http://bit.ly", ("Highly recommended"), False])
    sites.append([_("Bitbucket (Github mirror, not active yet)"), "https://bitbucket.org", ("Recommended"), False])
    sites.append([_("BlueJ"), "http://bluej.org", ("Recommended"), False])
    sites.append([_("PiNet metrics"), "https://secure.pinet.org.uk", ("Recommended"), False])
    for website in range(0, len(sites)):
        sites[website][3] = testSiteConnection(sites[website][1])
    if returnStatus:
        return sites
    if whiptail:
        message = ""
        for website in sites:
            if sites[3]:
                status = "Success"
            else:
                status = "Failed"
            message = message + status + " - " + website[2] + " - " +  website[0] + " (" + website[1] + ")\n"
            if (shutil.get_terminal_size()[0] < 105) or (shutil.get_terminal_size()[0] < 30):
                print("\x1b[8;30;105t")
                time.sleep(0.05)
        whiptailBox("msgbox", "Web filtering test results", message, True, height="14", width="100")
    else:
        for website in range(0, len(sites)):
            print(str(sites[website][2] + " - " ))

def internetFullStatusCheck(timeoutLimit = 5):
    results = internetFullStatusReport(timeoutLimit = timeoutLimit, returnStatus = True)
    for site in results:
        if site[2] == "Critical":
            if site[3] == False:
                whiptailBox("msgbox", _("Unable to proceed"), _("The requested action is unable to proceed as PiNet is not able to access a critical site. Perhaps your internet connection is not active or a proxy or web filtering system may be blocking access. The critical domain that is unable to be accessed is - " + site[1]), False, height="11")
                returnData(1)
                return False
        elif site[2] == "Highly recommended":
            if site[3] == False:
                answer = whiptailBox("yesno", _("Proceeding not recommended"), _("A highly recommended site is inaccessible. Perhaps a proxy or web filtering system may be blockeing access. Would you like to proceed anyway? (not recommended). The domain that is unable to be accessed is - " + site[1]), True, height="11")
                if answer == False:
                    returnData(1)
                    return False
        elif site[2] == "Recommended":
            if site[3] == False:
                answer = whiptailBox("yesno", _("Proceeding not recommended"), _("A recommended site is inaccessible. Perhaps a proxy or web filtering system may be blockeing access. Would you like to proceed anyway? (not recommended). The domain that is unable to be accessed is - " + site[1]), True, height="11")
                if answer == False:
                    returnData(1)
                    return False
        else:
            print("Unknown site type...")
    returnData(0)
    return True



def updatePiNet():
    """
    Fetches most recent PiNet and PiNet-functions-python.py
    """
    try:
        os.remove("/home/"+os.environ['SUDO_USER']+"/pinet")
    except: pass
    print("")
    print("----------------------")
    print(_("Installing update"))
    print("----------------------")
    print("")
    download = True
    if not downloadFile(RawRepository +"/" + ReleaseBranch + "/pinet", "/usr/local/bin/pinet"):
        download = False
    if not downloadFile(RawRepository +"/" + ReleaseBranch + "/Scripts/pinet-functions-python.py", "/usr/local/bin/pinet-functions-python.py"):
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
        line = data[i][0:8]
        if data[i][0:7] == "Release":
            line = data[i]
            version = str(data[i][8:len(data[i])]).rstrip()
            return version


def checkUpdate(currentVersion):
    if not internet_on(5, False):
        print(_("No Internet Connection"))
        returnData(0)
    import feedparser
    import xml.etree.ElementTree
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
    import feedparser
    import xml.etree.ElementTree
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
    cmd = ["whiptail", "--title", _("Release history (Use arrow keys to scroll)") + " - " + version, "--scrolltext", "--"+"yesno", "--yes-button", _("Install ") + output[0], "--no-button", _("Cancel"), thing, "24", "78"]
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

def previousImport():
    items = ["passwd", "group", "shadow", "gshadow"]
    #items = ["group",]
    toAdd = []
    for x in range(0, len(items)):
        #migLoc = "/Users/Andrew/Documents/Code/pinetImportTest/" + items[x] + ".mig"
        #etcLoc = "/Users/Andrew/Documents/Code/pinetImportTest/" + items[x]
        migLoc = "/root/move/" + items[x] + ".mig"
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
            line = ""
            for y in range(0, len(etc[i])):
                line = line  + etc[i][y] + ":"
            line = line[0:len(line) - 1]
            etc[i] = line
        debug(etc)
        writeTextFile(etc, etcLoc)

def importFromCSV(theFile, defaultPassword, test = True):
    import csv
    import os
    from sys import exit
    import crypt
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
                    whiptailBox("msgbox", _("Error!"), _("CSV file invalid!"), False)
                    sys.exit()
                user=theRow[0]
                if " " in user:
                    whiptailBox("msgbox", _("Error!"), _("CSV file names column (1st column) contains spaces in the usernames! This isn't supported."), False)
                    returnData("1")
                    sys.exit()
                if len(theRow) >= 2:
                    if theRow[1] == "":
                        password=defaultPassword
                    else:
                        password=theRow[1]
                else:
                    password=defaultPassword
                userData.append([user, password])
            if test:
                thing = ""
                for i in range(0, len(userData)):
                    thing = thing + _("Username") + " - " + userData[i][0] + " : " + _("Password - ") + userData[i][1] + "\n"
                cmd = ["whiptail", "--title", _("About to import (Use arrow keys to scroll)") ,"--scrolltext", "--"+"yesno", "--yes-button", _("Import") , "--no-button", _("Cancel"), thing, "24", "78"]
                p = Popen(cmd,  stderr=PIPE)
                out, err = p.communicate()
                if p.returncode == 0:
                    for x in range(0, len(userData)):
                        user = userData[x][0]
                        password = userData[x][1]
                        encPass = crypt.crypt(password,"22")
                        cmd = ["useradd", "-m", "-s", "/bin/bash", "-p", encPass, user]
                        p = Popen(cmd,  stderr=PIPE)
                        out, err = p.communicate()
                        fixGroupSingle(user)
                        print("Import of " + user + " complete.")
                    whiptailBox("msgbox", _("Complete"), _("Importing of CSV data has been complete."), False)
                else:
                    sys.exit()
    else:
        print(_("Error! CSV file not found at") + " " + theFile)

def fixGroupSingle(username):
    groups = ["adm", "dialout", "cdrom", "audio", "users", "video", "games", "plugdev", "input", "pupil"]
    for x in range(0, len(groups)):
        cmd = ["usermod", "-a", "-G", groups[x], username]
        p = Popen(cmd,  stderr=PIPE)
        out, err = p.communicate()

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
    #software.append(softwarePackage("Python-hardware", _("Python libraries for a number of additional addon boards"), "pip", ["pibrella skywriter unicornhat piglow pianohat explorerhat microstacknode twython"]))
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

def generateServerID():
    """
    Generates random server ID for use with stats system.
    """
    ID = random.randint(10000000000,99999999999)
    setConfigParameter("ServerID", str(ID))

def getIPAddress():
    """
    Get the PiNet server external IP address using the dnsdynamic.org IP address checker.
    If there is any issues, defaults to returning 0.0.0.0.
    """
    try:
        import urllib.request
        import socket
        with urllib.request.urlopen("http://myip.dnsdynamic.org/") as url:
            IP = url.read().decode()
            socket.inet_aton(IP)
    except:
        IP = "0.0.0.0"
    return IP


def sendStats():
    """
    Upload anonymous stats to the secure PiNet server (over encrypted SSL).
    """
    DisableMetrics = str(getConfigParameter("/etc/pinet", "DisableMetrics="))
    ServerID = str(getConfigParameter("/etc/pinet", "ServerID="))
    if ServerID == "None":
        generateServerID()
        ServerID = str(getConfigParameter("/etc/pinet", "ServerID="))
    if DisableMetrics.lower() == "true":
        PiNetVersion="0.0.0"
        Users="0"
        KernelVersion = "000"
        ReleaseChannel = "0"
        City = "Blank"
        OrganisationType = "Blank"
        OrganisationName = "Blank"
    else:
        PiNetVersion = str(getConfigParameter("/usr/local/bin/pinet", "version="))
        Users = str(len(getUsers()))
        if os.path.exists("/home/"+os.environ['SUDO_USER']+"/PiBoot/version.txt"):
            KernelVersion = str(getCleanList("/home/"+os.environ['SUDO_USER']+"/PiBoot/version.txt")[0])
        else:
            KernelVersion = "000"
        City = str(getConfigParameter("/etc/pinet", "City="))
        OrganisationType = str(getConfigParameter("/etc/pinet", "OrganisationType="))
        OrganisationName = str(getConfigParameter("/etc/pinet", "OrganisationName="))
        ReleaseChannel = str(getConfigParameter("/etc/pinet", "ReleaseChannel="))

    IPAddress = getIPAddress()

    command = 'curl --connect-timeout 2 --data "ServerID='+ ServerID + "&" + "PiNetVersion=" + PiNetVersion +  "&" + "Users=" + Users + "&" +  "KernelVersion=" + KernelVersion +  "&" +  "ReleaseChannel=" + ReleaseChannel + "&" + "IPAddress=" + IPAddress + "&" + "City=" + City + "&" + "OrganisationType=" + OrganisationType + "&" + "OrganisationName=" + OrganisationName + '"  https://secure.pinet.org.uk/pinetstatsv1.php -s -o /dev/null 2>&1'
    runBash(command)

def checkStatsNotification():
    """
    Displays a one time notification to the user only once on the metrics.
    """
    ShownStatsNotification = str(getConfigParameter("/etc/pinet", "ShownStatsNotification="))
    if ShownStatsNotification == "true":
        pass #Don't display anything
    else:
        whiptailBox("msgbox", _("Stats"), _("Please be aware PiNet now collects very basic usage stats. These stats are uploaded to the secure PiNet metrics server over an encrypted 2048 bit SSL/TLS connection. The stats logged are PiNet version, Raspbian kernel version, number of users, development channel (stable or dev), external IP address, a randomly generated unique ID and any additional information you choose to add. These stats are uploaded in the background when PiNet checks for updates. Should you wish to disable the stats, see - http://pinet.org.uk/articles/advanced/metrics.html"), False, height="14")
        setConfigParameter("ShownStatsNotification", "true", "/etc/pinet")
        askExtraStatsInfo()

def askExtraStatsInfo():
    import re
    """
    Ask the user for additional stats information.
    """
    whiptailBox("msgbox", _("Additional information"), _("It is really awesome to see and hear from users across the world using PiNet. So we can start plotting schools/organisations using PiNet on a map, feel free to add any extra information to your PiNet server. It hugely helps us out also for internationalisation/localisation of PiNet. If you do not want to attach any extra information, please simply leave the following prompts blank."), False, height="13")
    city = whiptailBox("inputbox", _("Nearest major city"), _("To help with putting a dot on the map for your server, what is your nearest major town or city? Leave blank if you don't want to answer."), False, returnErr = True)
    organisationType = whiptailSelectMenu(_("Organisation type"), _("What type of organisation are you setting PiNet up for? Leave on blank if you don't want to answer."), ["Blank", "School", "Non Commercial Organisation", "Commercial Organisation", "Raspberry Jam/Club", "N/A"])
    organisationName = whiptailBox("inputbox", _("School/organisation name"), _("What is the name of your organisation? Leave blank if you don't want to answer."), False, returnErr = True)
    whiptailBox("msgbox", _("Additional information"), _('Thanks for taking the time to read through (and if possible fill in) additional information. If you ever want to edit your information supplied, you can do so by selecting the "Other" menu and selecting "Edit-Information".'), False, height="11")
    try:
        organisationType = organisationType.decode("utf-8")
    except:
        organisationType = "Blank"
    if city == "":
        city = "Blank"
    if organisationType == "":
        organisationType = "Blank"
    if organisationName == "":
        organisationName = "Blank"
    city =  re.sub('[^0-9a-zA-Z]+', '_', city)
    organisationType = re.sub('[^0-9a-zA-Z]+', '_', organisationType)
    organisationName = re.sub('[^0-9a-zA-Z]+', '_', organisationName)
    setConfigParameter("City", city)
    setConfigParameter("OrganisationType", organisationType)
    setConfigParameter("OrganisationName", organisationName)
    sendStats()


#------------------------------Main program-------------------------

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
    elif sys.argv[1] == "sendStats":
        sendStats()
    elif sys.argv[1] == "checkStatsNotification":
        checkStatsNotification()
    elif sys.argv[1] == "askExtraStatsInfo":
        askExtraStatsInfo()
    elif sys.argv[1] == "internetFullStatusCheck":
        internetFullStatusCheck()
    elif sys.argv[1] == "setConfigParameter":
        setConfigParameter(sys.argv[2], sys.argv[3])
