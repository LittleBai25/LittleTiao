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
import uuid
from datetime import datetime

class ChatState(TypedDict):
    messages: List[BaseMessage]
    support_analysis: str

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
    
# 新增：支持文件分析agent的提示词
if "support_analyst_persona" not in st.session_state:
    st.session_state.support_analyst_persona = "我是一位专业的支持文件分析师，擅长从各种文档中提取关键信息和经历要点。我会仔细分析文件内容，找出最相关、最有价值的经历、技能和成就，并以清晰的方式组织这些信息。"
if "support_analyst_task" not in st.session_state:
    st.session_state.support_analyst_task = "请分析提供的支持文件，提取所有关键的工作经历、项目经验、技能证书和主要成就。将这些内容整理成结构化的关键要点，以便在简历中使用。需要特别关注：时间段、职位名称、公司/机构名称、职责描述、成就和量化结果。"
if "support_analyst_output_format" not in st.session_state:
    st.session_state.support_analyst_output_format = "请以markdown格式输出，使用以下结构：\n\n## 工作经历\n- [时间段] [公司名称] - [职位]\n  - 职责/成就1（尽量包含量化结果）\n  - 职责/成就2\n\n## 教育背景\n- [时间段] [学校名称] - [学位/专业]\n\n## 技能与证书\n- 技能分类1：具体技能列表\n- 证书：证书名称及获取时间\n\n## 项目经验\n- [项目名称]：简短描述及成果"

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
        "output_format": st.session_state.output_format,
        # 新增：支持文件分析agent的提示词
        "support_analyst_persona": st.session_state.support_analyst_persona,
        "support_analyst_task": st.session_state.support_analyst_task,
        "support_analyst_output_format": st.session_state.support_analyst_output_format
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
                # 新增：支持文件分析agent的提示词
                st.session_state.support_analyst_persona = prompts.get("support_analyst_persona", "")
                st.session_state.support_analyst_task = prompts.get("support_analyst_task", "")
                st.session_state.support_analyst_output_format = prompts.get("support_analyst_output_format", "")
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
def process_with_model(support_analyst_model, cv_assistant_model, resume_content, support_files_content, 
                      persona, task, output_format, 
                      support_analyst_persona, support_analyst_task, support_analyst_output_format):
    
    # 主运行ID
    main_run_id = str(uuid.uuid4())
    
    # 检查是否有支持文件
    has_support_files = len(support_files_content) > 0
    
    # 显示处理进度
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 创建日志区域
    debug_expander = st.expander("调试信息", expanded=False)
    
    try:
        # 1. 如果有支持文件，先用支持文件分析agent处理
        support_analysis_result = ""
        
        if has_support_files:
            status_text.text("第一阶段：正在分析支持文件...")
            with debug_expander:
                st.write("检测到支持文件，准备调用支持文件分析agent")
                st.write(f"支持文件数量: {len(support_files_content)}")
            
            # 准备支持文件的内容
            support_files_text = ""
            for i, content in enumerate(support_files_content):
                support_files_text += f"--- 文件 {i+1} ---\n{content}\n\n"
            
            # 构建支持文件分析agent的提示词
            support_prompt = f"""人物设定：{support_analyst_persona}

任务描述：{support_analyst_task}

输出格式：{support_analyst_output_format}

支持文件内容：
{support_files_text}
"""
            with debug_expander:
                st.write("### 支持文件分析agent的提示词")
                st.code(support_prompt, language="markdown")
            
            # 调用支持文件分析agent
            with debug_expander:
                st.write(f"开始调用支持文件分析agent，使用模型: {support_analyst_model}")
            
            try:
                support_analysis_result = run_agent(
                    "supporting_doc_analyst",
                    support_analyst_model,
                    support_prompt,
                    main_run_id
                )
                
                with debug_expander:
                    st.write("支持文件分析agent返回结果:")
                    st.write("结果长度:", len(support_analysis_result) if support_analysis_result else 0)
                    st.code(support_analysis_result[:500] + "..." if len(support_analysis_result) > 500 else support_analysis_result)
                
                # 验证第一个agent的输出
                if not support_analysis_result or len(support_analysis_result.strip()) < 10:
                    with debug_expander:
                        st.warning("警告：支持文件分析agent返回的结果为空或太短")
                    # 仍然继续，但使用原始支持文件
                    support_analysis_result = "支持文件分析agent未能提供有效分析。以下是原始支持文件内容：\n\n" + support_files_text
            
            except Exception as agent1_error:
                with debug_expander:
                    st.error(f"支持文件分析agent执行出错: {str(agent1_error)}")
                    import traceback
                    st.code(traceback.format_exc())
                # 仍然继续，但使用原始支持文件
                support_analysis_result = "支持文件分析agent执行出错。以下是原始支持文件内容：\n\n" + support_files_text
            
            progress_bar.progress(50)
            status_text.text("第一阶段完成：支持文件分析完毕")
        else:
            progress_bar.progress(50)
            status_text.text("未提供支持文件，跳过第一阶段分析")
            with debug_expander:
                st.write("未检测到支持文件，跳过第一阶段")
        
        # 2. 准备简历助手的输入
        status_text.text("第二阶段：正在生成简历...")
        
        # 准备简历素材内容
        file_contents = f"简历素材内容:\n{resume_content}\n\n"
        
        # 如果有支持文件分析结果，添加到提示中
        if has_support_files and support_analysis_result:
            file_contents += f"支持文件分析结果:\n{support_analysis_result}\n\n"
            with debug_expander:
                st.write("已将支持文件分析结果添加到第二阶段输入")
        
        # 或者直接添加原始支持文件内容（如果没有分析结果但有支持文件）
        elif has_support_files:
            file_contents += "支持文件内容:\n"
            for i, content in enumerate(support_files_content):
                file_contents += f"--- 文件 {i+1} ---\n{content}\n\n"
            with debug_expander:
                st.write("由于未获得支持文件分析结果，已将原始支持文件内容添加到第二阶段输入")
        
        # 构建最终的简历助手提示词
        cv_prompt = f"""人物设定：{persona}

任务描述：{task}

输出格式：{output_format}

文件内容：
{file_contents}
"""
        with debug_expander:
            st.write("### 简历助手agent的提示词")
            st.code(cv_prompt[:1000] + "..." if len(cv_prompt) > 1000 else cv_prompt, language="markdown")
            st.write(f"开始调用简历助手agent，使用模型: {cv_assistant_model}")
        
        # 调用简历助手agent
        try:
            final_result = run_agent(
                "cv_assistant", 
                cv_assistant_model,
                cv_prompt,
                main_run_id
            )
            
            with debug_expander:
                st.write("简历助手agent返回结果长度:", len(final_result) if final_result else 0)
        
        except Exception as agent2_error:
            with debug_expander:
                st.error(f"简历助手agent执行出错: {str(agent2_error)}")
                import traceback
                st.code(traceback.format_exc())
            raise  # 重新抛出异常，因为这是关键步骤
        
        progress_bar.progress(100)
        status_text.text("处理完成！")
        
        # 显示结果
        st.markdown(final_result, unsafe_allow_html=True)
        
        # 显示LangSmith链接（如果启用）
        if langsmith_api_key:
            langsmith_base_url = st.secrets.get("LANGSMITH_BASE_URL", "https://smith.langchain.com")
            langsmith_url = f"{langsmith_base_url}/projects/{langsmith_project}/runs/{main_run_id}"
            st.info(f"在LangSmith中查看此运行: [打开监控面板]({langsmith_url})")
            
    except Exception as e:
        progress_bar.progress(100)
        status_text.text("处理出错！")
        st.error(f"处理失败: {str(e)}")
        st.error("详细错误信息：")
        import traceback
        st.code(traceback.format_exc())

