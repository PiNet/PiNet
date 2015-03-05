#!/bin/bash
# Part of Raspi-LTSP https://github.com/gbaman/RaspberryPi-LTSP
#
# See LICENSE file for copyright and license details

version=001


runUpdate(){
		echo " "
		echo "-------------------------------------------------------"
		echo "Important SD card kernel file updates found!"
		echo "An automatic update will now be performed!"
		echo "Once the update finishes, the Raspberry Pi will reboot"
		echo ""
		echo "Do not disconnect the power or SD card till complete!"
		echo " "
		echo "-------------------------------------------------------"
		echo " "
		timerCountDown "till update start."
        cp "$fpath/cmdline.txt" "$fpath/cmdlineBackup.txt" 
        cp -rf "/bootfiles/." "$fpath/" 
        rm -rf "$fpath/cmdline.txt" >> /dev/null
        cp  "$fpath/cmdlineBackup.txt" "$fpath/cmdline.txt"
        rm -rf "$fpath/cmdlineBackup.txt" >> /dev/null
        echo "-------------------------------------------------------"
        echo "Update complete, will now reboot to apply it"
        echo "-------------------------------------------------------"
        timerCountDown "till reboot."
        reboot
}

timerCountDown(){
for i in {5..1};do echo "$i seconds $1" && sleep 1; done
echo " "
}

checkUpdate(){

echo "Checking for SD card kernel updates"

if [ -e "/dev/mmcblk0p1" ]; then
        fpath=$(df -P /dev/mmcblk0p1 | awk '{print $6}' | sed -n 2p)
        if [ ! "$fpath" = "" ]; then
        	if [ "$fpath" = "/dev" ]; then
        		mkdir /media/sdcard
        		mount /dev/mmcblk0p1 /media/sdcard
        		fpath="/media/sdcard"
        	fi
                if [ -e "/dev/mmcblk0p1" ]; then
                        if [ -f "$fpath/bootcode.bin" ]; then
                                if [ -f "/bootfiles/bootcode.bin" ]; then
                                        if [ -f "$fpath/version.txt" ]; then
                                                current=$(head -n 1 "$fpath/version.txt")
                                                new=$(head -n 1 "/bootfiles/version.txt")
                                                if [ ! "$current" = "$new" ]; then
                                                        runUpdate
                                                else
                                                        echo "No new updates found"
                                                        if [ "$fpath$" = "/media/sdcard" ]; then
                                                        	umount "/media/sdcard"
                                                        fi
                                                fi
                                        else
                                                runUpdate
                                
                                        fi
                                fi      
                        fi
                fi
        fi
else
        echo "No SD card filesystem mounted"
fi

}



checkUpdate