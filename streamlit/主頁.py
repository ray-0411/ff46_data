import streamlit as st
#streamlit run streamlit/app.py

st.set_page_config(
    page_title="VTuber 直播分析",
    layout="wide"
)

st.title("📊 VTuber 直播數據分析")

st.markdown("""
1.開台時間分布（Global Time Profile）
2.各時段觀眾變化（Individual Time Diff Heatmap）
3.同時直播競爭分析（By Time）
""")
