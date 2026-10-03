# Notes for Claude

Project context, working agreements and where we left off. The README covers what the project is and how to run it.

## Working agreements

- Work in `D:\Distributed-Volume-Coach`. It has its own repo: `origin` is https://github.com/Yogesh-OT/Distributed-Volume-Coach.git, branch `main`.
- **Commit and push to `origin/main` at every important milestone without asking**: a finished feature or phase, or a meaningful fix with tests passing. Don't commit half-done or failing work.
- **Android can't be compiled here.** So push Android changes to a short-lived branch first and let CI compile them. Then fast-forward `main` and delete the branch.
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
  - From commit "Fixed debug key, sync on open" onwards, debug builds use `android/app/debug.keystore`, so new builds install over old ones and keep their data.
  - Builds from before that were signed with CI's random key, so switching needed one uninstall. App data was backed up and restored with `run-as app.dvcoach tar`.
- **Autostart is off by default** on this phone: `appops` shows `MIUIOP(10008): ignore`. While the app is closed, MIUI then won't start it for WorkManager jobs, so a sync waited until the app was opened. Since that commit the app also syncs on every resume. Ask the user to turn Autostart on.
- **Offline sync verified on 2026-10-03.** The 18:37 set was logged from the notification's Done button while the server was down, and uploaded once the app was opened.

## Status (2026-10-02)

- **Pushed:** `7317dbc` (phase 1 MVP) and `89e1ac4` (phone testing: server address setting, APK built in CI).
- **First on-device test went cleanly.** Install, server connection, onboarding, max test, check-in, progress and account deletion all returned 2xx, with no crashes.
- The only check-in that day landed after the default 09:00–19:00 window, so the plan had no sets.
- **Not yet exercised on the phone:** set notifications, in-day logging, sync and the offline fallback plan.

## Session 2 (2026-10-03): built, needs checking on the phone

- **On-time reminders.** The app now asks for `SCHEDULE_EXACT_ALARM` (*Alarms & reminders*).
  - When it's granted, `PromptScheduler` uses `setExactAndAllowWhileIdle`; otherwise inexact alarms.
  - Granting it re-registers alarms. This happens through the permission-changed broadcast, and again when the Today screen comes back into view.
  - Check with `dumpsys alarm`: exact alarms show no `window=`.
- **Server address default.** Debug builds default to `http://127.0.0.1:8000` on real phones and `10.0.2.2` on emulators.
- **The Today screen** shows the training window with a **Change** button, which opens the new *Your day* screen. *Your day* uses `PUT /v1/profile`, and changes apply from the next check-in. The screen also explains "window has ended" plans.
- **Reset today (debug only).** A button on the Progress screen calls `DELETE /v1/dev/days/{day}`, which is mounted only when `DVC_AUTH_MODE=dev`, and clears today's data on the phone too.

## Session 2, second build: UI from the UX research

See `docs/ux-references.md`.

- **The Today hero card** shows one main action: check in, the next set (big rep count, time and "in 25 min") or the day's outcome. It also shows a progress bar and a 7-day week strip (trained / rest day / checked in).
- **The next set's buttons unlock 10 minutes before it's due**, with "Do it now anyway" behind a confirmation.
- **Pain asks how many reps were done**, instead of always logging 0.
- **A "How to do a push-up" sheet** opens from the hero card.
- **A new Settings tab** holds your day, the reminder status for notifications and on-time reminders (plus a Xiaomi Autostart tip), account deletion and test tools. Delete and Reset moved out of Progress.
- **Body form errors name the field**, and values are range-checked on the phone. Server validation errors are prefixed with the field name too.
- **The server reason now says "1 set"**, not "1 sets".

## Session 2, third build: streak and push-up levels (approved by the user)

- **Levels** live in `engine/levels.py`, with a Kotlin mirror in `engine/Levels.kt`: wall, incline, knee, full, decline.
  - The max test records its level. Plans carry the level, and reminders say "9 knee push-ups".
  - The 14-day spacing applies per level, so switching level is allowed any time.
  - Suggestions: up at 20+ reps, down below 5.
  - Database changes: Alembic `0002` and Room version 2 (`MIGRATION_1_2`) add `level`.
- **Streak** lives in `engine/streak.py` and is served by `GET /v1/streak` and inside `/v1/progress`.
  - A day counts when it had a set done, a mobility plan or a pain stop.
  - One rest pass per ISO week covers the first miss, keeping the streak without adding to it.
  - Today counts only once it's on plan.
- **Declined for now:** the 14-day block map and rep counting with the phone's sensor.

## Next up

1. **Phone checks.**
   - Verified on 2026-10-03: exact reminders (the 17:29 set fired at 17:29:09), in-app logging, Pain ending the day, and reset today.
   - Still to check: the notification buttons (Done / Hard / Snooze), offline logging and later sync, and the offline fallback plan.
2. **Streak and levels on the phone.** Verified on 2026-10-04: v5 installed over the existing app (fixed key), Room migration 1 → 2 ran on real data (`user_version` 2, plans and logs kept), and the app fetched the streak. Still to check by hand: the level picker, the streak line text and the guide's levels section.
3. **Then phase 2:**
   - Weekly progression and 14-day max tests.
   - The Hard-set model with the simulator.
   - Health Connect sleep.
   - Pull-ups.
   - A "Why this plan" screen.
