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
from langsmith.run_helpers import traceable
import tempfile
import streamlit.components.v1 as components
import datetime
from io import BytesIO

# 初始化全局变量用于记录模型信息
_run_metadata = {}

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Career Planning Assistant",
    page_icon="🚀",
    layout="wide"
)

# Function to check API status - 移动到文件前面
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
                    "model": "qwen/qwen-max",  # Use a default model
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 5
                }
            )
            st.session_state.api_status["openrouter"] = response.status_code == 200
        else:
            st.session_state.api_status["openrouter"] = False
    except Exception as e:
        st.error(f"OpenRouter API error: {str(e)}")
        st.session_state.api_status["openrouter"] = False
    
    # Check LangSmith status
    try:
        langsmith_key = st.secrets.get("LANGSMITH_API_KEY")
        if langsmith_key:
            # 确保环境变量设置正确
            os.environ["LANGSMITH_API_KEY"] = langsmith_key
            os.environ["LANGCHAIN_PROJECT"] = st.secrets.get("LANGSMITH_PROJECT", "career-planner")
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"  # 确保使用正确的端点
            
            # 创建客户端并测试连接 (仅在API状态页面显示消息)
            client = Client(api_key=langsmith_key)
            
            # 简单地使用API调用来验证连接
            try:
                # 使用Client的list_projects方法检查连接
                projects = client.list_projects(limit=1)
                st.session_state.api_status["langsmith"] = True
                # 不显示成功消息，只在API状态页面显示
            except Exception as inner_e:
                st.error(f"LangSmith API连接测试失败: {str(inner_e)}")
                st.session_state.api_status["langsmith"] = False
        else:
            st.session_state.api_status["langsmith"] = False
            st.warning("LangSmith API密钥未设置")
    except Exception as e:
        st.error(f"LangSmith API error: {str(e)}")
        st.session_state.api_status["langsmith"] = False

# 添加一个修改后的call_openrouter函数，包含模型信息的追踪
@traceable(run_type="llm", name="OpenRouter AI调用")
def call_openrouter(messages, model, temperature=0.7, is_vision=False, run_name="openrouter_call"):
    """调用OpenRouter API获取LLM响应"""
    # 这个特殊变量是为了LangSmith追踪元数据
    global _run_metadata
    
    # 设置元数据字典以在LangSmith中使用
    _run_metadata = {
        "model_name": model,
        "temperature": str(temperature), 
        "is_vision": str(is_vision),
        "messages_count": str(len(messages)),
        "model_provider": "OpenRouter"
    }
    
    try:
        api_key = st.secrets.get("OPENROUTER_API_KEY")
        if not api_key:
            return "Error: OpenRouter API key not set"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://career-planner.streamlit.app"
        }
        
        # 创建JSON安全的消息复制版本
        safe_messages = []
        for msg in messages:
            safe_msg = {}
            for key, value in msg.items():
                if isinstance(value, str):
                    # 仅复制字符串值，不做特殊处理
                    safe_msg[key] = value
                else:
                    # 非字符串值直接复制
                    safe_msg[key] = value
            safe_messages.append(safe_msg)
        
        payload = {
            "model": model,
            "messages": safe_messages,
            "temperature": temperature
        }
        
        # For vision models, we might need additional parameters
        if is_vision:
            # Additional vision-specific settings if needed
            pass
        
        print(f"调用OpenRouter API - 模型: {model}, 温度: {temperature}")
        
        # 发送API请求
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        result = response.json()
        
        # 如果有模型信息，添加到元数据
        if "model" in result:
            _run_metadata["actual_model"] = result["model"]
            print(f"实际使用的模型: {result['model']}")
        
        # 提取响应内容
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            error_msg = f"Request failed: {str(result)}"
            print(error_msg)
            return error_msg
    except Exception as e:
        error_msg = f"Error during request: {str(e)}"
        print(error_msg)
        return error_msg

