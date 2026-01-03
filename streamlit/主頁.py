import streamlit as st
#streamlit run streamlit/app.py

st.set_page_config(
    page_title="VTuber 直播分析",
    layout="wide"
)

st.title("📊 VTuber 直播數據分析")

st.markdown("""
這個網站整合多個直播分析頁面，  
請從左側選單選擇要查看的分析內容。
""")
