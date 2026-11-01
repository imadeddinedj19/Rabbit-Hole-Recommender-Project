# %% [markdown]
# # Part 4 - Video Nutrition Label (KuaiRec)
# **Author:** Imad eddine Djehlane
#
# **What this notebook does.** Food has an ingredient label. Short video has nothing. This notebook builds a
# "video nutrition label" for every user in KuaiRec: how many videos they watch per day, what the time is
# made of (categories = "ingredients"), how much is replays ("added sugar"), night viewing and the longest
# binge. It then writes a short plain-language summary with a language model and builds a clickable
# prototype (`label_prototype.html`) that opens in any browser.
#
# **How to use (Google Colab).** colab.research.google.com -> File -> Upload notebook. Run the cells from top
# to bottom (Shift+Enter). The only settings you may change are marked `<<< EDIT`. Without a Gemini key the
# notebook still runs: the summary is then a rule-based text, and it says so.
#
# **Data.** KuaiRec (Gao et al., 2022, CIKM '22). We use `big_matrix.csv` (natural viewing, with timestamps
# and play time) and `kuairec_caption_category.csv` (one category per video). `small_matrix.csv` is used
# only to rebuild the same 100-user sample as Roles 2 and 3 (seed 42).

# %% [markdown]
# ## Step 0 - Settings

# %%
import os, re, json, glob, time, getpass, html
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

SEED = 42                 # same as Roles 2 and 3
N_USERS = 100             # same shared sample as Roles 2 and 3
SESSION_GAP_MIN = 30      # a pause of 30+ minutes starts a new "sitting" (common web-analytics convention)
NIGHT_HOURS = range(0, 6) # 00:00-05:59, platform clock in the data
SKIP_RATIO = 0.25         # "quick swipe" = less than a quarter of the video watched
TOP_INGREDIENTS = 8       # categories shown by name on the label (8 = most colours a reader can tell apart)

USE_GEMINI = True         # <<< EDIT: False = skip Gemini and keep the summaries already saved in ai_summaries.json
# The key is NEVER written in this notebook: you paste it when asked (or set the GEMINI_API_KEY environment variable).
# Get a free key at aistudio.google.com/apikey. Press Enter without a key to skip Gemini.
GEMINI_MODELS = ["gemini-3.1-flash-lite", "gemini-3-flash-preview", "gemini-flash-latest"]
OUT = Path(os.environ.get("LABEL_OUT", "label_outputs"))   # where every output file goes
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "figures").mkdir(exist_ok=True)
print("Outputs go to:", OUT.resolve())

# %% [markdown]
# ## Step 1 - Find or download the data
# If the download fails, download `KuaiRec.zip` by hand from https://zenodo.org/records/18164998, upload it in
# the Colab file panel (left side) and run this cell again.

# %%
SEARCH_ROOTS = [os.environ.get("KUAIREC_DIR", ""), ".", "data/raw", "../data/raw", "../../data/raw"]

def find_file(name):
    for root in SEARCH_ROOTS:
        if root and os.path.isdir(root):
            hits = sorted(glob.glob(os.path.join(root, "**", name), recursive=True))
            if hits:
                return hits[0]
    return None

if not find_file("big_matrix.csv"):
    if not os.path.exists("KuaiRec.zip"):
        os.system("wget -q -O KuaiRec.zip 'https://zenodo.org/records/18164998/files/KuaiRec.zip?download=1'")
    os.system("unzip -q -o KuaiRec.zip")
BIG, SMALL, CAP = (find_file(n) for n in ["big_matrix.csv", "small_matrix.csv", "kuairec_caption_category.csv"])
print(BIG, SMALL, CAP, sep="\n")

# %% [markdown]
# ## Step 2 - Load viewing data and categories
# One row of `big_matrix` = one user watched one video once. `play_duration` and `video_duration` are in
# milliseconds. `time` is the platform's clock, `date` is the logging day (28 days between July and September 2020).

