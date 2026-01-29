import sqlite3
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder
from datetime import datetime
from pathlib import Path

#streamlit run streamlit/app.py

# 資料庫路徑
BASE_DIR = Path(__file__).resolve().parents[2]   # 指到 main
db_path = BASE_DIR / "database" / "calculate_data.db"

from page.data_fun import (
    plot_time_distribution,
    plot_time_count_distribution,
    plot_time_count_all_channels
)


#streamlit run main_data.py



# 讀取資料
with sqlite3.connect(db_path) as conn:
    df = pd.read_sql_query("SELECT * FROM main", conn)
    df_streamer = pd.read_sql_query("SELECT * FROM streamer", conn)
    df_stream = pd.read_sql_query("SELECT * FROM stream", conn)
    df_same_stream = pd.read_sql_query("SELECT * FROM same_stream", conn)

# 合併日期與時間
df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'])

# 建立 from_id -> to_id 映射字典
same_stream_map = dict(zip(df_same_stream['from_id'], df_same_stream['to_id']))

# 定義一個函數：如果直播ID在映射中，就轉成合併後的ID，否則維持原本ID
def map_stream_id(stream_id):
    return same_stream_map.get(stream_id, stream_id)

# 轉換 df_yt_summary 直播ID
df['yt_number'] = df['yt_number'].apply(map_stream_id)

# Twitch 同理
df['tw_number'] = df['tw_number'].apply(map_stream_id)


# 🔽 檢視模式選單
view_mode = st.selectbox("選擇檢視模式", ["總觀看統計","單一頻道", "全部頻道影片"])

# view_mode預設(debug用)
# view_mode = "全部頻道影片"  



