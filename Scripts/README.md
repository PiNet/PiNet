PiNet Scripts
=========================

Any additional scripts used by PiNet are stored here   
   
###Bootmenu   
Bootmenu is the bootup menu for PiNet that allows you to switch from using LTSP to booting off the local SD card.   
It is contained inside the initrd in /scripts/bootmenu   
It only displays the menu if Raspbian is present, it checks this by checking if there is a kernel.img file on the boot partition.   
If there is a local Raspbian install, it inserts a copy of itself to run on boot so you can easily switch back later.   

###ChangePassword
ChangePassword.sh is the password changing utility for the students. It is simply a Zenity based GUI.
There is also a desktop shortcut embedded in the main pinet script which is added when this is installed.