# %%
big = pd.read_csv(BIG, usecols=["user_id", "video_id", "play_duration", "video_duration", "time", "date", "timestamp"],
                  dtype={"user_id": "int32", "video_id": "int32", "play_duration": "int64",
                         "video_duration": "int64", "timestamp": "float64", "time": "string", "date": "string"})

# Categories: first-level category, translated (same mapping as src/categories.py in the team repo).
ENGLISH = {1: "Dance", 2: "Music", 3: "Gaming", 4: "Beauty & makeup", 5: "Fashion", 6: "Celebrities",
           7: "Sports", 8: "Good looks", 9: "Comedy", 10: "Travel", 11: "Lifestyle", 12: "Food",
           13: "Rural life", 14: "Education", 15: "Arts", 16: "Health", 17: "Pets", 18: "Cars",
           19: "Relationships", 20: "Anime & manga", 21: "Culture & history", 22: "Finance", 23: "Politics",
           24: "Astrology", 25: "Parenting", 26: "Photography", 27: "Tech & gadgets", 28: "Local news",
           29: "Science & law", 31: "Fitness", 32: "Short drama", 33: "Selfies", 34: "Miscellaneous",   # the platform's own "Other" (其他)
           35: "Military", 36: "Home & real estate", 37: "Oddities", 38: "Books", 39: "Film & TV",
           -124: "Unknown"}
cap = pd.read_csv(CAP, usecols=["video_id", "first_level_category_id"], dtype=str, engine="python")
cap = cap[cap["video_id"].str.fullmatch(r"\d+", na=False)]          # a few captions break rows in two
cats = pd.Series(cap["first_level_category_id"].astype(float).fillna(-124).astype(int).map(ENGLISH).values,
                 index=cap["video_id"].astype(int).values)
big["category"] = big["video_id"].map(cats).fillna("Unknown")
print(f"{len(big):,} views | {big.user_id.nunique():,} users | {big.video_id.nunique():,} videos | "
      f"{big.category.nunique()} categories")

# %% [markdown]
# ## Step 3 - Per-view features
# - **seconds watched** = play time. A video replayed on loop can count more seconds than its length.
# - **replay seconds** ("added sugar") = seconds watched beyond one full play of the video.
# - **quick swipe** = less than a quarter of the video watched.
# - **night** = watched between 00:00 and 05:59 (platform clock).
# - **sitting** (session) = a run of views with no pause of 30 minutes or more.

# %%
big["sec"] = big["play_duration"] / 1000
big["replay_sec"] = (big["play_duration"] - big["video_duration"]).clip(lower=0) / 1000
big["skip"] = big["play_duration"] < SKIP_RATIO * big["video_duration"]
big["hour"] = big["time"].str.slice(11, 13).astype(int)
big["day"] = big["date"]   # the 28 official logging days (0.1% of rows have a "time" outside them)
big["night"] = big["hour"].isin(list(NIGHT_HOURS))
big = big.sort_values(["user_id", "timestamp"]).reset_index(drop=True)
gap = big.groupby("user_id")["timestamp"].diff()
big["sitting"] = (gap.isna() | (gap > SESSION_GAP_MIN * 60)).cumsum()

# How much of the real viewing does KuaiRec log? Within a sitting, compare the logged play time with the
# time between the first and the last logged view. KuaiRec only contains 10,728 videos, so most of what a
# user watched in a sitting is not in the file. "Time in the app" below is therefore estimated from the
# sitting spans (first to last logged view). We tested it and REJECTED it for the label: a pause of up
# to 29 minutes counts as "in the app", so it gives a median of almost 4 hours a day and some 18-hour
# sittings. The label therefore counts videos, and shows logged minutes as a secondary line.
s = big.groupby("sitting").agg(t0=("timestamp", "min"), t1=("timestamp", "max"),
                               last=("sec", "last"), played=("sec", "sum"))
