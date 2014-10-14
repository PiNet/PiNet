#!/bin/sh

version=1

EmptyError(){
zenity --error \
--text="Password fields can't be blank!"
exit

}

bob=$(zenity --forms --title="Change Password" \
        --text="Enter your current and new password" \
        --separator="€%%" \
        --add-password="Current Password" \
        --add-password="New Password" \
        --add-password="Repeat New Password" )
case $? in
    0)
oldpassword=""
newpassword1=""
newpassword2=""
oldpassword=$(echo "$bob" | awk -F'€%%' '{print $1}')
newpassword1=$(echo "$bob" | awk -F'€%%' '{print $2}')
newpassword2=$(echo "$bob" | awk -F'€%%' '{print $3}')

if [ "$oldpassword" = "" ]; then
        EmptyError
fi

if [ "$newpassword1" = "" ]; then
        EmptyError
fi

if [ "$newpassword2" = "" ]; then
        EmptyError
fi

if [ "$newpassword1" = "$newpassword2" ]; then
        echo -e "$newpassword1\n$newpassword1" | passwd $SUDO_USER
        clear
        zenity --info \
--text="Password change complete."

else
zenity --error \
--text="Inputted passwords don't match.
No change was made."
exit
fi

;;
    1)
        echo "No change made"
        ;;
    -1)
        echo "An unexpected error has occurred."
        ;;
esac