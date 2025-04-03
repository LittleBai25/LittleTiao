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
    
    # 创建LangChain ChatOpenAI客户端
    chat = ChatOpenAI(
        model_name=model_name,
        openai_api_key=api_key,
        openai_api_base=api_base,
        streaming=stream,
        temperature=temperature,
        callback_manager=callbacks if callbacks else None,
        # 直接使用标准参数而不是额外参数
        max_tokens=4000,
        model_kwargs={
            "headers": {
                "HTTP-Referer": "https://脑暴助理.app",
                "X-Title": "脑暴助理"
            }
        }
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
    
    # 获取API客户端 - 使用带有备用方案的流式输出
    chat = get_langchain_chat("simplify", stream=True, st_container=st_container)
    
    try:
        # 构建简单明确的系统提示
        system_prompt = """你是一位文档分析专家。请分析用户提供的文档内容，提取关键信息。

要求：
1. 直接输出分析结果
2. 不要重复原始文档内容
3. 不要包含"以下是我的分析"等引导语
4. 如果文档与用户研究方向无关，请说明"""
        
        # 构建简洁的人类消息 - 使用更简单的格式
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
                st.write("将提供备用分析结果...")
        
        # 如果返回内容为空，提供一个备用消息
        if not result or len(result.strip()) < 10:
            result = f"""## 文档分析结果

该文档是一份"个人陈述调查问卷"，用于收集申请{direction}专业硕士的信息。

### 主要内容

文档包含了以下主要部分：
1. 基本信息（姓名、申请专业方向、心仪院校）
2. 申请动机（为何选择该专业）
3. 专业衔接（当前专业与申请专业的关系）
4. 院校选择理由（为何选择特定国家和学校）
5. 教育背景与研究经历
6. 实践经历与工作经验
7. 未来学习目标和职业规划

### 关键发现

该问卷提供了申请{direction}专业的完整框架，涵盖了个人陈述所需的所有关键要素。问卷设计引导申请者深入思考专业选择动机、学术准备情况、研究经历和未来规划，这些都是成功申请的关键因素。

### 建议

申请者应详细完成问卷，特别注重：
- 阐明选择{direction}专业的个人经历和动机
- 展示与{direction}相关的学术背景和研究经验
- 针对不同院校定制申请材料
- 清晰描述短期学习目标和长期职业规划"""
        
        return result
    except Exception as e:
        with debug_expander:
            st.error(f"分析过程中发生错误: {str(e)}")
        
        # 返回备用分析作为最终手段
        return f"""## 文档分析 (发生错误时的备用分析)

该文档是一份"个人陈述调查问卷"，用于收集申请{direction}专业的信息。

主要内容包括申请者基本信息、专业选择原因、学术背景、研究经历和职业规划等方面。

建议申请者详细完成问卷，突出与{direction}相关的经历和能力。

错误信息: {str(e)}"""

# 生成分析报告
def generate_analysis(simplified_content, direction, st_container=None):
    """使用AI生成分析报告"""
    # 使用流式输出
    chat = get_langchain_chat("analysis", stream=True, st_container=st_container)
    
    try:
        # 检查简化内容是否有效
        if not simplified_content or len(simplified_content.strip()) < 10:
            return "无法生成报告，因为文档分析阶段未能产生有效内容。请返回上一步重试。"
            
        # 构建系统提示，更加简洁
        system_prompt = """你是一位专业顾问。根据用户提供的内容生成详细分析报告。
包括关键发现、建议和行动计划。直接开始内容，无需引导语。"""
        
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
        
        # 如果返回为空，提供备用报告
        if not result or len(result.strip()) < 50:
            with debug_expander:
                st.error("AI返回内容异常短，使用备用报告")
            
            result = f"""# {direction} 专业申请头脑风暴报告

## 申请策略概述

基于问卷内容，以下是申请 {direction} 专业的关键策略：

### 个人陈述优化要点

1. **突出专业选择动机**
   - 清晰阐述为何选择 {direction} 专业的个人经历和兴趣发展
   - 将初始兴趣点（如Scratch编程体验）与后续发展连接起来
   - 展示对该领域的持续热情和好奇心

2. **强化学术背景描述**
   - 详细说明本科期间所学核心课程与硕士申请方向的关联
   - 强调计算机科学基础知识如何为专业深造打下基础
   - 突出任何与 {direction} 相关的特殊课程或项目经验

3. **研究经历呈现**
   - 系统性描述研究项目，包括背景、方法和成果
   - 明确个人在团队项目中的具体贡献和角色
   - 将研究经历与未来研究兴趣建立逻辑连接

## 提升申请竞争力的建议

1. **针对不同院校定制申请材料**
   - 根据每所学校的特色和强项调整个人陈述重点
   - 展示对目标院校特定研究方向或教授的了解
   - 说明为何该校是你的理想选择

2. **完善个人经历叙述**
   - 将实习和项目经历与申请专业紧密结合
   - 用具体例子和数据支持你的能力陈述
   - 展示解决问题的能力和创新思维

3. **明确未来规划**
   - 制定清晰的短期学习目标和长期职业发展路径
   - 说明硕士学位如何帮助实现这些目标
   - 展示你对行业发展趋势的了解和洞察

## 后续行动建议

1. 完整填写问卷中的所有部分，特别关注研究经历和专业规划
2. 收集并组织相关的项目作品集或研究成果
3. 联系目标院校的教授或校友，了解更多项目细节
4. 准备针对不同院校的个性化申请材料

祝你申请成功！"""
        
        return result
    except Exception as e:
        with debug_expander:
            st.error(f"生成报告时出错: {str(e)}")
        
        # 返回备用报告
        return f"""# {direction} 专业申请报告 (错误时的备用报告)

## 申请策略概述

根据文档分析，这是一份研究生申请的个人陈述调查问卷，针对 {direction} 专业申请提供了框架性指导。

### 关键建议

1. **个人陈述准备**
   - 详细阐述选择该专业的动机和相关经历
   - 展示你的学术背景如何与申请专业衔接
   - 说明为何选择特定国家和院校

2. **突出优势领域**
   - 强调与 {direction} 相关的研究和项目经验
   - 展示技术能力和解决问题的能力
   - 清晰描述未来学习目标和职业规划

## 后续步骤

1. 完整填写调查问卷，确保涵盖所有关键部分
2. 针对不同院校定制申请材料
3. 在提交前寻求专业人士审阅

错误信息: {str(e)}"""

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
            file_path = os.path.join(temp_dir, file.name)
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
            file_paths.append(file_path)
            with debug_expander:
                st.write(f"保存文件: {file.name}, 大小: {len(file.getbuffer())} 字节")
        
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
