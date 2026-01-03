import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path

#streamlit run ver_5/5_2_dataframe.py

# ─────────────────────────────
# 基本設定
# ─────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]   # 指到 main
DB_PATH = BASE_DIR / "database" / "calculate_data.db"


def load_df(sql):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(sql, conn)

st.header("📈 頻道趨勢斜率（30 日）")

df_slope = load_df("""
    SELECT
        s.channel_name,
        MAX(CASE WHEN c.platform = 'yt' THEN c.trend_slope END) AS yt_slope,
        MAX(CASE WHEN c.platform = 'tw' THEN c.trend_slope END) AS tw_slope
    FROM streamer s
    LEFT JOIN channel_30d_avg c
        ON c.channel_id = s.channel_id
    GROUP BY
        s.id,
        s.channel_name
    ORDER BY
        s.id;
""")

st.dataframe(
    df_slope,
    use_container_width=True
)
