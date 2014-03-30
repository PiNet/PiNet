RaspberryPi-LTSP
================

Linux Termal Server Project is a collection of pieces of software for running fat and thin clients from a linux based server.

This can also be done on the Raspberry Pi. It allows a master pi image to be created which is then booted by each pi. This means no more flashing 100s of sd cards with large raspberry pi OS's, just load the 30mb image produced by the server when it is installed onto all your pis and you are good to go.
It brings 3 main advantages to schools.

1. Pis boot off the network, only using SD card for kernel. (20mb) - The OS for them is stored on a central Linux server. Means if you want to add a new package to all the pis, you install it on the server in the pi chroot and reboot pis, poof, all of them have it installed!

2. Network user accounts - A pupil can sit down at any Raspberry Pi in the classroom and log in. Their files are stored on the central server so they have access to them at any pi. This includes a nice graphical login screen. 

3. Central user file storage - Because the files are stored centrally on the server, if a pi somehow goes up in flames (or the sd card just gets corrupt?) then the user has lost nothing as his/her files are on the server. Means 1 place to back up. Importantly for controlled assessments, means students canâ€™t just take the SD card home as there is no OS on it :)
We are working though on having a local OS, so that you swap 2 config files on the boot partition and it switches, or even better, hold down a key on boot.


The main part of this repository is Pi_ltsp. It is a bash script for installing and managing the built master image.

It is currently pre-alpha quality so I take no responsibility for deleted data or damage caused by it.

Use at your own risk




###How to install



To use, first install Debian wheezy onto your server and download the Pi_ltsp file.

Change to root with the command   su   (or run a root terminal)

Now run the script with     sh Pi_ltsp

The script will launch and you will be presented with a few options. 

Select full install to set everything up. This can take anywhere form 30 mins to 3 hours 

Next create your users with Manage-users

Finally run Graphics-fix in user-groups to fix all newly added user accounts




###Menu options


**Full** - Full installs a full version of the system. It should be only run once! Ever! It is the first command you run as most others won't work without it!  
**Change-IP** - Run this if your servers IP address changes or if you want to grab the most recent SD card image from the repository  
**Install-Program** - Use this to install any additional packages you want on your Raspberry Pis. The full package name is required! Just like if being done with apt-get install.  
**Update-All** - Updates all packages on the server and on the Raspberry Pi. Basically apt-get update && apt-get upgrade for server and Raspberry Pis.  
**Manage-Users** - Launches the graphical user management system to add users, remove users and reset passwords.  
**Epoptes-Menu** - Use for install epoptes classroom management software, for adding a new "teacher" account.  
**User-groups** - Functions for fixing users permissions.   
---**Add-teacher** - Used to add a teacher to the teacher group, a group able to access file uploads.  
---**Graphics-fix** - Fixes all the graphically accelerated applications for all users, e.g. MCPI.  
**Pi-control-menu** - Not implemented.  
**Update-Pi-LTSP** - Fetches the most recent version of the control script from github.  




###WARNING


This is a not a project yet for someone new to Linux. Although it should work, there is a number of places the system could fall over on. It is recommended, if you are interested in bringing this into your school, to drop a tweet to @gbaman1 (twitter).
