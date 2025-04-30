import streamlit as st
import os
from PIL import Image
import io
import pandas as pd
import base64
from dotenv import load_dotenv
import requests
import json
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langsmith import Client
from langsmith.run_trees import RunTree
import tempfile
import streamlit.components.v1 as components

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="职业规划助理",
    page_icon="🚀",
    layout="wide"
)

# Available models
AVAILABLE_MODELS = {
    "qwen/qwen3-32b:free": "Qwen 3 32B",
    "deepseek/deepseek-chat-v3-0324:free": "DeepSeek Chat v3",
    "qwen/qwen-max": "Qwen Max"
}

# Session state initialization
if 'user_inputs' not in st.session_state:
    st.session_state.user_inputs = {
        "university": "",
        "major": "",
        "target_industry": "",
        "target_position": "",
        "transcript_text": ""
    }

if 'career_agent_settings' not in st.session_state:
    st.session_state.career_agent_settings = {
        "role": "您是一位经验丰富的职业规划顾问，拥有丰富的行业知识和洞察力。",
        "task": "基于用户提供的学术背景、专业、意向行业和职位，分析其职业发展路径，提供具体可行的建议。",
        "output_format": "请提供一份结构化的职业规划分析，包括：\n1. 背景分析\n2. 职业路径建议\n3. 技能提升方向\n4. 行业前景\n5. 短期和长期目标",
        "model": "qwen/qwen3-32b:free"
    }

if 'submission_agent_settings' not in st.session_state:
    st.session_state.submission_agent_settings = {
        "role": "您是一位专业的职业规划报告编辑，擅长整合信息并制作美观的报告。",
        "task": "基于职业规划草稿，补充相关行业数据和信息，制作一份包含文字说明和可视化图表的完整报告。",
        "output_format": "请提供一份专业的职业规划报告，包括：\n1. 执行摘要\n2. 详细分析\n3. 数据支持的图表\n4. 行动计划\n5. 资源推荐",
        "model": "deepseek/deepseek-chat-v3-0324:free"
    }

if 'draft_report' not in st.session_state:
    st.session_state.draft_report = ""

if 'final_report' not in st.session_state:
    st.session_state.final_report = ""

if 'api_status' not in st.session_state:
    st.session_state.api_status = {
        "openrouter": False,
        "qwen": False,
        "langsmith": False
    }

# Simulated knowledge database
class KnowledgeDatabase:
    def __init__(self):
        # This would be replaced with an actual database connection in production
        self.data = {
            "industries": {
                "IT/互联网": {
                    "positions": [
                        {
                            "name": "软件工程师",
                            "skills": "Python, Java, JavaScript, 数据结构, 算法",
                            "education": "计算机科学/软件工程相关本科及以上",
                            "salary": "15K-30K",
                            "prospects": "行业需求持续增长，发展空间广阔"
                        },
                        {
                            "name": "前端开发",
                            "skills": "HTML, CSS, JavaScript, React/Vue/Angular, TypeScript",
                            "education": "计算机相关专业本科及以上",
                            "salary": "12K-25K",
                            "prospects": "随着互联网产品不断发展，前端开发人才需求旺盛"
                        },
                        {
                            "name": "数据分析师",
                            "skills": "SQL, Python, R, Excel, 数据可视化, 统计学基础",
                            "education": "统计学/数学/计算机相关专业本科及以上",
                            "salary": "15K-30K",
                            "prospects": "大数据时代，数据分析人才稀缺，发展前景良好"
                        }
                    ],
                    "overview": "IT/互联网行业技术更新快，竞争激烈，但薪资水平和发展空间较大"
                },
                "金融": {
                    "positions": [
                        {
                            "name": "投资分析师",
                            "skills": "财务分析, 估值模型, Excel, 金融市场知识",
                            "education": "金融/经济/会计相关专业本科及以上",
                            "salary": "12K-30K",
                            "prospects": "金融行业稳定，晋升路径清晰"
                        },
                        {
                            "name": "风险控制",
                            "skills": "风险评估, 数据分析, 法规知识, 金融工具",
                            "education": "金融/数学/统计相关专业本科及以上",
                            "salary": "15K-35K",
                            "prospects": "风控人才需求稳定，职业发展前景良好"
                        }
                    ],
                    "overview": "金融行业相对稳定，注重专业性和合规性，职业发展体系较为成熟"
                }
            },
            "majors": {
                "计算机科学": {
                    "suitable_industries": ["IT/互联网", "金融", "教育"],
                    "suitable_positions": ["软件工程师", "数据分析师", "IT顾问"],
                    "core_skills": "编程语言, 数据结构, 算法, 数据库, 网络基础",
                    "career_paths": "可从开发工程师发展为架构师、技术经理或产品经理"
                },
                "金融学": {
                    "suitable_industries": ["金融", "咨询", "企业财务"],
                    "suitable_positions": ["投资分析师", "风险控制", "财务顾问"],
                    "core_skills": "财务分析, 金融市场, 风险管理, 投资理论",
                    "career_paths": "可从分析师发展为投资经理、风控经理或财务总监"
                }
            }
        }
    
    def query(self, query_type, query_value):
        """
        Query the database with different query types
        query_type can be: 'industry', 'position', 'major'
        """
        if query_type == 'industry' and query_value in self.data['industries']:
            return self.data['industries'][query_value]
        elif query_type == 'major' and query_value in self.data['majors']:
            return self.data['majors'][query_value]
        elif query_type == 'position':
            # Search for position across all industries
            for industry, industry_data in self.data['industries'].items():
                for position in industry_data['positions']:
                    if position['name'] == query_value:
                        return position
            return None
        else:
            return None

