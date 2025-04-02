import streamlit as st
import pandas as pd
import os
import tempfile
import re
from pathlib import Path
import json
import openai

# 页面配置
st.set_page_config(
    page_title="脑暴助理",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 设置API密钥
def setup_openai_api(model_type="simplify"):
    """根据不同的模型类型设置API密钥"""
    if model_type == "simplify":
        openai.api_key = st.secrets["OPENAI_API_KEY_SIMPLIFY"]
    else:  # analysis
        openai.api_key = st.secrets["OPENAI_API_KEY_ANALYSIS"]
    return True

# 文件处理函数
def process_file(file_path, file_type):
    """处理不同类型的文件并返回内容"""
    try:
        if file_type == "csv":
            return pd.read_csv(file_path).to_string()
        elif file_type == "xlsx" or file_type == "xls":
            return pd.read_excel(file_path).to_string()
        elif file_type == "txt" or file_type == "md":
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif file_type == "json":
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.dumps(json.load(f), ensure_ascii=False, indent=2)
        else:
            return f"不支持的文件类型: {file_type}"
    except Exception as e:
        return f"处理文件时出错: {str(e)}"

# 简化文件内容
def simplify_content(content, direction):
    """使用AI简化上传的文件内容"""
    setup_openai_api("simplify")
    
    try:
        backstory = st.session_state.get('backstory_prompt', "你是一个专业的内容简化助手。")
        task = st.session_state.get('task_prompt', "请根据用户的方向，提取并简化文档中的关键信息。")
        output_format = st.session_state.get('output_prompt', "以清晰的要点形式组织输出内容。")
        
        system_prompt = f"{backstory}\n\n{task}\n\n{output_format}"
        
        response = openai.ChatCompletion.create(
            model="gpt-4",  # 使用固定的模型
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"我需要针对以下方向简化这份文档的内容: {direction}\n\n文档内容:\n{content}"}
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        return response.choices[0].message['content']
    except Exception as e:
        return f"简化内容时出错: {str(e)}"

# 生成分析报告
def generate_analysis(simplified_content, direction):
    """使用AI生成分析报告"""
    setup_openai_api("analysis")
    
    try:
        backstory = st.session_state.get('backstory_prompt', "你是一个专业的分析报告生成助手。")
        task = st.session_state.get('task_prompt', "你的任务是根据简化后的内容和用户的研究方向，生成一份深入的分析报告。")
        output_format = st.session_state.get('output_prompt', "报告应包括关键发现、潜在机会和具体建议。")
        
        system_prompt = f"{backstory}\n\n{task}\n\n{output_format}"
        
        response = openai.ChatCompletion.create(
            model="gpt-4",  # 使用固定的模型
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"我的研究方向是: {direction}\n\n基于以下简化后的内容，请为我生成一份详细的分析报告:\n{simplified_content}"}
            ],
            temperature=0.5,
            max_tokens=3000,
        )
        return response.choices[0].message['content']
    except Exception as e:
        return f"生成分析报告时出错: {str(e)}"

# 保存提示词函数
def save_prompts():
    """保存当前的提示词到会话状态"""
    st.session_state['backstory_prompt'] = st.session_state.backstory_prompt_input
    st.session_state['task_prompt'] = st.session_state.task_prompt_input
    st.session_state['output_prompt'] = st.session_state.output_prompt_input
    st.success("提示词已保存!")

# 初始化会话状态变量
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'direction' not in st.session_state:
    st.session_state.direction = ""
if 'simplified_content' not in st.session_state:
    st.session_state.simplified_content = ""
if 'analysis_report' not in st.session_state:
    st.session_state.analysis_report = ""
if 'backstory_prompt' not in st.session_state:
    st.session_state.backstory_prompt = "你是一个专业的内容分析和头脑风暴助手。"
if 'task_prompt' not in st.session_state:
    st.session_state.task_prompt = "请根据用户的方向，分析文档内容并提供深入的见解。"
