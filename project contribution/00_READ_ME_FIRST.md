# Part 4: Video Nutrition Label (Imad eddine Djehlane)

Everything for Part 4 of "No clocks in the casino" is in this folder. You don't need GitHub, Python or any installation to look at it.

## What to open

| File | What it is | How to open |
| --- | --- | --- |
| `01_label_prototype.html` | **The prototype.** Click between three demo users and see their label, the "bottle", the AI summary and the three moments | Double-click. Opens in any browser (Chrome, Edge, Firefox, Safari) |
| `02_slides/slide21.png`, `slide22.png` | Pictures of my two slides, as they look in the deck | Double-click |
| `02_slides/deck_with_part4_filled.html` | Lu's full deck with my two slides already in slots 21 and 22, plus one backup slide at the end | Double-click, then use the arrow keys |
| `02_slides/part4_sections_to_paste.html` | **For Lu:** the HTML code of my slides, ready to paste into the master deck | Open with a text editor (see "For Lu" below) |
| `03_report_part4.docx` / `.md` | My report section (Word, and the same text as plain text) | Word / any text editor |
| `04_notebook_video_nutrition_label.ipynb` | The full analysis, re-runnable | Google Colab: colab.research.google.com, then File, then Upload notebook. Run the cells top to bottom |
| `06_results/` | All numbers (CSV/JSON files) and the four charts used in the report | Excel / any image viewer |
| `05_code/` | The source code that produces everything above | Only needed to change something |

## For Lu (merging the deck)

Open `02_slides/part4_sections_to_paste.html` in a text editor (Notepad, TextEdit, VS Code). It contains three `<section>` blocks:

1. Replace the section marked `SLOT IMAD 1` in the master deck with the first block (slide 21, "same calories, different diet").
2. Replace the section marked `SLOT IMAD 2` with the second block (slide 22, "three moments, one clock").
3. The third block is an optional backup slide with numbers for questions. Put it after "questions?" or leave it out.

The slides use only the deck's existing styles, so nothing else needs to change. If you'd rather not edit code, `deck_with_part4_filled.html` is your deck with my slides already in place (built from the version you sent on 1 November).

## Could Part 4 be done alone?

**Yes.** Part 4 needs only the KuaiRec data. It doesn't depend on the models from Roles 2 and 3. What I needed from the team, I already had:

- **Lu's deck template**, to make my slides fit (slots 21 and 22).
- **The shared 100-user sample** (seed 42). I rebuilt it with the same code as Maximilian's notebook, so the prototype can show the label for the same users as the AI agent demo.

**Things the team should know:**

- **The 100 shared users can't get a fair label.** KuaiRec removed their test-set viewing from the training data, so they look like very light viewers (median 15 videos a day vs 82 for everyone else). This is correct for Roles 2 and 3 (that's how the test set is built), but my label compares users against the 5,765 users with a complete history instead. Details: report, finding 1.
- **Slide 23 (implementation cost) still has no owner.** My report section 6 already covers what a platform and a third party can and can't build, which could feed into it.
- **Optional link with Roles 2 and 3:** with their top-10 lists per user, I could show a "label of the recommended feed", for example how varied the popularity baseline's picks are compared with the personalised method's. This is a nice extra, not needed.

## Data

The KuaiRec data isn't included (it's 430 MB). The notebook downloads it automatically from https://zenodo.org/records/18164998. Citation: Gao et al. (2022), KuaiRec: A Fully-Observed Dataset and Insights for Evaluating Recommender Systems, CIKM '22.