# 运行单个Agent的函数
def run_agent(agent_name, model, prompt, parent_run_id=None):
    # 创建agent运行ID
    agent_run_id = str(uuid.uuid4())
    
    # 创建调试信息
    debug_info = f"运行 {agent_name} (模型: {model})"
    print(debug_info)  # 控制台日志
    
    # 在LangSmith中记录agent运行开始（如果启用）
    if langsmith_client and parent_run_id:
        try:
            metadata = {
                "model": model,
                "agent": agent_name,
                "timestamp": datetime.now()
            }
            # 记录agent运行
            langsmith_client.create_run(
                name=f"{agent_name}",
                run_type="chain",
                inputs={"prompt": prompt},
                project_name=langsmith_project,
                run_id=agent_run_id,
                parent_run_id=parent_run_id,
                extra=metadata
            )
        except Exception as e:
            print(f"LangSmith运行创建失败: {str(e)}")
            st.warning(f"LangSmith运行创建失败: {str(e)}")
    
    try:
        # 创建 LLM 实例
        llm = ChatOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            model=model,
            temperature=0.7,
        )
        
        # 使用 langchain 的 ChatOpenAI 处理信息
        messages = [HumanMessage(content=prompt)]
        print(f"发送请求到 {model}...")
        result = llm.invoke(messages)
        print(f"收到 {model} 响应，长度: {len(result.content) if result.content else 0}")
        
        # 在LangSmith中记录LLM调用（如果启用）
        if langsmith_client and parent_run_id:
            try:
                # 更新agent运行结果
                langsmith_client.update_run(
                    run_id=agent_run_id,
                    outputs={"response": result.content},
                    end_time=datetime.now()
                )
            except Exception as e:
                print(f"LangSmith更新运行结果失败: {str(e)}")
                st.warning(f"LangSmith更新运行结果失败: {str(e)}")
        
        # 验证返回结果不为空
        if not result.content or len(result.content.strip()) == 0:
            error_msg = f"{agent_name} 返回了空结果"
            print(error_msg)
            return f"错误: {error_msg}"
            
        return result.content
        
    except Exception as e:
        error_msg = f"{agent_name} 执行时出错: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return f"错误: {error_msg}\n\n请检查API密钥和模型设置是否正确。"

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
            support_analyst_model = st.session_state.get("selected_support_analyst_model", get_model_list()[0])
            cv_assistant_model = st.session_state.get("selected_cv_assistant_model", get_model_list()[0])
            
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
                support_analyst_model,
                cv_assistant_model,
                st.session_state.resume_content, 
                st.session_state.support_files_content,
                st.session_state.persona,
                st.session_state.task,
                st.session_state.output_format,
                st.session_state.support_analyst_persona,
                st.session_state.support_analyst_task,
                st.session_state.support_analyst_output_format
            )

