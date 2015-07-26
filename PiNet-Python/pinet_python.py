from pinet_functions_python import getTextFile, writeTextFile, cleanStrings, replaceLineOrAdd, checkStringExists, \
    downloadFile, stripEndWhitespaces, stripStartWhitespaces, runBash, runBashOutput


import subprocess
import os
import shutil
import errno
import pwd, grp
from pinet_users import addUsers


RAWREPOSTORY = "https://raw.github.com/pinet/pinet/"
BRANCH = "master"
REPOSITORY = RAWREPOSTORY + BRANCH


"""def copyFile(src, dest):
    try:
        shutil.copy(src, dest)
    # eg. src and dest are the same file
    except shutil.Error as e:
        print('Error: %s' % e)
    # eg. source or destination doesn't exist
    except IOError as e:
        print('Error: %s' % e.strerror)"""


def copyFile(src, dest):
    try:
        shutil.copytree(src, dest)
    except OSError as exc:
        if exc.errno == errno.ENOTDIR:
            shutil.copy(src, dest)
        elif exc.errno == 17:
            pass
        else:
            raise


def removeFile(file):
    try:
        shutil.rmtree(file)
    except (OSError, IOError):
        pass


def getUsers(includeRoot=False):
    users = []
    for p in pwd.getpwall():
        if (len(str(p[2])) > 3) and (str(p[5])[0:5] == "/home"): #or (str(p[5])[0:5] == "/root"):
            users.append(p[0])
    return users


def ltspChroot(command):
    runBash("ltsp-chroot --arch armhf " + command)

def updateConfig():
    pass

def installPackage(toInstall, update=False, upgrade=False, InstallOnServer=False):
    # cache = apt.Cache
    # pkgs = []
    # for i in range(0, len(toInstall)):
    #   pkgs.append(cache[toInstall[i]])
    #    pkgs[i].mark_install()
    # cache.commit()
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


def installLtspPackages():
    installPackage(
        "ltsp-server qemu-user-static binfmt-support ldm-server sed git gnome-control-center nfs-kernel-server xml2 openssh-server inotify-tools bindfs",
        True, True, True)
    # apt.Package.mark_install("ltsp-server qemu-user-static binfmt-support ldm-server sed git gnome-control-center nfs-kernel-server xml2 openssh-server inotify-tools bindfs")


def buildPiNetClient():
    runBash("wget http://archive.raspbian.org/raspbian.public.key -O - | gpg --import")
    runBash("gpg --export 90FDDD2E >> /etc/ltsp/raspbian.public.key.gpg")
    createTextFile("/etc/ltsp/ltsp-raspbian.conf",
                   """DEBOOTSTRAP_KEYRING=/etc/ltsp/raspbian.public.key.gpg
    DIST=wheezy
    # For alternate raspbian mirrors, see: http://www.raspbian.org/RaspbianMirrors
    MIRROR=http://mirrordirector.raspbian.org/raspbian
    SECURITY_MIRROR=none
    UPDATES_MIRROR=none
    LOCALE="$LANG UTF-8"
    KERNEL_PACKAGES=linux-image-3.10-3-rpi""")
    runBash("VENDOR=Debian ltsp-build-client --arch armhf --config /etc/ltsp/ltsp-raspbian.conf")


def setupOneOffFixes():
    replaceLineOrAdd("/etc/exports", "/opt/ltsp", "/opt/ltsp *(ro,no_root_squash,async,no_subtree_check)")
    replaceLineOrAdd("/etc/exports", "/home", "/home   *(rw,sync,no_subtree_check)")
    makeFolder("/etc/skel/handin")
    replaceLineOrAdd("/etc/network/if-up.d/tftpd-hpa", "#!", "#!/bin/sh")
    replaceLineOrAdd("/etc/network/if-up.d/tftpd-hpa", "service", "service tftpd-hpa restart")
    os.chmod("/etc/network/if-up.d/tftpd-hpa", 0o755)
    runBash("service tftpd-hpa restart")
    runBash("groupadd -g 2122 pupil")
    runBash("groupadd -g 2123 teacher")