# Initialize knowledge database
knowledge_db = KnowledgeDatabase()

# Initialize LangSmith client if enabled
def init_langsmith():
    try:
        langsmith_api_key = st.secrets.get("LANGSMITH_API_KEY")
        langsmith_project = st.secrets.get("LANGSMITH_PROJECT", "career-planner")
        os.environ["LANGSMITH_API_KEY"] = langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = langsmith_project
        return Client(api_key=langsmith_api_key)
    except Exception as e:
        st.error(f"LangSmith initialization error: {str(e)}")
        return None

# Function to call OpenRouter for API requests
def call_openrouter(messages, model, temperature=0.7):
    try:
        api_key = st.secrets.get("OPENROUTER_API_KEY")
        if not api_key:
            return "错误：未设置OpenRouter API密钥"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://career-planner.streamlit.app"  # Replace with your actual domain
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            return f"请求失败: {str(result)}"
    except Exception as e:
        return f"请求过程中出错: {str(e)}"

# Function to call Qwen VL model for transcript analysis
def analyze_transcript_with_qwen(image_bytes):
    try:
        # For Qwen VL we'll continue using Qwen's API directly as it has multimodal capabilities
        api_key = st.secrets.get("QWEN_API_KEY")
        if not api_key:
            return "错误：未设置Qwen API密钥"
        
        # Convert image to base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "qwen/qwen2.5-vl-72b-instruct",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "这是一份成绩单，请识别并提取出所有课程名称、学分和成绩信息，整理成表格形式。"},
                        {"type": "image", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ]
        }
        
        response = requests.post("https://api.qwen.ai/v1/chat/completions", headers=headers, json=payload)
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            return f"分析失败: {str(result)}"
    except Exception as e:
        return f"分析过程中出错: {str(e)}"

# Function to render Mermaid diagrams
def render_mermaid(mermaid_code):
    html = f"""
    <div class="mermaid">
    {mermaid_code}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({{ startOnLoad: true }});
    </script>
    """
    components.html(html, height=500)