# Initialize LangSmith client
def init_langsmith():
    """Initialize LangSmith client from secrets."""
    try:
        langsmith_api_key = st.secrets.get("LANGSMITH_API_KEY", "")
        langsmith_project = st.secrets.get("LANGSMITH_PROJECT", "career-planner")
        
        if langsmith_api_key:
            os.environ["LANGCHAIN_API_KEY"] = langsmith_api_key  # 兼容旧版本
            os.environ["LANGSMITH_API_KEY"] = langsmith_api_key
            os.environ["LANGCHAIN_PROJECT"] = langsmith_project
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            
            # 启用详细日志记录
            os.environ["LANGCHAIN_VERBOSE"] = "true"
            
            # 确保记录所有字段
            os.environ["LANGCHAIN_HIDE_INPUTS"] = "false"
            os.environ["LANGCHAIN_HIDE_MODEL_INFO"] = "false"
            
            print("LangSmith 配置完成，已启用详细跟踪")
            
            return True
        return False
    except Exception as e:
        st.error(f"Error initializing LangSmith: {str(e)}")
        return False

# 初始化LangSmith
langsmith_enabled = init_langsmith()

# Available models with full names
AVAILABLE_MODELS = {
    "qwen/qwen-max": "Qwen Max",
    "qwen/qwen3-32b:free": "Qwen 3 32B",
    "deepseek/deepseek-chat-v3-0324:free": "DeepSeek Chat v3"
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
        "role": "你是一位经验丰富的职业规划顾问，拥有丰富的行业知识和见解。",
        "task": "基于用户的学术背景、专业、期望进入的行业和职位，分析他们的职业发展路径，并提供具体、可行的建议。",
        "output_format": "请提供结构化的职业规划分析，包括：\n1. 背景分析\n2. 职业路径建议\n3. 技能发展方向\n4. 行业前景\n5. 短期和长期目标",
        "model": "qwen/qwen-max"
    }

if 'submission_agent_settings' not in st.session_state:
    st.session_state.submission_agent_settings = {
        "role": "你是一位专业的职业规划报告编辑，擅长整合信息并创建视觉吸引力强的报告。",
        "task": "基于职业规划草稿，补充相关行业数据和信息，创建一份包含文字描述和可视化内容的完整报告。",
        "output_format": "请提供专业的职业规划报告，包括：\n1. 执行摘要\n2. 详细分析\n3. 数据支持图表\n4. 行动计划\n5. 资源建议",
        "model": "qwen/qwen-max"
    }

if 'draft_report' not in st.session_state:
    st.session_state.draft_report = ""

if 'final_report' not in st.session_state:
    st.session_state.final_report = ""

if 'api_status' not in st.session_state:
    st.session_state.api_status = {
        "openrouter": False,
        "langsmith": False
    }

