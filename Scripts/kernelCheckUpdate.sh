#! /bin/sh
# Part of PiNet https://github.com/PiNet/PiNet
#
# See LICENSE file for copyright and license details

version=003

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

# Verify that there is an SD card connected. If has multiple partitions, will be /dev/mmcblk0p1, otherwise /dev/mmcblk0.
if [ -e "/dev/mmcblk0p1" ] || [ -e "/dev/mmcblk0" ]; then
    if [ -e "/dev/mmcblk0p1" ]; then
        fpath=$(df -P /dev/mmcblk0p1 | awk '{print $6}' | sed -n 2p)
        sdpath="/dev/mmcblk0p1"
    elif [ -e "/dev/mmcblk0" ]; then
        fpath=$(df -P /dev/mmcblk0 | awk '{print $6}' | sed -n 2p)
        sdpath="/dev/mmcblk0"
    fi
    if [ ! "$fpath" = "" ]; then
        # If the SD card isn't mounted, mount it to /media/sdcard.
        if [ "$fpath" = "/dev" ]; then
            mkdir /media/sdcard
            mount "$sdpath" "/media/sdcard"
            fpath="/media/sdcard"
        fi

        # Verify there is actual boot files on the SD card.
        if [ -f "$fpath/bootcode.bin" ] && [ -f "/bootfiles/bootcode.bin" ]; then
            # Compare versions of version.txt
            if [ -f "$fpath/version.txt" ]; then
                current=$(head -n 1 "$fpath/version.txt")
                new=$(head -n 1 "/bootfiles/version.txt")
                if [ -f "$fpath/config.txt" ]; then
                    currentConfig=`md5sum "$fpath/config.txt" | awk '{ print $1 }'`
                    newConfig=`md5sum "/bootfiles/config.txt" | awk '{ print $1 }'`
                fi

                if [ ! "$current" = "$new" ] || [ ! "$currentConfig" = "$newConfig" ]; then
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