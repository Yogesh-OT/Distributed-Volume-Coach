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
- **Windows Smart App Control is On.** It blocks SQLAlchemy's compiled `.pyd` modules ("An Application Control policy has blocked this file"). The venv therefore uses pure-Python SQLAlchemy, reinstalled with `DISABLE_SQLALCHEMY_CEXT=1 .venv/Scripts/python -m pip install --force-reinstall --no-deps --no-binary sqlalchemy sqlalchemy==<version>`. Redo that after any SQLAlchemy upgrade. Don't change the Windows setting. CI on Linux is unaffected.
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

## Session 2 (2026-10-03): on-time reminders and testing comfort

- **On-time reminders.** The app now asks for `SCHEDULE_EXACT_ALARM` (*Alarms & reminders*).
  - When it's granted, `PromptScheduler` uses `setExactAndAllowWhileIdle`; otherwise inexact alarms.
  - Granting it re-registers alarms. This happens through the permission-changed broadcast, and again when the Today screen comes back into view.
  - Check with `dumpsys alarm`: exact alarms show no `window=`.
- **Server address default.** Debug builds default to `http://127.0.0.1:8000` on real phones and `10.0.2.2` on emulators.
- **The Today screen** shows the training window with a **Change** button, which opens the new *Your day* screen. *Your day* uses `PUT /v1/profile`, and changes apply from the next check-in. The screen also explains "window has ended" plans.
- **Reset today (debug only).** A button under *Settings → Test tools* calls `DELETE /v1/dev/days/{day}`, which is mounted only when `DVC_AUTH_MODE=dev`, and clears today's data on the phone too.

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

## Session 3 (2026-10-04): weekly progression

- **Weekly progression** lives in `engine/progression.py` and the `progressions` table (Alembic `0003`).
  - At the first check-in of each week, the server reviews the week before. Pain-stop days are left out of the review.
  - Strong week (≥90% done, ≤10% Hard): +1 set, then +1 rep next time, alternating.
  - Rough week (<70% done or >25% Hard): one step back, reps before sets.
  - Fewer than 3 training days: no change.
  - Limits: sets stay within the prompt limit and window, at most +4 over the base, and reps never pass 60% of the max.
  - A new max test resets the extra reps. The plan's reason ends with "This week: …" when something changed.
  - The architecture page's "≤15% a week" became "one small step a week", because one set of 6 is already 17%.
- **The planner's percentage** is now the real reps ÷ max: 5 of 12 shows 42%, not 45%.
- **The Today screen** shows a "Max test due" card 14 days after the last max test.

## Session 4 (2026-10-04, evening): training research and the session engine

- **The user asked me to research and choose what's best over their opinions.** The evidence (ACSM 2026, Pelland 2026, Robinson 2024, Singer 2024 and others) and the rule taken from each finding are in `docs/training-research.md`. The full design is in `docs/session-mode-and-coach.md`.
- **Decided by research:**
  - 2, 3 or 4 days a week; 20, 30 or 45 minute sessions.
  - Exercises in pairs for different muscles, 60 s rest. Main movements get 3 sets and extras 2.
  - Rep ranges 6–15 (calves and core 8–20), most sets 1–3 reps short of failure, and the last set of each exercise as far as good form allows.
  - Double progression on ladders of levels.
  - About 10 sets per muscle a week to start, with a weekly volume step up to 20.
  - Back work: doorway rows, then table rows with a sturdy-table check. A pull-up bar is the first optional item later.
  - Get fit / lose fat: strength sessions plus low-impact interval circuits.
  - No gender setting, no calorie estimates, no scheduled rest weeks.
- **Built (server engine only, no API or Android yet):**
  - `engine/exercises.py`: 12 ladders (push, pike, row, squat, lunge, hinge, curl, calves, triceps, plank, crunch, side plank), muscle weights (indirect = ½), household needs, circuit moves and levels.
  - `engine/sessions.py`: week plans by goal and days, and session sizing. Pairs get in at minimum sets first, then sets grow, so more volume never drops a muscle. Also readiness trimming and circuits.
  - `engine/session_progression.py`: per-exercise steps after a session, the weekly volume review and circuit levels.
  - `tests/test_sessions.py`: 121 cases. They check every major muscle twice a week and that every session fits its length. The whole suite is 188 passing.