with TAB2:
    st.header("提示词与模型设置")
    
    # 尝试加载保存的提示词
    load_prompts()
    
    # 使用两列布局分别设置两个agent
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("支持文件分析 Agent (supporting_doc_analyst)")
        
        # 模型选择
        model_list = get_model_list()
        selected_support_analyst_model = st.selectbox(
            "选择支持文件分析模型", 
            model_list,
            key="support_analyst_model_selector"
        )
        # 将选择的模型保存到session_state
        st.session_state.selected_support_analyst_model = selected_support_analyst_model
        
        # 提示词输入区
        support_analyst_persona = st.text_area(
            "人物设定", 
            value=st.session_state.support_analyst_persona, 
            placeholder="如：我是一位专业的简历分析师，擅长从各种材料中提取关键经历要点……", 
            height=120
        )
        support_analyst_task = st.text_area(
            "任务描述", 
            value=st.session_state.support_analyst_task, 
            placeholder="如：请分析这些支持文件，提取关键的经历、技能和成就要点……", 
            height=120
        )
        support_analyst_output_format = st.text_area(
            "输出格式", 
            value=st.session_state.support_analyst_output_format, 
            placeholder="如：请用要点列表的形式整理出关键经历，每个要点包含时间、地点、职位、成就……", 
            height=120
        )
        
        # 更新session state
        st.session_state.support_analyst_persona = support_analyst_persona
        st.session_state.support_analyst_task = support_analyst_task
        st.session_state.support_analyst_output_format = support_analyst_output_format
    
    with col2:
        st.subheader("简历助手 Agent (cv_assistant)")
        
        # 模型选择
        selected_cv_assistant_model = st.selectbox(
            "选择简历生成模型", 
            model_list,
            key="cv_assistant_model_selector"
        )
        # 将选择的模型保存到session_state
        st.session_state.selected_cv_assistant_model = selected_cv_assistant_model
        
        # 提示词输入区
        persona = st.text_area(
            "人物设定", 
            value=st.session_state.persona, 
            placeholder="如：我是应届毕业生，主修计算机科学……", 
            height=120
        )
        task = st.text_area(
            "任务描述", 
            value=st.session_state.task, 
            placeholder="如：请根据我的简历素材和支持文件分析结果，生成一份针对XX岗位的简历……", 
            height=120
        )
        output_format = st.text_area(
            "输出格式", 
            value=st.session_state.output_format, 
            placeholder="如：请用markdown格式输出，包含以下部分……", 
            height=120
        )
        
        # 更新session state
        st.session_state.persona = persona
        st.session_state.task = task
        st.session_state.output_format = output_format
    
    # 保存按钮 (跨两列)
    if st.button("保存所有提示词", use_container_width=True):
        # 保存到文件
        if save_prompts():
            st.success("所有提示词已保存到文件，下次启动应用时会自动加载")
            
    # 添加处理流程说明
    st.info("""
    **处理流程说明**:
    1. 如果上传了支持文件，系统将先使用支持文件分析agent分析这些文件，提取经历要点
    2. 然后系统将使用简历助手agent，综合分析简历素材表和上一步的分析结果，生成最终简历
    3. 如果没有上传支持文件，系统将直接使用简历助手agent处理简历素材表
    """)

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