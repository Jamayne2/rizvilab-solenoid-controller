# 10. Maintenance and change control

## Golden rule

Do not modify the live BeagleBone installation directly as the only copy of a change. Work in a local Git clone, review the diff, commit the change, then deploy a known commit to the BeagleBone.

## Recommended workflow

1. Pull the latest `main` branch on the Mac.
2. Create a focused branch for the change.
3. Read the relevant code path and the corresponding documentation.
4. Make one logical change at a time.
5. Run static checks (Python 2 syntax check in the target environment, where available).
6. Review `git diff` and `git status`.
7. Commit with a clear message and push.
8. Back up the deployed file(s) on the BeagleBone.
9. Deploy the exact commit or release.
10. Stop any previous controller process safely.
11. Test with actuator loads disconnected and pneumatic supplies isolated.
12. Complete the approved bench test and record the result before reconnecting hardware.

## Useful Git commands

```bash
git pull --ff-only
git switch -c fix/describe-the-change

git status
git diff
git add <files>
git commit -m "Describe the change"
git push -u origin fix/describe-the-change
```

After review/merge, update the local `main` branch and record the deployed commit hash on the BeagleBone or in the handover log.

## Back up the deployed application

Before replacing files on the BeagleBone:

```bash
cd /home/debian/pratyush-controller-working
cp main.py main.py.backup.$(date +%Y%m%d-%H%M%S)
cp constants.py constants.py.backup.$(date +%Y%m%d-%H%M%S)
cp start.sh start.sh.backup.$(date +%Y%m%d-%H%M%S)
```

Back up the image directory as well if images are being changed.

## Stopping and restarting

Identify the exact process:

```bash
pgrep -af 'python2.*main.py'
```

After the outputs have been physically made safe using the approved procedure, terminate the identified PID:

```bash
kill <PID>
```

Verify the process is gone before starting another instance. Do not use broad `pkill python` commands on a system that may run other Python applications.

Launch manually from the GUI session:

```bash
cd /home/debian/pratyush-controller-working
bash start.sh
```

Killing the process does not guarantee relay outputs are OFF. Confirm the physical state independently.

## Change impact checklist

Before merging any change, ask:

- Does it affect GPIO mapping or pin initialization?
- Does it affect pulse timing or the cutoff timer?
- Does it affect `all_solenoids_off()` or any shutdown path?
- Does it change `shutdown_latched` behavior?
- Does it affect startup/shutdown navigation or standby?
- Does it change widget geometry or fullscreen scaling?
- Does it change image paths or filenames?
- Does it activate a legacy screen, timer, sensor, heater, or pressure routine?
- Does it require a hardware drawing, test procedure, or handover update?

Any change to an output or OFF path requires hardware review and a controlled test plan.

## Release management

Once a known commit has been validated on the actual BeagleBone and the test record is complete, tag it (for example, `v1.0.0`) and write release notes. Do not tag a source-only or syntax-only check as a hardware-validated release.
