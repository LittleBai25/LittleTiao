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
from langsmith import Client
from langchain_core.tracers import LangChainTracer
import uuid

class ChatState(TypedDict):
    messages: List[BaseMessage]

st.set_page_config(page_title="个人简历写作助手", layout="wide")

# 读取API KEY
api_key = st.secrets.get("OPENROUTER_API_KEY", "")

# 读取LangSmith配置（从secrets或环境变量）
langsmith_api_key = st.secrets.get("LANGSMITH_API_KEY", os.environ.get("LANGSMITH_API_KEY", ""))
langsmith_project = st.secrets.get("LANGSMITH_PROJECT", os.environ.get("LANGSMITH_PROJECT", "cv-assistant"))

# 设置LangSmith环境变量
if langsmith_api_key:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = langsmith_project

# 初始化LangSmith客户端（如果配置了API Key）
langsmith_client = None
if langsmith_api_key:
    try:
        langsmith_client = Client(api_key=langsmith_api_key)
        # 创建项目（如果不存在）
        projects = langsmith_client.list_projects()
        project_names = [p.name for p in projects]
        if langsmith_project not in project_names:
            langsmith_client.create_project(langsmith_project)
    except Exception as e:
        st.warning(f"LangSmith初始化失败: {str(e)}")

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
            # 创建唯一的运行ID用于跟踪
            run_id = str(uuid.uuid4())
            
            # 创建回调列表
            callbacks = []
            
            # 根据最新API添加LangChain追踪（如果启用了LangSmith）
            if langsmith_api_key:
                try:
                    from langchain.callbacks.tracers import LangChainTracer
                    # 使用新的方式初始化tracer
                    tracer = LangChainTracer(project_name=langsmith_project)
                    callbacks.append(tracer)
                except Exception as e:
                    st.warning(f"无法创建LangSmith追踪器: {str(e)}")
            
            # 构建 LangGraph 处理流程
            def create_cv_graph():
                # 创建 LLM 节点，使用 ChatOpenAI
                llm = ChatOpenAI(
                    api_key=api_key,
                    base_url="https://openrouter.ai/api/v1",
                    model=model,
                    temperature=0.7,
                    # 添加追踪器到回调
                    callbacks=callbacks if callbacks else None
                )
                
                # 定义 LLM 节点处理函数
                def llm_node(state: ChatState) -> ChatState:
                    messages = state.get("messages", [])
                    # 在LangSmith中记录请求
                    if langsmith_client:
                        try:
                            metadata = {
                                "model": model,
                                "message_count": len(messages),
                                "action": "generate_cv"
                            }
                            langsmith_client.create_run(
                                name="简历生成",
                                run_type="llm",
                                inputs={"messages": [m.content for m in messages]},
                                project_name=langsmith_project,
                                run_id=run_id,
                                extra=metadata
                            )
                        except Exception as e:
                            st.warning(f"LangSmith跟踪错误: {str(e)}")
                    
                    # 使用 langchain 的 ChatOpenAI 处理信息
                    result = llm.invoke(messages)
                    
                    # 在LangSmith中记录结果
                    if langsmith_client:
                        try:
                            langsmith_client.update_run(
                                run_id=run_id,
                                outputs={"content": result.content},
                                end_time=None  # 让LangSmith自动计算结束时间
                            )
                        except Exception as e:
                            st.warning(f"LangSmith更新错误: {str(e)}")
                    
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
            
            # 显示LangSmith链接（如果启用）
            if langsmith_api_key:
                langsmith_base_url = st.secrets.get("LANGSMITH_BASE_URL", "https://smith.langchain.com")
                langsmith_url = f"{langsmith_base_url}/projects/{langsmith_project}/runs/{run_id}"
                st.info(f"在LangSmith中查看此运行: [打开监控面板]({langsmith_url})")
        
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

# 添加LangSmith状态指示器
with st.sidebar:
    st.title("系统状态")
    
    # 显示API连接状态
    st.subheader("API连接")
    if api_key:
        st.success("OpenRouter API已配置")
    else:
        st.error("OpenRouter API未配置")
    
    # 显示LangSmith连接状态
    st.subheader("LangSmith监控")
    if langsmith_client:
        st.success(f"已连接到LangSmith")
        st.info(f"项目: {langsmith_project}")
        # 获取最近的运行记录
        try:
            runs = langsmith_client.list_runs(
                project_name=langsmith_project,
                limit=5
            )
            if runs:
                st.write("最近5次运行:")
                for run in runs:
                    st.write(f"- {run.name} ({run.run_type}) - {run.status}")
        except:
            st.write("无法获取最近运行记录")
    else:
        st.warning("LangSmith未配置")
        st.info("如需启用AI监控，请设置LANGSMITH_API_KEY")