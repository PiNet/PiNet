RaspberryPi-LTSP
================

Linux Termal Server Project is a collection of pieces of software for running fat and thin clients from a linux based server.

This can also be done on the Raspberry Pi. It allows a master pi image to be created which is then booted by each pi. This means no more flashing 100s of sd cards with large raspberry pi OS's, just load the 30mb image produced by the server when it is installed onto all your pis and you are good to go.

The main part of this repository is Pi_ltsp. It is a bash script for installing and managing the built master image.

It is currently pre-alpha quality so I take no responsibility for deleted data or damage caused by it.

Use at your own risk



To use first install Debian wheezy onto your server and download the Pi_ltsp file.
Change to root with the command   su
Now run the script with     sh Pi_ltsp