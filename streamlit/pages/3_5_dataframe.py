import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colors import Normalize
import numpy as np


# ─────────────────────────────
# 基本設定
# ─────────────────────────────
st.set_page_config(page_title="個人 × 時段 Diff Heatmap", layout="wide")

BASE_DIR = Path(__file__).resolve().parents[2]   # 指到 main
DB_PATH = BASE_DIR / "database" / "calculate_data.db"



def diff_to_color(v):
    try:
        v = float(v)
    except:
        return ""

    # 顏色定義（低彩度）
    POS_COLOR = (120, 180, 140)   # 綠（柔）
    NEG_COLOR = (220, 120, 120)   # 紅（柔）

    # 0 = 白
    if v == 0:
        return "background-color: #ffffff"

    # 正值：0 ~ 100 漸層，>=100 飽和
    if v > 0:
        ratio = min(v / 100.0, 1.0)
        r = int(255 + ratio * (POS_COLOR[0] - 255))
        g = int(255 + ratio * (POS_COLOR[1] - 255))
        b = int(255 + ratio * (POS_COLOR[2] - 255))
        return f"background-color: rgb({r},{g},{b})"

    # 負值：0 ~ -50 漸層，<=-50 飽和
    else:
        ratio = min(abs(v) / 100.0, 1.0)
        r = int(255 + ratio * (NEG_COLOR[0] - 255))
        g = int(255 + ratio * (NEG_COLOR[1] - 255))
        b = int(255 + ratio * (NEG_COLOR[2] - 255))
        return f"background-color: rgb({r},{g},{b})"


# 紅 → 白 → 綠（無黃色）
RED_WHITE_GREEN = LinearSegmentedColormap.from_list(
    "red_white_green",
    ["#d73027", "#ffffff", "#1a9850"]
)




# ─────────────────────────────
# 工具：時間排序（12:00 → 23:45 → 00:00 → 11:45）
# ─────────────────────────────
def time_sort_key(t):
    hour, minute = map(int, t.split(":"))
    return hour * 60 + minute + (1440 if hour < 12 else 0)

@st.cache_data
def load_streamer_order():
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("""
            SELECT channel_id, channel_name, id
            FROM streamer
            ORDER BY id
        """, conn)

    return df



# ─────────────────────────────
# 讀資料
# ─────────────────────────────
@st.cache_data
def load_platform_df(table, diff_col_name):
    with sqlite3.connect(DB_PATH) as conn:
        
        df = pd.read_sql(f"""
            SELECT
                channel_id,
                channel_name,
                time,
                ROUND(diff_percent, 2) AS {diff_col_name}
            FROM {table}
        """, conn)

    # 缺值補 0
    df = df.fillna(0)

    # 時間排序
    df["sort_key"] = df["time"].apply(time_sort_key)
    df.sort_values("sort_key", inplace=True)

    # pivot 成 heatmap 形式
    heat = df.pivot(
        index="channel_id",
        columns="time",
        values=diff_col_name
    ).fillna(0)
    


    # 依排序後時間重新排欄位
    heat = heat[df["time"].drop_duplicates()]


    # 套用 streamer 表定義的人物順序
    streamer_df = load_streamer_order()

    heat = heat.reindex(
        index=[cid for cid in streamer_df["channel_id"] if cid in heat.index]
    )
    
    heat.index = heat.index.map(
        streamer_df.set_index("channel_id")["channel_name"]
    )
    
    return heat






# ─────────────────────────────
# UI
# ─────────────────────────────
st.title("🔥 個人 × 時段 Diff 熱度圖")

# ────────────── YT ──────────────
st.markdown("### 🔴 YouTube（YT Diff）")

yt_heat = load_platform_df(
    "yt_time_profile",
    "yt_diff"
)

tw_heat = load_platform_df(
    "tw_time_profile",
    "tw_diff"
)

max_abs = max(
    yt_heat.abs().max().max(),
    tw_heat.abs().max().max()
)


if yt_heat.empty:
    st.warning("YT 沒有資料")
else:
    st.dataframe(
        yt_heat.style
            .applymap(diff_to_color)
            .format("{:.2f}"),
        width=900
    )

# ────────────── TW ──────────────
st.markdown("### 🟣 Twitch（TW Diff）")

if tw_heat.empty:
    st.warning("TW 沒有資料")
else:
    st.dataframe(
        tw_heat.style
            .applymap(diff_to_color)
            .format("{:.2f}"),
        width=900,
        height=425
    )