def setupConfigFixes():
    """sed -i -e 's,/bin/plymouth quit --retain-splash.*,/bin/plymouth quit --retain-splash || true,g' /opt/ltsp/armhf/etc/init.d/ltsp-client-core """

    replaceLineOrAdd("/opt/ltsp/armhf/etc/lts.conf", "LTSP_FATCLIENT", "LTSP_FATCLIENT=true")
    copyFile("/opt/ltsp/armhf/etc/lts.conf", "/var/lib/tftpboot/ltsp/armhf/lts.conf")
    replaceLineOrAdd("/opt/ltsp/armhf/etc/modules", "/opt/ltsp/armhf/etc/asound.conf",
                     "/opt/ltsp/armhf/etc/asound.conf")
    addSoundcardConfig()


def addSoundcardConfig():
    if checkStringExists("/opt/ltsp/armhf/etc/asound.conf", "mmap_emul") == False:
        createTextFile("/opt/ltsp/armhf/etc/asound.conf",
                       """pcm.!default {
        type hw;
        card 0;
        }

        ctl.!default {
            type hw
            card 0
        }""")
        return 1
    else:
        return 0


def addSinglePackageRepo(keyURL, repoLoc, repoData):
    downloadFile(keyURL, "/opt/ltsp/armhf/raspberrypi.gpg.key")
    ltspChroot("apt-key add /raspberrypi.gpg.key")
    os.remove("/opt/ltsp/armhf/raspberrypi.gpg.key")
    replaceLineOrAdd(repoLoc, repoData, repoData)


def addPackageRepos():
    addSinglePackageRepo("http://archive.raspberrypi.org/debian/raspberrypi.gpg.key",
                         "/opt/ltsp/armhf/etc/apt/sources.list.d/raspi.list",
                         "deb http://archive.raspberrypi.org/debian/ wheezy main")
    # addSinglePackageRepo("", "/opt/ltsp/armhf/etc/apt/sources.list.d/collabora.list", "deb http://raspberrypi.collabora.com wheezy rpi")
    downloadFile("http://archive.raspberrypi.org/debian/raspberrypi.gpg.key", "/opt/ltsp/armhf/raspberrypi.gpg.key")
    ltspChroot("apt-key add /raspberrypi.gpg.key")
    os.remove("/opt/ltsp/armhf/raspberrypi.gpg.key")
    #runBash("""ltsp-chroot --arch armhf debconf-set-selections wolfram-engine shared/accepted-wolfram-eula boolean true""")
    replaceLineOrAdd("/opt/ltsp/armhf/etc/apt/sources.list", "mirrordirector",
                     "deb http://mirrordirector.raspbian.org/raspbian/ wheezy main contrib non-free rpi ")
    #ltspChroot("apt-get update")