# Function to check API status
def check_api_status():
    # Check OpenRouter API
    try:
        openrouter_key = st.secrets.get("OPENROUTER_API_KEY")
        if openrouter_key:
            headers = {
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://career-planner.streamlit.app"
            }
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json={
                    "model": "qwen/qwen3-32b:free",  # Use one of our allowed models
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 5
                }
            )
            st.session_state.api_status["openrouter"] = response.status_code == 200
        else:
            st.session_state.api_status["openrouter"] = False
    except:
        st.session_state.api_status["openrouter"] = False
    
    # Check Qwen API
    try:
        qwen_key = st.secrets.get("QWEN_API_KEY")
        if qwen_key:
            headers = {
                "Authorization": f"Bearer {qwen_key}",
                "Content-Type": "application/json"
            }
            response = requests.post(
                "https://api.qwen.ai/v1/chat/completions",
                headers=headers,
                json={
                    "model": "qwen/qwen2.5-vl-72b-instruct",
                    "messages": [{"role": "user", "content": "Hello"}]
                }
            )
            st.session_state.api_status["qwen"] = response.status_code == 200
        else:
            st.session_state.api_status["qwen"] = False
    except:
        st.session_state.api_status["qwen"] = False
    
    # Check LangSmith status
    try:
        langsmith_key = st.secrets.get("LANGSMITH_API_KEY")
        if langsmith_key:
            client = Client(api_key=langsmith_key)
            # Just try to access the API
            _ = client.list_projects(limit=1)
            st.session_state.api_status["langsmith"] = True
        else:
            st.session_state.api_status["langsmith"] = False
    except:
        st.session_state.api_status["langsmith"] = False

# Function to query knowledge database
def query_knowledge_db(user_inputs):
    results = []
    
    # Query by industry
    if user_inputs['target_industry']:
        industry_data = knowledge_db.query('industry', user_inputs['target_industry'])
        if industry_data:
            results.append(f"行业概览 - {user_inputs['target_industry']}:\n{industry_data['overview']}")
            
            # If position is specified, find specific position data
            if user_inputs['target_position']:
                for position in industry_data['positions']:
                    if position['name'] == user_inputs['target_position']:
                        results.append(f"岗位详情 - {position['name']}:\n"
                                      f"所需技能: {position['skills']}\n"
                                      f"学历要求: {position['education']}\n"
                                      f"薪资范围: {position['salary']}\n"
                                      f"发展前景: {position['prospects']}")
                        break
            else:
                # List all positions in this industry
                results.append(f"{user_inputs['target_industry']}行业热门岗位:")
                for position in industry_data['positions']:
                    results.append(f"- {position['name']}: {position['prospects']}")
    
    # Query by major
    if user_inputs['major']:
        major_data = knowledge_db.query('major', user_inputs['major'])
        if major_data:
            results.append(f"专业就业方向 - {user_inputs['major']}:\n"
                          f"适合行业: {', '.join(major_data['suitable_industries'])}\n"
                          f"适合岗位: {', '.join(major_data['suitable_positions'])}\n"
                          f"核心技能: {major_data['core_skills']}\n"
                          f"职业路径: {major_data['career_paths']}")
    
    # Query by position (if not already found)
    if user_inputs['target_position'] and not user_inputs['target_industry']:
        position_data = knowledge_db.query('position', user_inputs['target_position'])
        if position_data:
            results.append(f"岗位详情 - {user_inputs['target_position']}:\n"
                          f"所需技能: {position_data['skills']}\n"
                          f"学历要求: {position_data['education']}\n"
                          f"薪资范围: {position_data['salary']}\n"
                          f"发展前景: {position_data['prospects']}")
    
    return "\n\n".join(results) if results else "知识库中未找到相关信息"

# Function to generate career planning draft with LangSmith tracking
def generate_career_planning_draft(user_inputs, agent_settings):
    try:
        # Initialize LangSmith if enabled
        langsmith_client = init_langsmith()
        
        # Query the knowledge database
        kb_data = query_knowledge_db(user_inputs)
        
        # Prepare the prompt for the career planning assistant
        role = agent_settings["role"]
        task = agent_settings["task"]
        output_format = agent_settings["output_format"]
        model = agent_settings["model"]
        
        user_info = f"""
        用户信息:
        - 本科院校: {user_inputs['university']}
        - 本科专业: {user_inputs['major']}
        - 意向行业: {user_inputs['target_industry']}
        - 意向岗位: {user_inputs['target_position']}
        
        成绩单信息:
        {user_inputs['transcript_text']}
        
        知识库信息:
        {kb_data}
        """
        
        messages = [
            {"role": "system", "content": f"{role}\n\n{task}\n\n输出格式要求:\n{output_format}"},
            {"role": "user", "content": user_info}
        ]
        
        # Track with LangSmith if available
        if langsmith_client:
            run_tree = RunTree(
                name="career_planning_draft",
                run_type="chain",
                inputs={"user_inputs": user_inputs, "agent_settings": agent_settings},
                client=langsmith_client
            )
            
            with run_tree:
                # Make API call through OpenRouter
                response = call_openrouter(
                    messages=messages, 
                    model=model, 
                    temperature=0.7
                )
                run_tree.end(outputs={"draft_report": response})
                return response
        else:
            # Make API call without tracking
            return call_openrouter(
                messages=messages, 
                model=model, 
                temperature=0.7
            )
    except Exception as e:
        return f"生成过程中出错: {str(e)}"

