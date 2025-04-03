import streamlit as st
import os
import tempfile
import re
from pathlib import Path
import json
import io
# 尝试导入额外依赖，如果不可用则跳过
try:
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    import docx
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False

try:
    from PIL import Image
    IMAGE_SUPPORT = True
except ImportError:
    IMAGE_SUPPORT = False

# 导入 LangChain 相关库
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

# 页面配置
st.set_page_config(
    page_title="脑暴助理",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 设置API客户端
def get_langchain_chat(model_type="simplify"):
    """根据不同的模型类型设置API客户端"""
    # 使用OpenRouter API
    api_base = "https://openrouter.ai/api/v1"
    
    if model_type == "simplify":
        # 素材分析使用的API密钥和模型
        api_key = st.secrets.get("OPENROUTER_API_KEY_SIMPLIFY", "")
        # 优先使用会话状态中的模型设置
        model_name = st.session_state.get("OPENROUTER_MODEL_SIMPLIFY", 
                     st.secrets.get("OPENROUTER_MODEL_SIMPLIFY", "anthropic/claude-3-haiku"))
        temperature = 0.3
        max_tokens = 2000
    else:  # analysis
        # 脑暴报告使用的API密钥和模型
        api_key = st.secrets.get("OPENROUTER_API_KEY_ANALYSIS", "")
        # 优先使用会话状态中的模型设置
        model_name = st.session_state.get("OPENROUTER_MODEL_ANALYSIS", 
                     st.secrets.get("OPENROUTER_MODEL_ANALYSIS", "anthropic/claude-3-sonnet"))
        temperature = 0.5
        max_tokens = 3000
        
    # 检查API密钥是否为空
    if not api_key:
        st.error(f"{'素材分析' if model_type == 'simplify' else '脑暴报告'} API密钥未设置！请在API设置选项卡中配置。")
        st.stop()
    
    # 创建LangChain ChatOpenAI客户端
    chat = ChatOpenAI(
        model_name=model_name,
        openai_api_key=api_key,  # LangChain 使用 openai_api_key 参数名，但值可以是OpenRouter的API密钥
        openai_api_base=api_base,
        streaming=False,
        temperature=temperature,
        max_tokens=max_tokens,
        headers={"HTTP-Referer": "https://my-app.com"}  # OpenRouter需要
    )
    
    return chat

# 文件处理函数
def process_file(file_path, file_type):
    """处理不同类型的文件并返回内容"""
    try:
        if file_type == "docx" and DOCX_SUPPORT:
            doc = docx.Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        elif file_type == "doc":
            # 简单处理，提示用户doc格式可能不完全支持
            return "注意：.doc格式不完全支持，建议转换为.docx格式。尝试读取内容如下：\n" + open(file_path, 'rb').read().decode('utf-8', errors='ignore')
        elif file_type == "pdf" and PDF_SUPPORT:
            pdf_reader = PdfReader(file_path)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        elif file_type in ["jpg", "jpeg", "png"] and IMAGE_SUPPORT:
            # 简单记录图像信息，而不进行OCR
            image = Image.open(file_path)
            width, height = image.size
            return f"[图像文件，尺寸: {width}x{height}，类型: {image.format}。请在分析时考虑此图像可能包含的视觉内容。]"
        elif file_type in ["jpg", "jpeg", "png"] and not IMAGE_SUPPORT:
            return f"[图像文件: {os.path.basename(file_path)}。请在分析时考虑此图像可能包含的视觉内容。]"
        else:
            # 尝试作为文本文件读取
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except:
                try:
                    with open(file_path, 'rb') as f:
                        return f.read().decode('utf-8', errors='ignore')
                except:
                    return f"无法读取文件: {file_type}"
    except Exception as e:
        return f"处理文件时出错: {str(e)}"

# 简化文件内容
def simplify_content(content, direction):
    """使用AI简化上传的文件内容"""
    chat = get_langchain_chat("simplify")
    
    try:
        backstory = st.session_state.get('material_backstory_prompt', "你是一个专业的内容分析助手。")
        task = st.session_state.get('material_task_prompt', "请根据用户的方向，提取并分析文档中的关键信息。")
        output_format = st.session_state.get('material_output_prompt', "以清晰的要点形式组织输出内容。")
        
        system_prompt = f"{backstory}\n\n{task}\n\n{output_format}"
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"我需要针对以下方向简化这份文档的内容: {direction}\n\n文档内容:\n{content}")
        ]
        
        response = chat(messages)
        return response.content
    except Exception as e:
        return f"简化内容时出错: {str(e)}"