s["span_min"] = ((s["t1"] - s["t0"]) + s["last"]) / 60
COVERAGE = float(s["played"].sum() / (s["span_min"].sum() * 60))
print(f"Logged play time = {COVERAGE:.1%} of the time between first and last view of each sitting")

# %% [markdown]
# ## Step 4 - One label per user (all 7,176 users)

# %%
def ingredients(g):
    by_cat = g.groupby("category")["sec"].sum().sort_values(ascending=False)
    share = by_cat / by_cat.sum()
    n80 = int((share.cumsum() < 0.8).sum() + 1)          # categories needed to reach 80% of the time
    return share, n80

rows, compositions = [], {}
for uid, g in big.groupby("user_id", sort=True):
    share, n80 = ingredients(g)
    days = g["day"].nunique()
    sit = g.groupby("sitting").size()
    longest = int(sit.max())
    longest_day = g.loc[g["sitting"] == sit.idxmax(), "day"].iloc[0]
    tot = g["sec"].sum()
    spans = s.loc[sit.index, "span_min"]
    rows.append({"user_id": int(uid), "days": days, "videos_per_day": len(g) / days,
                 "minutes_per_day": tot / 60 / days, "app_minutes_per_day": float(spans.sum()) / days,
                 "longest_sitting_minutes": float(spans.loc[sit.idxmax()]), "top_category": share.index[0],
                 "top_share": float(share.iloc[0]), "cats_for_80": n80, "cats_total": int(len(share)),
                 "replay_share": float(g["replay_sec"].sum() / tot) if tot else 0.0,
                 "night_share": float(g.loc[g["night"], "sec"].sum() / tot) if tot else 0.0,
                 "skip_share": float(g["skip"].mean()), "longest_sitting": longest,
                 "longest_sitting_day": longest_day, "sittings_per_day": len(sit) / days})
    compositions[int(uid)] = share
labels = pd.DataFrame(rows).set_index("user_id")

# IMPORTANT data trap. The 1,411 small-matrix users have an INCOMPLETE history in big_matrix: KuaiRec moved
# their views of the 3,327 small-matrix videos out of big_matrix (that is the test set). They look like
# very light viewers (median ~15 videos a day vs ~82 for everyone else). So the reference population for
# every comparison is the 5,765 users with a complete history ("complete" below).
small_users = set(pd.read_csv(SMALL, usecols=["user_id"])["user_id"].unique())
labels["complete"] = ~labels.index.isin(small_users)
ref = labels[labels["complete"]]
print(labels.groupby("complete")["videos_per_day"].median().rename("median videos/day"))

# Where does each user sit compared with the complete users? 0.82 = "higher than 82% of users".
METRICS = ["videos_per_day", "minutes_per_day", "top_share", "cats_for_80", "replay_share",
           "night_share", "skip_share", "longest_sitting"]
for m in METRICS:
    sv = np.sort(ref[m].values)
    labels[m + "_pct"] = (np.searchsorted(sv, labels[m].values, "left") +
                          np.searchsorted(sv, labels[m].values, "right")) / 2 / len(sv)
ref = labels[labels["complete"]]
labels.round(4).to_csv(OUT / "labels_all_users.csv")
labels[METRICS].describe(percentiles=[.1, .5, .9]).round(3)

# %% [markdown]
# ## Step 5 - Population findings (for the report)

# %%
# All population numbers use the complete users only (see the data trap in Step 4).
refv = big[big["user_id"].isin(ref.index)]
pop = {"n_users": int(len(ref)), "n_users_all": int(len(labels)), "n_views": int(len(refv)),
       "coverage": COVERAGE, "n_days_in_data": int(big["day"].nunique()),
       "small_users_median_videos_per_day": float(labels.loc[~labels["complete"], "videos_per_day"].median()),
       "small_users_median_longest_sitting": float(labels.loc[~labels["complete"], "longest_sitting"].median())}
for m in METRICS:
    pop[m] = {q: float(ref[m].quantile(v)) for q, v in [("p10", .1), ("p50", .5), ("p90", .9)]}
