import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path
import altair as alt



# ─────────────────────────────
# 基本設定
# ─────────────────────────────
st.set_page_config(page_title="全體時段分析（Global）", layout="wide")

BASE_DIR = Path(__file__).resolve().parents[2]   # 指到 main
DB_PATH = BASE_DIR / "database" / "calculate_data.db"

# ─────────────────────────────
# 工具：時間排序（12:00 → 23:45 → 00:00 → 11:45）
# ─────────────────────────────
def time_sort_key(t):
    hour, minute = map(int, t.split(":"))
    return hour * 60 + minute + (1440 if hour < 12 else 0)


# ─────────────────────────────
# 讀取全體時段資料
# ─────────────────────────────
@st.cache_data
def load_global_time_profile():
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("""
            SELECT
                time,
                yt_sum,
                yt_weighted_avg,
                yt_weighted_diff,
                tw_sum,
                tw_weighted_avg,
                tw_weighted_diff
            FROM time_global_profile
        """, conn)
    return df


# ─────────────────────────────
# UI
# ─────────────────────────────
#st.title("📊 全體時段表現分析（Global Time Profile）")

global_df = load_global_time_profile()

if global_df.empty:
    st.warning("time_global_profile 沒有資料")
    st.stop()

# None → 0
global_df = global_df.fillna(0)

# 取出 hour
global_df["hour"] = global_df["time"].apply(
    lambda t: int(t.split(":")[0])
)

# 時間排序（中午邏輯仍適用）
global_df["sort_key"] = global_df["time"].apply(time_sort_key)
global_df.sort_values("sort_key", inplace=True)


# 建立有序 x 軸（避免 Streamlit 亂排）
global_df["time_ordered"] = pd.Categorical(
    global_df["time"],
    categories=global_df["time"],
    ordered=True
)

# ─────────────────────────────
# 圖 1：Live 數量（sum）
# ─────────────────────────────


# 轉成 long format
plot_df = global_df.melt(
    id_vars=["time"],
    value_vars=["yt_sum", "tw_sum"],
    var_name="platform",
    value_name="live_sum"
)

# ★ 關鍵：先把平台名稱轉好
plot_df["platform_label"] = plot_df["platform"].map({
    "yt_sum": "YouTube",
    "tw_sum": "Twitch"
})

time_domain = global_df.sort_values("sort_key")["time"].tolist()

st.markdown("### ⏱️ 全體 Live 數量（YT vs TW）")

chart = (
    alt.Chart(plot_df)
    .mark_line(point=True,  strokeWidth=3)
    .encode(
        x=alt.X(
            "time:N",
            title="時間",
            scale=alt.Scale(domain=time_domain)  # ⭐ 核心
        ),
        y=alt.Y("live_sum:Q", title="Live 數量"),
        color=alt.Color(
            "platform_label:N",
            scale=alt.Scale(
                domain=["YouTube", "Twitch"],
                range=["red", "purple"]
            ),
            legend=alt.Legend(title="平台")
        ),
        tooltip=[
            alt.Tooltip("time:N", title="時間"),
            alt.Tooltip("live_sum:Q", title="Live 數量"),
            alt.Tooltip("platform_label:N", title="平台")
        ]
    )
    .properties(height=400)
)

chart = chart.properties(
    width=800,    # ← 調小這個
    height=400
)

st.altair_chart(chart, use_container_width=False)


