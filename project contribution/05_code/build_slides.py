"""Fill the Part 4 slots (slides 21 and 22) of the team deck "No clocks in the casino".

Usage (from this folder):
    python build_slides.py "<path to no_clocks_in_the_casino.html>"

Reads the label numbers from ../06_results/ and writes to ../02_slides/:
    part4_sections_to_paste.html   the two <section> blocks (+ one optional backup slide) for Lu to paste
    deck_with_part4_filled.html    the whole deck with the two slots replaced, to preview in context

All numbers on the slides come from the results files, so re-running the notebook and then this script
keeps the slides in sync with the data.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE.parent / "06_results"
OUT = HERE.parent / "02_slides"
OUT.mkdir(exist_ok=True)

data = json.load(open(RES / "labels_shared_users.json", encoding="utf-8"))
pop = json.load(open(RES / "population_summary.json", encoding="utf-8"))
users = {u["persona"]: u for u in data["users"] if u["persona"]}
narrow, broad, heavy = users["The narrow diet"], users["The broad diet"], users["The heavy viewer"]
COLORS = ["#e85d26", "#1aa3ad", "#b8860b", "#8b72d6", "#d95f8f", "#5c5c54"]   # validated for CVD on #111
PRESENTER = "Imad eddine Djehlane"
pct = lambda x: f"{round(x * 100)}%"

BOTTLE = ("M80 20 H120 V70 Q120 90 150 105 Q170 115 170 140 V320 Q170 340 150 340 H50 Q30 340 30 320 "
          "V140 Q30 115 50 105 Q80 90 80 70 Z")


def merged(u):
    """Top 3 categories + one 'Everything else' layer, so slide bottle and legend match exactly."""
    ing = u["ingredients"]
    rest = sum(g["share"] for g in ing[3:])
    return [(g["name"], g["share"], COLORS[i]) for i, g in enumerate(ing[:3])] + [("The rest", rest, COLORS[5])]


def bottle_svg(u, cid):
    top, bottom = 132, 340
    y, rects = bottom, []
    for name, share, color in merged(u):
        g = {"share": share}
        h = g["share"] * (bottom - top)
        y -= h
        rects.append(f'<rect x="0" y="{y:.1f}" width="200" height="{h:.1f}" fill="{color}" stroke="#111" stroke-width="2"/>')
    return (f'<svg viewBox="0 0 200 360" style="height:40vh;width:auto;display:block" role="img" '
            f'aria-label="Viewing of user {u["user_id"]} by category">'
            f'<defs><clipPath id="{cid}"><path d="{BOTTLE}"/></clipPath></defs>'
            f'<g clip-path="url(#{cid})">{"".join(rects)}</g>'
            f'<path d="{BOTTLE}" fill="none" stroke="var(--c-fg)" stroke-width="3"/>'
            f'<rect x="76" y="10" width="48" height="12" rx="2" fill="var(--c-fg)"/></svg>')


def legend(u):
    rows = []
    for name, share, color in merged(u):
        rows.append(f'<div style="display:grid;grid-template-columns:1vw 1fr auto;gap:0.8vw;align-items:center;'
                    f'padding:0.7vh 0;border-top:1px solid var(--c-border)">'
                    f'<i style="width:1vw;height:1vw;background:{color};border-radius:2px;display:block"></i>'
                    f'<span class="body" style="color:var(--c-fg)">{name}</span>'
                    f'<span class="body" style="font-weight:700;color:var(--c-fg)">{pct(share)}</span></div>')
    return "".join(rows)


def persona_col(u, cid, accent):
    return f'''
            <div style="display:grid;grid-template-columns:auto 1fr;gap:2vw;align-items:end">
              {bottle_svg(u, cid)}
              <div>
                <div class="label" style="color:{'var(--c-accent)' if accent else 'var(--c-fg-2)'};margin-bottom:1vh">{u["persona"]} · user {u["user_id"]}</div>
                <div style="font-family:var(--f-display);font-weight:900;font-size:4.2vw;line-height:.9;letter-spacing:-.03em;color:{'var(--c-accent)' if accent else 'var(--c-fg)'}">{pct(u["top_share"])}</div>
                <div class="caption muted" style="margin:0.8vh 0 2vh">of the time in one category</div>
                {legend(u)}
                <div class="caption muted" style="margin-top:1.2vh">{round(u["videos_per_day"])} videos a day · replays {pct(u["replay_share"])}</div>
              </div>
            </div>'''


videos_same = round((narrow["videos_per_day"] + broad["videos_per_day"]) / 2)
slide21 = f'''      <!-- ═══ 21 · PART 4 · THE LABEL (Imad) ═══ -->
      <section class="slide dark">
        <header class="slide-chrome">
          <span class="label muted">Part 4 · Video nutrition label</span>
          <span class="label muted">21</span>
        </header>
        <div class="slide-body" style="display:grid;grid-template-columns:1fr 2fr;gap:4vw;align-items:center;min-height:0">
          <div>
            <p class="kicker" data-anim="fade-in" data-delay="0">Our proposal</p>
            <div class="rule" data-anim="reveal-right" data-delay="1" style="margin: 1.5vh 0"></div>
            <h2 class="h2" data-anim="fade-up" data-delay="1" style="margin-bottom:3vh">same calories,<br />different diet</h2>
            <p class="lead muted" data-anim="fade-up" data-delay="2">Two real Kuaishou users, about {videos_same} videos a day each.
              A screen-time counter sees two identical users. A label shows what the time is made of.</p>
            <p class="body" data-anim="fade-up" data-delay="3" style="margin-top:2.5vh;color:var(--c-fg)">Each label also shows
              replays, night viewing and the longest sitting, plus a short AI-written summary.</p>
          </div>
          <div data-anim="fade-up" data-delay="2" style="display:grid;grid-template-columns:1fr 1fr;gap:4vw">
            {persona_col(narrow, "b21a", True)}
            {persona_col(broad, "b21b", False)}
          </div>
        </div>
        <footer class="slide-foot">
          <span class="label muted">KuaiRec (Gao et al. 2022) · {pop["n_users"]:,} users, 28 days · demo users picked by a fixed rule</span>
          <span class="label muted">Presenter: {PRESENTER}</span>
        </footer>
      </section>'''


def moment(num, title, body, mock):
    return f'''
            <div style="border-top:1px solid var(--c-border);padding-top:2vh;display:flex;flex-direction:column;gap:1.4vh">
              <div class="broadside-num" style="color:var(--c-accent)">{num}</div>
              <div class="h3" style="font-weight:800">{title}</div>
              <div style="min-height:9vh;display:flex;align-items:center">{mock}</div>
              <p class="body muted" style="margin:0">{body}</p>
            </div>'''


top = narrow["ingredients"][0]
chip = (f'<div class="caption" style="border:1px solid var(--c-accent);border-radius:0.8vw;padding:1vh 1vw;color:var(--c-fg)">'
        f'<b style="color:var(--c-accent)">{round(narrow["videos_per_day"])}</b> videos today · mostly {top["name"]} ({pct(top["share"])})</div>')
stack = "".join(f'<span style="flex:{g["share"]};background:{COLORS[i]}"></span>' for i, g in enumerate(narrow["ingredients"]))
pause = (f'<div class="caption" style="background:var(--c-fg);color:#111;border-radius:0.8vw;padding:1.2vh 1vw;width:100%">'
         f'<b>You reached your limit.</b> Today\'s mix:<div style="display:flex;gap:2px;height:1.2vh;margin:0.8vh 0">{stack}</div>'
         f'<span style="font-weight:700">Stop here</span> &nbsp;·&nbsp; 10 more</div>')
morning = (f'<div class="caption" style="background:var(--c-fg);color:#111;border-radius:0.8vw;padding:1.2vh 1vw;width:100%">'
           f'<b style="font-family:Arial Black,Arial,sans-serif">Yesterday, bottled</b><br>{round(narrow["videos_per_day"])} videos · '
           f'replays {pct(narrow["replay_share"])} · "about {pct(top["share"])} of your time went to {top["name"]}…"</div>')

slide22 = f'''      <!-- ═══ 22 · PART 4 · HOW IT WOULD WORK (Imad) ═══ -->
      <section class="slide dark">
        <header class="slide-chrome">
          <span class="label muted">Part 4 · Video nutrition label</span>
          <span class="label muted">22</span>
        </header>
        <div class="slide-body" style="display:flex;flex-direction:column;justify-content:center;gap:4vh;min-height:0">
          <div style="display:flex;justify-content:space-between;align-items:flex-end;gap:4vw">
            <div>
              <p class="kicker" data-anim="fade-in" data-delay="0">How it would work</p>
              <div class="rule" data-anim="reveal-right" data-delay="1" style="margin: 1.5vh 0"></div>
              <h2 class="h2" data-anim="fade-up" data-delay="1">three moments,<br />one clock</h2>
            </div>
            <p class="lead muted" data-anim="fade-up" data-delay="2" style="max-width:38%">The label informs, it doesn't block. The user sets the limit and decides what happens next.</p>
          </div>
          <div data-anim="fade-up" data-delay="2" style="display:grid;grid-template-columns:repeat(3,1fr);gap:3vw">
            {moment("01 · while scrolling", "a clock in the casino", "A small counter stays on screen. Nothing is blocked: the clock is simply back.", chip)}
            {moment("02 · at your limit", "a pause, not a wall", "At a limit the user chose, the feed pauses and shows what the sitting was made of. One tap continues.", pause)}
            {moment("03 · next morning", "the daily label", "The full label with the AI summary, once a day, when the user is not in the feed.", morning)}
          </div>
          <div data-anim="fade-up" data-delay="3" style="display:grid;grid-template-columns:1fr 1fr;border-top:1px solid var(--c-border)">
            <div style="padding:2vh 2vw 0 0">
              <div class="label" style="color:var(--c-fg);margin-bottom:1vh">A third party (plug-in, independent app) can</div>
              <p class="body muted" style="margin:0">Build moment 03 from the user's own data download (GDPR Art. 15 and 20) · run moment 01 on the web version via a browser plug-in · tag videos by topic with an AI model</p>
            </div>
            <div style="padding:2vh 0 0 2vw;border-left:1px solid var(--c-border)">
              <div class="label" style="color:var(--c-accent);margin-bottom:1vh">Only the platform can</div>
              <p class="body muted" style="margin:0">Show moments 01 and 02 inside the mobile app · see why a video was recommended · change what the feed optimises</p>
            </div>
          </div>
        </div>
        <footer class="slide-foot">
          <span class="label muted">Mock-ups use the numbers of user {narrow["user_id"]} (KuaiRec) · GDPR: Reg. (EU) 2016/679, right of access (Art. 15), data portability (Art. 20)</span>
          <span class="label muted">Presenter: {PRESENTER}</span>
        </footer>
      </section>'''

sp = pop["spearman"]
backup = f'''      <!-- ═══ BACKUP · PART 4 · WHAT THE DATA SAYS (Imad, optional, for questions) ═══ -->
      <section class="slide slide--stats orange">
        <header class="slide-chrome">
          <span class="broadside-num">Backup</span>
          <span class="corner-label">Part 4 · What the viewing data says</span>
        </header>
        <div class="slide-body" style="display:flex;flex-direction:column;justify-content:center;gap:5vh">
          <h2 class="h2" style="color:#111">the label, run on {pop["n_users"]:,} real users</h2>
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-value">{pct(pop["replay_share_all_time"])}</div>
              <div class="stat-label body">of all watch time is replays: seconds watched after a video already played once in full</div>
              <div class="stat-note">The label's "added sugar" line</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">{round(pop["longest_sitting"]["p50"])}</div>
              <div class="stat-label body">videos in the median user's longest sitting without a 30-minute break</div>
              <div class="stat-note">Logged videos only: the real number is higher</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">no</div>
              <div class="stat-label body">heavier users do not have a narrower diet (correlation {sp["top_share"]:+.2f}). They replay and skip less.</div>
              <div class="stat-note">Spearman, videos/day vs. top-category share</div>
            </div>
          </div>
          <p class="lead" style="color:rgba(17,17,17,.8)">KuaiRec logs only part of each user's viewing, so the label relies on counts and shares, not minutes.</p>
        </div>
        <footer class="slide-foot" style="border-color: rgba(17, 17, 17, 0.15)">
          <span class="broadside-num" style="opacity: 0.55">KuaiRec big matrix, 28 days · test-set users excluded (incomplete history)</span>
          <span class="broadside-num" style="opacity: 0.55">Presenter: {PRESENTER}</span>
        </footer>
      </section>'''

(OUT / "part4_sections_to_paste.html").write_text(
    "<!-- Part 4 (Imad eddine Djehlane): replace the two sections marked 'SLOT IMAD 1' and 'SLOT IMAD 2' in the deck\n"
    "     with the first two sections below. The third one is an optional backup slide for questions:\n"
    "     put it after the 'questions?' slide, or leave it out. -->\n\n"
    + slide21 + "\n\n" + slide22 + "\n\n" + backup + "\n", encoding="utf-8")

if len(sys.argv) > 1:
    deck = Path(sys.argv[1]).read_text(encoding="utf-8")
    pat = lambda tag: re.compile(r"      <!-- ═══ \d+ · SLOT IMAD " + tag + r".*?</section>", re.S)
    deck, n1 = pat("1").subn(lambda m: slide21, deck, count=1)
    deck, n2 = pat("2").subn(lambda m: slide22, deck, count=1)
    assert n1 == n2 == 1, "Could not find the SLOT IMAD 1/2 sections in the deck."
    deck = deck.replace("    </div>\n    <!-- /#deck -->", "\n" + backup + "\n\n    </div>\n    <!-- /#deck -->", 1)
    (OUT / "deck_with_part4_filled.html").write_text(deck, encoding="utf-8")
    print("Wrote deck_with_part4_filled.html")
print("Wrote part4_sections_to_paste.html")
