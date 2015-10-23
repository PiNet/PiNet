PiNet Scripts
=========================

Any additional scripts used by PiNet are stored here   
   
### Bootmenu (no longer supported)  
Bootmenu is the bootup menu for PiNet that allows you to switch from using LTSP to booting off the local SD card.   
It is contained inside the initrd in /scripts/bootmenu   
It only displays the menu if Raspbian is present, it checks this by checking if there is a kernel.img file on the boot partition.   
If there is a local Raspbian install, it inserts a copy of itself to run on boot so you can easily switch back later.   

### ChangePassword.sh
ChangePassword.sh is the password changing utility for the students. It is simply a Zenity based GUI.
There is also a desktop shortcut embedded in the main pinet script which is added when this is installed.

### KernelCheckUpdate.sh
A script added in as a startup script on the Raspbian chroot. It checks the boot files on the SD card are up to date vs the copy the server is storing in /opt/ltsp/armhf/bootfiles.

### Pinet-functions-python.py
The second section of the main pinet script. It contains hundreds of lines of supporting functions for PiNet to use written in Python. Slowly more and more of PiNet is getting moved over into this script and away from Bash.   

### Pinet-screenshot.sh
A simple script for taking screenshots using Raspi2png. Is based off the simple Zenity library.   
