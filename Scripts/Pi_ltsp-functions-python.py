#! /usr/bin/env python3


#Raspi-LTSP
#Pi_ltsp-functions-python.py
#Written by Andrew Mulholland
#Supporting python functions for the main Pi_ltsp script in BASH.
#Written for Python 3.4

#Raspi-LTSP is a utility for setting up and configuring a Linux Terminal Server Project (LTSP) network for Raspberry Pi's


from logging import debug, info, warning, basicConfig, INFO, DEBUG, WARNING
basicConfig(level=WARNING)
import sys, os



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
    import urllib.request
    req = urllib.request.Request(url)
    req.add_header('User-agent', 'Mozilla 5.10')
    f = urllib.request.urlopen(req)
    text_file = open(saveloc, "wb")
    text_file.write(f.read())
    text_file.close()

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

def compareVersions(local, web):
    """
    Compares 2 version numbers to decide if an update is required.
    """
    web = str(web).split(".")
    local = str(local).split(".")
    if int(web[0]) > int(local[0]):
        print(1)
        return
    else:
        if int(web[1]) > int(local[1]):
            print(1)
            return
        else:
            if int(web[2]) > int(local[2]):
                print(1)
                return
            else:
                print(0)
                return

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

def internet_on(timeoutLimit):
    """
    Checks if there is an internet connection.
    If there is, return a 0, if not, return a 1
    """
    import urllib.request
    try:
        response=urllib.request.urlopen('http://18.62.0.96',timeout=int(timeoutLimit))
        print("0")
        return
    except:  pass
    try:
        response=urllib.request.urlopen('http://74.125.228.100',timeout=int(timeoutLimit))
        print("0")
        return
    except:  pass
    print("1")
    return

def updatePiLTSP():
    """
    Fetches most recent Pi_ltsp and Pi_ltsp-functions-python.py
    """
    try:
        os.remove("/home/"+os.environ['SUDO_USER']+"/Pi_ltsp")
    except: pass
    downloadFile("http://bit.ly/piltspupdate", "/usr/local/bin/Pi_ltsp")
    downloadFile("https://raw.githubusercontent.com/gbaman/RaspberryPi-LTSP/master/Scripts/Pi_ltsp-functions-python.py", "/usr/local/bin/Pi_ltsp-functions-python.py")
    print(0)


def checkUpdate():
    """
    Grabs the xml commit log to check for releases. Picks out most recent release and returns it.
    """
    loc = "/tmp/raspiupdate.txt"
    downloadFile("http://bit.ly/piltspcheckmaster", loc)
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



#------------------------------Main program-------------------------


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
        checkUpdate()
    elif sys.argv[1] == "CompareVersion":
        compareVersions(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "updatePiLTSP":
        updatePiLTSP()
    elif sys.argv[1] == "triggerInstall":
        downloadFile("http://bit.ly/piltspinstall1", "/dev/null")


