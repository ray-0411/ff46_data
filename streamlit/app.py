import streamlit as st
#streamlit run streamlit/app.py

st.set_page_config(
    page_title="VTuber 直播分析",
    layout="wide"
)

pg = st.navigation([
    st.Page("page/0_main.py", title="🏠 主頁"),
    st.Page("page/1_live_times.py", title="1.開台時段分布"),
    st.Page("page/2_time_data.py", title="2.各時段觀眾變化"),
    st.Page("page/3_sametime_data.py", title="3.同時直播競爭分析"),
    st.Page("page/4_data_out.py", title="4.基本資料檢視"),
])

pg.run()


