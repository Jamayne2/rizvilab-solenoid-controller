# 5. GUI and operator workflow

## Screen sequence

```text
Fresh application start
    |
    v
W1 — Welcome
    |
    v
Startup Instructions title
    |  Back returns to Welcome; Continue starts illustrations
    v
W4 — Five startup illustrations
    |  Back/Continue between illustrations
    |  Final Continue: all_solenoids_off(), clear shutdown_latched
    v
W9 — Solenoid Controls
    |  GO N -> W9a dispensing
    |  TIME N -> edit duration for N only
    |  SHUTDOWN -> latch + all outputs OFF
    v
Shutdown Instructions title
    |  No Back button on title page
    |  Continue starts illustrations
    v
W13 — Five shutdown illustrations
    |  Back/Continue between illustrations
    |  First Back returns to shutdown title, not W9
    |  Final Continue enters standby
    v
Dark standby overlay
    |  Tap anywhere
    v
W1 — Welcome (shutdown latch remains set)
    |  Complete startup sequence to unlock controls
    v
W9 — Solenoid Controls
```

## Startup illustrations

The current `startup_images` list in `show_w4()` contains:

1. `open-co2-tank-valve-all-the-way.png`
2. `turn-on-recirculating-water-bath.png`
3. `open-air-pressure-valve-all-the-way.png`
4. `air-regulator-startup-turn-knob.png`
5. `air-regulator-startup-set-regulator-to-85psi.png`

These filenames and their displayed sequence are what the code currently uses. The regulator value and physical steps must be checked against the approved, current test-stand procedure before use.

## Shutdown illustrations

The current `shutdown_images` list in `show_w13()` contains:

1. `turn-off-batch.png`
2. `close-air-pressure-valve-all-the-way.png`
3. `air-regulator-shutdown-turn-knob.png`
4. `air-regulator-shutdown-set-regulator-0psi.png`
5. `close-co2-tank-valve-all-the-way.png`

Verify the wording, equipment names, and sequence against the approved shutdown SOP. Do not treat images alone as a validated safety procedure.

## Navigation behavior

- Startup title: Back and Continue.
- Startup images: Back and Continue.
- Shutdown title: Continue only; no Back to controls.
- Shutdown images: Back and Continue. The first image's Back returns to the shutdown title.
- Final shutdown image: button label changes to FINISH; completing it enters standby.
- Standby: full-screen dark button; tap returns to Welcome.

## Fullscreen scaling

The UI uses a 480 × 272 reference layout. `initUI()` calls `showFullScreen()` and then `scale_ui_to_screen()`, which scales direct child widget geometry and font sizes to the detected desktop resolution. Background labels are set to scaled contents.

For position/size edits in the original coordinate system:

- `setGeometry(x, y, width, height)` sets position and size.
- `move(x, y)` sets position.
- `resize(width, height)` sets size.

Widget geometry is generally constructed in `IceCreamGUI.__init__()`. Do not add another scaling pass or move widgets after the existing scaling pass without testing all screens.

## Images and path handling

Startup and shutdown illustration lists are built relative to the directory containing `main.py` (`window-background-images/`). Several title/background screens use `IMAGES_FOLDER` from `constants.py`, which is an absolute path in the current snapshot. The constructor also contains an initial hard-coded splash-image path from an earlier deployment. Verify all these paths on a new BeagleBone; see [Installation](07-installation-and-deployment.md).
