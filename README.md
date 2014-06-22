RaspberryPi-LTSP
================

![Main Menu](https://raw.githubusercontent.com/gbaman/RaspberryPi-LTSP/master/images/Raspi-LTSP-Menu.png "Raspi-LTSP Main Menu")

Raspi-LTSP is a configuration utility to facilitate using Raspberry Pis in a permanent classroom environment through setup as LTSP fat clients. It is based heavily on the Linux Terminal Server Project (LTSP).   
   
Linux Termal Server Project is a collection of pieces of software for running fat and thin clients from a Linux based server.

This can also be done on the Raspberry Pi. It allows a master pi image to be created which is then booted by each pi. This means no more flashing 100s of sd cards with large Raspberry Pi OS's, just load the 30mb image produced by the server when it is installed onto all your pis and you are good to go.
It brings 3 main advantages to schools.

1. **Pis boot off the network, only using SD card for kernel. (20mb)** - The OS for them is stored on a central Linux server. Means if you want to add a new package to all the pis, you install it on the server in the pi chroot and reboot pis, poof, all of them have it installed!

2. **Network user accounts** - A pupil can sit down at any Raspberry Pi in the classroom and log in. Their files are stored on the central server so they have access to them at any pi. This includes a nice graphical login screen. 

3. **Central user file storage** - Because the files are stored centrally on the server, if a pi somehow goes up in flames (or the sd card just gets corrupt?) then the user has lost nothing as his/her files are on the server. Means 1 place to back up. Importantly for controlled assessments, means students canâ€™t just take the SD card home as there is no OS on it :)
We are working though on having a local OS, so that you swap 2 config files on the boot partition and it switches, or even better, hold down a key on boot.


The main part of this repository is Pi_ltsp. It is a bash script for installing and managing the built master image.
Also included is a custom Raspberry Pi theme and some custom config files for booting the Raspberry Pis   

It is currently pre-alpha quality so I take no responsibility for deleted data or damage caused by it.   

Use at your own risk   
   
__More information can be found on the blog post http://pi.gbaman.info/?p=256__

###Hardware Requirements
+ Old computer with at least 2gb of ram, 30gb of hard drive space and a gigabit ethernet port (10/100/1000mb port)   
+ Network switch or router   
+ Wired (Ethernet) Raspberry Pi   
+ An SD card of at least 32mb

##Installation


###Ubuntu (Recommended)

####For a full draft userguide designed for complete beginners, see here http://bit.ly/1l26rti  
Raspi-LTSP is officially supported and tested on Ubuntu 14.04 LTS (Trusty Tahr). Other versions are very likely to work, but at not supported.

1. Download and install Ubuntu 14.04 on an old computer. This is a great guide to follow http://www.ubuntu.com/download/desktop/install-ubuntu-desktop .
2. Open a terminal and grab Raspi-LTSP with ```wget https://raw.github.com/gbaman/RaspberryPi-LTSP/master/Pi_ltsp```.
3. Run Raspi-LTSP with ```sudo bash Pi_ltsp```.
4. Raspi-LTSP should now ask if you want to run a full install, select yes.
5. Go make a few cups of tea, will take 1-2 hours.
6. Select any additional packages you want for your install from the menu, you can rerun this menu later if you want.
8. Verify your IP address is correct (important for machines with 2 NICs).
9. Decide whether to enable sudo support, if you aren't going to use GPIO no need to enable it, can be changed later.
10. Installation should now be complete on the server!
11. Copy the contents of the piboot folder (found in ```/home/YouUserName/piboot```) to a blank fat32 formatted SD card of at least 32mb.
12. Plug in keyboard, mouse, ethernet and power to your Raspberry Pi with your newly created SD card in it. It should boot up, find your server and present a login screen. If it fails to load, check _Connection timed out errors on boot_ section below.
13. You may wish to add some new users. The user management tools can be found in ```Manage-Users```

###Debian (Guide slightly out of date)

__A full userguide for Debian can be found at http://pi.gbaman.info/wp-content/uploads/2014/05/small_Userguide-pi-ltsp-full-size.pdf__   

To use, first install Debian wheezy onto your server and download the ```Pi_ltsp``` file.

Change to root with the command   ```su```   (or run a root terminal)

Now run the script with     ```bash Pi_ltsp```

The script will launch and you will be presented with a few options. 

Select full install to set everything up. This can take anywhere form 30 mins to 3 hours   

Next create your users with ```Manage-users``` or using ```adduser``` in the commandline   
   
The script will generate an SD card boot folder in /root/piboot. Copy these files onto root of an SD card formated as FAT. Or just drop on top of a Raspbian SD card image boot folder. Put your SD card into your Raspberry Pi, plug in ethernet and other required connectors and power it up, it should connect to the server and boot.   
   
To switch to the Raspberry Pi virtual OS at any time, use ```ltsp-chroot --arch armhf```   
This will change the shell to the Raspberry Pi OS. Make any changes and type ```exit``` to return to normal shell.   
   
If you are using NBD and make a change outside of Pi-LTSP, remember to run ```NBD-recompress``` to recompress the image again or the changes wont push out to the Pis when they boot.   

##Menu options

