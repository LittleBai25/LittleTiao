import streamlit as st
from markitdown import MarkItDown
import requests

st.set_page_config(page_title="个人简历写作助理", layout="wide")

# 读取API KEY
api_key = st.secrets.get("OPENROUTER_API_KEY", "")

# Tab布局
TAB1, TAB2 = st.tabs(["文件上传", "模型与提示词调试"])

with TAB1:
    st.header("上传你的简历素材和支持文件")
    resume_file = st.file_uploader("个人简历素材表（单选）", type=["pdf", "docx", "doc", "png", "jpg", "jpeg"], accept_multiple_files=False)
    support_files = st.file_uploader("支持文件（可多选）", type=["pdf", "docx", "doc", "png", "jpg", "jpeg"], accept_multiple_files=True)

    def read_file(file):
        try:
            mkd = MarkItDown(file)
            md_content = mkd.to_markdown()
            return md_content
        except Exception as e:
            return f"[MarkItDown 解析失败: {e}]"

    if resume_file:
        st.subheader("简历素材内容预览：")
        content = read_file(resume_file)
        st.markdown(content, unsafe_allow_html=True)

    if support_files:
        st.subheader("支持文件内容预览：")
        for f in support_files:
            st.markdown(f"**{f.name}**")
            content = read_file(f)
            st.markdown(content, unsafe_allow_html=True)

with TAB2:
    st.header("模型选择与提示词调试")
    model = st.selectbox("选择大模型", ["gpt-3.5-turbo", "gpt-4", "qwen-turbo", "glm-4", "其它模型..."])
    persona = st.text_area("人物设定", placeholder="如：我是应届毕业生，主修计算机科学……")
    task = st.text_area("任务描述", placeholder="如：请根据我的简历素材，生成一份针对XX岗位的简历……")
    output_format = st.text_area("输出格式", placeholder="如：请用markdown格式输出，包含以下部分……")

    if st.button("发送到大模型"):
        if not api_key:
            st.error("请在 Streamlit secrets 中配置 OPENROUTER_API_KEY")
        else:
            prompt = f"人物设定：{persona}\n任务描述：{task}\n输出格式：{output_format}"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}]
            }
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data
            )
            if response.status_code == 200:
                result = response.json()
                output = result.get("choices", [{}])[0].get("message", {}).get("content", "无返回内容")
                st.markdown(output)
            else:
                st.error(f"API请求失败: {response.text}")