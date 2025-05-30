import streamlit as st

st.set_page_config(page_title="Minimal Test")
st.title("🧪 最小限テスト")
st.write("Hello Streamlit!")
st.success("✅ 動作中")

if st.button("テストボタン"):
    st.balloons()
    st.write("ボタンが動作しました！")