# Simulated knowledge database
class KnowledgeDatabase:
    def __init__(self):
        # Load data from CSV file
        try:
            print(f"尝试加载CSV知识库: 模拟数据库.csv")
            self.df = pd.read_csv("模拟数据库.csv")
            print(f"成功加载CSV，共有{len(self.df)}行数据")
            self.industries = {}
            self.majors = {}
            
            # Process data from CSV
            for _, row in self.df.iterrows():
                industry = row["行业"]
                position = row["岗位"]
                skill_group = row["技能组"]
                skill_meaning = row["技能组意义"]
                knowledge_l1 = row["知识树-1级"]
                knowledge_l2 = row["知识树-2级"]
                
                # Create or get industry
                if industry not in self.industries:
                    self.industries[industry] = {
                        "positions": [],
                        "overview": f"{industry}行业需要各种专业技能，提供多种职业发展路径。"
                    }
                
                # Check if position already exists
                position_exists = False
                for pos in self.industries[industry]["positions"]:
                    if pos["name"] == position:
                        position_exists = True
                        # Update skills if not already included
                        if skill_group not in pos["skills"]:
                            pos["skills"] += f", {skill_group}"
                        break
                
                # Add new position if not exists
                if not position_exists:
                    self.industries[industry]["positions"].append({
                        "name": position,
                        "skills": skill_group,
                        "knowledge": f"{knowledge_l1}: {knowledge_l2}",
                        "education": "相关领域的学士及以上学位",
                        "skill_description": skill_meaning,
                        "prospects": "行业需求稳定，专业发展前景良好",
                        "salary": "根据经验和技能水平，薪资范围会有所不同"
                    })
            
            # Create major data based on industry connections
            unique_knowledge = set(self.df["知识树-1级"].unique())
            for knowledge in unique_knowledge:
                relevant_rows = self.df[self.df["知识树-1级"] == knowledge]
                relevant_industries = relevant_rows["行业"].unique()
                relevant_positions = relevant_rows["岗位"].unique()
                
                self.majors[knowledge] = {
                    "suitable_industries": list(relevant_industries),
                    "suitable_positions": list(relevant_positions),
                    "core_skills": ", ".join(relevant_rows["技能组"].unique()),
                    "career_paths": f"可从初级职位发展到高级职位，如{', '.join(relevant_positions[:3]) if len(relevant_positions) >= 3 else ', '.join(relevant_positions)}"
                }
                
            print(f"知识库初始化完成: {len(self.industries)}个行业, {len(self.majors)}个专业领域")
            for industry in self.industries.keys():
                print(f"  - 行业: {industry}, 职位数: {len(self.industries[industry]['positions'])}")
            for major in list(self.majors.keys())[:5]:  # 仅显示前5个专业
                print(f"  - 专业领域: {major}")
                
        except Exception as e:
            print(f"加载CSV数据失败: {str(e)}")
            # Fallback to demo data
            self.initialize_demo_data()
    
    def initialize_demo_data(self):
        # This demo data is used as fallback if CSV loading fails
        self.industries = {
            "IT/Internet": {
                "positions": [
                    {
                        "name": "Software Engineer",
                        "skills": "Python, Java, JavaScript, Data Structures, Algorithms",
                        "education": "Bachelor's degree or above in Computer Science/Software Engineering",
                        "salary": "$80K-$150K",
                        "prospects": "Continuous industry demand, broad development space"
                    },
                    {
                        "name": "Frontend Developer",
                        "skills": "HTML, CSS, JavaScript, React/Vue/Angular, TypeScript",
                        "education": "Bachelor's degree or above in Computer Science related majors",
                        "salary": "$70K-$130K",
                        "prospects": "High demand with continuous internet product development"
                    },
                    {
                        "name": "Data Analyst",
                        "skills": "SQL, Python, R, Excel, Data Visualization, Statistics",
                        "education": "Bachelor's degree or above in Statistics/Mathematics/Computer Science",
                        "salary": "$75K-$140K",
                        "prospects": "Scarce talent in the big data era, good development prospects"
                    }
                ],
                "overview": "The IT/Internet industry has fast technology updates and fierce competition, but offers high salary levels and development space"
            },
            "Finance": {
                "positions": [
                    {
                        "name": "Investment Analyst",
                        "skills": "Financial Analysis, Valuation Models, Excel, Financial Market Knowledge",
                        "education": "Bachelor's degree or above in Finance/Economics/Accounting",
                        "salary": "$85K-$150K",
                        "prospects": "Stable financial industry with clear promotion paths"
                    },
                    {
                        "name": "Risk Control",
                        "skills": "Risk Assessment, Data Analysis, Regulatory Knowledge, Financial Instruments",
                        "education": "Bachelor's degree or above in Finance/Mathematics/Statistics",
                        "salary": "$90K-$160K",
                        "prospects": "Stable demand for risk control talent, good career development prospects"
                    }
                ],
                "overview": "The financial industry is relatively stable, emphasizing professionalism and compliance, with a mature career development system"
            }
        }
        
        self.majors = {
            "Computer Science": {
                "suitable_industries": ["IT/Internet", "Finance", "Education"],
                "suitable_positions": ["Software Engineer", "Data Analyst", "IT Consultant"],
                "core_skills": "Programming Languages, Data Structures, Algorithms, Databases, Network Fundamentals",
                "career_paths": "Can develop from Developer to Architect, Technical Manager, or Product Manager"
            },
            "Finance": {
                "suitable_industries": ["Finance", "Consulting", "Corporate Finance"],
                "suitable_positions": ["Investment Analyst", "Risk Control", "Financial Advisor"],
                "core_skills": "Financial Analysis, Financial Markets, Risk Management, Investment Theory",
                "career_paths": "Can develop from Analyst to Investment Manager, Risk Manager, or CFO"
            }
        }
    
    def query(self, query_type, query_value):
        """
        Query the database with different query types
        query_type can be: 'industry', 'position', 'major'
        """
        if query_type == 'industry' and query_value in self.industries:
            return self.industries[query_value]
        elif query_type == 'major' and query_value in self.majors:
            return self.majors[query_value]
        elif query_type == 'position':
            # Search for position across all industries
            for industry, industry_data in self.industries.items():
                for position in industry_data['positions']:
                    if position['name'] == query_value:
                        return position
            return None
        else:
            return None

