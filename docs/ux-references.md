# UX references

Patterns from other fitness apps, adapted to how DV Coach works: one exercise, practised in small sets spread across the day. The goal is to borrow ideas, not visuals. No screenshots or assets from other apps are kept in this repo.

Collected 2026-10-03.

## Home Workout – No Equipment (Leap Fitness, Android)

Looked at on a phone: the Training, Discover, Report and Settings tabs, a workout's details, the workout player and the streak screen.

| Pattern | What it does | Use in DV Coach |
|---|---|---|
| Hero card with one action | "28 days challenge · Day 2 · 1/28", a progress bar and one big **Start day 2** button | Today gets one main card whose action changes through the day: **Check in**, then **Next set at 17:29**, then **Done for today**. It shows progress like "1 of 2 sets". |
| Weekly strip | Seven days with checkmarks, plus a "Weekly goal 1/7" with a pencil to edit it | A week strip on Today and Progress. A day is ticked when it went to plan, including planned rest days. |
| Streak and personal best | A flame with a count in the header. After a workout, a full-screen "Day streak 1 · Best 2 days" with the week strip. | Possible, with care (see below). |
| Program map | Weeks of numbered days with a trophy at the end of each week; "27 days left · 4%"; options to restart or adjust the plan | The **14-day block to the next max test**: "Day 5 of 14, next max test on 17 Oct". |
| Exercise info sheet | Video / Muscle / How-to tabs, duration or reps, instructions and focus-area chips | A **"How to do a push-up"** sheet from the set card: form cues, common mistakes and muscles worked. |
| Player | A big rep count ("×16") or timer, one big ✓, previous/next buttons, a 15 s "Ready to go" countdown | When a set notification is tapped, open a focused set screen: a big "8 push-ups" with Done / Hard / Easy. No timers needed. |
| Mid-workout exit | "You are doing great! Keep exercising / Restart / Do it later" | A short, warm confirmation after each logged set, plus when the next one is. |
| Report | Totals (workouts, kcal, minutes), history by week, streak, a weight chart with **Log** | Progress already has reps per day. Add the week strip and weight (we have it from Body). Skip kcal: the estimates are unreliable for a few push-ups. |
| Settings | Backup and sync (Google), workout settings, voice and TTS, language, Health Connect toggle, feedback | A **Settings tab**: your day, reminders and their permissions, account, test tools. |
| Search, filters, body-focus chips, goals | A catalogue of hundreds of sessions | Doesn't apply yet. The equivalent later is **push-up levels** (see below). |

**What not to copy:**
- Ads, "watch an ad to unlock", premium upsells and paywalls inside the flow.
- Aspirational body photos and claims like "lose belly fat fast".
- Calorie estimates.

### Second look (2026-10-04): sessions, rest and plan changes

This time the focus was on how a workout session runs and how the app adapts, for the new session mode (see `docs/session-mode-and-coach.md`).

| Pattern | What it does | Use in DV Coach |
|---|---|---|
| Rest screen | A countdown (30 s by default), **+20s** and **Skip**, "Edit rest time", and a preview of the next exercise ("Next 11/16 ×20") | Keep the layout. Rest length comes from the goal: 60–90 s for muscle sets, with a one-line reason. |
| Rest and prep timers | Set in *Workout settings*: rest up to about 60 s, a 10–15 s "get ready" countdown | A get-ready countdown, yes. A rest limit near 60 s, no: for muscle growth, more than 60 s works a little better. |
| Reps or time per exercise | A big "×20" with a ✓, "Each side ×10", and a Reps mode / Time mode switch | Reps for strength moves, time only for holds such as planks. After each set, log the reps done and how hard it was. |
| Exercise info | Video / Muscle / How-to tabs, a front and back muscle map, focus chips, common mistakes | Extend the push-up guide to every exercise. We write the text ourselves. |
| Quitting a workout | Asks why: "Just take a look", "Too hard", "Don't know how to do it" | Ask why, and act on it: Too hard → offer an easier level; Don't know how → open the how-to; Pain → stop and hide that exercise. |
| Resuming | "Continue · 63% completed" or Restart | Resume a session that was left part-way. |
| Plan adjust | An **Adjust** button opens "Your coach is busy working for you…", a staged loading screen ("Rescheduling week 1 of 4…"), then an ad, then "A new and easier 28-day plan is ready" with a **Before → After** table for day 1 and "No, I'd prefer my previous plan" | Keep the before/after table and the "keep my plan" choice. Drop the fake loading screen and the ad. Our change comes from the engine and logged sets, with the reason in one line. |
| Custom workouts | Create your own: choose from 369 exercises by name, every one 20 s by default, reorder, swap, +/− time, name it | Later, if at all. The coach should build the session for you, because most people don't know what to pick. |
| Home and Discover | Weekly goal, a challenge carousel, body-focus chips, filters by length, "Last time: Today" | Today shows the next session and the week. A "last time" note helps beat your previous numbers. |
| Workout settings | Gender, music, rest timer, prep timer, sound (voice guide, coach tips, effects), restart progress | Sound and voice cues later, using Android's on-device text-to-speech. |

