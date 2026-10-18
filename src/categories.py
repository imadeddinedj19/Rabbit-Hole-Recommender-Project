"""One category per video, for the diversity metric (plan step 1.5).

Usage:
    from categories import load_categories
    cats = load_categories()   # columns: video_id, category_id, category

We use the first-level category from kuairec_caption_category.csv: exactly
one per video, with readable names. KuaiRec ships the names in Chinese, so
they are translated here (matplotlib has no Chinese font by default, and the
report is in English). "Other" and "Unknown" are kept as categories of their
own: they are what the platform itself assigned.
"""

import pandas as pd

from sample import find_csv

ENGLISH_NAMES = {
    1: "Dance",                     # 舞蹈
    2: "Music",                     # 音乐
    3: "Gaming",                    # 游戏
    4: "Beauty & makeup",           # 美妆
    5: "Fashion",                   # 时尚
    6: "Celebrities",               # 明星娱乐
    7: "Sports",                    # 运动
    8: "Good looks",                # 颜值
    9: "Comedy",                    # 喜剧
    10: "Travel",                   # 旅游
    11: "Lifestyle",                # 生活
    12: "Food",                     # 美食
    13: "Rural life",               # 三农
    14: "Education",                # 教育
    15: "Arts",                     # 艺术
    16: "Health",                   # 健康
    17: "Pets",                     # 宠物
    18: "Cars",                     # 汽车
    19: "Relationships",            # 情感
    20: "Anime & manga",            # 二次元
    21: "Culture & history",        # 人文
    22: "Finance",                  # 财经
    23: "Politics",                 # 时政资讯
    24: "Astrology",                # 星座命理
    25: "Parenting",                # 亲子
    26: "Photography",              # 摄影
    27: "Tech & gadgets",           # 高新数码
    28: "Local news",               # 民生资讯
    29: "Science & law",            # 科学与法律
    31: "Fitness",                  # 健身
    32: "Short drama",              # 短剧
    33: "Selfies",                  # 自拍
    34: "Other",                    # 其他
    35: "Military",                 # 军事
    36: "Home & real estate",       # 房产家居
    37: "Oddities",                 # 奇人异象
    38: "Books",                    # 读书
    39: "Film & TV",                # 影视综
    -124: "Unknown",                # UNKNOWN
}


def load_categories():
    """video_id -> first-level category, one row per video (10,728 videos)."""
    df = pd.read_csv(
        find_csv("kuairec_caption_category.csv"),
        usecols=["video_id", "first_level_category_id"],
        dtype=str,
        engine="python",  # the C parser fails on some multi-line captions
    )
    # A few captions contain line breaks that split a row in two. The second
    # halves have no numeric video_id, so they are easy to drop. The first
    # halves (4 videos) lose their category, so they become "Unknown".
    df = df[df["video_id"].str.fullmatch(r"\d+", na=False)]

    cats = pd.DataFrame({
        "video_id": df["video_id"].astype("int32"),
        "category_id": df["first_level_category_id"].astype(float).fillna(-124).astype("int16"),
    })
    cats["category"] = cats["category_id"].map(ENGLISH_NAMES)
    assert cats["video_id"].is_unique, "More than one category row for some video."
    assert cats["category"].notna().all(), "A category id has no English name."
    return cats.reset_index(drop=True)