# ---------- 單一頻道模式 ----------
if view_mode == "單一頻道":
    # 建立 name -> channel_id 的映射
    name_to_id = dict(zip(df_streamer['channel_name'], df_streamer['channel_id']))

    
    filtered_channels = df_streamer['channel_name'].tolist()

    selected_name = st.selectbox("請選擇頻道", filtered_channels)



    # 取得對應的 channel_id
    selected_channel = name_to_id[selected_name]

    # 用 channel_id 篩選 main 表資料
    df_selected = df[df['channel'] == selected_channel].copy()

    # 平均觀看數（排除 <10）
    yt_avg = df_selected[df_selected['youtube'] >= 10]['youtube'].mean()
    tw_avg = df_selected[df_selected['twitch'] >= 10]['twitch'].mean()

    yt_avg_display = f"{yt_avg:.1f}" if not pd.isna(yt_avg) else "無資料"
    tw_avg_display = f"{tw_avg:.1f}" if not pd.isna(tw_avg) else "無資料"

    col1, col2 = st.columns(2)
    col1.metric("📺 YouTube 平均觀看數", yt_avg_display)
    col2.metric("🎮 Twitch 平均觀看數", tw_avg_display)

    # YouTube 統計
    df_youtube = df_selected[df_selected['yt_number'] != 0]
    df_yt_summary = df_youtube.groupby('yt_number').agg(
        yt_avg=('youtube', lambda x: x[x >= 10].mean()),
        yt_max=('youtube', lambda x: x[x >= 10].max()),
        yt_min=('youtube', lambda x: x[x >= 10].min()),
        count=('datetime', 'count'),
        start_time=('datetime', 'min'),
        end_time=('datetime', 'max')
    ).reset_index()
    df_yt_summary.columns = ['直播ID', '平均觀看數', '最大觀看數', '最小觀看數', '資料筆數', '開始時間', '結束時間']

    
    
    # Twitch 統計
    df_twitch = df_selected[df_selected['tw_number'] != 0]
    df_tw_summary = df_twitch.groupby('tw_number').agg(
        tw_avg=('twitch', lambda x: x[x >= 10].mean()),
        tw_max=('twitch', lambda x: x[x >= 10].max()),
        tw_min=('twitch', lambda x: x[x >= 10].min()),
        count=('datetime', 'count'),
        start_time=('datetime', 'min'),
        end_time=('datetime', 'max')
    ).reset_index()
    df_tw_summary.columns = ['直播ID', '平均觀看數', '最大觀看數', '最小觀看數', '資料筆數', '開始時間', '結束時間']

    # 加上時間字串欄位
    for df_summary in [df_yt_summary, df_tw_summary]:
        df_summary['日期'] = df_summary['開始時間'].dt.strftime("%Y-%m-%d").fillna("")
        df_summary['開始時間_str'] = df_summary['開始時間'].dt.strftime("%H:%M").fillna("")
        df_summary['結束時間_str'] = df_summary['結束時間'].dt.strftime("%H:%M").fillna("")
        df_summary.drop(columns=['開始時間', '結束時間'], inplace=True)

    # 合併直播名稱
    df_yt_summary = pd.merge(df_yt_summary, df_stream[['id', 'name']], how='left', left_on='直播ID', right_on='id')
    df_tw_summary = pd.merge(df_tw_summary, df_stream[['id', 'name']], how='left', left_on='直播ID', right_on='id')

    # 欄位顯示順序與映射
    col_name_map = {
        '直播ID': '直播ID',
        '平均觀看數': '平均觀看數',
        '最大觀看數': '最大觀看數',
        '最小觀看數': '最小觀看數',
        '資料筆數': '資料筆數',
        '日期': '日期',
        '開始時間': '開始時間_str',
        '結束時間': '結束時間_str',
        '直播名稱': 'name',
    }
    fixed_order = list(col_name_map.keys())
    selected_display_names = st.multiselect("📋 選擇要顯示的欄位", fixed_order, default=fixed_order)
    final_display_names = [col for col in fixed_order if col in selected_display_names]
    final_df_columns = [col_name_map[col] for col in final_display_names]

    # 顯示 YouTube 表格
    st.markdown("### 📺 YouTube 直播統計")
    df_yt_display = df_yt_summary[final_df_columns].rename(columns={
        'name': '直播名稱',
        '開始時間_str': '開始時間',
        '結束時間_str': '結束時間',
    })
    
    if '平均觀看數' in df_yt_display.columns:
        df_yt_display['平均觀看數'] = df_yt_display['平均觀看數'].round(1).fillna(0)
    if '最大觀看數' in df_yt_display.columns:
        df_yt_display['最大觀看數'] = df_yt_display['最大觀看數'].fillna(0).astype(int)
    if '最小觀看數' in df_yt_display.columns:
        df_yt_display['最小觀看數'] = df_yt_display['最小觀看數'].fillna(0).astype(int)
        
    if '直播ID' in df_yt_display.columns:
        df_yt_display['直播ID'] = pd.to_numeric(df_yt_display['直播ID'], errors='coerce').astype(float)

    for col in ['最大觀看數', '最小觀看數','資料筆數']:
        if col in df_yt_display.columns:
            df_yt_display[col] = pd.to_numeric(df_yt_display[col], errors='coerce').astype(float)


    gb = GridOptionsBuilder.from_dataframe(df_yt_display)
    gb.configure_default_column(
        editable=False, 
        groupable=False, 
        filter=False, 
        resizable=True, 
        sortable=True,
    )
    for col, width in zip(["直播ID", "平均觀看數", "最大觀看數", "最小觀看數", "資料筆數", "日期", "開始時間", "結束時間", "直播名稱"],
                        [80, 110, 110, 110, 90, 110, 90, 90, 2000]):
        if col in df_yt_display.columns:
            gb.configure_column(
                col, 
                width=width, 
                filter=False,
                minWidth=width,   # ⭐ 鎖死最小
                maxWidth=width,   # ⭐ 鎖死最大
            )
    
    
    AgGrid(
        df_yt_display,
        gridOptions=gb.build(),
        enable_enterprise_modules=False,
        fit_columns_on_grid_load=False,
        theme='balham',
        height=300,
        width='100%',
        custom_css={
            ".ag-header-cell-label": {
                "justify-content": "flex-start",   # 容器靠左
            },
            ".ag-header-cell-text": {
                "text-align": "left",              # ⭐ 標題文字本體靠左
                "width": "100%",                   # ⭐ 很重要，否則不會動
            },
            ".ag-cell": {
                "text-align": "left",              # 資料列靠左
            },
        },
        key=f"youtube_table_{view_mode}"
    )

    #開啟才能用修改same_stream
    same_viewable = False
    
    if same_viewable:
        # 新增 same_stream 表單
        st.markdown("### ➕ 新增資料到 same_stream")
        with st.form("add_same_stream_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                from_id = st.number_input("來源 ID（from_id）", min_value=1, step=1)
            with col2:
                to_id = st.number_input("合併至 ID（to_id）", min_value=1, step=1)
            
            if st.form_submit_button("新增"):
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 取得現在時間字串
                try:
                    with sqlite3.connect(db_path) as conn:
                        conn.execute(
                            "INSERT INTO same_stream (from_id, to_id, time) VALUES (?, ?, ?)",
                            (from_id, to_id, now)
                        )
                        st.success(f"✅ 已成功新增 from_id = {from_id} → to_id = {to_id}（{now}）")
                except Exception as e:
                    st.error(f"❌ 新增失敗：{e}")
    
    

    # 顯示 Twitch 表格
    st.markdown("### 🎮 Twitch 直播統計")
    df_tw_display = df_tw_summary[final_df_columns].rename(columns={
        'name': '直播名稱',
        '開始時間_str': '開始時間',
        '結束時間_str': '結束時間',
    })
    
    if '平均觀看數' in df_tw_display.columns:
        df_tw_display['平均觀看數'] = df_tw_display['平均觀看數'].round(1).fillna(0)
    if '最大觀看數' in df_tw_display.columns:
        df_tw_display['最大觀看數'] = df_tw_display['最大觀看數'].fillna(0).astype(int)
    if '最小觀看數' in df_tw_display.columns:
        df_tw_display['最小觀看數'] = df_tw_display['最小觀看數'].fillna(0).astype(int)
        
    if '直播ID' in df_tw_display.columns:
        df_tw_display['直播ID'] = pd.to_numeric(df_tw_display['直播ID'], errors='coerce').astype(float)

    for col in ['最大觀看數', '最小觀看數','資料筆數']:
        if col in df_tw_display.columns:
            df_tw_display[col] = pd.to_numeric(df_tw_display[col], errors='coerce').astype(float)

    gb2 = GridOptionsBuilder.from_dataframe(df_tw_display)
    gb2.configure_default_column(editable=False, groupable=False, filter=False, resizable=True, sortable=True)
    for col, width in zip(["直播ID", "平均觀看數", "最大觀看數", "最小觀看數", "資料筆數", "日期", "開始時間", "結束時間", "直播名稱"],
                        [80, 110, 110, 110, 90, 110, 90, 90, 2000]):
        if col in df_tw_display.columns:
            gb2.configure_column(
                col, 
                width=width, 
                filter=False,
                minWidth=width,   # ⭐ 鎖死最小
                maxWidth=width,   # ⭐ 鎖死最大
            )

    AgGrid(
        df_tw_display,
        gridOptions=gb2.build(),
        enable_enterprise_modules=False,
        fit_columns_on_grid_load=False,
        theme='balham',
        height=300,
        width='100%',
        custom_css={
            ".ag-header-cell-label": {
                "justify-content": "flex-start",   # 容器靠左
            },
            ".ag-header-cell-text": {
                "text-align": "left",              # ⭐ 標題文字本體靠左
                "width": "100%",                   # ⭐ 很重要，否則不會動
            },
            ".ag-cell": {
                "text-align": "left",              # 資料列靠左
            },
        },
        key=f"twitch_table_{view_mode}"
    )
    
    # 畫出時間分布圖
    plot_time_distribution(df, selected_channel)
    
    plot_time_count_distribution(df, selected_channel)
    
# ---------- 總統計模式 ----------
elif view_mode == "總觀看統計":
    st.subheader("📊 所有頻道的平均觀看統計")

    # 取 streamer 資料
    df_streamer = df_streamer[['channel_id', 'channel_name']]
    valid_channels = df_streamer['channel_id'].tolist()

    # 過濾 main 表只保留出現在 streamer 的頻道
    df_filtered = df[df['channel'].isin(valid_channels)].copy()

    # YouTube 直播場數計算（非0的 yt_number 計數）
    yt_counts = df_filtered[df_filtered['yt_number'] != 0].groupby('channel')['yt_number'].nunique().rename('YouTube 直播場數')

    # Twitch 直播場數計算（非0的 tw_number 計數）
    tw_counts = df_filtered[df_filtered['tw_number'] != 0].groupby('channel')['tw_number'].nunique().rename('Twitch 直播場數')


    # 平均統計（先用 channel_id 為主）
    grouped = df_filtered.groupby('channel').agg(
        yt_avg=('youtube', lambda x: x[x >= 10].mean()),
        tw_avg=('twitch', lambda x: x[x >= 10].mean()),
        
        yt_viewer_quarter_sum=('youtube', lambda x: x[x >= 10].sum()),
        tw_viewer_quarter_sum=('twitch', lambda x: x[x >= 10].sum()),
        
        count=('datetime', 'count')
    ).reset_index()
    
    # 合併直播場數
    grouped = grouped.merge(yt_counts, on='channel', how='left')
    grouped = grouped.merge(tw_counts, on='channel', how='left')

    # merge streamer 表取得中文名
    grouped = grouped.merge(df_streamer, left_on='channel', right_on='channel_id', how='left')

    # 根據 streamer.channel_id 的順序排序
    grouped['order'] = grouped['channel_id'].apply(lambda x: valid_channels.index(x))
    grouped = grouped.sort_values('order')
    
    # 重新排序 index，讓前面數字正常
    grouped = grouped.reset_index(drop=True)

    # 填補直播場數的 NaN 為 0
    grouped['YouTube 直播場數'] = grouped['YouTube 直播場數'].fillna(0).astype(int)
    grouped['Twitch 直播場數'] = grouped['Twitch 直播場數'].fillna(0).astype(int)

    grouped['YouTube 觀眾小時'] = grouped['yt_viewer_quarter_sum'] / 4
    grouped['Twitch 觀眾小時'] = grouped['tw_viewer_quarter_sum'] / 4 


    # 選取並重新命名欄位
    grouped = grouped[[
        'channel_name', 
        'yt_avg', 'tw_avg', 
        'count', 
        'YouTube 直播場數', 'Twitch 直播場數',
        'YouTube 觀眾小時', 'Twitch 觀眾小時',
    ]]
    grouped.columns = [
                    '頻道', 
                    'YouTube 平均觀看數', 'Twitch 平均觀看數', 
                    '紀錄筆數', 
                    'YouTube 直播場數', 'Twitch 直播場數',
                    'YouTube 觀眾小時', 'Twitch 觀眾小時',]

    # 補0欄位
    numeric_cols = [
        'YouTube 平均觀看數', 'Twitch 平均觀看數', 
        '紀錄筆數', 'YouTube 直播場數', 'Twitch 直播場數',
        'YouTube 觀眾小時', 'Twitch 觀眾小時',]

    # 先把這些欄位的 NaN 補成 0（數字型別）
    grouped[numeric_cols] = grouped[numeric_cols].fillna(0)

    # 如果有些欄位是空字串 "" 而非 NaN，轉成 NaN 再補 0
    grouped[numeric_cols] = grouped[numeric_cols].replace("", pd.NA).fillna(0)


    # 平均觀看數四捨五入到小數點第一位
    grouped['YouTube 平均觀看數'] = pd.to_numeric(grouped['YouTube 平均觀看數'], errors='coerce').round(1)
    grouped['Twitch 平均觀看數'] = pd.to_numeric(grouped['Twitch 平均觀看數'], errors='coerce').round(1)
    
    grouped['YouTube 觀眾小時'] = pd.to_numeric(grouped['YouTube 觀眾小時'], errors='coerce').round(1)
    grouped['Twitch 觀眾小時'] = pd.to_numeric(grouped['Twitch 觀眾小時'], errors='coerce').round(1)
    
    def format_k(x):
        if pd.isna(x) or x == 0:
            return "0k"
        return f"{max(x, 1) / 1000:.1f}k"

    grouped['YouTube 觀眾小時 (k)'] = grouped['YouTube 觀眾小時'].apply(format_k)
    grouped['Twitch 觀眾小時 (k)'] = grouped['Twitch 觀眾小時'].apply(format_k)
    
    grouped = grouped.drop(columns=[
        'YouTube 觀眾小時',
        'Twitch 觀眾小時'
    ])
    
    grouped = grouped.rename(columns={
        'YouTube 觀眾小時 (k)': 'YouTube 觀眾小時',
        'Twitch 觀眾小時 (k)': 'Twitch 觀眾小時',
    })
    



    # 新增流水號欄位（從 1 開始）
    grouped.insert(0, '編號', range(1, len(grouped) + 1))
    
    
    # AgGrid 設定（全欄位純文字、無 filter）
    gb = GridOptionsBuilder.from_dataframe(grouped)
    for col in grouped.columns:
        gb.configure_column(col, filter=False, editable=False, sortable=True, resizable=True)


    # 設定欄寬
    for col, width in zip(
        ["編號", "頻道", 
        "YouTube 平均觀看數", "Twitch 平均觀看數", 
        "紀錄筆數", "YouTube 直播場數", "Twitch 直播場數",
        "YouTube 觀眾小時", "Twitch 觀眾小時"],
        [80, 100, 180, 180, 100, 170, 160, 170, 170]
    ):
        gb.configure_column(
            col, 
            width=width,
            minWidth=width,   # ⭐ 鎖死最小
            maxWidth=width,   # ⭐ 鎖死最大
        )
    
    CUSTOM_CSS_LEFT = {
        ".ag-header-cell-label": {
            "justify-content": "flex-start",   # 容器靠左
        },
        ".ag-header-cell-text": {
            "text-align": "left",              # ⭐ 標題文字本體靠左
            "width": "100%",                   # ⭐ 很重要，否則不會動
        },
        ".ag-cell": {
            "text-align": "left",              # 資料列靠左
        },
    }


    # 顯示 AgGrid 表格
    AgGrid(grouped, gridOptions=gb.build(), 
        theme='balham', 
        height=560, 
        width='100%', 
        fit_columns_on_grid_load=False,
        custom_css=CUSTOM_CSS_LEFT,
        key=f'avg_all_channel_{view_mode}'
    )


# ---------- 全部頻道影片模式 ----------
elif view_mode == "全部頻道影片":

    # 濾除無意義資料（直播編號 = 0）
    df_youtube = df[df['yt_number'] != 0].copy()
    df_twitch = df[df['tw_number'] != 0].copy()

    # YouTube 統計
    df_yt_summary = df_youtube.groupby('yt_number').agg(
        yt_avg=('youtube', lambda x: x[x >= 10].mean()),
        yt_max=('youtube', lambda x: x[x >= 10].max()),
        yt_min=('youtube', lambda x: x[x >= 10].min()),
        count=('datetime', 'count'),
        start_time=('datetime', 'min'),
        end_time=('datetime', 'max'),
        channel=('channel', 'first')
    ).reset_index()
    df_yt_summary.columns = ['直播ID', '平均觀看數', '最大觀看數', '最小觀看數', '資料筆數', '開始時間', '結束時間', 'channel_id']
    df_yt_summary = pd.merge(df_yt_summary, df_stream[['id', 'name']], how='left', left_on='直播ID', right_on='id')
    df_yt_summary = pd.merge(df_yt_summary, df_streamer[['channel_id', 'channel_name']], how='left', on='channel_id')
    
    
    
    # Twitch 統計
    df_tw_summary = df_twitch.groupby('tw_number').agg(
        tw_avg=('twitch', lambda x: x[x >= 10].mean()),
        tw_max=('twitch', lambda x: x[x >= 10].max()),
        tw_min=('twitch', lambda x: x[x >= 10].min()),
        count=('datetime', 'count'),
        start_time=('datetime', 'min'),
        end_time=('datetime', 'max'),
        channel=('channel', 'first')
    ).reset_index()
    df_tw_summary.columns = ['直播ID', '平均觀看數', '最大觀看數', '最小觀看數', '資料筆數', '開始時間', '結束時間', 'channel_id']
    df_tw_summary = pd.merge(df_tw_summary, df_stream[['id', 'name']], how='left', left_on='直播ID', right_on='id')
    df_tw_summary = pd.merge(df_tw_summary, df_streamer[['channel_id', 'channel_name']], how='left', on='channel_id')

    # 加入日期與時間格式欄位
    for df_summary in [df_yt_summary, df_tw_summary]:
        df_summary['日期'] = df_summary['開始時間'].dt.strftime("%Y-%m-%d").fillna("")
        df_summary['開始時間_str'] = df_summary['開始時間'].dt.strftime("%H:%M").fillna("")
        df_summary['結束時間_str'] = df_summary['結束時間'].dt.strftime("%H:%M").fillna("")
        df_summary.drop(columns=['開始時間', '結束時間'], inplace=True)
    
    st.subheader("🎥 所有頻道影片一覽")

    # ===============================
    # 第一段：共用的欄位選擇（只做一次）
    # ===============================
    col_name_map = {
        '直播ID': '直播ID',
        '頻道名稱': 'channel_name',
        '平均觀看數': '平均觀看數',
        '最大觀看數': '最大觀看數',
        '最小觀看數': '最小觀看數',
        '資料筆數': '資料筆數',
        '日期': '日期',
        '開始時間': '開始時間_str',
        '結束時間': '結束時間_str',
        '直播名稱': 'name',
    }
    fixed_order = list(col_name_map.keys())

    selected_display_names = st.multiselect(
        "📋 選擇要顯示的欄位",
        fixed_order,
        default=fixed_order,
        key="all_video_cols_once",   # ⭐ 只在這裡用一次
    )

    final_df_columns = [col_name_map[c] for c in fixed_order if c in selected_display_names]

    # ===============================
    # 第二段：YouTube（完全仿單一頻道）
    # ===============================
    st.markdown("### 📺 YouTube 直播統計（全部頻道）")

    df_yt_display = (
        df_yt_summary[final_df_columns]
        .rename(columns={
            'channel_name': '頻道名稱',
            'name': '直播名稱',
            '開始時間_str': '開始時間',
            '結束時間_str': '結束時間',
        })
        .copy()
    )

    # 型別整理（跟單一頻道一樣）
    for col in ['直播ID', '平均觀看數', '最大觀看數', '最小觀看數', '資料筆數']:
        if col in df_yt_display.columns:
            df_yt_display[col] = pd.to_numeric(df_yt_display[col], errors='coerce')

    # 👉 單一頻道邏輯：這裡才 build grid
    gb_yt = GridOptionsBuilder.from_dataframe(df_yt_display)
    gb_yt.configure_default_column(editable=False, sortable=True, filter=False, resizable=True)

    if '平均觀看數' in df_yt_display.columns:
        df_yt_display['平均觀看數'] = df_yt_display['平均觀看數'].round(1)

    for col, width in zip(
        ["直播ID", "平均觀看數", "最大觀看數", "最小觀看數", "資料筆數", "日期", "開始時間", "結束時間", "直播名稱", "頻道名稱"],
        [80, 110, 110, 110, 90, 110, 100, 100, 2000, 100]
    ):
        if col in df_yt_display.columns:
            gb_yt.configure_column(col, width=width, minWidth=width, maxWidth=width,filter=False)

    AgGrid(
        df_yt_display,
        gridOptions=gb_yt.build(),
        theme="balham",
        height=400,
        width="100%",
        fit_columns_on_grid_load=False,
        enable_enterprise_modules=False,
        key="yt_all_video_clean",   # ⭐ 固定、不吃 rerun
        custom_css={
            ".ag-header-cell-label": {
                "justify-content": "flex-start",   # 容器靠左
            },
            ".ag-header-cell-text": {
                "text-align": "left",              # ⭐ 標題文字本體靠左
                "width": "100%",                   # ⭐ 很重要，否則不會動
            },
            ".ag-cell": {
                "text-align": "left",              # 資料列靠左
            },
        },
    )

    # ===============================
    # 第三段：Twitch（邏輯完全對稱）
    # ===============================
    st.markdown("### 🎮 Twitch 直播統計（全部頻道）")

    df_tw_display = (
        df_tw_summary[final_df_columns]
        .rename(columns={
            'channel_name': '頻道名稱',
            'name': '直播名稱',
            '開始時間_str': '開始時間',
            '結束時間_str': '結束時間',
        })
        .copy()
    )

    for col in ['直播ID', '平均觀看數', '最大觀看數', '最小觀看數', '資料筆數']:
        if col in df_tw_display.columns:
            df_tw_display[col] = pd.to_numeric(df_tw_display[col], errors='coerce')

    gb_tw = GridOptionsBuilder.from_dataframe(df_tw_display)
    gb_tw.configure_default_column(editable=False, sortable=True, filter=False, resizable=True)

    if '平均觀看數' in df_tw_display.columns:
        df_tw_display['平均觀看數'] = df_tw_display['平均觀看數'].round(1)

    for col, width in zip(
        ["直播ID", "平均觀看數", "最大觀看數", "最小觀看數", "資料筆數", "日期", "開始時間", "結束時間", "直播名稱", "頻道名稱"],
        [80, 110, 110, 110, 90, 110, 100, 100, 2000, 100]
    ):
        if col in df_tw_display.columns:
            gb_tw.configure_column(col, width=width, minWidth=width, maxWidth=width,filter=False)

    AgGrid(
        df_tw_display,
        gridOptions=gb_tw.build(),
        theme="balham",
        height=400,
        width="100%",
        fit_columns_on_grid_load=False,
        enable_enterprise_modules=False,
        key="tw_all_video_clean",
        custom_css={
            ".ag-header-cell-label": {
                "justify-content": "flex-start",   # 容器靠左
            },
            ".ag-header-cell-text": {
                "text-align": "left",              # ⭐ 標題文字本體靠左
                "width": "100%",                   # ⭐ 很重要，否則不會動
            },
            ".ag-cell": {
                "text-align": "left",              # 資料列靠左
            },
        },
    )

    plot_time_count_all_channels(df)
    