pop["replay_share_all_time"] = float(refv["replay_sec"].sum() / refv["sec"].sum())
pop["night_share_all_time"] = float(refv.loc[refv["night"], "sec"].sum() / refv["sec"].sum())

# Do heavier users have a narrower diet? Spearman correlation across users.
pop["spearman"] = {m: float(ref["videos_per_day"].corr(ref[m], method="spearman"))
                   for m in ["top_share", "cats_for_80", "replay_share", "night_share", "skip_share"]}
ref = ref.assign(volume_band=pd.qcut(ref["videos_per_day"], 5, labels=["lightest 20%", "2", "3", "4", "heaviest 20%"]))
bands = ref.groupby("volume_band", observed=True).agg(
    videos_per_day=("videos_per_day", "median"), top_share=("top_share", "median"),
    cats_for_80=("cats_for_80", "median"), replay_share=("replay_share", "median"),
    night_share=("night_share", "median"))
bands.round(3).to_csv(OUT / "volume_bands.csv")

# Ingredient table: what each category is "made of".
cat_tab = refv.groupby("category").agg(time_share=("sec", "sum"), replay_sec=("replay_sec", "sum"),
                                      skip_rate=("skip", "mean"), views=("sec", "size"))
cat_tab["replay_share"] = cat_tab["replay_sec"] / cat_tab["time_share"]
cat_tab["time_share"] = cat_tab["time_share"] / cat_tab["time_share"].sum()
cat_tab = cat_tab.drop(columns="replay_sec").sort_values("time_share", ascending=False)
cat_tab.round(4).to_csv(OUT / "category_ingredients.csv")
hours = (refv.groupby("hour")["sec"].sum() / refv["sec"].sum())
pop["hour_share"] = {int(h): float(v) for h, v in hours.items()}
pop["peak_hour"], pop["low_hour"] = int(hours.idxmax()), int(hours.idxmin())
pop["rejected_app_minutes_per_day_p50"] = float(ref["app_minutes_per_day"].median())
pop["rejected_longest_sitting_minutes_max"] = float(ref["longest_sitting_minutes"].max())
del refv
print(json.dumps(pop["spearman"], indent=1))
bands.round(3)

# %%
ORANGE, INK, MUTED, GRID = "#e85d26", "#1f1f1c", "#77776f", "#e4e2dc"
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.titleweight": "bold", "axes.titlesize": 13})

# Figure 1: how many videos per day do users watch?
fig, ax = plt.subplots(figsize=(8, 4))
v = ref["videos_per_day"].clip(upper=300)
ax.hist(v, bins=60, color=ORANGE, edgecolor="white", linewidth=0.5)
med = ref["videos_per_day"].median()
ax.axvline(med, color=INK, lw=1.5, ls="--")
ax.text(med + 4, ax.get_ylim()[1] * 0.9, f"median user: {med:.0f} videos a day", color=INK)
ax.set_xlabel("Logged videos per active day (5,765 users with a complete history; above 300 shown at 300)")
ax.set_ylabel("Number of users")
ax.set_title("Most users watch dozens of logged videos a day, a few watch hundreds")
fig.tight_layout(); fig.savefig(OUT / "figures/fig1_videos_per_day.png", dpi=200); plt.show()

# Figure 2: replays ("added sugar") by category, top 15 categories by time.
top15 = cat_tab.head(15).sort_values("replay_share")
fig, ax = plt.subplots(figsize=(8, 5.2))
ax.barh(top15.index, top15["replay_share"] * 100, color=ORANGE, height=0.6)
ax.axvline(pop["replay_share_all_time"] * 100, color=INK, lw=1.5, ls="--")
ax.text(pop["replay_share_all_time"] * 100 + 0.3, -0.9, f"all videos: {pop['replay_share_all_time']:.0%}", color=INK)
ax.set_xlabel("Share of watch time that is replay (% of seconds beyond one full play)")
ax.set_title("'Added sugar': how much of each category's time is replays")
ax.grid(axis="x", color=GRID); ax.set_axisbelow(True)
fig.tight_layout(); fig.savefig(OUT / "figures/fig2_replay_by_category.png", dpi=200); plt.show()