# Initialize knowledge database
knowledge_db = KnowledgeDatabase()

# Function to analyze transcript with vision model through OpenRouter
def analyze_transcript_with_vision_model(image_bytes):
    try:
        api_key = st.secrets.get("OPENROUTER_API_KEY")
        if not api_key:
            return "Error: OpenRouter API key not set"
        
        # Convert image to base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Create message with image
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "This is a transcript. Please identify and extract all course names, credits, and grade information, and organize them into a table format."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ]
        
        # Use Qwen's vision model through OpenRouter
        return call_openrouter(messages, "qwen/qwen2.5-vl-72b-instruct", temperature=0.3, is_vision=True)
    except Exception as e:
        return f"Error during analysis: {str(e)}"

# Function to render Mermaid diagrams
def render_mermaid(mermaid_code):
    # 清理可能包含的空格或特殊字符
    mermaid_code = mermaid_code.strip()
    
    html = f"""
    <div class="mermaid">
    {mermaid_code}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({{ 
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose',
            logLevel: 'error'
        }});
    </script>
    """
    components.html(html, height=500)

# Function to query knowledge database
@traceable(run_type="chain", name="知识库查询")
def query_knowledge_db(user_inputs):
    # 创建元数据字典
    run_metadata = {
        "query_type": "knowledge_db",
        "major": user_inputs['major'],
        "target_industry": user_inputs['target_industry'],
        "target_position": user_inputs['target_position']
    }
    
    print(f"查询知识库: 专业={user_inputs['major']}, 行业={user_inputs['target_industry']}, 职位={user_inputs['target_position']}")
    results = []
    
    # Query by industry
    if user_inputs['target_industry']:
        industry_data = knowledge_db.query('industry', user_inputs['target_industry'])
        if industry_data:
            print(f"找到行业信息: {user_inputs['target_industry']}, 包含{len(industry_data['positions'])}个职位")
            results.append(f"行业概览 - {user_inputs['target_industry']}:\n{industry_data['overview']}")
            
            # If position is specified, find specific position data
            if user_inputs['target_position']:
                found = False
                for position in industry_data['positions']:
                    if position['name'] == user_inputs['target_position']:
                        found = True
                        print(f"找到职位信息: {position['name']}, 技能: {position['skills']}")
                        # Check if we have new fields in our updated model
                        if 'skill_description' in position:
                            results.append(f"职位详情 - {position['name']}:\n"
                                          f"所需技能: {position['skills']}\n"
                                          f"技能详细描述: {position.get('skill_description', '无相关描述')}\n"
                                          f"相关知识领域: {position.get('knowledge', '无特定知识领域')}\n"
                                          f"教育要求: {position['education']}\n"
                                          f"薪资范围: {position['salary']}\n"
                                          f"职业前景: {position['prospects']}")
                        else:
                            results.append(f"职位详情 - {position['name']}:\n"
                                          f"所需技能: {position['skills']}\n"
                                          f"教育要求: {position['education']}\n"
                                          f"薪资范围: {position['salary']}\n"
                                          f"职业前景: {position['prospects']}")
                        break
                
                if not found:
                    print(f"未找到职位: {user_inputs['target_position']}")
                    results.append(f"在{user_inputs['target_industry']}行业中未找到{user_inputs['target_position']}职位的详细信息。")
                    # List similar positions as alternatives
                    results.append(f"{user_inputs['target_industry']}行业中的其他职位:")
                    for position in industry_data['positions']:
                        results.append(f"- {position['name']}: {position.get('skills', '无技能信息')}")
            else:
                # List all positions in this industry
                results.append(f"{user_inputs['target_industry']}行业中的热门职位:")
                for position in industry_data['positions']:
                    skills_summary = position['skills'].split(',')[0:3] if ',' in position['skills'] else [position['skills']]
                    skills_text = ', '.join(skills_summary)
                    results.append(f"- {position['name']}: 技能要求({skills_text}), {position['prospects']}")
    
    # Query by major
    if user_inputs['major']:
        major_data = knowledge_db.query('major', user_inputs['major'])
        if major_data:
            print(f"找到专业信息: {user_inputs['major']}, 适合行业: {major_data['suitable_industries']}")
            results.append(f"{user_inputs['major']}专业的职业方向:\n"
                          f"适合的行业: {', '.join(major_data['suitable_industries'])}\n"
                          f"适合的职位: {', '.join(major_data['suitable_positions'])}\n"
                          f"核心技能: {major_data['core_skills']}\n"
                          f"职业发展路径: {major_data['career_paths']}")
        else:
            print(f"未找到专业的精确匹配: {user_inputs['major']}, 尝试模糊匹配")
            # Try fuzzy match with knowledge areas
            found = False
            for major_name, major_info in knowledge_db.majors.items():
                if user_inputs['major'] in major_name or major_name in user_inputs['major']:
                    print(f"找到相关专业: {major_name}")
                    results.append(f"未找到完全匹配的专业，但找到相关专业 {major_name}:\n"
                                 f"适合的行业: {', '.join(major_info['suitable_industries'])}\n"
                                 f"适合的职位: {', '.join(major_info['suitable_positions'])}\n"
                                 f"核心技能: {major_info['core_skills']}\n"
                                 f"职业发展路径: {major_info['career_paths']}")
                    found = True
                    break
            
            if not found:
                results.append(f"未找到与{user_inputs['major']}专业直接相关的信息。建议考虑以下知识领域:")
                for major_name in list(knowledge_db.majors.keys())[:5]:  # List top 5 available majors
                    results.append(f"- {major_name}")
    
    # Query by position (if not already found)
    if user_inputs['target_position'] and not user_inputs['target_industry']:
        position_found = False
        for industry, industry_data in knowledge_db.industries.items():
            for position in industry_data['positions']:
                if position['name'] == user_inputs['target_position']:
                    position_found = True
                    print(f"找到职位信息(不指定行业): {position['name']} in {industry}")
                    results.append(f"职位详情 - {position['name']} (在{industry}行业中):\n"
                                  f"所需技能: {position['skills']}\n"
                                  f"技能详细描述: {position.get('skill_description', '无相关描述')}\n"
                                  f"相关知识领域: {position.get('knowledge', '无特定知识领域')}\n"
                                  f"教育要求: {position['education']}\n"
                                  f"薪资范围: {position['salary']}\n"
                                  f"职业前景: {position['prospects']}")
                    break
            if position_found:
                break
        
        if not position_found:
            print(f"未找到职位(不指定行业): {user_inputs['target_position']}")
            results.append(f"未找到{user_inputs['target_position']}职位的详细信息。")
            # Try to suggest similar positions
            similar_positions = []
            for industry, industry_data in knowledge_db.industries.items():
                for position in industry_data['positions']:
                    if user_inputs['target_position'] in position['name'] or position['name'] in user_inputs['target_position']:
                        similar_positions.append((position['name'], industry))
            
            if similar_positions:
                results.append("可能相关的职位:")
                for pos, ind in similar_positions:
                    results.append(f"- {pos} (在{ind}行业)")
    
    # If no specific queries matched, provide general industry overview
    if not results:
        print("未找到任何相关信息，提供通用概览")
        results.append("知识库中未找到与您的查询直接匹配的信息。")
        results.append("可用的行业信息:")
        for industry in knowledge_db.industries.keys():
            results.append(f"- {industry}")
        
        results.append("\n可用的知识领域:")
        for major in knowledge_db.majors.keys():
            results.append(f"- {major}")
    
    response = "\n\n".join(results)
    print(f"知识库查询完成，返回{len(response)}字节的信息")
    return response

