# Notes for Claude

Project context, working agreements and where we left off. The README covers what the project is and how to run it.

## Working agreements

- Work in `D:\Distributed-Volume-Coach`. It has its own repo: `origin` is https://github.com/Yogesh-OT/Distributed-Volume-Coach.git, branch `main`.
- **Commit and push to `origin/main` at every important milestone without asking**: a finished feature or phase, or a meaningful fix with tests passing. Don't commit half-done or failing work.
- The architecture page is https://claude.ai/artifact/3NHAmvSAMi8WSr2ww2Hhdb. Update it when the design changes.
- The in-day rules exist twice, in `server/engine/policy.py` and `android/.../engine/InDayPolicy.kt`. Change both, and add a case to `shared/policy_vectors.json`. CI runs those cases against both.
- The user is building this as their first portfolio project. Explain plainly, and say what was and wasn't verified.

## This computer

- **Python 3.14.** The server venv is `server/.venv`; recreate it with `python -m venv .venv` and then `.venv/Scripts/pip install -e ".[dev]"`. `server/.env` sets dev mode and the SQLite `dev.db`.
- **No Android SDK or Gradle here.** The Android app compiles in GitHub Actions, and every push uploads the `dv-coach-debug-apk` artifact.
  - Download artifacts with Git's stored GitHub credential: `git credential fill` gives a Bearer token for the artifact zip API. Never print the token.
- **adb** is at `D:\Android\platform-tools\adb.exe`.
  - In Git Bash, set `MSYS_NO_PATHCONV=1` when passing phone paths like `/sdcard/...`, or they get rewritten to Windows paths.
- **The PC's Wi-Fi is marked Public.** Keep the dev server on `127.0.0.1` and reach it from the phone with `adb reverse tcp:8000 tcp:8000`. The app's server address is then `http://127.0.0.1:8000`.
- Background tasks in this app stop after 2 hours. For longer tests, the user runs uvicorn in their own terminal.

## Test phone

- Xiaomi/Redmi `2406ERN9CI`, Android API 36, adb serial `92ca22e1`.
- **Installing:** `adb install` fails with `INSTALL_FAILED_USER_RESTRICTED`, because Xiaomi's "Install via USB" is off.
  - Instead, `adb push` the APK to `/sdcard/Download/` and the user installs it from File Manager.
  - Each CI build has a new debug signing key. Before installing a newer build, remove the old one with `adb uninstall app.dvcoach`.

## Status (2026-10-02)

- **Pushed:** `7317dbc` (phase 1 MVP) and `89e1ac4` (phone testing: server address setting, APK built in CI).
- **First on-device test went cleanly.** Install, server connection, onboarding, max test, check-in, progress and account deletion all returned 2xx, with no crashes.
- The only check-in that day landed after the default 09:00–19:00 window, so the plan had no sets.
- **Not yet exercised on the phone:** set notifications, in-day logging, sync and the offline fallback plan.

## Next up

1. **Reminder timing.**
   - `setAndAllowWhileIdle` got a 1-hour delivery window on the test phone: `dumpsys alarm` showed `window=+1h` for the check-in reminder. Set prompts can be just as late.
   - Fix: ask for *Alarms & reminders* (`SCHEDULE_EXACT_ALARM`, which the user grants). `USE_EXACT_ALARM` is limited by Play policy to alarm and calendar apps.
   - Use `setExactAndAllowWhileIdle` when `canScheduleExactAlarms()`. Otherwise keep inexact alarms and tell the user prompts may be late.
   - Then update the architecture page.
2. **Debug builds:** default the server address to `http://127.0.0.1:8000` on real devices, and keep `10.0.2.2` only for emulators.
3. **Testing comfort:**
   - Show the training window on the Today screen.
   - Explain "window has ended" plans better.
   - Consider a debug-only "reset today".
4. **Then phase 2:**
   - Weekly progression and 14-day max tests.
   - The Hard-set model with the simulator.
   - Health Connect sleep.
   - Pull-ups.
   - A "Why this plan" screen.
