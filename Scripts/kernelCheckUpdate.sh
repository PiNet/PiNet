#! /bin/sh
# Part of PiNet https://github.com/PiNet/PiNet
#
# See LICENSE file for copyright and license details
#
# Automatic SD card files updater. Checks if version.txt file matches the version.txt file in /bootfiles/ inside Raspbian chroot
# If they don't match, then it copies in new files from the /bootfiles folder of the Raspbian chroot.
# Note - The entire boot folder is deleted (bar any smaller files under 100kb that aren't already overwritten). This means any custom configuration is lost each update.

version=002

### BEGIN INIT INFO
# Provides:             None
# Required-Start:       $remote_fs $syslog
# Required-Stop:        $remote_fs $syslog
# Default-Start:        2
# Default-Stop:         0 1 6
# Short-Description:    Checks for SD card updates
### END INIT INFO

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
        cp "$fpath/cmdline.txt" "$fpath/cmdlineBackup.txt"  #Backup the cmdline.txt file, which contains the IP address
        if [ -e "$fpath/bootcode.bin" ]; then
            find "$fpath/." -size +100k -delete
        fi
        cp -rf "/bootfiles/." "$fpath/" #Copy new boot files over
        cp "$fpath/cmdlineNBD.txt" "$fpath/cmdline.txt" #Copy in the new cmdline.txt file
        ip=$(grep -E -o "(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)" "$fpath/cmdlineBackup.txt") #Get the IP address from old cmdline.txt file.
        sed -i "s/1.1.1.1/$ip/g" "$fpath/cmdline.txt" #Replace the 1.1.1.1 dummy address inside new cmdline.txt file with the old IP address of the PiNet server
        rm -rf "$fpath/cmdlineBackup.txt" >> /dev/null #Delete the backup cmdline.txt file
        echo "-------------------------------------------------------"
        echo "Update complete, will now reboot to apply it"
        echo "-------------------------------------------------------"
        timerCountDown "till reboot."
        reboot #Reboot Raspberry Pi
}

timerCountDown(){
for i in {5..1};do echo "$i seconds $1" && sleep 1; done #Simple 5 second countdown
echo " "
}

checkUpdate(){

echo "Checking for SD card kernel updates"

if [ -e "/dev/mmcblk0p1" ] || [ -e "/dev/mmcblk0" ]; then #Verify a card is in the SD card slot
    if [ -e "/dev/mmcblk0p1" ]; then #If card has more than 1 slot, first partition is suffixed with "p1"
        fpath=$(df -P /dev/mmcblk0p1 | awk '{print $6}' | sed -n 2p) #Get current mounted path. If not mounted, returns "/dev"
        partition="mmcblk0p1"
    else
        if [ -e "/dev/mmcblk0" ]; then #If the card only has a single partition, it does not include "p1"
            fpath=$(df -P /dev/mmcblk0 | awk '{print $6}' | sed -n 2p) #Get current mounted path. If not mounted, returns "/dev"
            partition="mmcblk0"
        else
            echo "Partition error!" #This should never be possible to hit...
            exit 1 #But if we do, quit the script as something bad has happened
        fi
    fi
    if [ ! "$fpath" = "" ]; then
        	if [ "$fpath" = "/dev" ]; then #If the SD card boot partition isn't mounted currently
        		mkdir /media/sdcard
        		mount /dev/$partition /media/sdcard
        		fpath="/media/sdcard"
        	fi
    fi

    if [ -f "$fpath/bootcode.bin" ]; then #Check that it is an actual Raspberry Pi boot partition by verifying if bootcode.bin exists
        if [ -f "/bootfiles/bootcode.bin" ]; then #Check the update from boot partition by verifying if bootcode.bin exists
            if [ -f "$fpath/version.txt" ]; then #Check if a version.txt file exists. If not just flash the card anyway
                current=$(head -n 1 "$fpath/version.txt") #Current version number
                new=$(head -n 1 "/bootfiles/version.txt") #Possible new version number
                if [ ! "$current" = "$new" ]; then #Check if both versions match. If newer or older on server, will still reflash
                    runUpdate #Reflash card
                else
                    echo "No new updates found"
                    if [ "$fpath$" = "/media/sdcard" ]; then
                        umount "/media/sdcard" #Unmount the card to clean up after ourselves
                    fi
                fi
            else
                runUpdate #Reflash card
            fi
        fi
    fi



else
    echo "No SD card filesystem mounted"
fi


}

case "$1" in
  start)
    checkUpdate
    ;;
  stop)
    echo "Nothing to start"
    ;;
  *)
    echo "Usage: sudo /etc/init.d/kernelCheckUpdate.sh {start|stop}"
    exit 1
    ;;
esac

exit 0