- **The report page** (the user asked for it) is designed in the same doc: week totals, sets per muscle, exercise progress, history, and body trend.

## Product direction (decided by the user on 2026-10-04)

- **The app grows into a coach-led home-workout app**, using Home Workout – No Equipment as the UX reference (`docs/ux-references.md`).
- **Equipment:** bodyweight only for the first version.
- **Goals at launch:** build muscle, and get fit / lose fat.
  - Build muscle needs a **session mode**: sets about 0–3 reps from failure, 60–90 s rest (Singer 2024: rest beyond about 90 s gave no extra benefit), and 10–20 hard sets per muscle per week, with progression.
  - The current spread-out micro-sets (about 40% of max, hours apart) suit strength, skill and habit, not hypertrophy.
- **Spread-out sets stay as a second mode.** It's a differentiator.
- **Coach:** an AI chat coach (Claude via the API) sitting on top of the engine.
  - The engine owns all numbers: sets, reps, rest, volume and progression, all tested.
  - The coach explains plans, answers questions and adapts within the engine's limits via tool calls. It never invents numbers.
  - Load the `claude-api` skill before writing any coach code.

## Where we left off (2026-10-04, about 21:45)

- **The phone runs v6** (`398bc21`, weekly progression). It installed over v5 and kept its data. Permissions are granted, Battery saver is set to No restrictions, and the user says Autostart is on (`appops` still reads `ignore`).
- **Test in progress (2026-10-04).**
  - The 15:20 check-in planned 4 sets of 8 (beginner load 40% of 20) at 15:58, 16:50, 17:44 and 18:37, all exact alarms.
  - The weekly review row for the week of 2026-09-28 says `not_enough_data`, which is correct.
  - s1 was logged **Hard** at 15:20 from the app (early). Verified: the remaining sets moved to 17:20 and 18:14 at 6 reps, the 18:37 set was dropped past the 19:00 window end, and the streak went to 2 with `today_on_plan` true.
  - **Still to verify:** Snooze from a set notification (should move the set 15 minutes) and Done while the server is off, then the upload on app open. The 17:20 test wasn't confirmed: the session paused for a usage limit, and the dev server was stopped at some point before 21:30.
- **The user's account:** max 20 standard push-ups (level 4) on 2026-10-03, so the next test at that level is on 2026-10-17. Streak: 2 (3 and 4 Oct).
- **Backups:** `server/dev.db.bak-*` (from before migrations 0002 and 0003) and the phone app data in `D:\Android\backup\*.tar` (latest: `dvcoach-data-before-v6.tar`).

## Next up

1. **Check by eye:** the level picker on the max test screen, the streak line on Today and the levels section in the push-up guide.
2. **Full-day test.**
   - Steps: the 07:15 check-in reminder, check in with the server running, then use the notification's **Hard** and **Snooze** buttons during the day.
   - Check in once with the server off, to test the offline fallback plan.
   - Already verified: exact reminders, the notification's Done button with the app closed, offline logging and later sync, Pain ending the day, reset today, the update over the old app, and Room migration 1 → 2.
3. **Session mode, step 2: the API.** See the build order in `docs/session-mode-and-coach.md`.
   - Profile fields: mode, goal, days, session length, available items and high-impact.
   - Today's session, session logs, the weekly review, a return-after-a-break rule, report endpoints and an Alembic migration.
   - Then Android (the session player and the report), then the coach. Load the `claude-api` skill first.
4. **Then the rest of phase 2.** Weekly progression and the max-test-due card are done (session 3):
   - The Hard-set model with the simulator.
   - Health Connect sleep.
   - Pull-ups.
   - A "Why this plan" screen, which the coach may cover.