# Function to generate final career planning report with LangSmith tracking
def generate_final_report(draft_report, agent_settings):
    try:
        # Initialize LangSmith if enabled
        langsmith_client = init_langsmith()
        
        # Prepare the prompt for the submission agent
        role = agent_settings["role"]
        task = agent_settings["task"]
        output_format = agent_settings["output_format"]
        model = agent_settings["model"]
        
        messages = [
            {"role": "system", "content": f"{role}\n\n{task}\n\n输出格式要求:\n{output_format}\n\n请在适当的地方加入Mermaid图表，用```mermaid和```包裹图表代码。"},
            {"role": "user", "content": f"这是职业规划报告初稿:\n\n{draft_report}\n\n请基于此初稿，补充相关信息，并制作一份包含文字和图表的完整报告。"}
        ]
        
        # Track with LangSmith if available
        if langsmith_client:
            run_tree = RunTree(
                name="final_report_generation",
                run_type="chain",
                inputs={"draft_report": draft_report, "agent_settings": agent_settings},
                client=langsmith_client
            )
            
            with run_tree:
                # Make API call through OpenRouter
                response = call_openrouter(
                    messages=messages, 
                    model=model, 
                    temperature=0.7
                )
                run_tree.end(outputs={"final_report": response})
                return response
        else:
            # Make API call without tracking
            return call_openrouter(
                messages=messages, 
                model=model, 
                temperature=0.7
            )
    except Exception as e:
        return f"生成过程中出错: {str(e)}"

# Main application interface
st.title("职业规划助理")

# Create tabs
tab1, tab2, tab3 = st.tabs(["信息收集", "助理设置", "API状态"])

# Tab 1: Information Collection
with tab1:
    st.header("用户信息收集")
    
    col1, col2 = st.columns(2)
    
    with col1:
        university = st.text_input("本科院校", value=st.session_state.user_inputs["university"])
        major = st.text_input("本科专业", value=st.session_state.user_inputs["major"])
    
    with col2:
        target_industry = st.text_input("意向行业", value=st.session_state.user_inputs["target_industry"])
        target_position = st.text_input("意向岗位", value=st.session_state.user_inputs["target_position"])
    
    # Transcript upload
    uploaded_file = st.file_uploader("上传成绩单（仅支持图片格式）", type=['png', 'jpg', 'jpeg'])
    
    transcript_text = ""
    if uploaded_file is not None:
        # Read the file
        image_bytes = uploaded_file.getvalue()
        
        # Call Qwen VL model to analyze the transcript
        with st.spinner("正在分析成绩单..."):
            transcript_text = analyze_transcript_with_qwen(image_bytes)
        
        # Display the analysis result in an expandable section
        with st.expander("成绩单分析结果", expanded=True):
            st.write(transcript_text)
    
    # Store user inputs in session state
    if st.button("开始分析"):
        # Validate inputs
        if not (major or target_industry or target_position):
            st.error("错误：本科专业、意向行业和意向岗位必须至少填写一项")
        else:
            st.session_state.user_inputs = {
                "university": university,
                "major": major,
                "target_industry": target_industry,
                "target_position": target_position,
                "transcript_text": transcript_text
            }
            
            # Generate career planning draft
            with st.spinner("正在生成职业规划报告草稿..."):
                draft_report = generate_career_planning_draft(
                    st.session_state.user_inputs,
                    st.session_state.career_agent_settings
                )
                st.session_state.draft_report = draft_report
            
            # Display the draft report
            st.subheader("职业规划报告草稿")
            st.write(st.session_state.draft_report)
            
            # Generate final report
            with st.spinner("正在生成最终职业规划报告..."):
                final_report = generate_final_report(
                    st.session_state.draft_report,
                    st.session_state.submission_agent_settings
                )
                st.session_state.final_report = final_report
            
            # Display the final report
            st.subheader("最终职业规划报告")
            
            # Process and display text and Mermaid diagrams separately
            report_parts = st.session_state.final_report.split("```mermaid")
            
            for i, part in enumerate(report_parts):
                if i == 0:
                    # First part is just text
                    st.write(part)
                else:
                    # Subsequent parts contain mermaid code followed by text
                    code_and_text = part.split("```", 1)
                    if len(code_and_text) == 2:
                        mermaid_code = code_and_text[0]
                        text = code_and_text[1]
                        
                        # Render the Mermaid diagram
                        render_mermaid(mermaid_code)
                        
                        # Display the text that follows
                        st.write(text)

