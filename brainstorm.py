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
from langchain.callbacks.streamlit import StreamlitCallbackHandler

# 页面配置
st.set_page_config(
    page_title="脑暴助理",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 设置API客户端
def get_langchain_chat(model_type="simplify", stream=False, st_container=None):
    """根据不同的模型类型设置API客户端"""
    # 使用OpenRouter API
    api_base = "https://openrouter.ai/api/v1"
    
    if model_type == "simplify":
        # 素材分析使用的API密钥和模型
        api_key = st.secrets.get("OPENROUTER_API_KEY_SIMPLIFY", "")
        model_name = st.secrets.get("OPENROUTER_MODEL_SIMPLIFY", "anthropic/claude-3-haiku")
        temperature = 0.3
        max_tokens = 2000
    else:  # analysis
        # 脑暴报告使用的API密钥和模型
        api_key = st.secrets.get("OPENROUTER_API_KEY_ANALYSIS", "")
        model_name = st.secrets.get("OPENROUTER_MODEL_ANALYSIS", "anthropic/claude-3-sonnet")
        temperature = 0.5
        max_tokens = 3000
        
    # 检查API密钥是否为空
    if not api_key:
        st.error(f"{'素材分析' if model_type == 'simplify' else '脑暴报告'} API密钥未设置！请在secrets.toml中配置。")
        st.stop()
    
    # 设置回调处理器
    callbacks = None
    if stream and st_container:
        callbacks = CallbackManager([StreamlitCallbackHandler(st_container)])
    
    # 创建LangChain ChatOpenAI客户端，不使用headers参数
    chat = ChatOpenAI(
        model_name=model_name,
        openai_api_key=api_key,
        openai_api_base=api_base,
        streaming=stream,
        temperature=temperature,
        max_tokens=max_tokens,
        callback_manager=callbacks if callbacks else None
    )
    
    return chat

# 文件处理函数
def process_file(file_path, file_type):
    """处理不同类型的文件并返回内容"""
    try:
        # 检查文件是否存在并有内容
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return f"警告: 文件 {os.path.basename(file_path)} 为空或不存在"
            
        if file_type == "docx" and DOCX_SUPPORT:
            doc = docx.Document(file_path)
            content = "\n".join([para.text for para in doc.paragraphs])
            # 记录日志，便于调试
            st.write(f"从DOCX文件 {os.path.basename(file_path)} 读取了 {len(content)} 字符")
            return content
        elif file_type == "doc":
            # 简单处理，提示用户doc格式可能不完全支持
            raw_content = open(file_path, 'rb').read().decode('utf-8', errors='ignore')
            st.write(f"从DOC文件 {os.path.basename(file_path)} 读取了 {len(raw_content)} 字符")
            return "注意：.doc格式不完全支持，建议转换为.docx格式。尝试读取内容如下：\n" + raw_content
        elif file_type == "pdf" and PDF_SUPPORT:
            pdf_reader = PdfReader(file_path)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            st.write(f"从PDF文件 {os.path.basename(file_path)} 读取了 {len(text)} 字符")
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
                    content = f.read()
                    st.write(f"从文本文件 {os.path.basename(file_path)} 读取了 {len(content)} 字符")
                    return content
            except:
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read().decode('utf-8', errors='ignore')
                        st.write(f"从二进制文件 {os.path.basename(file_path)} 读取了 {len(content)} 字符")
                        return content
                except:
                    return f"无法读取文件: {file_type}"
    except Exception as e:
        return f"处理文件时出错: {str(e)}"

# 简化文件内容
def simplify_content(content, direction, st_container=None):
    """使用AI简化上传的文件内容"""
    # 记录日志，确认内容长度
    st.write(f"准备分析的内容总长度: {len(content)} 字符")
    
    chat = get_langchain_chat("simplify", stream=True, st_container=st_container)
    
    try:
        backstory = st.session_state.get('material_backstory_prompt', "你是一个专业的内容分析助手。")
        task = st.session_state.get('material_task_prompt', "请根据用户的方向，提取并分析文档中的关键信息。")
        output_format = st.session_state.get('material_output_prompt', "以清晰的要点形式组织输出内容。")
        
        # 增强系统提示，避免输出固定模板
        system_prompt = f"""
{backstory}

{task}

{output_format}

重要说明：
1. 你必须严格分析用户提供的原始文档内容，不要生成与文档无关的内容
2. 不要输出任何模板化或重复的内容，如"请描述您对计算机科学专业产生兴趣的契机"
3. 如果文档内容与"留学"或"申请"相关，不要自动生成申请模板或问题列表
4. 你的分析必须100%基于用户提供的文件内容，避免猜测或假设
"""
        
        # 强化人类消息，确保模型理解任务
        human_prompt = f"""
我需要针对以下研究方向简化文档内容: {direction}

以下是完整的文档内容，请仔细阅读并提取关键信息：

---文档开始---
{content}
---文档结束---

请基于上述文档内容进行深入分析，不要输出任何与文档无关的内容，尤其不要输出重复的模板化问题。
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        # 记录发送给AI的消息长度
        st.write(f"发送给AI的系统提示长度: {len(system_prompt)} 字符")
        st.write(f"发送给AI的人类消息长度: {len(human_prompt)} 字符")
        
        response = chat(messages)
        return response.content
    except Exception as e:
        return f"简化内容时出错: {str(e)}"

# 生成分析报告
def generate_analysis(simplified_content, direction, st_container=None):
    """使用AI生成分析报告"""
    chat = get_langchain_chat("analysis", stream=True, st_container=st_container)
    
    try:
        backstory = st.session_state.get('brainstorm_backstory_prompt', "你是一个专业的头脑风暴报告生成助手。")
        task = st.session_state.get('brainstorm_task_prompt', "你的任务是根据素材分析内容和用户的研究方向，生成一份创新的头脑风暴报告。")
        output_format = st.session_state.get('brainstorm_output_prompt', "报告应包括关键发现、创新思路、潜在机会和具体建议。")
        
        # 增强系统提示
        system_prompt = f"""
{backstory}

{task}

{output_format}

重要说明：
1. 你的报告必须基于用户提供的素材分析内容，不要生成与素材无关的内容
2. 不要输出任何模板化或重复的内容
3. 请确保报告的内容与用户的研究方向相关并基于素材分析结果
"""
        
        # 强化人类消息
        human_prompt = f"""
我的研究方向是: {direction}

以下是简化后的素材内容，请基于这些内容生成详细的分析报告:

---素材开始---
{simplified_content}
---素材结束---

请基于上述素材内容生成有深度的头脑风暴报告，不要输出任何与上述素材无关的内容。
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
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
tab1, tab2 = st.tabs(["脑暴助理", "管理员设置"])

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
        # 创建一个折叠面板用于显示调试信息
        debug_expander = st.expander("文件处理调试信息", expanded=False)
        
        with debug_expander:
            st.write(f"处理 {len(uploaded_files)} 个上传文件")
        
        # 保存上传的文件到临时目录
        temp_dir = tempfile.mkdtemp()
        file_paths = []
        
        for file in uploaded_files:
            file_path = os.path.join(temp_dir, file.name)
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
            file_paths.append(file_path)
            with debug_expander:
                st.write(f"保存文件: {file.name}, 大小: {len(file.getbuffer())} 字节")
        
        # 确保立即保存方向信息到会话状态
        st.session_state.uploaded_files = file_paths
        st.session_state.direction = direction
        
        # 处理上传的文件内容
        all_content = ""
        for file_path in file_paths:
            file_ext = Path(file_path).suffix.lower().replace(".", "")
            with debug_expander:
                st.write(f"处理文件: {os.path.basename(file_path)}, 类型: {file_ext}")
            
            content = process_file(file_path, file_ext)
            file_name = os.path.basename(file_path)
            all_content += f"\n\n===== 文件: {file_name} =====\n\n{content}"
        
        # 验证文件内容
        if not all_content or len(all_content.strip()) < 50:
            st.error("❌ 文件内容似乎为空或过短。请确保上传了有效的文件。")
            with debug_expander:
                st.write("文件内容为空或过短")
                st.write(f"内容长度: {len(all_content)} 字符")
                st.write(f"内容预览: {all_content[:100]}...")
            st.stop()
        
        with debug_expander:
            st.write(f"处理完成，总内容长度: {len(all_content)} 字符")
            st.write("内容预览:")
            st.text(all_content[:500] + "..." if len(all_content) > 500 else all_content)
        
        # 创建一个容器用于流式输出
        analysis_container = st.empty()
        
        # 简化内容
        with st.spinner("正在分析素材..."):
            with debug_expander:
                st.write("开始调用 AI 简化内容...")
            
            simplified = simplify_content(all_content, direction, st_container=analysis_container)
            
            # 确保立即保存简化内容到会话状态
            st.session_state.simplified_content = simplified
            
            with debug_expander:
                st.write("AI 简化内容完成")
                st.write(f"简化内容长度: {len(simplified)} 字符")
        
        # 显示结果
        st.subheader("素材分析结果")
        st.markdown(simplified)
    
    # 第二步：生成头脑风暴辅助报告
    st.header("第二步：生成头脑风暴辅助报告")
    
    # 每次UI渲染时都确保研究方向同步更新
    if direction and direction != st.session_state.direction:
        st.session_state.direction = direction

    if st.button("生成脑暴报告", disabled=not (st.session_state.simplified_content and st.session_state.direction)):
        # 使用已经生成的简化内容和研究方向
        
        # 创建一个容器用于流式输出
        report_container = st.empty()
        
        # 生成分析报告
        with st.spinner("正在生成脑暴报告..."):
            report = generate_analysis(st.session_state.simplified_content, st.session_state.direction, st_container=report_container)
            st.session_state.analysis_report = report
        
        # 显示结果
        st.subheader("脑暴报告")
        st.markdown(report)

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

# 添加页脚
st.markdown("---")
st.markdown("© 2025 脑暴助理 | 由Streamlit、LangChain和OpenRouter提供支持")