**Install-Program** - Use to install new packages for your Raspbian image.   
**Manage-Users** - A submenu with tools for adding, removing and changing passwords of users.  
---**Add-user** - Tool for adding new users to Linux.   
---**Remove-user** - Tool for removing users from Linux.   
---**Change-password** - Tool for changing Linux user passwords.   
---**Launch-graphical** - Launches graphical user management panel.   
---**Add-teacher** - Used to add users to the teacher group.   
---**Enable-Sudo** - Enable the use of Sudo for students. Required for GPIO work.   
---**Disable-Sudo** - Disables use of Sudo for students.   
**Update-All** - Runs apt-get upgrade on server and Raspberry Pi OS to update everything.   
**Backup-Menu** - A submenu containing automatic backup setup wizard and options for backups.   
---**Configure-backup** - Launches backup configuration tool to setup backups for students work.   
---**Disable-Backup** - Disables backup. Old backups are not deleted.   
---**Display-Logs** - Displays the log file for the backup system. Should be checked regularly!   
**Collect-work** - Collects work from students ```handin``` folders. See below.   
**Change-IP** - Run this if your servers IP address changes or want to update your SD card image.   
**Rebuild-OS** - Run this to rebuild the Raspberry Pi operating system if something goes wrong.   
**Epoptes-Menu** - Use to manage Epoptes classroom management software.   
---**Install** - Install Epoptes for the server and the Raspberry Pis.   
---**Epoptes-launch** - Launches the Epoptes admin console.   
---**Epoptes-admin** - Allows user to add a new admin account for Epoptes.   
---**Remove-Epoptes** - Removes Epoptes from server and Raspberry Pis.   
**Pi-control-menu** - Use for installing Picontrol classroom management software.   
---**Enable/update-Picontrol** - Installs Picontrol or runs an update on it.  
---**Disable-Picontrol** - Uninstalls Picontrol.   
**Full-Install** - Runs a full install of Raspi-LTSP. Also useful if full reinstall is required.   
**Other** - Submenu for miscellaneous options.   
---**Network-technology** - Allows the user to switch between NBD and NFS network technologies.   
---**NBD-recompress** - Forces a NBD OS recompression.    
---**NBD-compress-disable** - Disables NBD recompressing temporarily without disabling NBD overall.   
---**NBD-compress-enable** - Enables NBD recompressing again after being temporarily disabled.  



##Handin system   
   
A simple handin system is included with Pi_ltsp. Each user account is created with a handin folder in their home folder. E.g. ```/home/andrew/handin```   
It goes through all users (in the ```pupil``` group) and grabs their handin folder. It then copies this to the provided teacher account into a new folder called ```submitted```.   
Each students handin folder is renamed to that students name in the submitted folder.   
   

##Common issues
###Connection timed out errors on boot

This normally occures if the IP address in the cmdline.txt file that the Raspberry Pi uses to connect to the server is wrong. It is automatically set when Raspi-LTSP builds the SD card. To change it, open the cmdline.txt file on the SD card and set ```nbdroot= ``` to the IP address of your server.   
You can find your servers IP address with ```ifconfig```   
Or the easier way ```ifconfig | perl -nle'/dr:(\S+)/ && print $1'```   

Remember to ignore ```127.0.0.1``` as this is the reserved local address.

##New Features   
If you have an idea for a new feature that your school would find useful for this project, please feel free to open an issue at tag it with feature.   
Issues can be found on the right side of the page.   

##Benchmarks
I have ran a few timed tests with Raspi-LTSP.   
The tests use Raspi-LTSP running on Ubuntu 14.04 on a fully gigabit (10/100/1000) ethernet network. They should be similar on a 100mbit network if the server is connected to the main switch via a gigabit port (also known as a stacking port).   
The local SD card image is running a clean Raspbian 2014.01.07 with the test applications installed.   
I am running only 1 Raspberry Pi on the network so loading time between NFS and NBD should be similar.   
For Raspi-LTSP there are 2 modes it can be run in    
**1. NFS mode** - NFS is an older network technology. It is uncompressed and so any change made to the master operating system is live on the clients. It is good for testing and monitoring the exact amount of data needed to be loaded for a test to run. It is not recommended for production use due to it being slower than NBD mode. Do not use for more than 8 Raspberry Pis at one time!   
**2. NBD mode** -  Uses NBD and squashFS compression to compress the operating system beforehand. After every change to the master operating system, the OS must be recompressed, which takes roughly 5-10 minutes. It is recommended for production use. The compression normally involves the amount of data cross the network dropping to roughly 40% of what NFS mode uses making it very useful for slower networks or networks running 8+ Raspberry Pis.   
   
The SD card used in these tests is a class 10 SanDisk Ultra card rated at 30MB/s
###Results
####Boot to login
Test | SD card | NFS | NBD (with compression)
----|----|----|----
Time | 35s* |66s| 63s

####Open Libreoffice Writter
    | SD card | NFS | NBD (with compression)
----|----|----|----
Time | 15s |24s| 20s
Data crossing network | N/A |75mb| 28mb

####Open Chromium web browser
    | SD card | NFS | NBD (with compression)
----|----|----|----
Time | 13s |20s| 12s
Data crossing network | N/A |45mb| 30mb

####Open Scratch
    | SD card | NFS | NBD (with compression)
----|----|----|----
Time | 6s |7s| 6s
Data crossing network | N/A |4.7mb| 3.6mb

####Open Sonic-Pi version 2 RC3
    | SD card | NFS | NBD (with compression)
----|----|----|----
Time | 37s |42s| 36s
Data crossing network | N/A |11.2mb| 11.1mb


*This is with boot to desktop enabled as LTSP loads a graphical login window.   
##WARNING

The software included should work but is not heavily tested with every new code change. Consider it Alpha quality software.   
It is recommended, if you are interested in bringing this into your school, to drop a tweet to @gbaman1 (twitter).   
For details on the licence of this project, see the LICENCE file
