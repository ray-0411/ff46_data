import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path
import altair as alt


# streamlit run ver_4/4_2_make_graph.py

# ─────────────────────────────
# 基本設定
# ─────────────────────────────
st.set_page_config(
    page_title="同時直播競爭分析（By Time）",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parents[2]   # 指到 main
DB_PATH = BASE_DIR / "database" / "calculate_data.db"

# ─────────────────────────────
# 工具：時間排序（12:00 → 23:45 → 00:00 → 11:45）
# ─────────────────────────────
def time_sort_key(t):
    hour, minute = map(int, t.split(":"))
    return hour * 60 + minute + (1440 if hour < 12 else 0)


# ─────────────────────────────
# 讀取資料
# ─────────────────────────────
@st.cache_data
def load_live_count_by_time():
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql("""
            SELECT
                time,
                avg_live_count,
                cnt_0, cnt_1, cnt_2, cnt_3, cnt_4,
                cnt_5, cnt_6, cnt_7, cnt_8, cnt_9, cnt_10
            FROM live_count_by_time
        """, conn)


@st.cache_data
def load_expected_perf():
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql("""
            SELECT
                t.time,
                (
                    t.cnt_0 * 0
                    + t.cnt_1 * e1.avg_geo_perf_percent
                    + t.cnt_2 * e2.avg_geo_perf_percent
                    + t.cnt_3 * e3.avg_geo_perf_percent
                    + t.cnt_4 * e4.avg_geo_perf_percent
                    + t.cnt_5 * e5.avg_geo_perf_percent
                    + t.cnt_6 * e6.avg_geo_perf_percent
                    + t.cnt_7 * e7.avg_geo_perf_percent
                    + t.cnt_8 * e8.avg_geo_perf_percent
                    + t.cnt_9 * e9.avg_geo_perf_percent
                    + t.cnt_10 * e10.avg_geo_perf_percent
                ) / 180.0 AS expected_perf
            FROM live_count_by_time t
            LEFT JOIN concurrent_effect e1  ON e1.live_count  = 1
            LEFT JOIN concurrent_effect e2  ON e2.live_count  = 2
            LEFT JOIN concurrent_effect e3  ON e3.live_count  = 3
            LEFT JOIN concurrent_effect e4  ON e4.live_count  = 4
            LEFT JOIN concurrent_effect e5  ON e5.live_count  = 5
            LEFT JOIN concurrent_effect e6  ON e6.live_count  = 6
            LEFT JOIN concurrent_effect e7  ON e7.live_count  = 7
            LEFT JOIN concurrent_effect e8  ON e8.live_count  = 8
            LEFT JOIN concurrent_effect e9  ON e9.live_count  = 9
            LEFT JOIN concurrent_effect e10 ON e10.live_count = 10
            ORDER BY t.time
        """, conn)

def load_df(query):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn)


# ─────────────────────────────
# UI
# ─────────────────────────────
st.title("📺 同時直播競爭結構分析（By Time）")

df = load_live_count_by_time()
df_perf = load_expected_perf()

if df.empty:
    st.warning("live_count_by_time 沒有資料")
    st.stop()

# 時間排序
df["sort_key"] = df["time"].apply(time_sort_key)
df.sort_values("sort_key", inplace=True)

df_perf = df_perf.merge(
    df[["time", "sort_key"]],
    on="time",
    how="left"
).sort_values("sort_key")

# 建立有序 x 軸
df["time_ordered"] = pd.Categorical(
    df["time"],
    categories=df["time"],
    ordered=True
)

df_perf["time_ordered"] = pd.Categorical(
    df_perf["time"],
    categories=df["time"],
    ordered=True
)

# ─────────────────────────────
# 圖 1：平均同時直播數
# ─────────────────────────────
st.markdown("### ⏱️ 各時段平均同時直播數")

st.line_chart(
    df,
    x="time_ordered",
    y="avg_live_count",
    width=800,
)

st.caption("數值越高，代表該時段結構上同時直播競爭越激烈")

# ─────────────────────────────
# 圖 2：各時段同時直播數結構（累積長條圖，1底→10頂）
# ─────────────────────────────
st.markdown("### 📊 各時段同時直播數結構")

cnt_cols = [f"cnt_{i}" for i in range(1, 11)]

# 轉 long format
df_long = df[["time", "time_ordered"] + cnt_cols].copy()
df_long = df_long.melt(
    id_vars=["time", "time_ordered"],
    value_vars=cnt_cols,
    var_name="cnt_k",
    value_name="cnt"
)

# cnt_1 -> 1
df_long["live_count"] = df_long["cnt_k"].str.replace("cnt_", "", regex=False).astype(int)

# 轉成比例（你這裡分母固定 180）
df_long["ratio"] = df_long["cnt"] / 180.0

# x 軸排序：用你已經排好的 df["time"] 順序
time_order = df["time"].tolist()

chart = (
    alt.Chart(df_long)
    .mark_bar()
    .encode(
        x=alt.X("time:O", sort=time_order, title="Time"),
        y=alt.Y("ratio:Q", stack="zero", title="比例"),
        color=alt.Color(
            "live_count:N",
            sort=list(range(1, 11)),      # legend 顯示 1→10
            title="同時直播數"
        ),
        order=alt.Order("live_count:Q", sort="ascending")  # ✅ 1 在底、10 在頂
    )
    .properties(height=420)
)

chart = chart.properties(
    width=800,    # ← 調小這個
)

st.altair_chart(chart, use_container_width=False)

# ─────────────────────────────
# 圖 3：同時直播數 × 平均表現影響
# ─────────────────────────────
st.markdown("### 📉 同時直播數對單場表現的影響")

df_effect = load_df("""
    SELECT
        live_count,
        avg_geo_perf_percent,
        sample_cnt
    FROM concurrent_effect
    ORDER BY live_count;
""")

chart = (
    alt.Chart(df_effect)
    .mark_line(point=True, strokeWidth=3)
    .encode(
        x=alt.X("live_count:Q", 
                title="同時直播數",
                axis=alt.Axis(
                tickMinStep=1,     # ← 關鍵：最小刻度間距 = 1
                format="d"         # ← 不顯示小數
            )),
        y=alt.Y("avg_geo_perf_percent:Q", title="平均表現變化（%）")
    )
    .properties(
        width=600,   # ← 你要的 width 在這
        height=400
    )
)

st.altair_chart(chart, use_container_width=False)

st.caption("""
x 軸為同時直播數，  
y 軸為一般一場直播相對於自身典型表現的平均變化（%）。
""")

# ─────────────────────────────
# 原始資料
# ─────────────────────────────
with st.expander("📄 查看原始資料"):
    st.dataframe(
        df.drop(columns=["sort_key", "hour"], errors="ignore"),
        width="stretch"
    )