**Also not to copy:** the "coach" is a stock photo with canned messages; "Height increase" programs; "lose belly fat" spot-reduction claims; time-only sets for strength moves, which can't show progress in reps. Searching "cus" didn't find "Create your own".

## Other apps

- **[Grease the Groove](https://apps.apple.com/us/app/id1497802037)** (iOS) is the closest competitor.
  - It works for push-ups, pull-ups, squats and dips.
  - You enter your max, and it builds a plan that adjusts as you progress.
  - It has reminders, XP and achievements, and costs about $3–5 a month.
  - A companion watch timer, [Notch](https://appshunter.io/ios/app/notch-gtg-watch-timer/id6772011909), handles logging on the wrist.
  - Where DV Coach differs: Android, a readiness check-in, rules that adjust the rest of the day, sets placed exactly within your window, and the reason shown for each plan.
- **[Wakeout](https://screensdesign.com/showcase/wakeout-break-the-sit-habit)** is built around movement breaks during the day.
  - "Three taps to move", and reminders that adapt to your habits.
  - One daily score that counts small efforts.
  - Confetti when a break is done.
  - A 13-step onboarding that reviewers flag as a drop-off risk. Ours is one long page, and splitting it into short steps is worth considering.
- **[Freeletics](https://freeletics.com/en/blog/posts/freeletics-sports-science)**
  - After each session you rate it too easy, just right or too hard.
  - The coach changes **one variable at a time**, and **volume before intensity**.
  - This supports our Easy / Solid / Hard ratings and is a good rule for phase 2's weekly progression.
- **[Fitbod](https://fitbod.me/blog/how-fitbods-ai-knows-exactly-when-you-should-lift-heavier-and-when-to-recover/)**
  - Its recovery map explains **why** today's workout is what it is, and it logs reps in reserve.
  - This supports the planned "Why this plan" screen.
- **Push-up programs** such as [Push-Ups: Pro](https://apps.apple.com/app/id6755532435), [PushPush](https://apps.apple.com/app/id6751195808) and [100 Pushups](https://apps.apple.com/us/app/id1542390886):
  - They start from a max test.
  - They use **levels**: knee, negatives, full.
  - PushPush **counts reps with the front camera and light sensor**. A phone placed under the chest could count reps the same way, which would check the "Done" taps.
- **[Duolingo's streak research](https://blog.duolingo.com/how-duolingo-streak-builds-habit)** found that streak freezes, a day off without losing the streak, raised retention. Critics also note that streaks can cause anxiety; see [this UX Collective piece](https://uxdesign.cc/3-reframing-streaks-on-duolingo-5-ideas-for-a-more-healthy-and-flexible-approach-to-language-8fd89545771e). If DV Coach adds a streak, it should count rest and mobility days as on plan and never punish taking a planned break.
- **Demand signal:** users have asked another fitness app for exactly this, "randomised nudges within a time window" for Grease the Groove sets ([Bevel feature request](https://feedback.bevel.health/feature-requests/p/grease-the-groove-and-micromovement-nudges)).

## Shortlist for DV Coach

**No product decision needed:**
1. **Today hero card.** One main action for the time of day, today's set progress, and the week strip.
2. **Settings tab.** Your day, reminders and their permissions, account, test tools and server address.
3. **Lock the next set** until shortly before it's due, with "Do it now anyway" behind a confirmation. Today you could log the 18:26 set at 16:37.
4. **Field-specific errors** on the body form, and range checks before sending.
5. **A "How to do a push-up" sheet** from the set card.
6. **A focused set screen** when a set notification is tapped.

**Decided on 2026-10-03:**
- **Streak: built.** Days on plan; rest days and pain stops count; one rest pass a week.
- **Push-up levels: built.** Wall → incline → knee → full → decline, chosen at the max test.

**Not now:**
- **The 14-day block shown as a program map** leading to the next max test.
- **Counting reps with the phone's sensor.**