if 'output_prompt' not in st.session_state:
    st.session_state.output_prompt = "输出应包含关键发现、潜在机会和具体建议，格式清晰易读。"

# 创建两个标签页
tab1, tab2 = st.tabs(["脑暴助理", "管理员设置"])

# 用户界面标签页
with tab1:
    st.title("🧠 脑暴助理")
    st.markdown("欢迎使用脑暴助理！上传您的文件，输入研究方向，获取专业分析报告。")

    # 第一步：上传文件和输入方向
    st.header("第一步：上传文件和输入研究方向")
    
    uploaded_files = st.file_uploader("上传文件（支持CSV, Excel, TXT, MD, JSON）", 
                                     type=['csv', 'xlsx', 'xls', 'txt', 'md', 'json'], 
                                     accept_multiple_files=True)
    
    direction = st.text_area("请输入您的研究方向", 
                             height=100, 
                             help="详细描述您的研究方向，帮助AI更好地理解您的需求")
    
    # 第二步：生成头脑风暴辅助报告（只使用一个按钮）
    st.header("第二步：生成头脑风暴辅助报告")

    if st.button("开始脑暴", disabled=not uploaded_files or not direction):
        # 保存上传的文件到临时目录
        temp_dir = tempfile.mkdtemp()
        file_paths = []
        
        for file in uploaded_files:
            file_path = os.path.join(temp_dir, file.name)
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
            file_paths.append(file_path)
        
        st.session_state.uploaded_files = file_paths
        st.session_state.direction = direction
        
        # 处理上传的文件内容
        all_content = ""
        for file_path in file_paths:
            file_ext = Path(file_path).suffix.lower().replace(".", "")
            content = process_file(file_path, file_ext)
            file_name = os.path.basename(file_path)
            all_content += f"\n\n===== 文件: {file_name} =====\n\n{content}"
        
        # 简化内容
        with st.spinner("正在简化内容..."):
            simplified = simplify_content(all_content, direction)
            st.session_state.simplified_content = simplified
        
        # 生成分析报告
        with st.spinner("正在生成分析报告..."):
            report = generate_analysis(simplified, direction)
            st.session_state.analysis_report = report
        
        # 显示结果
        st.subheader("简化后的内容")
        with st.expander("查看简化后的内容"):
            st.markdown(simplified)
        
        st.subheader("分析报告")
        st.markdown(report)
        
        # 导出选项
        col1, col2 = st.columns(2)
        with col1:
            if st.download_button(
                label="导出报告为TXT",
                data=report,
                file_name="分析报告.txt",
                mime="text/plain"
            ):
                st.success("报告已导出为TXT文件")
        
        with col2:
            if st.download_button(
                label="导出报告为Markdown",
                data=report,
                file_name="分析报告.md",
                mime="text/markdown"
            ):
                st.success("报告已导出为Markdown文件")

# 管理员设置标签页
with tab2:
    st.title("🔧 管理员设置")
    st.markdown("配置AI提示词")
    
    # 提示词设置 - 分为三个部分
    st.header("提示词设置")
    
    st.subheader("Backstory")
    backstory_prompt = st.text_area("AI背景设定", 
                                   value=st.session_state.backstory_prompt,
                                   height=100,
                                   key="backstory_prompt_input",
                                   help="设定AI的角色和背景")
    
    st.subheader("Task Description")
    task_prompt = st.text_area("任务描述", 
                              value=st.session_state.task_prompt,
                              height=100,
                              key="task_prompt_input",
                              help="描述AI需要执行的具体任务")
    
    st.subheader("Output Format")
    output_prompt = st.text_area("输出格式", 
                                value=st.session_state.output_prompt,
                                height=100,
                                key="output_prompt_input",
                                help="指定AI输出的格式和风格")
    
    if st.button("保存提示词设置"):
        save_prompts()

# 添加页脚
st.markdown("---")
st.markdown("© 2025 脑暴助理 | 由Streamlit和OpenAI提供支持")
