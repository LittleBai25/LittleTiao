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
    else:  # analysis
        # 脑暴报告使用的API密钥和模型
        api_key = st.secrets.get("OPENROUTER_API_KEY_ANALYSIS", "")
        model_name = st.secrets.get("OPENROUTER_MODEL_ANALYSIS", "anthropic/claude-3-sonnet")
        temperature = 0.5
        
    # 检查API密钥是否为空
    if not api_key:
        st.error(f"{'素材分析' if model_type == 'simplify' else '脑暴报告'} API密钥未设置！请在secrets.toml中配置。")
        st.stop()
    
    # 设置回调处理器
    callbacks = None
    if stream and st_container:
        callbacks = CallbackManager([StreamlitCallbackHandler(st_container)])
    
    # 创建LangChain ChatOpenAI客户端 - 使用最基本的参数
    chat = ChatOpenAI(
        model_name=model_name,
        openai_api_key=api_key,
        openai_api_base=api_base,
        streaming=stream,
        temperature=temperature,
        max_tokens=4000,  # 直接设置最大token
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
            try:
                doc = docx.Document(file_path)
                # 提取段落文本
                paragraphs_text = [para.text for para in doc.paragraphs if para.text.strip()]
                
                # 提取表格文本
                tables_text = []
                for table in doc.tables:
                    for row in table.rows:
                        row_text = [cell.text for cell in row.cells if cell.text.strip()]
                        if row_text:
                            tables_text.append(" | ".join(row_text))
                
                # 合并所有文本，先添加段落，然后添加表格内容
                all_text = paragraphs_text + tables_text
                content = "\n".join(all_text)
                
                # 记录日志，便于调试
                st.write(f"从DOCX文件 {os.path.basename(file_path)} 读取了 {len(content)} 字符")
                with debug_expander:
                    st.write(f"段落数: {len(paragraphs_text)}, 表格行数: {len(tables_text)}")
                    st.write(f"文档内容预览: {content[:200]}..." if len(content) > 200 else content)
                return content
            except Exception as e:
                error_msg = f"读取DOCX文件时出错: {str(e)}"
                st.error(error_msg)
                with debug_expander:
                    st.write(error_msg)
                return error_msg
        elif file_type == "doc":
            # 简单处理，提示用户doc格式可能不完全支持
            try:
                raw_content = open(file_path, 'rb').read().decode('utf-8', errors='ignore')
                st.write(f"从DOC文件 {os.path.basename(file_path)} 读取了 {len(raw_content)} 字符")
                return "注意：.doc格式不完全支持，建议转换为.docx格式。尝试读取内容如下：\n" + raw_content
            except Exception as e:
                error_msg = f"读取DOC文件时出错: {str(e)}"
                st.error(error_msg)
                return error_msg
        elif file_type == "pdf" and PDF_SUPPORT:
            try:
                pdf_reader = PdfReader(file_path)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                st.write(f"从PDF文件 {os.path.basename(file_path)} 读取了 {len(text)} 字符")
                return text
            except Exception as e:
                error_msg = f"读取PDF文件时出错: {str(e)}"
                st.error(error_msg)
                return error_msg
        elif file_type in ["jpg", "jpeg", "png"] and IMAGE_SUPPORT:
            # 简单记录图像信息，而不进行OCR
            try:
                image = Image.open(file_path)
                width, height = image.size
                info = f"[图像文件，尺寸: {width}x{height}，类型: {image.format}。请在分析时考虑此图像可能包含的视觉内容。]"
                st.write(f"处理图像文件: {os.path.basename(file_path)}")
                return info
            except Exception as e:
                error_msg = f"处理图像文件时出错: {str(e)}"
                st.error(error_msg)
                return error_msg
        elif file_type in ["jpg", "jpeg", "png"] and not IMAGE_SUPPORT:
            info = f"[图像文件: {os.path.basename(file_path)}。请在分析时考虑此图像可能包含的视觉内容。]"
            st.write(info)
            return info
        else:
            # 尝试作为文本文件读取
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    st.write(f"从文本文件 {os.path.basename(file_path)} 读取了 {len(content)} 字符")
                    return content
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read().decode('utf-8', errors='ignore')
                        st.write(f"从二进制文件 {os.path.basename(file_path)} 读取了 {len(content)} 字符")
                        return content
                except Exception as e:
                    error_msg = f"以二进制模式读取文件时出错: {str(e)}"
                    st.error(error_msg)
                    return error_msg
            except Exception as e:
                error_msg = f"读取文本文件时出错: {str(e)}"
                st.error(error_msg)
                return error_msg
    except Exception as e:
        error_msg = f"处理文件时出错: {str(e)}"
        st.error(error_msg)
        return error_msg

# 简化文件内容
def simplify_content(content, direction, st_container=None):
    """使用AI简化上传的文件内容"""
    # 记录日志，确认内容长度
    st.write(f"准备分析的内容总长度: {len(content)} 字符")
    
    # 获取API客户端 - 使用带有备用方案的流式输出
    chat = get_langchain_chat("simplify", stream=True, st_container=st_container)
    
    try:
        # 从会话状态获取提示词
        backstory = st.session_state.material_backstory_prompt
        task = st.session_state.material_task_prompt
        output_format = st.session_state.material_output_prompt
        
        # 构建系统提示 - 使用用户定义的提示词
        system_prompt = f"""{backstory}

{task}

{output_format}

请注意：
1. 只分析提供的文档内容
2. 输出必须与研究方向相关
3. 不要生成与文档无关的内容列表"""
        
        # 构建人类消息
        human_prompt = f"""分析以下文档内容，研究方向是{direction}:

{content}"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        # 记录消息长度
        with debug_expander:
            st.write(f"系统提示长度: {len(system_prompt)} 字符")
            st.write(f"人类消息长度: {len(human_prompt)} 字符")
            st.write(f"总输入长度: {len(system_prompt) + len(human_prompt)} 字符")
            st.write("开始调用AI分析...")
        
        # 尝试直接调用
        response = chat(messages)
        result = response.content
        
        # 检查结果
        with debug_expander:
            st.write(f"AI返回结果长度: {len(result)} 字符")
            if len(result) < 10:
                st.error("警告: AI返回内容异常短!")
                st.write(f"完整返回内容: '{result}'")
        
        # 如果返回内容为空，提供简短的错误信息
        if not result or len(result.strip()) < 10:
            return "AI分析未能生成有效结果。请检查文档内容是否相关，或调整提示词设置。"
        
        return result
    except Exception as e:
        with debug_expander:
            st.error(f"分析过程中发生错误: {str(e)}")
        
        return f"分析过程中发生错误: {str(e)}"

# 生成分析报告
def generate_analysis(simplified_content, direction, st_container=None):
    """使用AI生成分析报告"""
    # 使用流式输出
    chat = get_langchain_chat("analysis", stream=True, st_container=st_container)
    
    try:
        # 检查简化内容是否有效
        if not simplified_content or len(simplified_content.strip()) < 10:
            return "无法生成报告，因为文档分析阶段未能产生有效内容。请返回上一步重试。"
            
        # 从会话状态获取提示词
        backstory = st.session_state.brainstorm_backstory_prompt
        task = st.session_state.brainstorm_task_prompt
        output_format = st.session_state.brainstorm_output_prompt
        
        # 构建系统提示 - 使用用户定义的提示词
        system_prompt = f"""{backstory}

{task}

{output_format}

请注意：
1. 只根据提供的分析结果生成报告
2. 不要生成与研究方向无关的内容"""
        
        # 构建更简洁的人类消息
        human_prompt = f"""研究方向: {direction}

分析结果:
{simplified_content}

请生成一份申请策略和提升方案的报告。"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        with debug_expander:
            st.write("开始调用AI生成报告...")
            st.write(f"系统提示长度: {len(system_prompt)} 字符")
            st.write(f"人类消息长度: {len(human_prompt)} 字符")
        
        # 直接调用API
        response = chat(messages)
        result = response.content
        
        with debug_expander:
            st.write(f"AI返回报告长度: {len(result)} 字符")
        
        # 如果返回为空，提供简短错误信息
        if not result or len(result.strip()) < 50:
            return "生成报告失败。请检查分析内容是否有效，或调整提示词设置。"
        
        return result
    except Exception as e:
        with debug_expander:
            st.error(f"生成报告时出错: {str(e)}")
        
        return f"生成报告时出错: {str(e)}"

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
if 'show_analysis_section' not in st.session_state:
    st.session_state.show_analysis_section = False

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
langsmith_api_key = st.secrets["LANGCHAIN_API_KEY"]
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = langsmith_api_key
os.environ["LANGCHAIN_PROJECT"] = "脑暴助理1"

# 创建两个标签页
tab1, tab2 = st.tabs(["脑暴助理", "管理员设置"])

# 用户界面标签页
with tab1:
    st.title("🧠 脑暴助理")
    st.markdown("欢迎使用脑暴助理！上传您的文件，输入研究方向，获取专业分析报告。")

    # 第一步：上传文件和输入方向
    st.header("第一步：上传文件和输入研究方向")
    
    uploaded_files = st.file_uploader("上传文件（支持DOC, DOCX, PDF, JPG, PNG, TXT）", 
                                     type=['doc', 'docx', 'pdf', 'jpg', 'jpeg', 'png', 'txt'], 
                                     accept_multiple_files=True)
    
    direction = st.text_area("请输入您的研究方向", 
                             height=100, 
                             help="详细描述您的研究方向，帮助AI更好地理解您的需求")
    
    # 创建一个折叠面板用于显示调试信息
    debug_expander = st.expander("文件处理调试信息", expanded=True)
    
    if st.button("开始素材分析", disabled=not uploaded_files or not direction):
        with debug_expander:
            st.write(f"处理 {len(uploaded_files)} 个上传文件")
            st.write("===== 调试模式开启 =====")
            for file in uploaded_files:
                st.write(f"文件名: {file.name}, 大小: {len(file.getbuffer())} 字节, 类型: {file.type}")
            st.write("========================")
        
        # 保存上传的文件到临时目录
        temp_dir = tempfile.mkdtemp()
        file_paths = []
        
        # 保存文件并添加到处理列表
        for file in uploaded_files:
            # 使用安全的文件名，移除特殊字符
            safe_filename = re.sub(r'[^\w\-\.]', '_', file.name)
            file_path = os.path.join(temp_dir, safe_filename)
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
            file_paths.append(file_path)
            with debug_expander:
                st.write(f"保存文件: {file.name} -> {file_path}, 大小: {len(file.getbuffer())} 字节")
        
        # 确保立即保存方向信息到会话状态
        st.session_state.uploaded_files = file_paths
        st.session_state.direction = direction
        
        # 处理上传的文件内容，逐个处理每个文件并收集内容
        all_content = ""
        for file_path in file_paths:
            file_ext = Path(file_path).suffix.lower().replace(".", "")
            
            with debug_expander:
                st.write(f"处理文件: {os.path.basename(file_path)}, 类型: {file_ext}")
                st.write(f"文件路径: {file_path}")
                st.write(f"文件大小: {os.path.getsize(file_path)} 字节")
            
            # 使用process_file函数提取文件内容，并添加到all_content
            content = process_file(file_path, file_ext)
            file_name = os.path.basename(file_path)
            
            # 检查提取的内容
            with debug_expander:
                st.write(f"提取到内容长度: {len(content)}")
                if len(content) < 100:
                    st.warning(f"警告: 从{file_name}提取的内容非常短，可能没有正确读取")
                    st.write(f"完整内容: {content}")
            
            all_content += f"\n\n===== 文件: {file_name} =====\n\n{content}"
            
        # 在debug中显示完整的内容长度
        with debug_expander:
            st.write(f"所有文件合并后的内容长度: {len(all_content)}")
            st.write("内容前1000字符预览:")
            st.text(all_content[:1000] + "..." if len(all_content) > 1000 else all_content)
        
        # 验证文件内容不为空
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
            
            # 调用AI分析内容
            simplified = simplify_content(all_content, direction, st_container=analysis_container)
            
            # 确保立即保存简化内容到会话状态
            st.session_state.simplified_content = simplified
            st.session_state.show_analysis_section = True
            
            with debug_expander:
                st.write("AI 简化内容完成")
                st.write(f"简化内容长度: {len(simplified)} 字符")
        
        # 显示结果
        st.subheader("素材分析结果")
        st.markdown(simplified)
    
    # 第二步：生成头脑风暴辅助报告
    if st.session_state.show_analysis_section or st.session_state.simplified_content:
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
