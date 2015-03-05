#!/bin/sh

version=1

result=$(zenity --forms --title="Screenshot" \
--text="A screenshot will be taken and stored in your home folder." \
--add-entry="Delay before screenshot taken in seconds")

if [ ! -n "$result" ]; then
  exit
fi


if ! expr "$result" : '-\?[0-9]\+$' >/dev/null
  then
  zenity --error \
  --text="Time entry was not valid."
  exit
  
fi

if [ $result -ge 60 ]; then
  zenity --error \
  --text="Time entry of $result seconds was too large."
  exit
fi
raspi2png --delay $result
zenity --info \
--text="Screenshot complete.
You can find it in /home/$USER/screenshot.png"
