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

st.set_page_config(page_title="个人RL写作助手", layout="wide")

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
            try:
                langsmith_client.create_project(langsmith_project)
            except Exception as e:
                # 只要是已存在的冲突就忽略
                if "409" in str(e) or "already exists" in str(e):
                    pass
                else:
                    st.warning(f"LangSmith项目创建失败: {str(e)}")
    except Exception as e:
        st.warning(f"LangSmith初始化失败: {str(e)}")

# 初始化session state用于存储提示词和文件内容
if "persona" not in st.session_state:
    st.session_state.persona = """你是一位经验丰富的推荐信写作专家，专门为申请国外高校的中国学生撰写高质量的推荐信。请根据我提供的学生信息和推荐人信息，创作一篇真实、具体、有说服力的推荐信，突出学生的学术能力、个人品质和发展潜力。即使素材中包含了一些非积极的内容，你也会转换表述方式，确保全篇表述百分百积极肯定被推荐人，不暗示推荐人参与较少或与被推荐人互动不足或暗示被推荐人能力不足的内容。
"""
if "task" not in st.session_state:
    st.session_state.task = """1.请首先阅读第一个agent生成的辅助文档分析报告（如有）
2.重点深入理解和分析用户上传的素材表，融入辅助文档分析报告的细节进行创作
3.在开始写作前，先对素材表内容进行有条理的整理与分类： 
a.区分推荐人的基本信息、与被推荐人的关系、课程/项目经历以及对被推荐人的评价 
b.将混乱的素材按推荐信四段结构所需内容重新分类组织 
c.对于不完整或表述不清的信息，进行合理推断并标记为补充内容 
d.提取每段所需的核心信息，确保信件逻辑连贯、重点突出
4.素材表中可能包含多位推荐人信息，如用户未明确指定，默认使用第一位推荐人的信息和素材进行写作。请确保不要混淆不同推荐人的素材内容。
5.用户如输入"请撰写第二位推荐人"的指令一般是指学术推荐人2
6.推荐信必须以推荐人为第一人称进行写作
7.推荐信分为两种类型： 
a.学术推荐信：适用于推荐人是老师或学术导师的情况
b.工作推荐信：适用于推荐人是工作单位领导或校内辅导员的情况（即使在校内，但互动主要非学术性质）
8.两种推荐信结构一致，基本为四段： 
a.第一段：介绍推荐人与被推荐人如何认识
b.第二段和第三段：作为核心段落，从两个不同方面描述二人互动细节，点明被推荐人展示的能力、品质、性格特点
c.第四段：表明明确的推荐意愿，对被推荐人未来发展进行预测，并添加客套语如"有疑问或需要更多信息，可与我联系"
9.第一段介绍时，应遵循以下原则： 
a.首先表达自己写这封推荐信是为了支持XXX的申请
b.全面且准确地描述推荐人与被推荐人之间的所有关系（如既是任课老师又是毕业论文导师）
c.主要关系应放在句首位置（如"作为XXX的[主要关系]，我也曾担任她的[次要关系]"） 
d.重点描述与被推荐人的互动历程和熟悉程度，而非推荐人个人成就
e.确保第一段内容简洁明了，为后续段落奠定基础
10.两种推荐信在第二段和第三段的侧重点不同： 
a.学术推荐信： 
●第二段：描述课堂中的互动细节（包括但不限于课堂问答互动，小组讨论，课后互动等） 
●第三段：描述课外互动细节（包括但不限于推荐人监管下的科研项目经历）
b.工作推荐信： 
●第二段：描述工作过程中的互动细节（包括但不限于推荐人监管下的项目或工作内容） 
●第三段：描述推荐人观察到的被推荐人与他人相处细节，展现性格特点和个人品质
11.切忌出现不谈细节，只评论的情况。必须基于具体事件细节出发进行创作
12.确保第二段和第三段的经历选取不重复
13.确保第二段和第三段描述的能力、品质或特点不重复，分别突出不同的优势
14.补充原则：绝大部分内容需基于素材表，缺失细节允许补充，但禁止补充任何数据和专业操作步骤
例如：
●允许补充：【补充：在讨论过程中，XXX在项目中通过深入分析数据进行了预测，展现出了敏锐的分析能力和清晰的逻辑思维】
●禁止补充：【补充：XXX在项目中处理了5,378条数据，使用了R语言中的随机森林算法进行预测分析】
15.推荐信中应避免提及被推荐人的不足之处，即使素材表中有相关信息
16.正文最后一段无需提供邮箱和电话等联系信息
17.正文最后一段的总结必须与前文所述的具体事例直接关联，确保整封信的连贯性和说服力
18.推荐信语气应始终保持积极、肯定和自信： 
a.禁止使用以下语言结构和表述： 任何形式的转折语（如"虽然"、"尽管"等）
●任何形式的否定或弱化表述（如"不算"、"并非"等）
●任何弱化程度的词语（如"较为"、"比较"等）
b.对互动描述必须是完全积极的：
●应描述为"在我们有意义的互动中"或"通过我们的深入交流"
●不得暗示或明示互动不足或不深入 
c.对学生的评价必须是直接、肯定的断言：
●使用"展现了"、"证明了"、"表现出"等肯定表述
●成绩必须直接描述为"优秀"、"卓越"等正面词汇 
d.禁止使用任何可能暗示学生不足的表述 
e.必须始终聚焦学生的优势和特长，永远不提及任何可能被解读为不足的方面

重要提醒 
1.【补充：】标记的使用是强制性要求，所有非素材表中的事实性内容必须使用【补充：具体内容】完整标记 
2.用户需求始终是第一位的：若用户要求添加或编造内容，应立即执行
3.在用户没有明确表示的情况下，必须基于素材表创作
4.每添加非素材表内容时，使用【补充：】标记以供用户参考
5.任何情况下都应优先满足用户的创作需求，其次才是考虑内容的来源问题
6.未正确标记补充内容将导致任务完全失败，没有例外 

内容真实性标准
1.用户授权优先：若用户明确要求添加或编造特定内容，应无条件执行
2.默认状态下，所有段落中的事实内容应基于素材表
3.【补充：具体内容】标记用于标记非素材表中的事实性内容，便于用户识别
4.不需使用【补充：】标记的内容仅限于：逻辑连接词、对素材的分析反思、重新组织或表述已有信息
5.在没有用户明确授权的情况下，避免编造关键事实：如具体项目/课程、研究方法/技术、具体成就/结果、任何类型的数据
6.在素材有限的情况下，应适当添加与学生专业和申请方向相符的具体细节，以丰富推荐信内容，但所有补充内容必须与素材表提供的基本信息保持一致性
7.在素材较多的情况下，应进行筛选，选择最贴合申请专业或者专业深度深（如未提供申请专业相关信息）的经历
8.每个补充内容必须有明确的逻辑依据，不得凭空捏造或做出与素材表明显不符的联想
"""
if "output_format" not in st.session_state:
    st.session_state.output_format = """请以中文输出一封完整的推荐信，直接从正文开始（无需包含信头如日期和收信人），以"尊敬的招生委员会："开头，以"此致 敬礼"结尾，并在最后只添加推荐人姓名和职位，无需包含任何具体的联系方式（包括但不限于联系电话及电子邮箱。
在补充素材表没有的细节时必须使用【补充：XXXX】标记
"""
if "resume_content" not in st.session_state:
    st.session_state.rl_content = ""