# 生成分析报告
def generate_analysis(simplified_content, direction):
    """使用AI生成分析报告"""
    chat = get_langchain_chat("analysis")
    
    try:
        backstory = st.session_state.get('brainstorm_backstory_prompt', "你是一个专业的头脑风暴报告生成助手。")
        task = st.session_state.get('brainstorm_task_prompt', "你的任务是根据素材分析内容和用户的研究方向，生成一份创新的头脑风暴报告。")
        output_format = st.session_state.get('brainstorm_output_prompt', "报告应包括关键发现、创新思路、潜在机会和具体建议。")
        
        system_prompt = f"{backstory}\n\n{task}\n\n{output_format}"
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"我的研究方向是: {direction}\n\n基于以下简化后的内容，请为我生成一份详细的分析报告:\n{simplified_content}")
        ]
        
        response = chat(messages)
        return response.content
    except Exception as e:
        return f"生成分析报告时出错: {str(e)}"

# 保存提示词函数
def save_prompts():
    """保存当前的提示词到会话状态"""
    # 保存素材分析提示词
    st.session_state['material_backstory_prompt'] = st.session_state.material_backstory_prompt_input
    st.session_state['material_task_prompt'] = st.session_state.material_task_prompt_input
    st.session_state['material_output_prompt'] = st.session_state.material_output_prompt_input
    
    # 保存脑暴报告提示词
    st.session_state['brainstorm_backstory_prompt'] = st.session_state.brainstorm_backstory_prompt_input
    st.session_state['brainstorm_task_prompt'] = st.session_state.brainstorm_task_prompt_input
    st.session_state['brainstorm_output_prompt'] = st.session_state.brainstorm_output_prompt_input
    
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

# 素材分析提示词初始化
if 'material_backstory_prompt' not in st.session_state:
    st.session_state.material_backstory_prompt = "你是一个专业的素材内容分析助手。"
if 'material_task_prompt' not in st.session_state:
    st.session_state.material_task_prompt = "请根据用户的方向，提取并分析文档中的关键信息。"
if 'material_output_prompt' not in st.session_state:
    st.session_state.material_output_prompt = "以清晰的要点形式组织输出内容，突出关键信息和见解。"

# 脑暴报告提示词初始化
if 'brainstorm_backstory_prompt' not in st.session_state:
    st.session_state.brainstorm_backstory_prompt = "你是一个专业的头脑风暴报告生成助手。"
if 'brainstorm_task_prompt' not in st.session_state:
    st.session_state.brainstorm_task_prompt = "你的任务是根据素材分析内容和用户的研究方向，生成一份创新的头脑风暴报告。"
if 'brainstorm_output_prompt' not in st.session_state:
    st.session_state.brainstorm_output_prompt = "报告应包括关键发现、创新思路、潜在机会和具体建议，格式清晰易读。"

# 创建两个标签页
tab1, tab2, tab3 = st.tabs(["脑暴助理", "管理员设置", "API设置"])

# 用户界面标签页
with tab1:
    st.title("🧠 脑暴助理")
    st.markdown("欢迎使用脑暴助理！上传您的文件，输入研究方向，获取专业分析报告。")

    # 第一步：上传文件和输入方向
    st.header("第一步：上传文件和输入研究方向")
    
    uploaded_files = st.file_uploader("上传文件（支持DOC, DOCX, PDF, JPG, PNG）", 
                                     type=['doc', 'docx', 'pdf', 'jpg', 'jpeg', 'png'], 
                                     accept_multiple_files=True)
    
    direction = st.text_area("请输入您的研究方向", 
                             height=100, 
                             help="详细描述您的研究方向，帮助AI更好地理解您的需求")
    
    if st.button("开始素材分析", disabled=not uploaded_files or not direction):
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
        with st.spinner("正在分析素材..."):
            simplified = simplify_content(all_content, direction)
            st.session_state.simplified_content = simplified
        
        # 显示结果
        st.subheader("素材分析结果")
        st.markdown(simplified)
    
    # 第二步：生成头脑风暴辅助报告
    st.header("第二步：生成头脑风暴辅助报告")

    if st.button("生成脑暴报告", disabled=not (st.session_state.simplified_content and st.session_state.direction)):
        # 使用已经生成的简化内容和研究方向
        
        # 生成分析报告
        with st.spinner("正在生成脑暴报告..."):
            report = generate_analysis(st.session_state.simplified_content, st.session_state.direction)
            st.session_state.analysis_report = report
        
        # 显示结果
        st.subheader("脑暴报告")
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
    
    # 素材分析提示词设置
    st.header("素材分析提示词设置")
    
    st.subheader("素材分析 - Backstory")
    material_backstory_prompt = st.text_area("素材分析AI背景设定", 
                                   value=st.session_state.material_backstory_prompt,
                                   height=100,
                                   key="material_backstory_prompt_input",
                                   help="设定素材分析AI的角色和背景")
    
    st.subheader("素材分析 - Task Description")
    material_task_prompt = st.text_area("素材分析任务描述", 
                              value=st.session_state.material_task_prompt,
                              height=100,
                              key="material_task_prompt_input",
                              help="描述素材分析AI需要执行的具体任务")
    
    st.subheader("素材分析 - Output Format")
    material_output_prompt = st.text_area("素材分析输出格式", 
                                value=st.session_state.material_output_prompt,
                                height=100,
                                key="material_output_prompt_input",
                                help="指定素材分析AI输出的格式和风格")
    
    # 脑暴报告提示词设置
    st.header("脑暴报告提示词设置")
    
    st.subheader("脑暴报告 - Backstory")
    brainstorm_backstory_prompt = st.text_area("脑暴报告AI背景设定", 
                                   value=st.session_state.brainstorm_backstory_prompt,
                                   height=100,
                                   key="brainstorm_backstory_prompt_input",
                                   help="设定脑暴报告AI的角色和背景")
    
    st.subheader("脑暴报告 - Task Description")
    brainstorm_task_prompt = st.text_area("脑暴报告任务描述", 
                              value=st.session_state.brainstorm_task_prompt,
                              height=100,
                              key="brainstorm_task_prompt_input",
                              help="描述脑暴报告AI需要执行的具体任务")
    
    st.subheader("脑暴报告 - Output Format")
    brainstorm_output_prompt = st.text_area("脑暴报告输出格式", 
                                value=st.session_state.brainstorm_output_prompt,
                                height=100,
                                key="brainstorm_output_prompt_input",
                                help="指定脑暴报告AI输出的格式和风格")
    
    if st.button("保存提示词设置"):
        save_prompts()

