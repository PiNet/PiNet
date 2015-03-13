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
from subprocess import Popen, PIPE
import time

RepositoryBase="https://github.com/pinet/"
RepositoryName="pinet"
RawRepositoryBase="https://raw.github.com/pinet/"
Repository=RepositoryBase + RepositoryName
RawRepository=RawRepositoryBase + RepositoryName
ReleaseBranch = "master"

def getReleaseChannel():
    Channel = "Stable"
    configFile = getList("/etc/pinet")
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
        #print(textFile[i])
        found = textFile[i].find(searchfor)
        if (found != -1):
            #print(textFile[i])
            bob = found+len(searchfor)
            jill = len(searchfor)
            value = textFile[i][found+len(searchfor):len(textFile[i])]

    if value == "":
        value = "None"

    return value

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

#----------------Whiptail functions-----------------
def whiptailBox(type, title, message, returnTF ,height = "8", width= "78"):
    cmd = ["whiptail", "--title", title, "--"+type, message, height, width]
    p = Popen(cmd,  stderr=PIPE)
    out, err = p.communicate()

    if returnTF:
        if p.returncode == 0:
            return True
        elif p.returncode == 1:
            return False
        else:
            return "ERROR"
    else:
        return p.returncode

def whiptailSelectMenu(title, message, items):
    height, width, other = "16", "78", "5"
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

def internet_on(timeoutLimit, returnType = True):
    """
    Checks if there is an internet connection.
    If there is, return a 0, if not, return a 1
    """
    import urllib.request
    #print("Checking internet")
    try:
        response=urllib.request.urlopen('http://18.62.0.96',timeout=int(timeoutLimit))
        returnData(0)
        #print("returning 0")
        return True
    except:  pass
    try:
        response=urllib.request.urlopen('http://74.125.228.100',timeout=int(timeoutLimit))
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
    try:
        os.remove("/home/"+os.environ['SUDO_USER']+"/pinet")
    except: pass
    print("")
    print("----------------------")
    print("Installing update")
    print("----------------------")
    print("")
    download = True
    if not downloadFile(RawRepository +"/" + ReleaseBranch + "/pinet", "/usr/local/bin/pinet"):
        download = False
    if not downloadFile(RawRepository +"/" + ReleaseBranch + "/Scripts/pinet-functions-python.py", "/usr/local/bin/pinet-functions-python.py"):
        download = False
    if download:
        print("----------------------")
        print("Update complete")
        print("----------------------")
        print("")
        returnData(0)
    else:
        print("")
        print("----------------------")
        print("Update failed...")
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
        print("ERROR")
        print("No release update found!")

def GetVersionNum(data):
    for i in range(0, len(data)):
        bob = data[i][0:8]
        if data[i][0:7] == "Release":
            bob = data[i]
            version = str(data[i][8:len(data[i])]).rstrip()
            return version


def checkUpdate(currentVersion):
    if not internet_on(5, False):
        print("No Internet Connection")
        returnData(0)
    import feedparser
    import xml.etree.ElementTree
    d = feedparser.parse(Repository +'/commits/' +ReleaseBranch + '.atom')
    releases = []
    data = (d.entries[0].content[0].get('value'))
    data = ''.join(xml.etree.ElementTree.fromstring(data).itertext())
    data = data.split("\n")
    thisVersion = GetVersionNum(data)
    #thisVersion = data[0].rstrip()
    #thisVersion = thisVersion[8:len(thisVersion)]

    if compareVersions(currentVersion, thisVersion):
        whiptailBox("msgbox", "Update detected", "An update has been detected for PiNet. Select OK to view the Release History.", False)
        displayChangeLog(currentVersion)
    else:
        print("No updates found")
        #print(thisVersion)
        #print(currentVersion)
        returnData(0)



def checkKernelFileUpdateWeb():
    downloadFile(RawRepository +"/" + ReleaseBranch + "/boot/version.txt", "/tmp/kernelVersion.txt")
    import os.path
    user=os.environ['SUDO_USER']
    currentPath="/home/"+user+"/piBoot/version.txt"
    if (os.path.isfile(currentPath)) == True:
        current = int(getCleanList(currentPath)[0])
        new = int(getCleanList("/tmp/kernelVersion.txt")[0])
        if new > current:
            returnData(1)
            return False
        else:
            returnData(0)
            return True
    else:
        returnData(0)

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
    cmd = ["whiptail", "--title", "Release history (Use arrow keys to scroll) - " + version, "--scrolltext", "--"+"yesno", "--yes-button", "Install " + output[0], "--no-button", "Cancel", thing, "24", "78"]
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



#------------------------------Main program-------------------------

getReleaseChannel()
#previousImport()
if len(sys.argv) == 1:
    print("This python script does nothing on its own, it must be passed stuff")



else:
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