# Figure 3: heavier users vs. how narrow their diet is.
fig, ax = plt.subplots(figsize=(8, 4))
x = np.arange(len(bands))
ax.bar(x, bands["top_share"] * 100, color=ORANGE, width=0.6)
for i, (vpd, ts) in enumerate(zip(bands["videos_per_day"], bands["top_share"])):
    ax.text(i, ts * 100 + 0.6, f"{ts:.0%}", ha="center", color=INK)
ax.set_xticks(x, [f"{b}\n(~{vpd:.0f} videos/day)" for b, vpd in zip(bands.index, bands["videos_per_day"])])
ax.set_ylabel("Median share of time in\nthe user's top category (%)")
ax.set_title("Heavier users do not have a narrower diet")
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
fig.tight_layout(); fig.savefig(OUT / "figures/fig3_volume_vs_concentration.png", dpi=200); plt.show()

# Figure 4: time of day.
fig, ax = plt.subplots(figsize=(8, 3.6))
colors = [ORANGE if h in NIGHT_HOURS else "#c9c6bd" for h in hours.index]
ax.bar(hours.index, hours.values * 100, color=colors, width=0.75)
ax.set_xticks(range(0, 24, 2)); ax.set_xlabel("Hour of day (platform clock in the data)")
ax.set_ylabel("% of all watch time")
ax.set_title("When the logged viewing happens (orange = our 'night' window, 00:00-05:59)")
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
fig.tight_layout(); fig.savefig(OUT / "figures/fig4_hour_of_day.png", dpi=200); plt.show()

# %% [markdown]
# ## Step 6 - The shared 100-user sample (identical to Roles 2 and 3)
# Same code as the Role 3 notebook: users drawn from `small_matrix` with seed 42, kept only if they have at
# least one liked video (watch_ratio > 2) with a caption entry. We also pick three contrasting "demo users"
# by a fixed rule, so nobody can say we cherry-picked.

# %%
small = pd.read_csv(SMALL, usecols=["user_id", "video_id", "watch_ratio"])   # only to rebuild the shared sample
users = sorted(small.user_id.unique())
sample = np.random.RandomState(SEED).choice(users, N_USERS, replace=False)
has_like = set(small[small.video_id.isin(cats.index) & (small.watch_ratio > 2)].user_id.unique())
shared = [int(u) for u in sample if int(u) in has_like]
del small
print(len(shared), "shared users")
print("Shared users, median videos/day:", round(labels.loc[shared, "videos_per_day"].median(), 1),
      "| complete users:", round(ref["videos_per_day"].median(), 1))
pop["shared_median_videos_per_day"] = float(labels.loc[shared, "videos_per_day"].median())
pop["shared_max_videos_per_day"] = float(labels.loc[shared, "videos_per_day"].max())
json.dump(pop, open(OUT / "population_summary.json", "w"), indent=2)

# Demo users are chosen from the complete users, by a fixed rule, among users with a typical amount of viewing
# (between the 40th and 60th percentile of videos per day), so the three labels are comparable.
# Why not from the shared 100? They are all light viewers in big_matrix (see the report): KuaiRec removed
# their small-matrix videos from their big-matrix history, so their labels miss part of their viewing.
typical = ref[ref["videos_per_day"].between(ref["videos_per_day"].quantile(.4),
                                            ref["videos_per_day"].quantile(.6))]
narrow = int(typical["top_share"].idxmax())                                   # narrowest diet
broad = int(typical["top_share"].idxmin())                                    # broadest diet
heavy = int((ref["videos_per_day"] - ref["videos_per_day"].quantile(.95)).abs().idxmin())  # p95 viewer
DEMO = {narrow: "The narrow diet", broad: "The broad diet", heavy: "The heavy viewer"}
print(DEMO)

