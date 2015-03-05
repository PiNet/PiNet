#!/bin/sh

#Constants
#------------------------
ConfigFileLoc=/etc/raspi-ltsp
Timeout=1
PythonFunctions="/usr/local/bin/Pi_ltsp-functions-python.py"
PythonStart="python3"
p="$PythonStart $PythonFunctions"
RepositoryBase="https://github.com/gbaman/"
RepositoryName="RaspberryPi-LTSP"
RawRepositoryBase="https://raw.github.com/gbaman/"
Repository="$RepositoryBase$RepositoryName"
RawRepository="$RawRepositoryBase$RepositoryName"
ReleaseBranch="master"
ltspBase="/opt/ltsp/"
cpuArch="armhf"


#------------------------


UpdateConfig(){
	local configName=$1
	local configValue=$2
	egrep -i "^$configName" $ConfigFileLoc >> /dev/null
	if [ $? = 0 ]; then
		sed -i "s/$configName.*/$configName=$configValue/g" $ConfigFileLoc
	else
		echo "$configName=$configValue" >> $ConfigFileLoc
	fi	
}

UpdateConfig NBD false


cp /usr/local/bin/Pi_ltsp /tmp/back1
cp /usr/local/bin/Pi_ltsp-functions-python.py /tmp/back2
echo "Checking auto updater"
sed -i '6s/.*/ version=0.10.1/' /usr/local/bin/Pi_ltsp
read
cp /tmp/back1 /usr/local/bin/Pi_ltsp 
cp /tmp/back2 /usr/local/bin/Pi_ltsp-functions-python.py 
echo "Checking kernel update detector"
sed -i '1s/.*/ 001/' /home/andrew/piBoot/version.txt
read
echo "Checking kernel updater non existing"
rm -rf /opt/ltsp/armhf/etc/init.d/kernelCheckUpdate.sh
read
echo "Checking kernel updater out of date"
sed -i '6s/.*/ 000/' /opt/ltsp/armhf/etc/init.d/kernelCheckUpdate.sh
echo "Checking UI mods install correctly"
ltsp-chroot --arch armhf apt-get -y purge raspberrypi-ui-mods
read
echo "Removing Tree"
ltsp-chroot --arch armhf apt-get purge -y tree
echo "Checking Tree - Please install"
read
ltsp-chroot --arch armhf dpkg-query -s tree > /dev/null 2>&1
if [ $? -eq 0 ]; then
	echo "Tree installed"
else
	echo "Tree not installed"
	exit
fi
userdel -rf test
echo "Add student test"
read
if id -u test >/dev/null 2>&1; then
        echo "test added"
        if groups "test" | grep -q -E ' pupil(\s|$)'; then
    		echo ""
    		if groups "test" | grep -q -E ' teacher(\s|$)'; then
    			echo "Test in staff! No!"
    			exit
    		else
    			echo "Test not in staff, correct"
    		fi
		else
    		echo "Test not in pupil"
    		exit
		fi
else
        echo "test does not exist"
        exit
fi
userdel -rf test
echo "Add staff test"
read
if id -u test >/dev/null 2>&1; then
        echo "test added"
        if groups "test" | grep -q -E ' pupil(\s|$)'; then
    		echo ""
    		if groups "test" | grep -q -E ' teacher(\s|$)'; then
    			echo "Test in staff! Yes!"
    		else
    			echo "Test not in staff, No!"
    			exit
    		fi
		else
    		echo "Test not in pupil"
    		exit
		fi
else
        echo "test does not exist"
        exit
fi





UpdateConfig NBD true