def addSoftware():
    ltspChroot("apt-get update")
    installPackage(
        "idle idle3 python-dev nano python3-dev scratch python3-tk git debian-reference-en dillo python python-pygame python3-pygame python-tk sudo sshpass pcmanfm chromium python3-numpy wget xpdf gtk2-engines alsa-utils wpagui omxplayer lxde net-tools",
        False, False, False)
    installPackage(
        "ssh locales less fbset sudo psmisc strace module-init-tools ifplugd ed ncdu console-setup keyboard-configuration debconf-utils parted unzip build-essential manpages-dev python bash-completion gdb pkg-config python-rpi.gpio v4l-utils lua5.1 luajit hardlink ca-certificates curl fake-hwclock ntp nfs-common usbutils libraspberrypi-dev libraspberrypi-doc libfreetype6-dev",
        False, False, False)
    installPackage(
        "python3-rpi.gpio python-rpi.gpio python-pip python3-pip python-picamera python3-picamera x2x xserver-xorg-video-fbturbo netsurf-common netsurf-gtk rpi-update",
        False, False, False)
    installPackage(
        "ftp libraspberrypi-bin python3-pifacecommon python3-pifacedigitalio python3-pifacedigital-scratch-handler python-pifacecommon python-pifacedigitalio i2c-tools man-db",
        False, False, False)
    installPackage("--no-install-recommends cifs-utils midori lxtask", False, False, False)
    installPackage("minecraft-pi python-smbus dosfstools ruby iputils-ping", False, False, False)
    installPackage(
        "gstreamer1.0-x gstreamer1.0-omx gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-alsa gstreamer1.0-libav",
        False, False, False)
    installPackage("--no-install-recommends -y epiphany-browser cgroup-bin", False, False, False)
    installPackage("""-o Dpkg::Options::="--force-confnew" raspberrypi-net-mods""", False, False, False)
    installPackage(
        "java-common oracle-java8-jdk apt-utils wpasupplicant wireless-tools firmware-atheros firmware-brcm80211 firmware-libertas firmware-ralink firmware-realtek libpng12-dev",
        False, False, False)
    installPackage(
        "linux-image-3.18.0-trunk-rpi linux-image-3.18.0-trunk-rpi2 linux-image-3.12-1-rpi linux-image-3.10-3-rpi linux-image-3.2.0-4-rpi linux-image-rpi-rpfv linux-image-rpi2-rpfv",
        False, False, False)
    installPackage("", False, False, False)
    runBash("DEBIAN_FRONTEND=noninteractive ltsp-chroot --arch armhf apt-get install -y sonic-pi")
    ltspChroot("update-rc.d nfs-common disable")
    ltspChroot("update-rc.d rpcbind disable")
    installPackage("bindfs python3-feedparser ntp", False, False, True)

    if not os.path.exists("/opt/ltsp/armhf/usr/local/bin/raspi2png"):
        downloadFile("https://github.com/AndrewFromMelbourne/raspi2png/blob/master/raspi2png?raw=true",
                     "/tmp/raspi2png")
        copyFile("/tmp/raspi2png", "/opt/ltsp/armhf/usr/local/bin/raspi2png")
        os.chmod("/opt/ltsp/armhf/usr/local/bin/raspi2png", 0o755)


def raspiTheme():
    removeFile("/tmp/pinet")
    runBash("git clone --depth 1 https://github.com/PiNet/PiNet.git /tmp/pinet")
    copyFile("/tmp/pinet/themes/raspi", "/opt/ltsp/armhf/usr/share/ldm/themes/raspi")
    removeFile("/opt/ltsp/armhf/etc/alternatives/ldm-theme")
    runBash("ln -s /usr/share/ldm/themes/raspi /opt/ltsp/armhf/etc/alternatives/ldm-theme")
    removeFile("/tmp/pinet")
    copyFile("/opt/ltsp/armhf/usr/share/ldm/themes/raspi/bg.png",
             "/opt/ltsp/armhf/usr/share/images/desktop-base/pinet.png")
    ltspChroot(
        "update-alternatives --install /usr/share/images/desktop-base/desktop-background desktop-background /usr/share/images/desktop-base/pinet.png 100")