# 使用 @traceable 装饰器追踪生成职业规划草稿的过程
@traceable(run_type="chain", name="职业规划草稿生成")
def generate_career_planning_draft(user_inputs, agent_settings):
    """使用追踪装饰器生成职业规划草稿"""
    # 创建元数据字典
    run_metadata = {
        "model": agent_settings["model"],
        "step": "draft_generation",
        "target_industry": user_inputs['target_industry'],
        "target_position": user_inputs['target_position']
    }
    
    try:
        # Query the knowledge database
        kb_data = query_knowledge_db(user_inputs)
        
        # Prepare the prompt for the career planning assistant
        role = agent_settings["role"]
        task = agent_settings["task"]
        output_format = agent_settings["output_format"]
        model = agent_settings["model"]
        
        # 记录使用的模型信息
        print(f"职业规划草稿使用模型: {model}")
        
        user_info = f"""
        用户信息:
        - 大学: {user_inputs['university']}
        - 专业: {user_inputs['major']}
        - 目标行业: {user_inputs['target_industry']}
        - 目标职位: {user_inputs['target_position']}
        
        成绩单信息:
        {user_inputs['transcript_text']}
        
        知识库信息 (非常重要，请务必详细参考这些信息):
        {kb_data}
        """
        
        system_prompt = f"""{role}

{task}

请务必详细参考知识库中提供的信息，这些是真实的行业和职位数据，对职业规划至关重要。根据用户的专业、目标和知识库信息，提供有针对性的职业建议。

输出格式要求:
{output_format}
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_info}
        ]
        
        # Make API call through OpenRouter
        response = call_openrouter(
            messages=messages, 
            model=model, 
            temperature=0.7,
            run_name="职业规划AI调用"
        )
        
        return response
    except Exception as e:
        error_msg = f"报告生成过程中发生错误: {str(e)}"
        print(error_msg)
        return error_msg

# 使用 @traceable 装饰器追踪生成最终报告的过程
@traceable(run_type="chain", name="最终职业规划报告生成")
def generate_final_report(draft_report, agent_settings):
    """使用追踪装饰器生成最终职业规划报告"""
    # 创建元数据字典
    run_metadata = {
        "model": agent_settings["model"],
        "step": "final_report_generation",
        "draft_length": len(draft_report) if draft_report else 0
    }
    
    try:
        # Prepare the prompt for the submission agent
        role = agent_settings["role"]
        task = agent_settings["task"]
        output_format = agent_settings["output_format"]
        model = agent_settings["model"]
        
        # 记录使用的模型信息
        print(f"最终报告使用模型: {model}")
        
        # 更新系统提示，提供更简单的Mermaid图表示例和更严格的语法要求
        system_prompt = f"""{role}

