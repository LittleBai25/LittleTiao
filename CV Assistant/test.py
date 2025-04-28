import streamlit as st
from markitdown import MarkItDown
import requests
import io
# 添加 langgraph 相关导入
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import OpenAIChatNode
import openai

st.set_page_config(page_title="个人简历写作助理", layout="wide")

# 读取API KEY
api_key = st.secrets.get("OPENROUTER_API_KEY", "")

# Tab布局
TAB1, TAB2 = st.tabs(["文件上传", "模型与提示词调试"])

# 获取模型列表（从secrets读取，逗号分隔）
def get_model_list():
    model_str = st.secrets.get("OPENROUTER_MODEL", "")
    if model_str:
        return [m.strip() for m in model_str.split(",") if m.strip()]
    else:
        return ["qwen/qwen-max", "deepseek/deepseek-chat-v3-0324:free", "qwen-turbo", "其它模型..."]

with TAB1:
    st.header("上传你的简历素材和支持文件")
    resume_file = st.file_uploader("个人简历素材表（单选）", type=["pdf", "docx", "doc", "png", "jpg", "jpeg"], accept_multiple_files=False)
    support_files = st.file_uploader("支持文件（可多选）", type=["pdf", "docx", "doc", "png", "jpg", "jpeg"], accept_multiple_files=True)

    def read_file(file):
        try:
            file_bytes = file.read()
            # 将 bytes 转换为 BytesIO 对象，这是一个 BinaryIO 类型
            file_stream = io.BytesIO(file_bytes)
            
            md = MarkItDown()
            # 传递 file_stream 而不是原始字节
            raw_content = md.convert(file_stream)
            return raw_content
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
    model_list = get_model_list()
    model = st.selectbox("选择大模型", model_list)
    persona = st.text_area("人物设定", placeholder="如：我是应届毕业生，主修计算机科学……")
    task = st.text_area("任务描述", placeholder="如：请根据我的简历素材，生成一份针对XX岗位的简历……")
    output_format = st.text_area("输出格式", placeholder="如：请用markdown格式输出，包含以下部分……")

    if st.button("发送到大模型"):
        if not api_key:
            st.error("请在 Streamlit secrets 中配置 OPENROUTER_API_KEY")
        else:
            # 准备 prompt
            prompt = f"人物设定：{persona}\n任务描述：{task}\n输出格式：{output_format}"
            
            with st.spinner("AI 正在处理中..."):
                try:
                    # 设置 OpenAI 配置
                    openai.api_key = api_key
                    openai.base_url = "https://openrouter.ai/api/v1"
                    
                    # 构建 LangGraph 处理流程
                    def create_cv_graph():
                        # 创建 LLM 节点
                        llm_node = OpenAIChatNode(model=model)
                        
                        # 创建图结构
                        workflow = StateGraph()
                        
                        # 添加节点
                        workflow.add_node("generate_cv", llm_node)
                        
                        # 设置入口点
                        workflow.set_entry_point("generate_cv")
                        
                        # 设置流程完成点
                        workflow.set_finish_point("generate_cv", END)
                        
                        # 编译图为可执行对象
                        return workflow.compile()
                    
                    # 初始化图结构并执行
                    cv_chain = create_cv_graph()
                    
                    # 准备输入数据
                    input_data = {"messages": [{"role": "user", "content": prompt}]}
                    
                    # 执行图并获取结果
                    result = cv_chain.invoke(input_data)
                    
                    # 从结果中提取 AI 回复
                    output = result["messages"][-1]["content"]
                    
                    # 显示回复
                    st.markdown(output, unsafe_allow_html=True)
                
                except Exception as e:
                    st.error(f"LangGraph 处理失败: {str(e)}")