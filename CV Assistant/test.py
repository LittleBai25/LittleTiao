import streamlit as st
import pandas as pd
import io
import requests
import json

# 设置页面标题和配置
st.set_page_config(
    page_title="个人简历写作助理",
    page_icon="📝",
    layout="wide"
)

# 从Streamlit Secrets获取API密钥
def get_api_key():
    try:
        return st.secrets["openrouter_api_key"]
    except Exception:
        return None

# 读取Excel文件
def read_excel(uploaded_file):
    try:
        return pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"无法读取Excel文件: {e}")
        return None

# 读取文本文件
def read_text_file(uploaded_file):
    try:
        return uploaded_file.getvalue().decode("utf-8")
    except Exception as e:
        st.error(f"无法读取文本文件: {e}")
        return None

# 处理上传的文件
def process_file(uploaded_file):
    if uploaded_file is None:
        return None
    
    file_extension = uploaded_file.name.split(".")[-1].lower()
    
    if file_extension in ["xlsx", "xls"]:
        return read_excel(uploaded_file)
    elif file_extension in ["txt", "md"]:
        return read_text_file(uploaded_file)
    else:
        return read_text_file(uploaded_file)

# 调用OpenRouter API
def call_openrouter_api(model, messages):
    api_key = get_api_key()
    
    if not api_key:
        st.error("未找到API密钥。请确保已在Streamlit的secrets中设置了openrouter_api_key。")
        return None
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": messages
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=json.dumps(data)
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API调用失败: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"API调用出错: {e}")
        return None

# 主应用
def main():
    st.title("个人简历写作助理")
    
    # 创建两个标签页
    tab1, tab2 = st.tabs(["📄 上传简历素材", "⚙️ 模型设置与提示词"])
    
    # 第一个标签页：文件上传
    with tab1:
        st.header("上传简历素材")
        
        # 个人简历素材表上传（单选，必传）
        st.subheader("个人简历素材表（单选，必传）")
        resume_file = st.file_uploader("选择您的个人简历素材表", 
                                      type=["xlsx", "xls", "txt", "md"], 
                                      key="resume_file")
        
        if resume_file is None:
            st.warning("⚠️ 个人简历素材表是必须上传的")
        else:
            # 处理简历文件
            resume_data = process_file(resume_file)
            if resume_data is not None:
                st.success(f"成功上传: {resume_file.name}")
                
                # 根据数据类型显示不同的预览
                with st.expander("预览简历素材表"):
                    if isinstance(resume_data, pd.DataFrame):
                        st.dataframe(resume_data)
                    else:
                        st.text(str(resume_data)[:1000] + "..." if len(str(resume_data)) > 1000 else str(resume_data))
                
                # 将数据保存到会话状态
                st.session_state['resume_data'] = resume_data
                st.session_state['resume_file_name'] = resume_file.name
        
        # 支持文件上传（多选，非必传）
        st.subheader("支持文件（多选，非必传）")
        support_files = st.file_uploader("选择支持文件", 
                                       type=["txt", "md", "xlsx", "xls"],
                                       accept_multiple_files=True,
                                       key="support_files")
        
        if support_files:
            st.success(f"成功上传 {len(support_files)} 个支持文件")
            
            support_data = {}
            for file in support_files:
                file_data = process_file(file)
                if file_data is not None:
                    support_data[file.name] = file_data
                    with st.expander(f"预览: {file.name}"):
                        if isinstance(file_data, pd.DataFrame):
                            st.dataframe(file_data)
                        else:
                            st.text(str(file_data)[:1000] + "..." if len(str(file_data)) > 1000 else str(file_data))
            
            # 将支持文件数据保存到会话状态
            st.session_state['support_data'] = support_data
    
    # 第二个标签页：模型设置和提示词
    with tab2:
        st.header("模型设置与提示词")
        
        # 模型选择
        st.subheader("选择大模型")
        models = [
            "anthropic/claude-3-5-sonnet",
            "anthropic/claude-3-opus",
            "anthropic/claude-3-haiku",
            "openai/gpt-4-turbo",
            "openai/gpt-4o",
            "openai/gpt-3.5-turbo"
        ]
        
        selected_model = st.selectbox("选择要使用的模型", models)
        st.session_state['selected_model'] = selected_model
        
        # 提示词设置
        st.subheader("提示词设置")
        
        # 默认值
        default_persona = """你是一位专业的简历顾问，擅长根据用户的经历和技能，编写出专业、吸引人的简历内容。"""
        default_task = """请根据提供的个人信息和支持材料，为用户编写一份针对特定职位的简历内容。"""
        default_format = """输出格式应包含以下部分：个人信息、个人简介、工作经历、教育背景、技能列表。"""
        
        # 创建三个文本框
        persona = st.text_area("人物设定", value=default_persona, height=100)
        task = st.text_area("任务描述", value=default_task, height=100)
        output_format = st.text_area("输出格式", value=default_format, height=100)
        
        # 保存到会话状态
        st.session_state['persona'] = persona
        st.session_state['task'] = task
        st.session_state['output_format'] = output_format
        
        # 生成简历按钮
        st.subheader("生成简历")
        
        if st.button("开始生成简历", type="primary"):
            # 检查是否上传了简历素材
            if 'resume_data' not in st.session_state:
                st.error("请先上传个人简历素材表！这是必须的。")
            else:
                with st.spinner("正在生成您的简历，请稍候..."):
                    # 准备API调用所需的数据
                    resume_data = st.session_state.get('resume_data')
                    resume_file_name = st.session_state.get('resume_file_name', '个人简历素材')
                    support_data = st.session_state.get('support_data', {})
                    
                    # 处理简历数据
                    resume_info = f"个人简历素材表（{resume_file_name}）内容：\n"
                    
                    if isinstance(resume_data, pd.DataFrame):
                        # 如果是DataFrame（Excel）
                        resume_info += str(resume_data)
                    else:
                        # 普通文本
                        resume_info += str(resume_data)
                    
                    # 整合支持文件内容
                    support_info = ""
                    if support_data:
                        support_info = "支持文件内容：\n"
                        for filename, content in support_data.items():
                            support_info += f"\n--- {filename} ---\n"
                            if isinstance(content, pd.DataFrame):
                                support_info += str(content)
                            else:
                                support_info += str(content)
                            support_info += "\n"
                    
                    # 构建完整的提示词
                    system_message = f"{persona}\n\n{task}\n\n{output_format}"
                    
                    user_message = f"""请根据以下提供的信息，按照要求编写一份专业的简历：

{resume_info}

{support_info if support_info else '未提供支持文件。'}

请根据以上信息，编写一份简历。"""
                    
                    # 准备API调用
                    messages = [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message}
                    ]
                    
                    # 调用API
                    response = call_openrouter_api(st.session_state['selected_model'], messages)
                    
                    if response:
                        try:
                            result = response['choices'][0]['message']['content']
                            st.session_state['resume_result'] = result
                            
                            # 显示结果
                            st.success("简历生成完成！")
                            st.subheader("生成的简历内容")
                            st.markdown(result)
                        except Exception as e:
                            st.error(f"处理API响应时出错: {e}")
                    else:
                        st.error("简历生成失败，请重试。")

if __name__ == "__main__":
    main()