if "support_files_content" not in st.session_state:
    st.session_state.support_files_content = []
if "writing_requirements" not in st.session_state:
    st.session_state.writing_requirements = ""
    
# 新增：支持文件分析agent的提示词
if "support_analyst_persona" not in st.session_state:
    st.session_state.support_analyst_persona = """您是一位专业的文档分析专家，擅长从各类文件中提取和整合信息。您的任务是分析用户上传的辅助文档（如项目海报、报告或作品集），并生成标准化报告，用于简历顾问后续处理。您具备敏锐的信息捕捉能力和系统化的分析方法，能够从复杂文档中提取关键经历信息。"""
if "support_analyst_task" not in st.session_state:
    st.session_state.support_analyst_task = """经历分类： 
● 科研项目经历：包括课题研究、毕业论文、小组科研项目等学术性质的活动 
● 实习工作经历：包括正式工作、实习、兼职等与就业相关的经历 
● 课外活动经历：包括学生会、社团、志愿者、比赛等非学术非就业的活动经历
文件分析工作流程：
1.仔细阅读所有上传文档，不遗漏任何页面和部分内容
2.识别文档中所有经历条目，无论是否完整
3.将多个文档中的相关信息进行交叉比对和整合
4.为每个经历创建独立条目，保留所有细节
5.按照下方格式整理每类经历，并按时间倒序排列

信息整合策略： 
● 多文件整合：系统性关联所有辅助文档信息，确保全面捕捉关键细节 
● 团队项目处理：对于团队项目，明确关注个人在团队中的具体职责和贡献，避免笼统描述团队成果 
● 内容优先级：专业知识与能力 > 可量化成果 > 职责描述 > 个人感受 
● 表达原则：简洁精准、专业导向、成果突显、能力凸显
"""
if "support_analyst_output_format" not in st.session_state:
    st.session_state.support_analyst_output_format = """辅助文档分析报告
【科研经历】 
经历一： [项目名称]
时间段：[时间] 
组织：[组织名称] 
角色：[岗位/角色]（如有缺失用[未知]标记） 
核心信息：
●[项目描述] 具体内容
●[使用技术/方法] 具体内容
●[个人职责] 具体内容
●[项目成果] 具体内容 信息完整度评估：[完整/部分完整/不完整] 缺失信息：[列出缺失的关键信息]

经历二： [按照相同格式列出]

【实习工作经历】 
经历一： 
时间段：[时间] 
组织：[组织名称] 
角色：[岗位/角色]（如有缺失用[未知]标记） 
核心信息：
●[工作职责] 具体内容
●[使用技术/工具] 具体内容
●[解决问题] 具体内容
●[工作成果] 具体内容 信息完整度评估：[完整/部分完整/不完整] 缺失信息：[列出缺失的关键信息]

经历二： [按照相同格式列出]

【课外活动经历】 
经历一： 
时间段：[时间] 
组织：[组织名称] 
角色：[岗位/角色]（如有缺失用[未知]标记） 
核心信息：
●[活动描述] 具体内容
●[个人职责] 具体内容
●[使用能力] 具体内容
●[活动成果] 具体内容 信息完整度评估：[完整/部分完整/不完整] 缺失信息：[列出缺失的关键信息]

经历二： [按照相同格式列出]
注意：如果用户未上传任何辅助文档，请直接回复："未检测到辅助文档，无法生成文档分析报告。"
"""

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
def process_with_model(support_analyst_model, rl_assistant_model, rl_content, support_files_content, 
                      persona, task, output_format, 
                      support_analyst_persona, support_analyst_task, support_analyst_output_format,
                      writing_requirements=""):
    # 主运行ID
    main_run_id = str(uuid.uuid4())
    # 检查是否有支持文件
    has_support_files = len(support_files_content) > 0
    # 显示处理进度
    progress_bar = st.progress(0)
    status_text = st.empty()
    try:
        # 1. 如果有支持文件，先用支持文件分析agent处理
        support_analysis_result = ""
        if has_support_files:
            status_text.text("第一阶段：正在分析支持文件...")
            # 准备支持文件的内容
            support_files_text = ""
            for i, content in enumerate(support_files_content):
                support_files_text += f"--- 文件 {i+1} ---\n{content}\n\n"
            # 构建支持文件分析agent的提示词
            support_prompt = f"""人物设定：{support_analyst_persona}
\n任务描述：{support_analyst_task}
\n输出格式：{support_analyst_output_format}
\n支持文件内容：
{support_files_text}
"""
            # 调用支持文件分析agent
            support_analysis_result = run_agent(
                "supporting_doc_analyst",
                support_analyst_model,
                support_prompt,
                main_run_id
            )
            progress_bar.progress(50)
            status_text.text("第一阶段完成：支持文件分析完毕")
        else:
            progress_bar.progress(50)
            status_text.text("未提供支持文件，跳过第一阶段分析")
        # 2. 准备RL助理的输入
        status_text.text("第二阶段：正在生成RL报告...")
        # 准备RL素材内容
        file_contents = f"RL素材内容:\n{rl_content}\n\n"
        # 如果有支持文件分析结果，添加到提示中
        if has_support_files and support_analysis_result:
            file_contents += f"支持文件分析结果:\n{support_analysis_result}\n\n"
        # 或者直接添加原始支持文件内容（如果没有分析结果但有支持文件）
        elif has_support_files:
            file_contents += "支持文件内容:\n"
            for i, content in enumerate(support_files_content):
                file_contents += f"--- 文件 {i+1} ---\n{content}\n\n"
        
        # 如果有用户写作需求，添加到提示中
        user_requirements = ""
        if writing_requirements:
            user_requirements = f"\n用户写作需求:\n{writing_requirements}\n"
            
        # 构建最终的RL助理提示词
        rl_prompt = f"""人物设定：{persona}
\n任务描述：{task}{user_requirements}
\n输出格式：{output_format}
\n文件内容：
{file_contents}
"""
        # 调用RL助理agent
        final_result = run_agent(
            "rl_assistant", 
            rl_assistant_model,
            rl_prompt,
            main_run_id
        )
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
            st.warning(f"LangSmith运行创建失败: {str(e)}")
    # 创建 LLM 实例
    llm = ChatOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        model=model,
        temperature=0.7,
    )
    # 使用 langchain 的 ChatOpenAI 处理信息
    messages = [HumanMessage(content=prompt)]
    result = llm.invoke(messages)
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
            st.warning(f"LangSmith更新运行结果失败: {str(e)}")
    return result.content

