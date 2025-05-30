import streamlit as st

st.set_page_config(page_title="Streamlit Test")
st.title("🧪 Streamlit動作テスト")
st.write("Hello Streamlit!")
st.success("✅ 正常に動作しています")

if st.button("テストボタン"):
    st.balloons()
    st.write("🎉 ボタンが動作しました！")

st.sidebar.title("サイドバーテスト")
st.sidebar.write("サイドバーも動作中")