import streamlit as st

st.title("测试应用")
st.write("这是一个简单的测试应用。")

option = st.selectbox("选择一个选项", ["选项1", "选项2", "选项3"])
st.write(f"你选择了: {option}")

if st.button("点击我"):
    st.success("按钮被点击了！")

st.text_input("输入一些文本")