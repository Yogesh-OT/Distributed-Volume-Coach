# Session mode, the report and the AI coach

**Status:** decided on 2026-10-04. The user asked for the best-supported choices over their own opinions; the evidence is in `docs/training-research.md`. The engine part (step 1 below) is built and tested.

**Decided earlier by the user:**
- Bodyweight only.
- Goals: build muscle, and get fit / lose fat.
- Spread-out sets stay as a second mode.
- An AI chat coach sits on top of the engine.

The UX reference findings are in `docs/ux-references.md`.

## Two modes, two jobs

- **Spread-out sets** (the app today): about 40–50% of your max, hours apart, far from failure. They build strength and skill at one movement.
- **Sessions** (new): several exercises, sets close to failure, short rests, about 10+ sets per muscle a week. They build muscle.
- How close sets get to failure matters for muscle growth but barely for strength (Robinson 2024), so each mode does a different job. The app suggests sessions for both launch goals and keeps spread-out sets as an option.

## The exercise library (`server/engine/exercises.py`)

Each movement is a ladder of levels, easiest first. Each exercise has form cues written by us, and some need household items. If something isn't available, that level is skipped.

| Ladder | Muscles (1 = direct, ½ = indirect) | Levels | Range |
|---|---|---|---|
| Push-up | chest; ½ triceps, shoulders | wall → incline → knee → push-up → decline → archer → pseudo planche | 6–15 |
| Pike push-up | shoulders; ½ triceps | hands-raised pike → pike → feet-raised pike → wall handstand lowering | 6–15 (3–8 last) |
| Row | back; ½ biceps | doorway row → table row, knees bent → table row → feet raised | 6–15 |
| Squat | quads; ½ glutes | chair squat → squat → split squat → Bulgarian split squat → assisted shrimp → box pistol | 6–15 |
| Lunge | quads; ½ glutes | reverse lunge → step-up → deficit reverse lunge | 6–15 |
| Hip thrust | glutes; ½ hamstrings | glute bridge → single-leg bridge → hip thrust → single-leg hip thrust | 8–20 |
| Leg curl | hamstrings; ½ glutes | sliding leg curl → single-leg → Nordic curl lowering (needs a heavy sofa) | 6–15 (3–8 Nordic) |
| Calf raise | calves | calf raise → single-leg → single-leg on a step | 10–20 |
| Close push-up | triceps; ½ chest | close incline → close knee → diamond → bodyweight triceps extension | 6–15 |
| Plank | core | knee plank → plank → long plank → body saw | 20–60 s |
| Core curl | core | dead bug → reverse crunch → leg raise → hollow rock | 8–20 |
| Side plank | core | knee side plank → side plank → top leg raised | 15–45 s |

- The push-up ladder's first five levels are the spread-out mode's levels, so a max test carries over: sets start at 70% of the max.
- **Decided: back training without a pull-up bar.** Doorway rows for everyone. Table rows if you have a sturdy table, and onboarding asks: not glass, not folding, test it first. A pull-up bar is the first optional item later. Lying Y-T-W raises were the safer alternative, but they barely load the back, and back work is what keeps push and pull muscles in balance.
- **Gaps we can't close without equipment:** side shoulders and biceps get only indirect work. A resistance band would be the second optional item.

## The week (`server/engine/sessions.py`)

**Decided:** 2, 3 or 4 days a week (3 recommended), and sessions of 20, 30 or 45 minutes (30 recommended).

| Goal | 2 days | 3 days | 4 days |
|---|---|---|---|
| Build muscle | Full body A, B | Full body A, B, C | Upper 1, Lower 1, Upper 2, Lower 2 |
| Get fit / lose fat | Full body A, B, each with a short circuit at 30+ min | A, circuit, B | A, circuit, B, circuit |

Each session is a list of **pairs**: two exercises for different muscles, done alternately with 60 s rest. For example:

| Full body A | Full body B | Full body C |
|---|---|---|
| push-up + row | push-up + row | push-up + row |
| squat + core curl | squat + plank | squat + side plank |
| hip thrust + calf raise | leg curl + calf raise | hip thrust + calf raise |
| pike push-up + plank | close push-up + core curl | pike push-up + core curl |

**How a session is sized:**
- **Sets:** main movements (push, row, squat, lunge, hinge, curl, pike) get 3 sets, and extras get 2.
- **Fitting the time:** every pair that fits gets in at its minimum first (2 sets for main movements, 1 for extras), then sets are added up to the target. So more volume never pushes a muscle out.
- **The volume step:** the weekly review moves it from −1 to +2. That's 2 to 4 sets for main movements and 1 to 3 for extras, and the session length caps it.
- **Results** (tested; the plans start at volume step 0):
  - **3 days × 30 min:** about 9–10 sets per week each for chest, back, shoulders, quads and glutes. Hamstrings get 5.
  - **4 days × 45 min at +1:** 10–16 for most muscles.
  - **2 days × 20 min:** 2–5 per muscle. This is close to the minimum that still works, about 4 (Iversen 2021).
- **Every major muscle is trained at least twice a week** in every plan (ACSM 2026). Every session fits its chosen length. Both are tested.
- **Warm-up:** 3 minutes.
- **Tough check-in:**
  - Readiness below 0.5: one set fewer on extras.
  - Below 0.25: a light session, with main movements only, 2 sets each and no test sets.
- **Fitness circuits:** 4–5 moves, low-impact by default (marching, step jacks, step-back burpees). They go from 20 s on / 40 s off × 3 rounds up to 40/20 × 4 rounds of 5 moves, and take 15–23 minutes.

