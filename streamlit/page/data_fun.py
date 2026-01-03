import pandas as pd
import plotly.express as px
import streamlit as st

def plot_time_distribution(df_main, selected_channel):

    df_selected = df_main[df_main['channel'] == selected_channel].copy()

    # 建立 datetime
    df_selected['datetime'] = pd.to_datetime(df_selected['date'] + " " + df_selected['time'])

    # 把時間四捨五入到15分鐘
    def round_to_15min(dt):
        discard = pd.Timedelta(minutes=dt.minute % 15,
                                seconds=dt.second,
                                microseconds=dt.microsecond)
        dt = dt - discard
        if discard >= pd.Timedelta(minutes=7.5):
            dt += pd.Timedelta(minutes=15)
        return dt

    df_selected['time_15min_dt'] = df_selected['datetime'].apply(round_to_15min)

    # 取出一天中的時間（忽略日期），轉成 pd.Timedelta（方便排序和跨天處理）
    df_selected['time_only'] = df_selected['time_15min_dt'].dt.time.apply(
        lambda t: pd.Timedelta(hours=t.hour, minutes=t.minute)
    )

    # 為了讓時間軸從12:00開始，跨到隔天12:00，
    # 把早於12:00的時間加一天(24小時)
    def adjust_time(timedelta_obj):
        noon = pd.Timedelta(hours=12)
        if timedelta_obj < noon:
            return timedelta_obj + pd.Timedelta(days=1)
        else:
            return timedelta_obj

    df_selected['time_for_sort'] = df_selected['time_only'].apply(adjust_time)

    # YouTube 平均（過濾 >= 10）
    df_youtube_group = (
        df_selected[df_selected['youtube'] >= 10]
        .groupby('time_for_sort')['youtube']
        .mean()
        .reset_index()
    )

    # Twitch 平均（過濾 >= 10）
    df_twitch_group = (
        df_selected[df_selected['twitch'] >= 10]
        .groupby('time_for_sort')['twitch']
        .mean()
        .reset_index()
    )

    # 合併兩平台
    df_group = pd.merge(df_youtube_group, df_twitch_group, on='time_for_sort', how='outer').fillna(0)
    df_group = df_group.sort_values('time_for_sort')

    # 轉成可顯示的時間字串（格式 HH:MM）
    def timedelta_to_str(td):
        total_minutes = int(td.total_seconds() // 60)
        hours = (total_minutes // 60) % 24
        minutes = total_minutes % 60
        return f"{hours:02d}:{minutes:02d}"

    df_group['time_15min_str'] = df_group['time_for_sort'].apply(timedelta_to_str)

    # 轉長格式畫圖
    df_melt = df_group.melt(id_vars='time_15min_str', value_vars=['youtube', 'twitch'],
                            var_name='平台', value_name='平均觀眾數')

    fig = px.line(
        df_melt,
        x='time_15min_str',
        y='平均觀眾數',
        color='平台',
        title=f'📊 {selected_channel} 以一天24小時（12:00~隔天12:00）為基準的平均觀眾數',
        markers=True
    )
    fig.update_layout(
        xaxis_title="時間",
        yaxis_title="平均觀眾數",
        xaxis_tickangle=-45,
        xaxis=dict(tickmode='array', tickvals=df_group['time_15min_str'][::4])  # 每小時顯示一次刻度
    )
    st.plotly_chart(fig, use_container_width=True)


def plot_time_count_distribution(df_main, selected_channel):
    import pandas as pd
    import plotly.express as px
    import streamlit as st

    df_selected = df_main[df_main['channel'] == selected_channel].copy()

    # 建立 datetime
    df_selected['datetime'] = pd.to_datetime(df_selected['date'] + " " + df_selected['time'])

    # 四捨五入到15分鐘
    def round_to_15min(dt):
        discard = pd.Timedelta(minutes=dt.minute % 15,
                                seconds=dt.second,
                                microseconds=dt.microsecond)
        dt = dt - discard
        if discard >= pd.Timedelta(minutes=7.5):
            dt += pd.Timedelta(minutes=15)
        return dt

    df_selected['time_15min_dt'] = df_selected['datetime'].apply(round_to_15min)

    # 取出一天中的時間（忽略日期）
    df_selected['time_only'] = df_selected['time_15min_dt'].dt.time.apply(
        lambda t: pd.Timedelta(hours=t.hour, minutes=t.minute)
    )

    # 調整時間排序起點12:00
    def adjust_time(timedelta_obj):
        noon = pd.Timedelta(hours=12)
        if timedelta_obj < noon:
            return timedelta_obj + pd.Timedelta(days=1)
        else:
            return timedelta_obj

    df_selected['time_for_sort'] = df_selected['time_only'].apply(adjust_time)

    # YouTube 計次（過濾 youtube >= 10）
    df_youtube_count = (
        df_selected.loc[df_selected['youtube'] >= 10]
        .groupby('time_for_sort')
        .size()
        .reset_index(name='youtube_count')
    )

    # Twitch 計次（過濾 twitch >= 10）
    df_twitch_count = (
        df_selected.loc[df_selected['twitch'] >= 10]
        .groupby('time_for_sort')
        .size()
        .reset_index(name='twitch_count')
    )

    # 合併
    df_group = pd.merge(df_youtube_count, df_twitch_count, on='time_for_sort', how='outer').fillna(0)

    df_group = df_group.sort_values('time_for_sort')

    # 時間字串
    def timedelta_to_str(td):
        total_minutes = int(td.total_seconds() // 60)
        hours = (total_minutes // 60) % 24
        minutes = total_minutes % 60
        return f"{hours:02d}:{minutes:02d}"

    df_group['time_15min_str'] = df_group['time_for_sort'].apply(timedelta_to_str)

    # 轉長格式畫圖
    df_melt = df_group.melt(
        id_vars='time_15min_str',
        value_vars=['youtube_count', 'twitch_count'],
        var_name='平台',
        value_name='計次'
    )

    # 改顯示平台名稱簡潔一點
    df_melt['平台'] = df_melt['平台'].map({'youtube_count': 'YouTube', 'twitch_count': 'Twitch'})

    fig = px.line(
        df_melt,
        x='time_15min_str',
        y='計次',
        color='平台',
        title=f'📊 {selected_channel} 12:00~隔天12:00 每15分鐘時段出現次數統計',
        markers=True
    )
    fig.update_layout(
        xaxis_title="時間",
        yaxis_title="計次",
        xaxis_tickangle=-45,
        xaxis=dict(tickmode='array', tickvals=df_group['time_15min_str'][::4])  # 每小時顯示一次
    )
    st.plotly_chart(fig, use_container_width=True)
    

def plot_time_count_all_channels(df_main):

    df_selected = df_main.copy()

    # 建立 datetime
    df_selected['datetime'] = pd.to_datetime(df_selected['date'] + " " + df_selected['time'])

    # 四捨五入到15分鐘
    def round_to_15min(dt):
        discard = pd.Timedelta(minutes=dt.minute % 15,
                                seconds=dt.second,
                                microseconds=dt.microsecond)
        dt = dt - discard
        if discard >= pd.Timedelta(minutes=7.5):
            dt += pd.Timedelta(minutes=15)
        return dt

    df_selected['time_15min_dt'] = df_selected['datetime'].apply(round_to_15min)

    # 取出一天中的時間（忽略日期）
    df_selected['time_only'] = df_selected['time_15min_dt'].dt.time.apply(
        lambda t: pd.Timedelta(hours=t.hour, minutes=t.minute)
    )

    # 調整時間排序起點12:00
    def adjust_time(timedelta_obj):
        noon = pd.Timedelta(hours=12)
        if timedelta_obj < noon:
            return timedelta_obj + pd.Timedelta(days=1)
        else:
            return timedelta_obj

    df_selected['time_for_sort'] = df_selected['time_only'].apply(adjust_time)

    # YouTube 計次（過濾 youtube >= 10）
    df_youtube_count = (
        df_selected.loc[df_selected['youtube'] >= 10]
        .groupby('time_for_sort')
        .size()
        .reset_index(name='youtube_count')
    )

    # Twitch 計次（過濾 twitch >= 10）
    df_twitch_count = (
        df_selected.loc[df_selected['twitch'] >= 10]
        .groupby('time_for_sort')
        .size()
        .reset_index(name='twitch_count')
    )

    # 合併
    df_group = pd.merge(df_youtube_count, df_twitch_count, on='time_for_sort', how='outer').fillna(0)

    df_group = df_group.sort_values('time_for_sort')

    # 時間字串
    def timedelta_to_str(td):
        total_minutes = int(td.total_seconds() // 60)
        hours = (total_minutes // 60) % 24
        minutes = total_minutes % 60
        return f"{hours:02d}:{minutes:02d}"

    df_group['time_15min_str'] = df_group['time_for_sort'].apply(timedelta_to_str)

    # 轉長格式畫圖
    df_melt = df_group.melt(
        id_vars='time_15min_str',
        value_vars=['youtube_count', 'twitch_count'],
        var_name='平台',
        value_name='計次'
    )

    # 改顯示平台名稱簡潔一點
    df_melt['平台'] = df_melt['平台'].map({'youtube_count': 'YouTube', 'twitch_count': 'Twitch'})

    fig = px.line(
        df_melt,
        x='time_15min_str',
        y='計次',
        color='平台',
        title=f'📊 全頻道 12:00~隔天12:00 每15分鐘時段出現次數統計',
        markers=True
    )
    fig.update_layout(
        xaxis_title="時間",
        yaxis_title="計次",
        xaxis_tickangle=-45,
        xaxis=dict(tickmode='array', tickvals=df_group['time_15min_str'][::4])  # 每小時顯示一次
    )
    st.plotly_chart(fig, use_container_width=True)