{task}

请基于草稿中的数据和行业信息，确保最终报告详细反映知识库中的专业数据。这些行业和职位信息是真实的，应该在报告中得到充分展示。

输出格式要求:
{output_format}

请在适当的位置包含Mermaid图表。创建Mermaid图表时，请注意以下几点：
1. 将图表代码包裹在```mermaid和```标签中
2. 使用非常简单的Mermaid语法，避免复杂的功能
3. 创建一个简单的职业路径流程图
4. 图表中只使用基本节点和连接，不要使用复杂样式
5. 避免在节点文字中使用特殊字符和标点符号
6. 所有节点必须有连接，不能有孤立节点

非常简单的有效Mermaid代码示例：
```mermaid
flowchart TD
    A[开始] --> B[学习]
    B --> C[工作]
```

注意：请确保使用最简单的语法创建图表，避免任何可能导致语法错误的复杂功能。
所有内容请使用中文输出。
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"这是职业规划报告草稿：\n\n{draft_report}\n\n基于这份草稿，请补充相关信息，创建一份包含文字和一个简单流程图的完整报告。图表必须非常简单，仅使用基本节点和连接。请用中文输出所有内容。"}
        ]
        
        # Make API call through OpenRouter
        response = call_openrouter(
            messages=messages, 
            model=model, 
            temperature=0.7,
            run_name="报告生成AI调用"
        )
        
        return response
    except Exception as e:
        error_msg = f"报告生成过程中发生错误: {str(e)}"
        print(error_msg)
        return error_msg

