# Distributed Volume Coach

An Android app that spreads small sets of push-ups across the day and adjusts them based on how each set felt. This repo is the phase 1 MVP described on the [architecture page](https://claude.ai/artifact/3NHAmvSAMi8WSr2ww2Hhdb).

```
server/    Python: training engine (pure functions) + FastAPI API + Alembic migrations
android/   Kotlin: Jetpack Compose app, Room, AlarmManager prompts, WorkManager sync
shared/    policy_vectors.json: in-day rule test cases run by both Python and Kotlin
```

## How a day works

1. **Check-in (phone).** 15 minutes after the user's wake time, a reminder asks about sleep, soreness and energy (1 to 5 each).
2. **Plan (server).** `POST /v1/checkins` builds today's plan right then: `reps = round(load × max)`, and the number of sets scales with readiness. If the server doesn't answer within 10 seconds, the phone repeats its last plan with one set fewer.
3. **Prompts (phone).** One inexact alarm per set. Each notification has three buttons (Android's limit): Done, Hard and Snooze 15 min. Easy, Pain and Skip are in the app.
4. **In-day rules (phone).** A hard set trims the rest of today by 20% and pushes it 30 minutes later. Two hard sets end the day, and pain stops push-ups for the day. Every set stays at least 45 minutes after the last one.
5. **Sync (phone).** WorkManager uploads logs when online. Each log carries an ID made on the phone, so a retry never counts a set twice.

The formulas live in `server/engine/planner.py` and `server/engine/policy.py`. The numbers are cautious starting values to tune with real logs, not research constants.

## Run the server

Needs Python 3.12 or newer.

```bash
cd server
python -m venv .venv
source .venv/Scripts/activate # Git Bash; PowerShell: .venv\Scripts\Activate.ps1; macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # dev mode: SQLite + dev sign-in
alembic upgrade head
uvicorn app.main:create_app --factory --reload --port 8000
```

API docs are at http://localhost:8000/docs. In dev mode, any request with `Authorization: Bearer dev:<anything>` is accepted. Never expose a dev-mode server to the internet.

Run the tests:

```bash
pytest
```

The tests cover the shared policy cases, the planner (including 2,000 random schedules), body profile, safety rules and the full API flow.

## Run the Android app

1. Open the `android/` folder in Android Studio. If it asks about the Gradle wrapper, let it use the one in `gradle/wrapper/gradle-wrapper.properties`. Or, with Gradle installed, run `gradle wrapper` once inside `android/`.
2. Start the server as above on port 8000.
3. Run the `app` configuration on an emulator. Debug builds call `http://10.0.2.2:8000/`, which is your computer as seen from the emulator, and use dev sign-in.

The Kotlin unit tests run the same shared policy cases as the Python tests: `gradle testDebugUnitTest`.

### Try it on your Android phone

Every push builds a test app (`app-debug.apk`) in GitHub Actions. To use it without Android Studio:

1. **Get the app.** Open the repo's **Actions** tab, then the latest green run. Download **dv-coach-debug-apk** under *Artifacts* and unzip it.
2. **Get adb.** Download Google's [SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools) and unzip them.
3. **Turn on USB debugging.**
   - On the phone, open *Settings → About phone* and tap *Build number* seven times.
   - Then turn on *Settings → Developer options → USB debugging*.
   - Plug the phone in and accept the prompt on the phone.
4. **Install and connect**, from the platform-tools folder:
   ```bash
   adb devices                          # your phone should be listed as "device"
   adb install -r path/to/app-debug.apk
   adb reverse tcp:8000 tcp:8000        # the phone's 127.0.0.1:8000 now reaches your computer
   ```
5. **Start the server** as above. It only needs to listen on `127.0.0.1`.
6. **Check the connection.** Open DV Coach and tap **Save and test** under *Server address*. On a real phone it already says `http://127.0.0.1:8000`; on the emulator it says `http://10.0.2.2:8000`.
7. **Allow on-time reminders.** On the Today screen, tap **Allow on-time reminders** and switch on *Alarms & reminders*. Without it, Android may hold set reminders back by up to an hour. *Settings → Reminders* shows the current state.

`adb reverse` lasts until the cable is unplugged or the phone restarts, so run it again after either. Test builds are signed with the fixed debug key in `android/app/debug.keystore`, so a newer build installs over the old one and keeps its data. That key is debug-only and deliberately public.

**Xiaomi, Redmi and POCO phones** need three extra steps:
- `adb install` is blocked unless *Install via USB* is on in Developer options. Instead, copy the APK to the phone and install it from File Manager.
- For DV Coach, turn on **Autostart**.
- Set **Battery saver** to *No restrictions*. Otherwise the system can stop reminders while the app is closed.

**Test builds** have a **Reset today** button under *Settings → Test tools*. It forgets today's check-in, plan and sets, so you can check in again. It only works against a dev-mode server. To change your training window, tap **Change** next to it on the Today screen, or use *Settings → Change your day*.

Using Wi-Fi instead of USB means starting the server with `--host 0.0.0.0` and letting it through Windows Firewall. Do that only on a private network you trust, because dev mode accepts any sign-in.

### Release builds (Firebase sign-in)

1. Create a Firebase project and enable **Anonymous** sign-in.
2. Download `google-services.json` into `android/app/`. It's gitignored.
3. Set `API_BASE_URL` in `android/app/build.gradle.kts`.
4. On the server, set `DVC_AUTH_MODE=firebase` and `GOOGLE_APPLICATION_CREDENTIALS`, install `pip install ".[prod]"`, and point `DVC_DATABASE_URL` at PostgreSQL.

## Phase 1 scope

Included:
- Questionnaire with screening
- Max test
- Body measurements and profile card
- Check-in that returns a plan
- Set reminders (exact when *Alarms & reminders* is allowed) and logging from notifications
- Changing your daily schedule
- In-day rules and the offline fallback plan
- Sync
- Progress chart
- Account export and deletion

Not yet (later phases): weekly progression, the learned fatigue model and simulator, Health Connect, pull-ups, photos, and a session mode for other goals.

## Known issues

- **Set reminders can still be late if *Alarms & reminders* is off.** The app then falls back to inexact alarms. On a test phone running Android API 36, Android gave those alarms up to a 1-hour delivery window. The Today screen asks for the permission.

First on-device test (Xiaomi, Android API 36): install, server connection, onboarding, max test, check-in, progress and account deletion all worked with no crashes. Set notifications, in-day logging, sync and the offline plan haven't been tested on a phone yet.

## Safety notes

- 18+ only.
- Screening "yes" answers block max tests until the user confirms a doctor's clearance.
- The screening questions are paraphrased from the PAR-Q+. Check the PAR-Q+ Collaboration's terms before shipping the official wording.
- This is training guidance, not medical advice.
