# 9. Troubleshooting

Use the symptom table to identify the likely software area. Always isolate actuators and pneumatic supplies before debugging relay behavior.

| Symptom | Checks | Likely area |
|---|---|---|
| `python2: can't open file 'main.py'` | Run `cd /home/debian/pratyush-controller-working`; confirm `ls main.py`; use `bash start.sh` | Wrong working directory / launcher path |
| GUI does not appear at boot | Check `~/.config/autostart/pratyush-controller.desktop`, LXQt login state, `Exec` path, and `start.sh` output | Desktop autostart / display session |
| Two GUIs appear | Run `pgrep -af 'python2.*main.py'`; inspect all autostart entries and manual launches | Duplicate process / duplicate autostart |
| `GPIO channel has not been setup() as an OUTPUT` | Confirm `main()` calls `initialize_system()` before GUI construction; confirm `setup_gpio()` sets up the mapped pins | GPIO initialization not run or mapping mismatch |
| GPIO export reports an error | Check whether the GPIO is already exported, whether the sysfs node exists, and permissions; do not change GPIO numbers without verifying pin mapping | `start.sh` / kernel GPIO state |
| Relay does not activate after shutdown and wake | Confirm startup sequence reaches its final image; `w4_continue_button_callback()` must successfully call `all_solenoids_off()` before clearing `shutdown_latched` | Shutdown latch intentionally still set |
| Relay does not turn off at selected time | Check `solenoid_cutoff_timer` initialization, `setSingleShot(True)`, timeout connection to `hide_w9a()`, and Qt event loop | Timer wiring / blocked event loop |
| Progress bar looks empty for 1-second pulse | Confirm range and animation values are 0–1000 while duration is 1000 ms | Progress animation configuration |
| One TIME button changes another nozzle | Check lambda capture uses `n=number`; verify `pulse_durations[nozzle_number]` and button dictionary keys | Per-nozzle callback binding |
| Blank/missing background | Check exact filename/case, `window-background-images/`, `IMAGES_FOLDER`, and absolute paths listed in Installation | Asset path / missing file |
| GUI fills window but widgets remain small | Confirm `showFullScreen()` and `scale_ui_to_screen()` are called in `initUI()` after widgets are created | Fullscreen scaling call/order |
| `AttributeError` for `solenoid_cutoff_timer` | Confirm it is created in `IceCreamGUI.__init__()` before UI callbacks can run | Timer initialization missing |
| Popup does not save selected duration | Confirm a button is checked and `button_group.checkedId()` is in 1–5; check `dialog.exec_()` result | Duration dialog |

## Safe diagnostic commands

```bash
# On the BeagleBone: identify the current user and directory
whoami
pwd
ls -la

# Check process list
pgrep -af 'python2.*main.py'

# Check Python syntax (does not touch the hardware)
cd /home/debian/pratyush-controller-working
/usr/bin/python2 -m py_compile main.py

# Inspect startup script and desktop autostart
cat start.sh
cat ~/.config/autostart/pratyush-controller.desktop
```

## If the application crashes during a pulse

Do not assume the output turned OFF. Isolate the pneumatic and electrical actuator supplies using the approved physical procedure, verify relay state independently, and inspect the GPIO/relay hardware. The application timer cannot run after the Python process has crashed.

## Capture useful information for a bug report

Record:

- Exact error and full traceback.
- Current Git commit (`git rev-parse HEAD`).
- BeagleBone OS and Python versions.
- Screen/state at time of failure.
- Which solenoid and selected duration were involved.
- Whether the relay input and relay contact changed state.
- Whether actuator loads were connected.
- Recent code or wiring changes.