# %% [markdown]
# ## Step 7 - The label as data, and the AI summary
# The language model only ever sees the numbers on the label (no raw history), and is told to stay neutral:
# no diagnosis, no moralising, only numbers from the input.

# %%
def pct_text(p):
    return f"more than {p:.0%} of users" if p >= 0.5 else f"less than {1 - p:.0%} of users"

shared_set = set(shared)

def label_dict(uid):
    r = labels.loc[uid]
    share = compositions[uid]
    top = share.head(TOP_INGREDIENTS)
    ing = [{"name": c, "share": round(float(v), 4)} for c, v in top.items()]
    rest = 1 - float(top.sum())
    if rest > 0.0005:
        tail = share.iloc[TOP_INGREDIENTS:]
        ing.append({"name": f"All other topics ({len(tail)} categories, each under {np.ceil(tail.max() * 100):.0f}%)",
                    "share": round(rest, 4)})
    d = {"user_id": int(uid), "persona": DEMO.get(uid, ""), "days": int(r.days),
         "videos_per_day": round(float(r.videos_per_day), 1), "minutes_per_day": round(float(r.minutes_per_day), 1),
         "shared_sample": int(uid) in shared_set, "complete": bool(r.complete),
         "top_category": r.top_category, "top_share": round(float(r.top_share), 3),
         "cats_for_80": int(r.cats_for_80), "cats_total": int(r.cats_total),
         "replay_share": round(float(r.replay_share), 3), "night_share": round(float(r.night_share), 3),
         "skip_share": round(float(r.skip_share), 3), "longest_sitting": int(r.longest_sitting),
         "longest_sitting_day": r.longest_sitting_day, "sittings_per_day": round(float(r.sittings_per_day), 1),
         "ingredients": ing}
    d["pct"] = {m: round(float(r[m + "_pct"]), 3) for m in METRICS}
    return d

# Prompt v2. Version 1 sent bare numbers ("longest_sitting": 10, "night_share": 0.9) and Gemini made errors:
# it called 10 videos "10 minutes" and turned "higher than 90% of users" into "90% more than other users".
# v2 sends every fact as a labelled line with its unit and a ready-made comparison, and marks the most
# unusual line, so the model only has to phrase, not interpret. (v1 outputs: gemini_prompt_v1_examples.json)
PROMPT = """You write the summary on a "video nutrition label" for a short-video app user.
Facts about this user (averages over {days} days of viewing; "typical" = the median user):
{facts}

Write exactly 3 short sentences in plain English, speaking to the user as "you".
1. What the viewing is mostly made of: name the top 2 or 3 categories with their %.
2. The fact marked [MOST UNUSUAL], in your own natural words, keeping its number, the typical value and
   the comparison exactly (for example "higher than 96% of users").
3. One gentle, optional suggestion that helps the user notice or limit their viewing (for example a break,
   a time limit, or trying a new topic), phrased as a choice. Use no numbers in this sentence, and never
   suggest watching more or for longer.
Rules: copy numbers and units exactly as written above; never convert units; never write "percentile";
never write "X% more than other users"; no medical or psychological claims; no moralising;
no word "addiction"; under 70 words. Reply with the 3 sentences only."""

def compare(p):
    share = p if p >= 0.5 else 1 - p
    who = "almost all users" if share >= 0.995 else f"{share:.0%} of users"
    return ("higher than " if p >= 0.5 else "lower than ") + who

