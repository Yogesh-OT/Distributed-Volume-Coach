# Session mode and the AI coach (proposal)

**Status:** proposed on 2026-10-04 and waiting for the user's go-ahead.

**Already decided by the user:**
- Bodyweight only.
- Goals: build muscle, and get fit / lose fat.
- Spread-out sets stay as a second mode.
- An AI chat coach sits on top of the engine.

The UX reference findings are in `docs/ux-references.md`.

## Why two modes

- **Spread-out sets** are what the app does today: about 40–50% of your max, hours apart, never close to failure. They build strength and skill at one movement (Grease the Groove).
- **Sessions** are the new mode: several exercises in one go, sets taken close to failure, short rests, and enough sets each week. They build muscle.
- Research backs the split. How close a set gets to failure barely changes strength gains, but it does change muscle growth. So each mode does a different job, and the app suggests the one that fits your goal.

## The research behind the numbers

| Rule | Source |
|---|---|
| Bodyweight work can build muscle. Push-ups adjusted to the same load as a 40% bench press grew chest and triceps as much as the bench press over 8 weeks. This was a small study of 18 men. | [Kikuchi & Nakazato 2017](https://pubmed.ncbi.nlm.nih.gov/29541130/) |
| Sets closer to failure give somewhat more growth. Strength gains don't depend on it. | [Robinson et al. 2024](https://rke.abertay.ac.uk/en/publications/exploring-the-dose-response-relationship-between-estimated-resist/), meta-regressions of 55 hypertrophy and 67 strength studies |
| Rests longer than 60 s give a small benefit, and rests past about 90 s add nothing more. | Singer et al. 2024 |
| More weekly sets per muscle give more growth, up to a point. Programs commonly use about 10–20. | Schoenfeld, Ogborn & Krieger 2017 (dose-response meta-analysis) |

## Session mode: the engine (server)

**1. Exercise library: a ladder of levels per movement.**

| Movement | Muscles | Levels, easiest first |
|---|---|---|
| Push | chest, triceps, front shoulders | wall → incline → knee → full → decline → diamond (the first five already exist) |
| Overhead push | shoulders | pike push-up → feet-raised pike |
| Squat | thighs, glutes | squat → split squat → Bulgarian split squat → box pistol |
| Hinge | glutes, hamstrings | glute bridge → single-leg bridge → shoulders-on-sofa hip thrust |
| Back | upper back, biceps | **open question** (see the end) |
| Core | trunk | plank → side plank → hollow hold (timed holds) |

Each exercise records:
- the muscles it works
- reps or a timed hold
- whether it's done on each side
- form cues and common mistakes, written by us

**2. A weekly template, based on your days per week.**
- 2–3 days: full body every session.
- 4 days: upper body, then lower body.
- Session length (20, 30 or 45 minutes) caps the number of sets.

**3. Sets for "build muscle."**
- **Reps:** a range per exercise, about 8–20. Bodyweight sets can go up to about 30 before the next level is due.
- **Effort:**
  - Most sets stop with 1–2 reps left.
  - The last set of an exercise can go to 0–1 left.
- **Rest:**
  - 90 s for push, squat and hinge.
  - 60 s for core and smaller moves.
  - +20 s and Skip are allowed, and the real rest time is logged.
- **Weekly sets per muscle:** beginners start near 10. The weekly review moves this up toward 20, one step at a time.

**4. Sets for "get fit / lose fat."**
- Circuits of 3–4 rounds with 30–45 s rests.
- Moderate effort, stopping with 2–4 reps left.
- Low-impact cardio moves mixed in, such as marching and step jacks.
- **Honest framing:** fat loss mostly comes from eating less. Workouts keep muscle and build fitness. The app shows no calorie-burn numbers.

**5. Logging each set.** Record the reps done and how hard the set felt:
- **Easy:** 4 or more reps left
- **Good:** 2–3 left
- **Hard:** 1 left
- **Max:** no more reps possible

**6. Progression.** Bodyweight can't add weight, so the version of adding weight is to add reps, then move up a level.
- Within the rep range, aim for +1 rep per set when last time's sets were Easy or Good.
- When every set reaches the top of the range with at least 1 rep left, move to the next level and start at the bottom of its range.
- When reps fall below the range, or most sets were Max, step back a level.
- The weekly review works like `progression.py` today, changing one thing at a time:
  - After a strong week, add one set for a muscle.
  - After a rough week, remove one.

**7. Plan changes show Before → After.**
- The engine builds the new plan.
- The app shows the difference and asks *Use new plan* or *Keep my plan*.
- One line says why the plan changed.

**8. Offline.** When the server can't be reached, the phone repeats the last session's plan, the same way the fallback planner works today. Logs sync later.

## Session player (phone)

1. **Start.** A 10 s get-ready countdown.
2. **The exercise screen.**
   - A big "×12".
   - The target, for example "8–15, stop with 1–2 left".
   - A **How-to** button.
3. **After the set.** Enter the reps done (pre-filled with the target, with +/− buttons) and tap one of the four effort buttons.
4. **The rest screen.**
   - A countdown with **+20 s** and **Skip**.
   - The next exercise.
   - One line on why the rest is this long.
5. **The summary.**
   - Sets and reps compared with last time, for example "+3 push-ups".
   - The streak.
   - The next session.

**Quitting asks why**, with these answers:
- **Too hard:** offer an easier level.
- **Don't know how:** open the how-to.
- **No time:** save the session so it can be resumed.
- **Pain:** stop, and pause that exercise until you say it's fine.
- **Just looking.**

**The rest timer** runs in a foreground service, so it keeps counting with the screen off. It ends with a sound and a vibration. Voice cues using Android's on-device text-to-speech come later.

## The AI coach

**Where it runs.**
- The app calls a server endpoint, `POST /v1/coach/messages`.
- The server holds the Claude API key, and the app never sees it.

**What it can read**, through tool calls backed by the engine and database:
- your goal and profile
- this week's plan and the engine's reasons for it
- recent sessions and progress
- exercise info

**What it can propose:**
- easier or harder
- swapping an exercise
- changing days per week or session length

For every proposal, the engine computes the new plan and returns a Before → After preview. You tap to accept, and the coach can never change a plan by itself.

**Rules in its instructions:**
- Use only the engine's numbers.
- For pain: stop, see a professional, and never diagnose.
- Respect screening answers.
- Give general guidance only on food. No diet plans or supplements.
- Keep answers short.

**Not every message needs the AI.** The short notes after a check-in or a session come from the engine's own reason text, which is free, instant and works offline. The chat is for questions and changes.

**Cost:**
- A daily message limit per user.
- The model choice and prompt caching get settled when the coach is built, after loading the `claude-api` skill.

**Privacy:**
- Chat messages go to Anthropic's API, and the consent screen says so.
- Chat history is deleted with the account.

**Testing:**
- The tools get unit tests like the rest of the engine.
- A fixed set of conversations gets checked by hand, for example "make it easier", "my wrist hurts" and "why only 3 sets?".

## Build order

1. **The server engine:** exercise library, weekly templates, set rules, rest rules and level progression, all with tests.
2. **The API:**
   - today's session
   - session logs
   - the plan-change preview, and accepting it
   - an Alembic migration
3. **Android:**
   - choosing a mode in onboarding
   - a session card on Today
   - the session player and summary
   - how-to for every exercise
   - a Room migration
4. **The coach:** the server endpoint with tools, a chat screen, and accepting proposed changes.
5. **Later:**
   - voice cues
   - Health Connect
   - a pull-up bar as the first optional equipment

## Open questions

1. **Back exercises without equipment.** Nothing at home replaces rows or pull-ups well, and skipping back work leaves push and pull out of balance.
   - **(a)** Lying Y-T-W raises and supermans now (safe, but a weak stimulus), with a pull-up bar as the first optional equipment later. **Recommended.**
   - **(b)** Towel rows on a door or rows under a sturdy table now. They work the back better, but there's a risk if the door or table gives way.
   - **(c)** Allow a pull-up bar from day one.
2. **Days and length.** Offer 2–4 days a week and 20, 30 or 45 minute sessions?