# Tab布局 - 修改为三个标签页
TAB1, TAB2, TAB3 = st.tabs(["文件上传与分析", "提示词与模型设置", "系统状态"])

with TAB1:
    st.header("上传你的推荐信素材和支持文件")
    rl_file = st.file_uploader("推荐信素材表（必传）", type=["pdf", "docx", "doc", "png", "jpg", "jpeg"], accept_multiple_files=False)
    support_files = st.file_uploader("支持文件（可多选）", type=["pdf", "docx", "doc", "png", "jpg", "jpeg"], accept_multiple_files=True)
    
    
    # 定义添加写作需求文本的函数
    def add_requirement(requirement):
        # 检查是否是互斥的推荐人选择
        if requirement in ["请撰写第一位推荐人的推荐信", "请撰写第二位推荐人的推荐信"]:
            # 移除其他推荐人选择相关的文本
            current_text = st.session_state.writing_requirements
            if "请撰写第一位推荐人的推荐信" in current_text:
                current_text = current_text.replace("请撰写第一位推荐人的推荐信", "")
            if "请撰写第二位推荐人的推荐信" in current_text:
                current_text = current_text.replace("请撰写第二位推荐人的推荐信", "")
            
            # 清理多余的换行符
            current_text = "\n".join([line for line in current_text.split("\n") if line.strip()])
            
            # 添加新的推荐人选择
            if current_text:
                st.session_state.writing_requirements = current_text + "\n" + requirement
            else:
                st.session_state.writing_requirements = requirement
        else:
            # 普通需求，检查是否已经存在
            if requirement not in st.session_state.writing_requirements:
                if st.session_state.writing_requirements:
                    st.session_state.writing_requirements += "\n" + requirement
                else:
                    st.session_state.writing_requirements = requirement
    
    # 创建单行四列布局
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("第一位推荐人", use_container_width=True):
            add_requirement("请撰写第一位推荐人的推荐信")
    
    with col2:
        if st.button("第二位推荐人", use_container_width=True):
            add_requirement("请撰写第二位推荐人的推荐信")
    
    with col3:
        if st.button("课堂互动细节", use_container_width=True):
            add_requirement("请补充更多课堂互动细节")
    
    with col4:
        if st.button("科研项目细节", use_container_width=True):
            add_requirement("请补充更多科研项目细节")
    
    # 添加用户写作需求输入框
    writing_requirements = st.text_area("写作需求（可选）", 
                                      value=st.session_state.writing_requirements, 
                                      placeholder="请输入你的具体写作需求，例如：具体撰写哪一位推荐人的推荐信",
                                      height=120)
    st.session_state.writing_requirements = writing_requirements
    
    # 添加"开始生成"按钮
    if st.button("开始生成", use_container_width=True):
        if not api_key:
            st.error("请在 Streamlit secrets 中配置 OPENROUTER_API_KEY")
        elif not rl_file:
            st.error("请上传推荐信素材表")
        else:
            # 从session_state获取模型
            support_analyst_model = st.session_state.get("selected_support_analyst_model", get_model_list()[0])
            rl_assistant_model = st.session_state.get("selected_rl_assistant_model", get_model_list()[0])
            
            # 读取文件内容
            rl_content = read_file(rl_file)
            st.session_state.rl_content = rl_content
            
            support_files_content = []
            if support_files:
                for f in support_files:
                    content = read_file(f)
                    support_files_content.append(content)
            st.session_state.support_files_content = support_files_content
            
            # 处理并显示结果
            process_with_model(
                support_analyst_model,
                rl_assistant_model,
                st.session_state.rl_content, 
                st.session_state.support_files_content,
                st.session_state.persona,
                st.session_state.task,
                st.session_state.output_format,
                st.session_state.support_analyst_persona,
                st.session_state.support_analyst_task,
                st.session_state.support_analyst_output_format,
                st.session_state.writing_requirements
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
        st.subheader("RL助理 Agent (rl_assistant)")
        # 模型选择
        selected_rl_assistant_model = st.selectbox(
            "选择RL生成模型", 
            model_list,
            key="rl_assistant_model_selector"
        )
        # 将选择的模型保存到session_state
        st.session_state.selected_rl_assistant_model = selected_rl_assistant_model
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
            placeholder="如：请根据我的RL素材和支持文件分析结果，生成一份针对XX岗位的RL报告……", 
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
        2. 然后系统将使用RL助理agent，综合分析RL素材表和上一步的分析结果，生成最终RL报告
        3. 如果没有上传支持文件，系统将直接使用RL助理agent处理RL素材表
        """)

# 添加系统状态到第三个标签页
with TAB3:
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