## Progression (`server/engine/session_progression.py`)

**After each set,** you log the reps (pre-filled with the target) and how it felt:
- **Easy:** 4 or more reps left
- **Good:** 2–3 left
- **Hard:** 1 left
- **Max:** nothing left

**The last set of each exercise** goes as far as good form allows. It's skipped for the Nordic curl and the handstand lowering.

**After each session, each exercise takes one step:**
- **All sets Good or Easy:** +1 rep next time. If the last set showed much more, the target catches up to 3 below it.
- **A Hard set, or one missed:** same target, because that's the effort we want.
- **Two sets missed or at Max:** 1 rep fewer.
- **At the top of the range with 2 reps spare:** next level, at the bottom of its range.
- **Below the range twice in a row:** the level before.
- **Pain:** that exercise pauses until you say it's fine.
- **Holds** work the same way, in 5-second steps.

**Once a week, the volume review runs:**
- **One step up when all of these hold:**
  - At least 90% of sets were done.
  - At most 10% of sets were at Max.
  - Soreness was below 4.
- **One step down** when fewer than 70% of sets were done, or more than 25% were at Max.
- **No step up** past 20 sets per muscle, or when sessions are already full. In that case the note suggests longer sessions or another day.

**Circuits:**
- Easy, or Good twice in a row: one level up.
- Too hard, or quitting: one level down.

**No scheduled rest weeks** (Coleman 2024). After 2+ weeks off, you come back with fewer reps; this is still to build in the API.

## Session player (phone)

1. **Start.** A 3-minute guided warm-up, then a 10 s get-ready countdown.
2. **Exercise.**
   - A big "×12" with the target ("6–15, stop with 1–2 left").
   - The last set says "as many as you can with good form".
   - A **How-to** button.
3. **After the set.** Reps (pre-filled) and the four effort buttons.
4. **Rest.**
   - A countdown with +20 s and Skip.
   - The next exercise.
   - One line on why the rest is this long.
5. **Summary.**
   - This session against last time ("+3 push-ups").
   - Level-ups.
   - The streak.
   - The next session.

**Quitting asks why**, and each answer leads somewhere:

| Answer | What happens |
|---|---|
| Too hard | An easier level is offered |
| Don't know how | The how-to opens |
| No time | The session is saved to resume |
| Pain | That exercise pauses |
| Just looking | Nothing |

**The rest timer** runs in a foreground service, so it keeps going with the screen off. It ends with a sound and a vibration.

**Plan changes** show a Before → After table with *Use new plan* / *Keep my plan*.

**Offline:** the phone repeats the last session's plan, and logs sync later.

## The report

The user wants a report page. The reference app's Report tab (seen on 2026-10-03) has totals (workouts, calories, minutes), weekly history, the streak and a weight chart. DV Coach's report:

- **This week:**
  - Sessions done and planned, sets and minutes.
  - The streak.
- **Muscles this week:**
  - Sets per muscle, with indirect work counted as half, against the 10–20 band.
  - It shows why the plan is what it is. Hevy offers a similar chart.
- **Exercise progress:**
  - Each ladder's current level, plus a chart of last-set reps over time.
  - Personal bests ("New best: 14 push-ups") and level-ups.
- **History:** a calendar of past sessions and their details.
- **Body:**
  - Weight as a 7-day average, and waist.
  - For the fat-loss goal, the weekly rate against the 0.5–1% guide (Helms 2014).
- **Spread-out mode:** the existing reps-per-day chart.
- **Left out:** calorie estimates.

## The AI coach

**Where it runs.**
- The app calls a server endpoint, `POST /v1/coach/messages`.
- The server holds the Claude API key, and the app never sees it.

**What it can read**, through tool calls backed by the engine and database:
- your goal and profile
- this week's plan and the engine's notes
- recent sessions and progress
- the weekly muscle sets
- exercise info

**What it can propose:**
- easier or harder
- swapping an exercise
- changing days or session length

For every proposal, the engine computes the new plan and returns Before → After. You tap to accept; the coach can't change a plan by itself.

**Knowledge:** its instructions include the rules from `docs/training-research.md`, so its answers match the engine.

**Rules:**
- Use only the engine's numbers.
- For pain: stop, see a professional, never diagnose.
- Respect screening answers.
- Give general guidance only on food (0.5–1% a week, about 1.6 g protein per kg). No meal plans or supplements.
- Keep answers short.

**Not every message needs the AI.** The engine's notes after each session are free, instant and work offline. The chat is for questions and changes.

**Cost:**
- A daily message limit per user.
- The model choice and prompt caching get settled when building, after loading the `claude-api` skill.

**Privacy:**
- Chat goes to Anthropic's API, and the consent screen says so.
- Chat history is deleted with the account.

## Build order

1. **Done:** the engine, with the exercise library, week plans, session sizing, progression, the volume review and circuits. `server/tests/test_sessions.py` has 34 tests, which run as 121 cases because several check every plan.
2. **The API:**
   - Profile fields: mode, goal, days, session length, available items and high-impact.
   - `GET` today's session and `POST` session logs.
   - The weekly review.
   - A "return after a break" rule.
   - Report endpoints.
   - An Alembic migration.
3. **Android:**
   - Onboarding for the mode and goal.
   - A session card on Today.
   - The session player and summary.
   - How-to for every exercise.
   - The report.
   - A Room migration.
4. **The coach:** the endpoint with tools, a chat screen, and accepting changes.
5. **Later:**
   - voice cues
   - Health Connect (sleep and steps: 8,000–10,000 a day, Paluch 2022)
   - a pull-up bar, then a resistance band
