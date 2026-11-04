# 6. Solenoid pulse control

## Per-solenoid duration settings

`IceCreamGUI.__init__()` initializes:

```python
self.pulse_durations = {
    1: 1,
    2: 1,
    3: 1
}
```

Each value is in seconds. The current UI provides a separate TIME button next to each GO button. `edit_nozzle_duration(nozzle_number)` opens a 1–5 second selector and updates only the selected dictionary entry and button label.

The values are held in application memory. They are not persisted to a file or across a reboot. A fresh process starts with 1 second for each solenoid.

## Pulse sequence

1. Operator presses GO for nozzle `n`.
2. `w9_fire_nozzle_button_callback(n)` checks `shutdown_latched`. If true, it returns without firing.
3. If not latched, the control screen is hidden and `show_w9a(n)` is called.
4. `show_w9a(n)` reads `pulse_durations[n]` and converts seconds to milliseconds.
5. It configures the progress bar to 0–1000 and configures the animation duration to the selected number of milliseconds.
6. It calls `set_nozzle_solenoid(n, True)` and records the commanded state in `nozzle_solenoid_on[n]`.
7. It starts the single-shot `solenoid_cutoff_timer` for the selected duration and starts the visual animation.
8. When the cutoff timer expires, `hide_w9a()` runs. The animation's finished signal is also connected to `hide_w9a()`.
9. `hide_w9a()` stops the timer and animation, sends OFF commands to all three solenoids, hides the dispensing widgets, and returns to W9 only if shutdown is not latched.

## Why the progress bar uses 0–1000

The progress bar uses an integer range of 0 to 1000. This gives the visual animation many intermediate integer values even for a 1-second pulse. The actual pulse time is controlled by `solenoid_cutoff_timer`, not by the visual scale.

## Shutdown latch

`shutdown_latched` is set true when the operator starts shutdown and remains true through the shutdown instructions, standby, and wake-to-Welcome transition. It is cleared only by the final startup Continue action, after `all_solenoids_off()` succeeds. This prevents a tap on the standby screen or a return to Welcome from immediately re-enabling the GO buttons.

## Extending the controller with another solenoid

Adding a fourth output is not just adding a button. A maintainer must review and update, at minimum:

1. Approved electrical schematic, relay channel, valve wiring, protection, and connector documentation.
2. `SOLENOID_NUMBER_PIN` in `constants.py` and the corresponding Linux GPIO export in `start.sh`.
3. `setup_gpio()` and any state dictionaries / OFF loops that currently explicitly iterate over 1, 2, and 3.
4. `pulse_durations` initialization and the duration editor's range of supported nozzle IDs.
5. The GUI widget construction, signal wiring, show/hide behavior, and scaling layout.
6. `all_solenoids_off()` and all other safety-related OFF paths.
7. Operator procedures, troubleshooting, test checklist, and hardware verification record.
8. Bench testing with loads isolated before any system-level test.

Do not make a partial software-only change: an omitted OFF path can leave a new output uncontrolled by shutdown.

## Timing limitations

Qt timers depend on the Python process and event loop. They are not guaranteed hardware timing under process crash, OS hang, CPU starvation, or loss of power. Use an independently engineered hardware cutoff / fail-safe where required by the system risk assessment. Confirm OFF at the relay and valve using appropriate instrumentation; the UI state variable is not physical feedback.