def prompt_for(d):
    P, q = d["pct"], {m: pop[m]["p50"] for m in METRICS}
    lines = {
        "videos_per_day": f"Videos per day: {d['videos_per_day']:.0f} (typical: {q['videos_per_day']:.0f}); {compare(P['videos_per_day'])}",
        "top_share": f"Share of time in the top category ({d['top_category']}): {d['top_share']:.0%} "
                     f"(typical: {q['top_share']:.0%}); {compare(P['top_share'])}",
        "replay_share": f"Replays (seconds re-watched after a video already played once): {d['replay_share']:.0%} of watch time "
                        f"(typical: {q['replay_share']:.0%}); {compare(P['replay_share'])}",
        "night_share": f"Night viewing (00:00-05:59): {d['night_share']:.0%} of watch time (typical: {q['night_share']:.0%}); "
                       f"{compare(P['night_share'])}",
        "skip_share": f"Quick swipes (left before a quarter of the video): {d['skip_share']:.0%} of videos "
                      f"(typical: {q['skip_share']:.0%}); {compare(P['skip_share'])}",
        "longest_sitting": f"Longest sitting: {d['longest_sitting']} videos in a row without a 30-minute break "
                           f"(typical: {q['longest_sitting']:.0f} videos); {compare(P['longest_sitting'])}",
    }
    # Users with an incomplete history (test-set users) have deflated counts, so only shares can stand out.
    allowed = lines if d.get("complete", True) else [k for k in lines if k.endswith("_share")]
    top = max(allowed, key=lambda k: abs(P[k] - 0.5))
    ing = ", ".join(f"{g['name']} {g['share']:.0%}" for g in d["ingredients"])
    facts = [f"- What the watch time is made of: {ing}",
             f"- Variety: 80% of the time is spread over {d['cats_for_80']} of 39 categories (typical: {q['cats_for_80']:.0f})"]
    facts += [f"- {v}" + ("  [MOST UNUSUAL]" if k == top else "") for k, v in lines.items()]
    return PROMPT.format(days=d["days"], facts="\n".join(facts))

def rule_summary(d):
    a, b = d["ingredients"][0], d["ingredients"][1]
    s1 = (f"About {a['share']:.0%} of your viewing time goes to {a['name']} and {b['share']:.0%} to {b['name']}, "
          f"across {d['videos_per_day']:.0f} videos a day.")
    standouts = {"videos_per_day": f"you watch more videos a day than {d['pct']['videos_per_day']:.0%} of users",
                 "top_share": f"your top category takes a bigger share of your time than for {d['pct']['top_share']:.0%} of users",
                 "replay_share": f"{d['replay_share']:.0%} of your time is replays, more than for {d['pct']['replay_share']:.0%} of users",
                 "night_share": f"{d['night_share']:.0%} of your time is between midnight and 6 am, more than for {d['pct']['night_share']:.0%} of users",
                 "longest_sitting": f"your longest sitting was {d['longest_sitting']} videos without a 30-minute break"}
    key = max(standouts, key=lambda k: d["pct"][k])
    s2 = "What stands out: " + standouts[key] + "."
    if d["pct"]["top_share"] < 0.25:
        s2 = f"What stands out: your mix is broad, with 80% of your time spread over {d['cats_for_80']} categories."
        return " ".join([s1, s2, "If you want, you could check this label now and then to see if it stays that way."])
    s3 = {"videos_per_day": "If you want, you could set a daily video budget and see how it feels.",
          "top_share": "If you want, you could follow one new topic this week and see if your feed widens.",
          "replay_share": "If you want, you could turn off autoplay loops for a week.",
          "night_share": "If you want, you could set a quiet-hours reminder after midnight.",
          "longest_sitting": "If you want, you could set a gentle break reminder every 30 minutes."}[key]
    return " ".join([s1, s2, s3])

SUMMARY_FILE = OUT / "ai_summaries.json"
summaries = json.load(open(SUMMARY_FILE, encoding="utf-8")) if SUMMARY_FILE.exists() else {}

def ask_gemini(client, prompt):
    """Try each model in GEMINI_MODELS; wait and retry when the free tier says 'too many requests' (429)."""
    for model in GEMINI_MODELS:
        for attempt in range(4):
            try:
                r = client.models.generate_content(model=model, contents=prompt)
                time.sleep(4)          # stay under the free rate limit
                return (r.text or "").strip(), model
            except Exception as e:
                msg = str(e)
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    print("rate limit, waiting", 20 * (attempt + 1), "s"); time.sleep(20 * (attempt + 1)); continue
                print(model, "failed:", msg[:120]); break
    return "", None