# Tab 2: Agent Settings
with tab2:
    st.header("助理设置")
    
    st.subheader("职业规划助理设置")
    career_role = st.text_area("人物设定", value=st.session_state.career_agent_settings["role"], height=100)
    career_task = st.text_area("任务描述", value=st.session_state.career_agent_settings["task"], height=100)
    career_output_format = st.text_area("输出格式", value=st.session_state.career_agent_settings["output_format"], height=150)
    
    # Add model selection dropdown for career planning agent
    career_model = st.selectbox(
        "选择职业规划助理模型", 
        options=list(AVAILABLE_MODELS.keys()),
        format_func=lambda x: AVAILABLE_MODELS[x],
        index=list(AVAILABLE_MODELS.keys()).index(st.session_state.career_agent_settings["model"])
    )
    
    st.subheader("交稿助理设置")
    submission_role = st.text_area("人物设定", value=st.session_state.submission_agent_settings["role"], height=100)
    submission_task = st.text_area("任务描述", value=st.session_state.submission_agent_settings["task"], height=100)
    submission_output_format = st.text_area("输出格式", value=st.session_state.submission_agent_settings["output_format"], height=150)
    
    # Add model selection dropdown for submission agent
    submission_model = st.selectbox(
        "选择交稿助理模型", 
        options=list(AVAILABLE_MODELS.keys()),
        format_func=lambda x: AVAILABLE_MODELS[x],
        index=list(AVAILABLE_MODELS.keys()).index(st.session_state.submission_agent_settings["model"])
    )
    
    if st.button("保存设置"):
        st.session_state.career_agent_settings = {
            "role": career_role,
            "task": career_task,
            "output_format": career_output_format,
            "model": career_model
        }
        
        st.session_state.submission_agent_settings = {
            "role": submission_role,
            "task": submission_task,
            "output_format": submission_output_format,
            "model": submission_model
        }
        
        st.success("设置已保存")

# Tab 3: API Status
with tab3:
    st.header("API状态检测")
    
    if st.button("检测API状态"):
        with st.spinner("正在检测API状态..."):
            check_api_status()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status = "✅ 正常" if st.session_state.api_status["openrouter"] else "❌ 异常"
            st.metric("OpenRouter API", status)
            
            if not st.session_state.api_status["openrouter"]:
                st.warning("请检查Streamlit Secrets中的OPENROUTER_API_KEY是否正确设置")
        
        with col2:
            status = "✅ 正常" if st.session_state.api_status["qwen"] else "❌ 异常"
            st.metric("Qwen API", status)
            
            if not st.session_state.api_status["qwen"]:
                st.warning("请检查Streamlit Secrets中的QWEN_API_KEY是否正确设置")
        
        with col3:
            status = "✅ 正常" if st.session_state.api_status["langsmith"] else "❌ 异常"
            st.metric("LangSmith", status)
            
            if not st.session_state.api_status["langsmith"]:
                st.warning("请检查Streamlit Secrets中的LANGSMITH_API_KEY是否正确设置") 