# Check API status on startup
check_api_status()

# Main application interface
st.title("Career Planning Assistant")

# Create tabs
tab1, tab2, tab3 = st.tabs(["Information Collection", "Agent Settings", "API Status"])

# Tab 1: Information Collection
with tab1:
    st.header("User Information Collection")
    
    col1, col2 = st.columns(2)
    
    with col1:
        university = st.text_input("University", value=st.session_state.user_inputs["university"])
        major = st.text_input("Major", value=st.session_state.user_inputs["major"])
    
    with col2:
        target_industry = st.text_input("Target Industry", value=st.session_state.user_inputs["target_industry"])
        target_position = st.text_input("Target Position", value=st.session_state.user_inputs["target_position"])
    
    # Transcript upload
    uploaded_file = st.file_uploader("Upload Transcript (Image formats only)", type=['png', 'jpg', 'jpeg'])
    
    transcript_text = ""
    if uploaded_file is not None:
        # Read the file
        image_bytes = uploaded_file.getvalue()
        
        # Call vision model to analyze the transcript
        with st.spinner("Analyzing transcript..."):
            transcript_text = analyze_transcript_with_vision_model(image_bytes)
        
        # Display the analysis result in an expandable section
        with st.expander("Transcript Analysis Result", expanded=True):
            st.write(transcript_text)
    
    # Store user inputs in session state
    if st.button("Start Analysis"):
        # Validate inputs
        if not (major or target_industry or target_position):
            st.error("Error: At least one of Major, Target Industry, or Target Position must be filled")
        else:
            st.session_state.user_inputs = {
                "university": university,
                "major": major,
                "target_industry": target_industry,
                "target_position": target_position,
                "transcript_text": transcript_text
            }
            
            # Generate career planning draft
            with st.spinner("Generating career planning report draft..."):
                draft_report = generate_career_planning_draft(
                    st.session_state.user_inputs,
                    st.session_state.career_agent_settings
                )
                st.session_state.draft_report = draft_report
            
            # Display the draft report in a collapsible section
            with st.expander("Career Planning Report Draft", expanded=False):
                st.write(st.session_state.draft_report)
            
            # Generate final report
            with st.spinner("Generating final career planning report..."):
                final_report = generate_final_report(
                    st.session_state.draft_report,
                    st.session_state.submission_agent_settings
                )
                st.session_state.final_report = final_report
            
            # Display the final report
            st.subheader("Final Career Planning Report")
            
            # 显示报告内容
            if st.session_state.final_report:
                # 更新处理图表的方式，添加更多健壮性
                try:
                    # 检查是否包含Mermaid图表
                    if "```mermaid" in st.session_state.final_report:
                        # Process and display text and Mermaid diagrams separately
                        report_parts = st.session_state.final_report.split("```mermaid")
                        
                        # Display the first text part
                        if report_parts and len(report_parts) > 0:
                            st.write(report_parts[0])
                        
                        # Process each mermaid diagram and following text
                        for i in range(1, len(report_parts)):
                            part = report_parts[i]
                            # Split by the closing code block marker
                            if "```" in part:
                                mermaid_code, remaining_text = part.split("```", 1)
                                # Clean mermaid code and render
                                mermaid_code = mermaid_code.strip()
                                
                                # 为调试添加一个选项来显示原始mermaid代码
                                with st.expander("查看图表代码"):
                                    st.code(mermaid_code, language="mermaid")
                                
                                # 尝试修复常见的语法错误
                                if "graph" in mermaid_code and "flowchart" not in mermaid_code:
                                    # 旧版语法，转换为新版
                                    mermaid_code = mermaid_code.replace("graph", "flowchart")
                                
                                try:
                                    # Render diagram with error handling
                                    render_mermaid(mermaid_code)
                                except Exception as e:
                                    st.error(f"图表渲染失败: {str(e)}")
                                    st.code(mermaid_code, language="mermaid")
                                    
                                    # 尝试渲染一个备用的简单图表
                                    st.warning("尝试渲染备用图表...")
                                    try:
                                        fallback_code = """
flowchart TD
    A[学习] --> B[实践]
    B --> C[就业]
                                        """
                                        render_mermaid(fallback_code)
                                    except:
                                        st.error("备用图表也渲染失败")
                                
                                # Display the text that follows
                                st.write(remaining_text)
                            else:
                                # No closing marker found, just display as text
                                st.write(part)
                    else:
                        # 如果没有图表标记，直接显示报告
                        st.write(st.session_state.final_report)
                except Exception as e:
                    # 如果解析失败，直接显示完整报告
                    st.error(f"处理图表时出错: {str(e)}")
                    st.write(st.session_state.final_report)