# 新增API设置标签页
with tab3:
    st.title("⚙️ API设置")
    st.markdown("配置OpenRouter API参数")
    
    # 添加说明
    st.info("""
    在此处配置OpenRouter API参数。您需要为素材分析和脑暴报告分别设置API密钥和模型。
    可以使用相同的API密钥，但建议为不同任务选择适合的模型。
    """)
    
    # 素材分析API设置
    st.header("素材分析API设置")
    
    # 使用会话状态存储模型名称
    if "OPENROUTER_MODEL_SIMPLIFY" not in st.session_state:
        st.session_state.OPENROUTER_MODEL_SIMPLIFY = st.secrets.get("OPENROUTER_MODEL_SIMPLIFY", "anthropic/claude-3-haiku")
    
    api_key_simplify = st.text_input(
        "素材分析API密钥", 
        value=st.secrets.get("OPENROUTER_API_KEY_SIMPLIFY", ""),
        type="password",
        help="输入您的OpenRouter API密钥"
    )
    
    model_name_simplify = st.text_input(
        "素材分析模型名称",
        value=st.session_state.OPENROUTER_MODEL_SIMPLIFY,
        help="例如：anthropic/claude-3-haiku, openai/gpt-4-turbo"
    )
    
    # 脑暴报告API设置
    st.header("脑暴报告API设置")
    
    # 使用会话状态存储模型名称
    if "OPENROUTER_MODEL_ANALYSIS" not in st.session_state:
        st.session_state.OPENROUTER_MODEL_ANALYSIS = st.secrets.get("OPENROUTER_MODEL_ANALYSIS", "anthropic/claude-3-sonnet")
    
    api_key_analysis = st.text_input(
        "脑暴报告API密钥", 
        value=st.secrets.get("OPENROUTER_API_KEY_ANALYSIS", ""),
        type="password",
        help="输入您的OpenRouter API密钥"
    )
    
    model_name_analysis = st.text_input(
        "脑暴报告模型名称",
        value=st.session_state.OPENROUTER_MODEL_ANALYSIS,
        help="例如：anthropic/claude-3-sonnet, openai/gpt-4-turbo"
    )
    
    if st.button("保存API设置"):
        # 把API设置保存到会话状态
        st.session_state.OPENROUTER_MODEL_SIMPLIFY = model_name_simplify
        st.session_state.OPENROUTER_MODEL_ANALYSIS = model_name_analysis
        
        # 提示用户需要手动更新secrets.toml文件
        st.success("""API设置已暂时保存到会话状态！

要永久保存这些设置，请在Streamlit应用的secrets.toml文件中添加以下内容：
```
OPENROUTER_API_KEY_SIMPLIFY = "您的素材分析API密钥"
OPENROUTER_MODEL_SIMPLIFY = "{}"
OPENROUTER_API_KEY_ANALYSIS = "您的脑暴报告API密钥"
OPENROUTER_MODEL_ANALYSIS = "{}"
```
""".format(model_name_simplify, model_name_analysis))

# 添加页脚
st.markdown("---")
st.markdown("© 2025 脑暴助理 | 由Streamlit、LangChain和OpenRouter提供支持")
