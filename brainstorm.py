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
def setup_openai_api():
    if 'OPENAI_API_KEY' in st.session_state:
        openai.api_key = st.session_state['OPENAI_API_KEY']
        return True
    return False

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
    if not setup_openai_api():
        return "请先设置OpenAI API密钥"
    
    try:
        response = openai.ChatCompletion.create(
            model=st.session_state.get('model_name', 'gpt-4'),
            messages=[
                {"role": "system", "content": "你是一个专业的内容简化助手，请根据用户的方向，提取并简化文档中的关键信息。"},
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
    if not setup_openai_api():
        return "请先设置OpenAI API密钥"
    
    try:
        response = openai.ChatCompletion.create(
            model=st.session_state.get('model_name', 'gpt-4'),
            messages=[
                {"role": "system", "content": "你是一个专业的分析报告生成助手，你的任务是根据简化后的内容和用户的研究方向，生成一份深入的分析报告。"},
                {"role": "user", "content": f"我的研究方向是: {direction}\n\n基于以下简化后的内容，请为我生成一份详细的分析报告，包括关键发现、潜在机会和建议:\n{simplified_content}"}
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
    st.session_state['simplify_prompt'] = st.session_state.simplify_prompt_input
    st.session_state['analysis_prompt'] = st.session_state.analysis_prompt_input
    st.success("提示词已保存!")

# 初始化会话状态变量
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'direction' not in st.session_state:
    st.session_state.direction = ""
if 'simplified_content' not in st.session_state:
    st.session_state.simplified_content = ""
if 'analysis_report' not in st.session_state:
    st.session_state.analysis_report = ""
if 'simplify_prompt' not in st.session_state:
    st.session_state.simplify_prompt = "你是一个专业的内容简化助手，请根据用户的方向，提取并简化文档中的关键信息。"
if 'analysis_prompt' not in st.session_state:
    st.session_state.analysis_prompt = "你是一个专业的分析报告生成助手，你的任务是根据简化后的内容和用户的研究方向，生成一份深入的分析报告。"
if 'model_name' not in st.session_state:
    st.session_state.model_name = "gpt-4"

# 创建两个标签页
tab1, tab2 = st.tabs(["脑暴助理", "管理员设置"])

# 用户界面标签页
with tab1:
    st.title("🧠 脑暴助理")
    st.markdown("欢迎使用脑暴助理！上传您的文件，输入研究方向，获取专业分析报告。")

    # 第一步：上传文件和输入方向
    if st.session_state.step == 1:
        st.header("第一步：上传文件和输入研究方向")
        
        uploaded_files = st.file_uploader("上传文件（支持CSV, Excel, TXT, MD, JSON）", 
                                         type=['csv', 'xlsx', 'xls', 'txt', 'md', 'json'], 
                                         accept_multiple_files=True)
        
        direction = st.text_area("请输入您的研究方向", 
                                 height=100, 
                                 help="详细描述您的研究方向，帮助AI更好地理解您的需求")
        
        if st.button("下一步", disabled=not uploaded_files or not direction):
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
            st.session_state.step = 2
            st.experimental_rerun()

    # 第二步：内容简化
    elif st.session_state.step == 2:
        st.header("第二步：内容简化")
        
        st.write(f"研究方向: {st.session_state.direction}")
        
        all_content = ""
        for file_path in st.session_state.uploaded_files:
            file_ext = Path(file_path).suffix.lower().replace(".", "")
            content = process_file(file_path, file_ext)
            file_name = os.path.basename(file_path)
            st.subheader(f"文件: {file_name}")
            with st.expander("查看文件内容"):
                st.text(content)
            all_content += f"\n\n===== 文件: {file_name} =====\n\n{content}"
        
        if st.button("简化内容"):
            with st.spinner("正在简化内容..."):
                simplified = simplify_content(all_content, st.session_state.direction)
                st.session_state.simplified_content = simplified
                st.session_state.step = 3
                st.experimental_rerun()
                
        if st.button("返回上一步"):
            st.session_state.step = 1
            st.experimental_rerun()

    # 第三步：生成分析报告
    elif st.session_state.step == 3:
        st.header("第三步：生成分析报告")
        
        st.write(f"研究方向: {st.session_state.direction}")
        
        with st.expander("查看简化后的内容"):
            st.markdown(st.session_state.simplified_content)
        
        if not st.session_state.analysis_report:
            if st.button("生成分析报告"):
                with st.spinner("正在生成分析报告..."):
                    report = generate_analysis(st.session_state.simplified_content, st.session_state.direction)
                    st.session_state.analysis_report = report
                    st.experimental_rerun()
        else:
            st.subheader("分析报告")
            st.markdown(st.session_state.analysis_report)
            
            # 导出选项
            col1, col2 = st.columns(2)
            with col1:
                if st.download_button(
                    label="导出报告为TXT",
                    data=st.session_state.analysis_report,
                    file_name="分析报告.txt",
                    mime="text/plain"
                ):
                    st.success("报告已导出为TXT文件")
            
            with col2:
                if st.download_button(
                    label="导出报告为Markdown",
                    data=st.session_state.analysis_report,
                    file_name="分析报告.md",
                    mime="text/markdown"
                ):
                    st.success("报告已导出为Markdown文件")
        
        if st.button("重新开始"):
            st.session_state.step = 1
            st.session_state.simplified_content = ""
            st.session_state.analysis_report = ""
            st.experimental_rerun()
            
        if st.button("返回上一步"):
            st.session_state.step = 2
            st.session_state.analysis_report = ""
            st.experimental_rerun()

# 管理员设置标签页
with tab2:
    st.title("🔧 管理员设置")
    st.markdown("配置AI模型和提示词")
    
    # OpenAI API设置
    st.header("API设置")
    api_key = st.text_input("OpenAI API密钥", 
                           type="password", 
                           help="输入您的OpenAI API密钥",
                           value=st.session_state.get('OPENAI_API_KEY', ''))
    
    model_options = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
    selected_model = st.selectbox("选择模型", 
                                 options=model_options,
                                 index=model_options.index(st.session_state.model_name) if st.session_state.model_name in model_options else 1,
                                 help="选择要使用的OpenAI模型")
    
    if st.button("保存API设置"):
        st.session_state['OPENAI_API_KEY'] = api_key
        st.session_state['model_name'] = selected_model
        st.success("API设置已保存!")
    
    # 提示词设置
    st.header("提示词设置")
    
    st.subheader("简化内容提示词")
    simplify_prompt = st.text_area("简化内容提示词", 
                                  value=st.session_state.simplify_prompt,
                                  height=150,
                                  key="simplify_prompt_input")
    
    st.subheader("分析报告提示词")
    analysis_prompt = st.text_area("分析报告提示词", 
                                  value=st.session_state.analysis_prompt,
                                  height=150,
                                  key="analysis_prompt_input")
    
    if st.button("保存提示词设置"):
        save_prompts()

# 添加页脚
st.markdown("---")
st.markdown("© 2025 脑暴助理 | 由Streamlit和OpenAI提供支持")