# Tab 2: Agent Settings
with tab2:
    st.header("Agent Settings")
    
    st.subheader("Career Planning Assistant Settings")
    career_role = st.text_area("Character Setting", value=st.session_state.career_agent_settings["role"], height=100)
    career_task = st.text_area("Task Description", value=st.session_state.career_agent_settings["task"], height=100)
    career_output_format = st.text_area("Output Format", value=st.session_state.career_agent_settings["output_format"], height=150)
    
    # Add model selection dropdown for career planning agent
    career_model = st.selectbox(
        "Select Career Planning Assistant Model", 
        options=list(AVAILABLE_MODELS.keys()),
        format_func=lambda x: AVAILABLE_MODELS[x],
        index=list(AVAILABLE_MODELS.keys()).index(st.session_state.career_agent_settings["model"])
    )
    
    st.subheader("Report Submission Assistant Settings")
    submission_role = st.text_area("Character Setting", value=st.session_state.submission_agent_settings["role"], height=100)
    submission_task = st.text_area("Task Description", value=st.session_state.submission_agent_settings["task"], height=100)
    submission_output_format = st.text_area("Output Format", value=st.session_state.submission_agent_settings["output_format"], height=150)
    
    # Add model selection dropdown for submission agent
    submission_model = st.selectbox(
        "Select Report Submission Assistant Model", 
        options=list(AVAILABLE_MODELS.keys()),
        format_func=lambda x: AVAILABLE_MODELS[x],
        index=list(AVAILABLE_MODELS.keys()).index(st.session_state.submission_agent_settings["model"])
    )
    
    if st.button("Save Settings"):
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
        
        st.success("Settings saved successfully")

# Tab 3: API Status
with tab3:
    st.header("API Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        status = "✅ 已连接" if st.session_state.api_status["openrouter"] else "❌ 未连接"
        st.metric("OpenRouter API", status)
        
        if not st.session_state.api_status["openrouter"]:
            st.warning("请检查Streamlit Secrets中的OPENROUTER_API_KEY是否正确设置")
    
    with col2:
        status = "✅ 已连接" if st.session_state.api_status["langsmith"] else "❌ 未连接"
        st.metric("LangSmith", status)
        
        if not st.session_state.api_status["langsmith"]:
            st.warning("请检查Streamlit Secrets中的LANGSMITH_API_KEY是否正确设置")
    
    # 添加LangSmith设置信息
    if st.session_state.api_status["langsmith"]:
        st.subheader("LangSmith配置")
        st.code(f"""
项目名称: {os.environ.get('LANGCHAIN_PROJECT', '未设置')}
端点: {os.environ.get('LANGCHAIN_ENDPOINT', '未设置')}
追踪状态: {'启用' if os.environ.get('LANGCHAIN_TRACING_V2') == 'true' else '未启用'}
        """)
    
    # Add a refresh button for API status
    if st.button("刷新状态"):
        with st.spinner("正在检查API状态..."):
            check_api_status()
        st.rerun()