API_KEY = os.environ.get("GEMINI_API_KEY", "")
if USE_GEMINI and not API_KEY:
    API_KEY = getpass.getpass("Paste your FREE Gemini API key and press Enter (or just Enter to skip): ").strip()
if USE_GEMINI and API_KEY:
    from google import genai   # installed by the pip cell at the top
    client = genai.Client(api_key=API_KEY)
    todo = [u for u in list(DEMO) + [u for u in shared if u not in DEMO]
            if not summaries.get(str(u), {}).get("source", "").startswith("Gemini")]
    print(len(todo), "summaries to write with Gemini (about 5 seconds each)")
    for i, uid in enumerate(todo, 1):
        text, model = ask_gemini(client, prompt_for(label_dict(uid)))
        if text:
            summaries[str(uid)] = {"text": text, "source": f"Gemini ({model}), free API"}
        if i % 10 == 0 or i == len(todo):
            json.dump(summaries, open(SUMMARY_FILE, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            print(i, "/", len(todo), "done")
    for uid in DEMO:
        print(f"\n{DEMO[uid]} (user {uid}):", summaries.get(str(uid), {}).get("text", "(none)"))

else:
    print("Gemini skipped: the prototype uses the summaries already saved in", SUMMARY_FILE)

# Fact check (a simple guardrail): every number in an AI summary must also appear in the facts the model
# was given. It catches invented numbers, not every wrong sentence, so we still read the demo summaries.
NUM = re.compile(r"\d+(?:\.\d+)?")
checked = bad = 0
for uid, entry in summaries.items():
    if int(uid) not in labels.index:
        continue
    allowed = set(NUM.findall(prompt_for(label_dict(int(uid)))))
    extra = [n for n in NUM.findall(entry["text"]) if n not in allowed]
    entry["number_check"] = "ok" if not extra else "numbers not on the label: " + ", ".join(extra)
    checked += 1; bad += bool(extra)
json.dump(summaries, open(SUMMARY_FILE, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(f"Fact check: {checked - bad} of {checked} summaries use only numbers from the label")

print("Example prompt:\n", prompt_for(label_dict(narrow)))

# %% [markdown]
# ## Step 8 - Build the clickable prototype (`label_prototype.html`)
# One self-contained HTML file: open it in any browser, no installation, no internet needed (fonts fall back).

# %%
cards = []
for uid in list(DEMO) + [u for u in shared if u not in DEMO]:
    d = label_dict(uid)
    ai = summaries.get(str(uid))
    d["summary"] = ai["text"] if ai else rule_summary(d)
    d["summary_source"] = ai["source"] if ai else "Rule-based text (no AI key was used for this user)"
    if ai and ai.get("number_check") == "ok":
        d["summary_source"] += " · fact check passed: every number is on the label"
    elif ai and ai.get("number_check"):
        d["summary_source"] += " · fact check: " + ai["number_check"]
    cards.append(d)
payload = {"users": cards, "pop": {m: pop[m] for m in METRICS}, "n_users": pop["n_users"],
           "coverage": pop["coverage"], "n_days": pop["n_days_in_data"],
           "shared_median": pop["shared_median_videos_per_day"]}
json.dump(payload, open(OUT / "labels_shared_users.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)

TEMPLATE_PATH = find_file("label_template.html") or "label_template.html"
template = open(TEMPLATE_PATH, encoding="utf-8").read()
page = template.replace("/*__DATA__*/null", json.dumps(payload, ensure_ascii=False))
open(OUT / "label_prototype.html", "w", encoding="utf-8").write(page)
print("Saved", OUT / "label_prototype.html", "- download it from the file panel and open it in a browser.")
