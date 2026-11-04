#!/bin/sh
#
# BASH Script start.bash starts the touchscreen user interface on booth
# This script assumes that you've configured a crontab job that calls it:
#
#    $ crontab -e  #Then enter the following text:
## Did not work ==>    @reboot sleep 90; sh /home/debian/pratyush-controller/start.sh > /home/debian/pratyush-controller/gui-boot.log 2 > &1
#    worked:  @reboot sleep 90; sh /home/debian/pratyush-controller/start.sh
#
#
# To disable its execution,
#    $ crontab -e  #Then enter the following text:
#    #reboot sleep 90; sh /home/debian/pratyush-pratyush-controller/start.sh > /home/debian/pratyush-controller/gui-boot.log 2 > &1 ]
#
# Can check on what happened via:
#     $ grep CRON /var/log/syslog
#
# Can get crontab editing in vim via:
#   export VISUAL=vim
#
# Programmer:  Bruce McKee, Pratyush Sudhakar
#
# Revision History: August 13, 2024 - Modifications of existing file
#
# Reference: https://unix.stackexchange.com/questions/374000/crontab-with-sudo-not-working-on-debian-beaglebone-black
#            https://www.digikey.com/en/maker/projects/9c40ef28d1144b318e5cc38be203e20bf
#
#===========================================================================================
# Have to set PATH explictly, else you will only get PATH=/user/bin:/bin







#============================OLD CONTROLLER=====================================================

# PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/debian/pratyush-controller

# echo "Setting up GPIO for the relays"

# # Function to create GPIO directory and set it up
# setup_gpio() {
#     local gpio_num=$1
#     local pin_num=$2
#     local gpio_dir="/sys/class/gpio/gpio$gpio_num"

#     if [ ! -d "$gpio_dir" ]; then
#         echo "Creating directory for GPIO $gpio_num"
#         echo $gpio_num > /sys/class/gpio/export
#         sleep 1  # Give the system a moment to create the directory
#     fi

#     if [ -d "$gpio_dir" ]; then
#         echo "Setting up GPIO $gpio_num"
#         echo out > "$gpio_dir/direction"
#         echo 0 > "$gpio_dir/value"
#     else
#         echo "Failed to create directory for GPIO $gpio_num"
#     fi
# }

# # Setup GPIO 115 (nozzle 1 solenoid)
# setup_gpio 115 27

# # Setup GPIO 20 (nozzle 2 solenoid)
# setup_gpio 20 41

# # Setup GPIO 7 (nozzle 3 solenoid)
# setup_gpio 7 42

# # Setup GPIO 111 (vessel heater relay)
# setup_gpio 111 29

# # Setup GPIO 3 (vessel heater relay)
# setup_gpio 3 21

# # Set up the touch screen
# pkill pcmanfm-qt  # desktop handling should be gone now
# pkill lxqt-panel  # voila - no panel anymore
# cd /home/debian/pratyush-controller
# export DISPLAY=:0.0; python2 main.py

#!/bin/bash

# Manual-only launcher for historical controller.
# NOT configured for autostart.

# WARNING: main.py still controls old heaters, pressure and sensors;
# do not run with connected equipment until those routines
# are reviewed/disabled.

#===========================================================================================

set -e

cd "$(dirname "$0")"

for n in 51 117 60; do

    if [ ! -d "/sys/class/gpio/gpio$n" ]; then
        echo "$n" > /sys/class/gpio/export
    fi

    for i in $(seq 1 25); do
        [ -w "/sys/class/gpio/gpio$n/direction" ] && break
        sleep 0.2
    done

    if [ ! -w "/sys/class/gpio/gpio$n/direction" ]; then
        echo "GPIO $n not writable" >&2
        exit 1
    fi

done

export DISPLAY="${DISPLAY:-:0.0}"

exec /usr/bin/python2 main.py