def addDesktopIcons():
    removeFile("/etc/skel/Desktop")
    os.mkdir("/etc/skel/Desktop")
    desktopIcons = "scratch.desktop idle.desktop idle3.desktop lxterminal.desktop debian-reference-common.desktop epiphany-browser.desktop sonic-pi.desktop minecraft-pi.desktop"
    #wolfram-mathematica.desktop wolfram-language.desktop

    desktopIcons = desktopIcons.split(" ")
    for d in desktopIcons:
        copyFile("/opt/ltsp/armhf/usr/share/applications/" + d, "/etc/skel/Desktop/" + d)
    #downloadFile("https://github.com/KenT2/python-games/tarball/master", "/tmp/python_games.tar.gz")
    runBash("git clone https://github.com/KenT2/python-games.git /tmp/python_games")
    copyFile("/tmp/python_games", "/etc/skel/python_games")
    os.chmod("/etc/skel/python_games/launcher.sh", 0o755)
    removeFile("/tmp/python_games.tar.gz")
    createTextFile("/etc/skel/Desktop/python_games.desktop", """
    [Desktop Entry]
    Name=Python Games
    Comment=From http://inventwithpython.com/pygame/
    Exec=sh -c $HOME/python_games/launcher.sh
    Icon=/usr/share/pixmaps/python.xpm
    Terminal=false
    Type=Application
    Categories=Application;Games;
    StartupNotify=true""")

    for i in getUsers():
        try:
            os.mkdir("/home/" + i + "/Desktop")
        except (OSError, IOError):
            pass
        for file in os.listdir("/etc/skel/Desktop"):
            copyFile("/etc/skel/Desktop/" + str(file), "/home/" + i + "/Desktop/" + str(file))
            os.chown("/home/" + i + "/Desktop/" + str(file), pwd.getpwnam(i).pw_uid, grp.getgrnam(i).gr_gid)
        copyFile("/etc/skel/python_games", "/home/" + i + "python_games")
    addPasswordResetToolToAll()
    addScreenshotToolToAll()


def addScreenshotToolToAll():
    downloadFile(REPOSITORY + "/Scripts/pinet-screenshot.sh", "/tmp/pinet-screenshot.sh")
    downloadFile(REPOSITORY + "/images/pinet-screenshot.png", "/tmp/pinet-screenshot.png")
    copyFile("/tmp/pinet-screenshot.png", "/opt/ltsp/armhf/usr/share/pixmaps/pinet-screenshot.png")
    copyFile("/tmp/pinet-screenshot.sh", "/opt/ltsp/armhf/usr/local/bin/pinet-screenshot.sh")
    os.chmod("/opt/ltsp/armhf/usr/local/bin/pinet-screenshot.sh", 0o755)
    for user in getUsers():
        addScreenshotToolSingleUser(user)


def addScreenshotToolSingleUser(user):
    if not os.path.exists("/home/" + user + "/Desktop/pinet-screenshot.desktop"):
        createTextFile("/home/" + user + "/Desktop/pinet-screenshot.desktop", """
        [Desktop Entry]
        Version=1.0
        Name=Take Screenshot
        Comment=Take Screenshot
        Exec=bash pinet-screenshot.sh
        Icon=/usr/share/pixmaps/pinet-screenshot.png
        Terminal=false
        Type=Application
        Categories=Utility;Application;
        """)
        os.chown("/home/" + user + "/Desktop/pinet-screenshot.desktop", pwd.getpwnam(user).pw_uid,
                 grp.getgrnam(user).gr_gid)


def addPasswordResetToolToAll():
    print(REPOSITORY + "/images/pinet-change-password.png")
    downloadFile(REPOSITORY + "/Scripts/changePassword.sh", "/tmp/changePassword.sh")
    downloadFile(REPOSITORY + "/images/pinet-change-password.png", "/tmp/pinet-change-password.png")
    copyFile("/tmp/pinet-change-password.png", "/opt/ltsp/armhf/usr/share/pixmaps/pinet-change-password.png")
    copyFile("/tmp/changePassword.sh", "/opt/ltsp/armhf/usr/local/bin/changePassword.sh")
    os.chmod("/opt/ltsp/armhf/usr/local/bin/changePassword.sh", 0o755)
    for user in getUsers():
        addPasswordResetToolSingleUser(user)


def addPasswordResetToolSingleUser(user):
    if not os.path.exists("/home/" + user + "/Desktop/pinet-password.desktop"):
        createTextFile("/home/" + user + "/Desktop/pinet-password.desktop", """
        [Desktop Entry]
        Version=1.1
        Name=Change Password
        Comment=Change password
        Exec=ltsp-remoteapps bash changePassword.sh
        Icon=/usr/share/pixmaps/pinet-change-password.png
        Terminal=false
        Type=Application
        Categories=Utility;Application;
        """)
        os.chown("/home/" + user + "/Desktop/pinet-password.desktop", pwd.getpwnam(user).pw_uid,
                 grp.getgrnam(user).gr_gid)


