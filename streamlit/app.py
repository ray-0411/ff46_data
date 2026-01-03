import streamlit as st
#streamlit run streamlit/app.py

st.set_page_config(
    page_title="VTuber 直播分析",
    layout="wide"
)

pg = st.navigation([
    st.Page("pages/0_main", title="🏠 主頁"),
    st.Page("pages/1_live_times.py", title="1.開台時段分布"),
    st.Page("pages/2_time_data.py", title="2.各時段觀眾變化"),
    st.Page("pages/3_sametime_data.py", title="3.同時直播競爭分析"),
])

pg.run()


