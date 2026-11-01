# Part 4 speech: the Video Nutrition Label

**Presenter:** Imad eddine Djehlane · **Length:** about 4 minutes · **Order:** slide 21 → live app → slide 22

## The three hooks to remember

If you forget everything else, remember these three phrases. The whole speech hangs on them.

1. **"Same calories, different diet"** (slide 21)
2. **"The numbers are counted, the AI only talks"** (the app)
3. **"Now, at your limit, tomorrow morning"** (slide 22)

---

## Opening (on Lu's slide 20, "we'll give users one")

> Lu just told you the casino has no clocks. So let me ask you something simpler.
>
> *(pick up a snack or a bottle, or just mime holding one)*
>
> When you buy a bottle of juice, you can turn it around and read exactly what's inside: calories, ingredients, sugar. By law.
>
> You probably watched an hour of short videos yesterday. Can you turn *that* around and read what was inside?
>
> *(pause)*
>
> No. Nobody can. So we built the label.

## Slide 21: "same calories, different diet" (about 1 minute)

*(click to slide 21)*

> These are two real people from the Kuaishou data. Real viewing logs, anonymous.
>
> The person on the left watches **76 videos a day**. The person on the right, **77**. Practically identical.
>
> If you're the phone's screen-time counter, these two people are the same person. Same "calories".
>
> But look inside the bottles.
>
> *(point left)* This person spends **39%** of their time on one single topic, local news. That's more concentrated than **96%** of all users.
>
> *(point right)* This person's biggest topic is only **10%**. Their time is spread over 16 topics.
>
> **Same calories. Completely different diet.** A clock tells you *how much*. A label tells you *what*. That's the difference, and that's our proposal.

## Live app: the fake app (about 1.5 minutes)

*(switch to the browser with `01_label_prototype.html` already open on "The narrow diet")*

> This is the prototype. Think of it as the back of the juice bottle, but for video.
>
> *(point at the white label, top to bottom)*
>
> - **Videos per day:** the calories.
> - **Ingredients:** what the time was made of, topic by topic.
> - **Replays:** our "added sugar". That's time spent watching a clip that already finished and is looping. Across all users, **more than a quarter** of all watch time is replays. For this person it's almost half.
> - **Longest sitting:** how many videos in a row without a real break.
>
> And under every line: how you compare with **5,765 real users**. We don't say "this is too much", because no doctor has ever defined a healthy amount of TikTok. We just show you where you stand.
>
> *(click "The heavy viewer")*
>
> This user watches **137 videos a day**, more than 95% of people. Once, **341 videos in a row** without a 30-minute break.
>
> *(point at the AI box on the right)*
>
> Now the AI part, because this is an AI course. The AI does **not** decide anything here. The numbers are counted by simple code. **The numbers are counted, the AI only talks.** It reads the label and explains it in three human sentences, with one gentle suggestion.
>
> And we learned something the hard way. In our first version, the AI got creative. It turned "10 videos" into "10 minutes". It said "90% more" when the data said "more than 90% of people". So we changed two things. We give it pre-explained facts, and every sentence it writes is now checked automatically against the label. 101 summaries, all passed.
>
> The business lesson: **AI is a great explainer, but you have to check its homework.**

## Slide 22: "three moments, one clock" (about 1 minute)

*(back to the slides, slide 22)*

> A label only works if you see it at the right moment. The juice label is useless if it's inside the bottle. So we designed three moments: **now, at your limit, tomorrow morning.**
>
> - **Now:** while you scroll, a tiny counter in the corner. "76 videos today, mostly local news." It blocks nothing. It just puts the clock back on the casino wall.
> - **At your limit:** you choose a limit. When you hit it, the feed pauses and shows you what that session was made of. Stop, or ten more. **Your** choice.
> - **Tomorrow morning:** the full label, with the AI summary, when you're not in the feed.
>
> *(point at the bottom row)*
>
> Now the business reality. Who can actually build this?
>
> The platform could build all three **tomorrow**. It already has every number we used. An outside company can only do the morning report, from the data you're legally allowed to download under GDPR. It can't get inside the app.
>
> So the platform can do it, and doesn't. That's exactly the gap Lu showed in the law.

## Closing (about 15 seconds)

> We didn't build a better recommender. We built a **mirror**.
>
> The platform knows exactly what you consumed, to the second, and never shows you. Food companies had to print the label. We think video platforms should too.
>
> **If the casino won't hang a clock, we just built one.** Thank you.

---

## Cheat card (print this, keep it in your hand)

```
OPEN    juice bottle → "can you read what was in your scrolling?"
S21     76 vs 77 videos → 39% one topic vs 10%  → SAME CALORIES, DIFFERENT DIET
APP     calories / ingredients / sugar (replays ¼ of all time) / longest sitting
        heavy viewer: 137 a day, 341 in a row
        AI: COUNTED BY CODE, AI ONLY TALKS → it made mistakes → fixed + fact check (101/101)
S22     NOW · AT YOUR LIMIT · TOMORROW MORNING
        platform could do it tomorrow; outsiders only the morning report (GDPR)
CLOSE   "not a better recommender, a mirror" → "we just built the clock"
```

## Before you start (30-second checklist)

- Open `01_label_prototype.html` in a browser tab **before** the talk, on "The narrow diet".
- Don't use the dropdown of shared users (their data is incomplete).
- The app works offline, so there's no Wi-Fi risk.

## Three likely questions, with short answers

**"Is the data reliable?"**
> It's real Kuaishou data published for research. One limit: the dataset only logs part of each person's viewing, so we trust the counts and percentages, not the minutes. That's why the label shows videos per day, not hours.

**"Why would a platform ever do this? It would lose watch time."**
> Maybe a little. But regulation is moving that way: the EU is already investigating addictive design. Food companies also didn't print labels voluntarily. And trust is a business asset too.

**"Couldn't the AI give wrong advice?"**
> It did, at first. That's why it only sees the label numbers, never your history, and why every summary is automatically checked. The AI explains; it never decides.