def installRaspberryPiUIMods():
    ltspChroot("""apt-get -o Dpkg::Options::="--force-overwrite --force-confnew" install -y raspberrypi-ui-mods """)
    fixUIConfigFile(True, "pcmanfm.conf")
    fixUIConfigFile(True, "desktop-items-0.conf")
    checkRaspberryPiUIModsAllUsers()


def checkRaspberryPiUIModsAllUsers():
    for user in getUsers():
        if not os.path.exists("/home/" + user + "/.config/pcmanfm/LXDE-pi/desktop-items-0.conf"):
            fixUIConfigFile(False, "pcmanfm.conf", user)
            fixUIConfigFile(False, "desktop-items-0.conf", user)


def fixUIConfigFile(system, file, username="a"):
    if system:
        replaceLineOrAdd("/opt/ltsp/armhf/etc/xdg/pcmanfm/LXDE-pi/" + file, "wallpaper_mode=", "wallpaper_mode=stretch")
        replaceLineOrAdd("/opt/ltsp/armhf/etc/xdg/pcmanfm/LXDE-pi/" + file, "wallpaper=",
                         "wallpaper=/etc/alternatives/desktop-background")
        replaceLineOrAdd("/opt/ltsp/armhf/etc/xdg/pcmanfm/LXDE-pi/" + file, "side_pane_mode=", "side_pane_mode=1")
        replaceLineOrAdd("/opt/ltsp/armhf/etc/xdg/pcmanfm/LXDE-pi/" + file, "desktop_shadow=", "desktop_shadow=#000000")
        replaceLineOrAdd("/opt/ltsp/armhf/etc/xdg/pcmanfm/LXDE-pi/" + file, "desktop_fg=", "desktop_fg=#ffffff")
    else:
        makeFolder("/home/" + username + "/.config/pcmanfm/LXDE-pi/")
        replaceLineOrAdd("/home/" + username + "/.config/pcmanfm/LXDE-pi/" + file, "wallpaper_mode=",
                         "wallpaper_mode=stretch")
        replaceLineOrAdd("/home/" + username + "/.config/pcmanfm/LXDE-pi/" + file, "wallpaper=",
                         "wallpaper=/etc/alternatives/desktop-background")
        replaceLineOrAdd("/home/" + username + "/.config/pcmanfm/LXDE-pi/" + file, "side_pane_mode=",
                         "side_pane_mode=1")
        replaceLineOrAdd("/home/" + username + "/.config/pcmanfm/LXDE-pi/" + file, "desktop_shadow=",
                         "desktop_shadow=#000000")
        replaceLineOrAdd("/home/" + username + "/.config/pcmanfm/LXDE-pi/" + file, "desktop_fg=", "desktop_fg=#ffffff")


def enableNBDSwap():
    removeFile("/etc/nbd-server/conf.d/swap.conf")
    createTextFile("/etc/nbd-server/conf.d/swap.conf", """
    [swap]
    exportname = /tmp/nbd-swap/%s
    prerun = nbdswapd %s
    postrun = rm -f %s""")
    runBash("service nbd-server restart")

def DisableI2C_SPI():
    pass

def resetCleanup():
    runBash("service nfs-kernel-server restart")
    runBash("DEBIAN_FRONTEND=noninteractive dpkg-reconfigure nbd-server")
    runBash("service nbd-server restart")


def enableNBD():
    runBash("/usr/sbin/ltsp-update-image --config-nbd /opt/ltsp/armhf")

def fullInstall():
    installLtspPackages()
    buildPiNetClient()
    setupOneOffFixes()
    setupConfigFixes()
    addPackageRepos()
    addSoftware()
    raspiTheme()
    addDesktopIcons()
    installRaspberryPiUIMods()
    enableNBDSwap()
    enableNBD()
    resetCleanup()
    print("Done!")
