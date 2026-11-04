# 8. Autostart and startup

## Current deployment mechanism

The deployment discussed for this controller uses the LXQt desktop autostart mechanism. The autostart file is created on the BeagleBone under the `debian` user's home directory; it is not part of the Git repository.

Expected file:

```text
/home/debian/.config/autostart/pratyush-controller.desktop
```

Expected contents for the current working directory:

```ini
[Desktop Entry]
Type=Application
Name=RIZVILAB Solenoid Controller
Comment=Launch solenoid controller at desktop startup
Exec=/bin/bash /home/debian/pratyush-controller-working/start.sh
Path=/home/debian/pratyush-controller-working
Terminal=false
```

This entry launches `start.sh` after the graphical desktop session starts. It does not launch the GUI before login. If the BeagleBone stops at a login screen, desktop autostart will not run until the user logs in unless automatic login is separately configured.

## Verify autostart on the BeagleBone

```bash
cat ~/.config/autostart/pratyush-controller.desktop
ls -la ~/.config/autostart/
```

Confirm that:

- The file exists for the intended desktop user (`debian`).
- `Exec` points to the actual deployed `start.sh`.
- The old controller's autostart entry is disabled or removed.
- There is only one controller instance.

## Check for a running process

```bash
pgrep -af 'python2.*main.py'
```

If more than one matching application is running, do not blindly kill every Python process. Identify the process IDs and the exact command first. Before terminating a controller process, isolate hardware and use the approved OFF procedure; killing Python does not itself guarantee relay outputs go LOW.

## Reboot test

With solenoid loads disconnected and pneumatic supplies isolated for the initial deployment test:

```bash
sudo reboot
```

After reboot, verify that the desktop starts and the Welcome screen appears. A fresh Python process starts at Welcome; it does not restore the in-memory standby state or previously selected pulse durations.

## Standby versus power-off

The dark standby screen is a GUI overlay. The BeagleBone, Python process, and supporting electronics remain powered. Tapping the screen returns to Welcome. The shutdown latch remains set until the operator completes the startup illustrations. Unplugging and reconnecting power creates a new process and returns to Welcome.

Standby is not a physical isolation state and is not a substitute for closing valves, isolating pneumatic supplies, or following the approved shutdown procedure.
