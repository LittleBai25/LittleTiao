import streamlit as st
from markitdown import MarkItDown
import requests
import io
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import openai
from typing import TypedDict, List, Dict, Any
from langchain_core.messages import BaseMessage
import json
import os

class ChatState(TypedDict):
    messages: List[BaseMessage]

st.set_page_config(page_title="个人简历写作助手", layout="wide")

# 读取API KEY
api_key = st.secrets.get("OPENROUTER_API_KEY", "")

# 初始化session state用于存储提示词和文件内容
if "persona" not in st.session_state:
    st.session_state.persona = ""
if "task" not in st.session_state:
    st.session_state.task = ""
if "output_format" not in st.session_state:
    st.session_state.output_format = ""
if "resume_content" not in st.session_state:
    st.session_state.resume_content = ""
if "support_files_content" not in st.session_state:
    st.session_state.support_files_content = []

# 获取模型列表（从secrets读取，逗号分隔）
def get_model_list():
    model_str = st.secrets.get("OPENROUTER_MODEL", "")
    if model_str:
        return [m.strip() for m in model_str.split(",") if m.strip()]
    else:
        return ["qwen/qwen-max", "deepseek/deepseek-chat-v3-0324:free", "qwen-turbo", "其它模型..."]

# 保存提示词到文件
def save_prompts():
    prompts = {
        "persona": st.session_state.persona,
        "task": st.session_state.task,
        "output_format": st.session_state.output_format
    }
    # 创建保存目录
    os.makedirs("prompts", exist_ok=True)
    with open("prompts/saved_prompts.json", "w", encoding="utf-8") as f:
        json.dump(prompts, f, ensure_ascii=False, indent=2)
    return True

# 加载保存的提示词
def load_prompts():
    try:
        if os.path.exists("prompts/saved_prompts.json"):
            with open("prompts/saved_prompts.json", "r", encoding="utf-8") as f:
                prompts = json.load(f)
                st.session_state.persona = prompts.get("persona", "")
                st.session_state.task = prompts.get("task", "")
                st.session_state.output_format = prompts.get("output_format", "")
            return True
        return False
    except Exception as e:
        st.error(f"加载提示词失败: {str(e)}")
        return False

# 读取文件内容函数
def read_file(file):
    try:
        file_bytes = file.read()
        file_stream = io.BytesIO(file_bytes)
        md = MarkItDown()
        raw_content = md.convert(file_stream)
        return raw_content
    except Exception as e:
        return f"[MarkItDown 解析失败: {e}]"

# 处理模型调用
def process_with_model(model, resume_content, support_files_content, persona, task, output_format):
    # 准备提示词和文件内容
    file_contents = f"简历素材内容:\n{resume_content}\n\n"
    
    if support_files_content:
        file_contents += "支持文件内容:\n"
        for i, content in enumerate(support_files_content):
            file_contents += f"--- 文件 {i+1} ---\n{content}\n\n"
    
    prompt = f"人物设定：{persona}\n\n任务描述：{task}\n\n输出格式：{output_format}\n\n文件内容：\n{file_contents}"
    
    with st.spinner("AI 正在处理中..."):
        try:
            # 构建 LangGraph 处理流程
            def create_cv_graph():
                # 创建 LLM 节点，使用 ChatOpenAI
                llm = ChatOpenAI(
                    api_key=api_key,
                    base_url="https://openrouter.ai/api/v1",
                    model=model,
                    temperature=0.7
                )
                
                # 定义 LLM 节点处理函数
                def llm_node(state: ChatState) -> ChatState:
                    messages = state.get("messages", [])
                    # 使用 langchain 的 ChatOpenAI 处理信息
                    result = llm.invoke(messages)
                    # 更新状态
                    return {"messages": messages + [result]}
                
                # 创建图结构，并提供状态架构
                workflow = StateGraph(ChatState)
                
                # 添加自定义 LLM 节点
                workflow.add_node("generate_cv", llm_node)
                
                # 设置入口点
                workflow.set_entry_point("generate_cv")
                
                # 设置流程完成点 - 修复方法调用
                workflow.add_edge("generate_cv", END)
                
                # 编译图为可执行对象
                return workflow.compile()
            
            # 初始化图结构
            cv_chain = create_cv_graph()
            
            # 准备输入数据，使用langchain的消息格式
            input_data = {"messages": [HumanMessage(content=prompt)]}
            
            # 执行图并获取结果
            result = cv_chain.invoke(input_data)
            
            # 从结果中提取 AI 回复
            output = result["messages"][-1].content
            
            # 显示回复
            st.markdown(output, unsafe_allow_html=True)
        
        except Exception as e:
            st.error(f"LangChain/LangGraph 处理失败: {str(e)}")
            st.error("详细错误信息：")
            import traceback
            st.code(traceback.format_exc())

# Tab布局
TAB1, TAB2 = st.tabs(["文件上传与分析", "提示词与模型设置"])

with TAB1:
    st.header("上传你的简历素材和支持文件")
    resume_file = st.file_uploader("个人简历素材表（单选）", type=["pdf", "docx", "doc", "png", "jpg", "jpeg"], accept_multiple_files=False)
    support_files = st.file_uploader("支持文件（可多选）", type=["pdf", "docx", "doc", "png", "jpg", "jpeg"], accept_multiple_files=True)
    
    # 添加"开始分析"按钮
    if st.button("开始分析", use_container_width=True):
        if not api_key:
            st.error("请在 Streamlit secrets 中配置 OPENROUTER_API_KEY")
        elif not resume_file:
            st.error("请上传简历素材表")
        else:
            # 从session_state获取模型
            model = st.session_state.get("selected_model", get_model_list()[0])
            
            # 读取文件内容
            resume_content = read_file(resume_file)
            st.session_state.resume_content = resume_content
            
            support_files_content = []
            if support_files:
                for f in support_files:
                    content = read_file(f)
                    support_files_content.append(content)
            st.session_state.support_files_content = support_files_content
            
            # 处理并显示结果
            process_with_model(
                model, 
                st.session_state.resume_content, 
                st.session_state.support_files_content,
                st.session_state.persona,
                st.session_state.task,
                st.session_state.output_format
            )

with TAB2:
    st.header("提示词与模型设置")
    
    # 尝试加载保存的提示词
    load_prompts()
    
    # 模型选择移到这里
    st.subheader("选择模型")
    model_list = get_model_list()
    selected_model = st.selectbox("选择大模型", model_list)
    # 将选择的模型保存到session_state
    st.session_state.selected_model = selected_model
    
    st.subheader("提示词设置")
    
    # 提示词输入区
    persona = st.text_area("人物设定", value=st.session_state.persona, placeholder="如：我是应届毕业生，主修计算机科学……", height=150)
    task = st.text_area("任务描述", value=st.session_state.task, placeholder="如：请根据我的简历素材，生成一份针对XX岗位的简历……", height=150)
    output_format = st.text_area("输出格式", value=st.session_state.output_format, placeholder="如：请用markdown格式输出，包含以下部分……", height=150)
    
    # 简化按钮，只保留一个保存按钮
    if st.button("保存提示词", use_container_width=True):
        # 更新session state
        st.session_state.persona = persona
        st.session_state.task = task
        st.session_state.output_format = output_format
        
        # 保存到文件
        if save_prompts():
            st.success("提示词已保存到文件，下次启动应用时会自动加载")
            
    # 添加简短的说明
    st.info("提示：保存后的提示词会在每次应用启动时自动加载。修改后需点击保存才会生效。")