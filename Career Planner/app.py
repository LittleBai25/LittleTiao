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
import datetime

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Career Planning Assistant",
    page_icon="🚀",
    layout="wide"
)

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
        # This would be replaced with an actual database connection in production
        self.data = {
            "industries": {
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
            },
            "majors": {
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
            
            # 简单地使用API调用来验证连接，不使用get_project方法
            try:
                # 尝试创建一个简单的运行来测试API连接
                run_tree = RunTree(
                    name="test_connection",
                    run_type="chain",
                    inputs={"test": "connection"},
                    client=client
                )
                run_tree.post()
                run_tree.end(outputs={"result": "success"})
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

# Initialize LangSmith client if enabled
def init_langsmith():
    try:
        langsmith_api_key = st.secrets.get("LANGSMITH_API_KEY")
        if not langsmith_api_key:
            # 不在UI中显示警告，只返回None
            return None
            
        langsmith_project = st.secrets.get("LANGSMITH_PROJECT", "career-planner") 
        # 设置所有必要的环境变量
        os.environ["LANGSMITH_API_KEY"] = langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = langsmith_project or "default"
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
        # 添加额外的必要环境变量
        os.environ["LANGCHAIN_API_KEY"] = langsmith_api_key  # 兼容性
        
        # 创建并返回客户端 - 不显示任何UI消息
        return Client(api_key=langsmith_api_key) 
    except Exception as e:
        # 只在Debug模式下记录错误，不显示UI消息
        print(f"LangSmith初始化错误: {str(e)}")
        return None

# 添加新的LangSmith追踪工具函数
def log_to_langsmith(name, inputs, outputs=None, error=None, parent_run_id=None):
    """使用直接API调用记录到LangSmith"""
    try:
        api_key = os.environ.get("LANGSMITH_API_KEY")
        if not api_key:
            print("没有找到LangSmith API密钥")
            return None
            
        project_name = os.environ.get("LANGCHAIN_PROJECT", "career-planner")
        
        # 准备基本的运行数据
        run_data = {
            "name": name,
            "run_type": "chain",
            "inputs": inputs,
            "project_name": project_name,
            "start_time": datetime.datetime.utcnow().isoformat() + "Z"
        }
        
        # 如果有父运行ID，添加到数据中
        if parent_run_id:
            run_data["parent_run_id"] = parent_run_id
            
        # 发送创建运行的请求
        response = requests.post(
            "https://api.smith.langchain.com/runs",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=run_data
        )
        
        if response.status_code != 200:
            print(f"创建LangSmith运行失败: {response.status_code} - {response.text}")
            return None
            
        # 获取运行ID
        run_id = response.json().get("id")
        print(f"成功创建LangSmith运行: {run_id}, 名称: {name}")
        
        # 如果提供了输出或错误，立即结束运行
        if outputs is not None or error is not None:
            end_data = {
                "end_time": datetime.datetime.utcnow().isoformat() + "Z"
            }
            
            if outputs is not None:
                end_data["outputs"] = outputs
                end_data["status"] = "success"
            elif error is not None:
                end_data["error"] = str(error)
                end_data["status"] = "error"
                
            # 发送结束运行的请求
            end_response = requests.patch(
                f"https://api.smith.langchain.com/runs/{run_id}",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=end_data
            )
            
            if end_response.status_code != 200:
                print(f"结束LangSmith运行失败: {end_response.status_code} - {end_response.text}")
        
        return run_id
    except Exception as e:
        print(f"LangSmith API调用错误: {str(e)}")
        return None

# 修改调用OpenRouter的函数，集成LangSmith日志
def call_openrouter(messages, model, temperature=0.7, is_vision=False, run_name="openrouter_call", parent_run_id=None):
    run_id = None
    start_time = datetime.datetime.utcnow()
    
    try:
        api_key = st.secrets.get("OPENROUTER_API_KEY")
        if not api_key:
            return "Error: OpenRouter API key not set"
        
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
        
        # 记录LLM调用开始
        run_id = log_to_langsmith(
            name=run_name,
            inputs={
                "messages": messages, 
                "model": model,
                "temperature": temperature
            },
            parent_run_id=parent_run_id
        )
        
        # 发送API请求
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        result = response.json()
        
        # 提取响应内容
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            
            # 记录成功的结果
            if run_id:
                log_to_langsmith(
                    name=f"{run_name}_end",
                    inputs={},
                    outputs={"content": content},
                    parent_run_id=run_id
                )
                
                # 更新父运行
                end_time = datetime.datetime.utcnow()
                duration_ms = int((end_time - start_time).total_seconds() * 1000)
                
                requests.patch(
                    f"https://api.smith.langchain.com/runs/{run_id}",
                    headers={
                        "Authorization": f"Bearer {os.environ.get('LANGSMITH_API_KEY')}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "end_time": end_time.isoformat() + "Z",
                        "status": "success",
                        "outputs": {"content": content[:1000] + ("..." if len(content) > 1000 else "")},
                        "metrics": {
                            "tokens": len(content.split()) * 1.3,  # 估算
                            "duration_ms": duration_ms
                        }
                    }
                )
            
            return content
        else:
            error_msg = f"Request failed: {str(result)}"
            
            # 记录错误
            if run_id:
                requests.patch(
                    f"https://api.smith.langchain.com/runs/{run_id}",
                    headers={
                        "Authorization": f"Bearer {os.environ.get('LANGSMITH_API_KEY')}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "end_time": datetime.datetime.utcnow().isoformat() + "Z",
                        "status": "error",
                        "error": error_msg
                    }
                )
            
            return error_msg
    except Exception as e:
        error_msg = f"Error during request: {str(e)}"
        
        # 记录异常
        if run_id:
            requests.patch(
                f"https://api.smith.langchain.com/runs/{run_id}",
                headers={
                    "Authorization": f"Bearer {os.environ.get('LANGSMITH_API_KEY')}",
                    "Content-Type": "application/json"
                },
                json={
                    "end_time": datetime.datetime.utcnow().isoformat() + "Z",
                    "status": "error",
                    "error": error_msg
                }
            )
        
        return error_msg

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
def query_knowledge_db(user_inputs):
    results = []
    
    # Query by industry
    if user_inputs['target_industry']:
        industry_data = knowledge_db.query('industry', user_inputs['target_industry'])
        if industry_data:
            results.append(f"Industry Overview - {user_inputs['target_industry']}:\n{industry_data['overview']}")
            
            # If position is specified, find specific position data
            if user_inputs['target_position']:
                for position in industry_data['positions']:
                    if position['name'] == user_inputs['target_position']:
                        results.append(f"Position Details - {position['name']}:\n"
                                      f"Required Skills: {position['skills']}\n"
                                      f"Education Requirements: {position['education']}\n"
                                      f"Salary Range: {position['salary']}\n"
                                      f"Career Prospects: {position['prospects']}")
                        break
            else:
                # List all positions in this industry
                results.append(f"Popular Positions in {user_inputs['target_industry']}:")
                for position in industry_data['positions']:
                    results.append(f"- {position['name']}: {position['prospects']}")
    
    # Query by major
    if user_inputs['major']:
        major_data = knowledge_db.query('major', user_inputs['major'])
        if major_data:
            results.append(f"Career Directions for {user_inputs['major']} Major:\n"
                          f"Suitable Industries: {', '.join(major_data['suitable_industries'])}\n"
                          f"Suitable Positions: {', '.join(major_data['suitable_positions'])}\n"
                          f"Core Skills: {major_data['core_skills']}\n"
                          f"Career Paths: {major_data['career_paths']}")
    
    # Query by position (if not already found)
    if user_inputs['target_position'] and not user_inputs['target_industry']:
        position_data = knowledge_db.query('position', user_inputs['target_position'])
        if position_data:
            results.append(f"Position Details - {user_inputs['target_position']}:\n"
                          f"Required Skills: {position_data['skills']}\n"
                          f"Education Requirements: {position_data['education']}\n"
                          f"Salary Range: {position_data['salary']}\n"
                          f"Career Prospects: {position_data['prospects']}")
    
    return "\n\n".join(results) if results else "No relevant information found in the knowledge base"

# Function to generate career planning draft with LangSmith tracking
def generate_career_planning_draft(user_inputs, agent_settings):
    try:
        # 确保环境变量设置正确
        langsmith_api_key = st.secrets.get("LANGSMITH_API_KEY")
        if langsmith_api_key:
            os.environ["LANGSMITH_API_KEY"] = langsmith_api_key
            os.environ["LANGCHAIN_PROJECT"] = st.secrets.get("LANGSMITH_PROJECT", "career-planner")
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            
        # 开始记录整个职业规划过程
        parent_run_id = log_to_langsmith(
            name="职业规划分析流程",
            inputs={
                "university": user_inputs["university"],
                "major": user_inputs["major"],
                "target_industry": user_inputs["target_industry"],
                "target_position": user_inputs["target_position"]
            }
        )
        
        # Query the knowledge database
        kb_data = query_knowledge_db(user_inputs)
        
        # 记录知识库查询
        kb_run_id = log_to_langsmith(
            name="知识库查询",
            inputs=user_inputs,
            outputs={"knowledge_data": kb_data},
            parent_run_id=parent_run_id
        )
        
        # Prepare the prompt for the career planning assistant
        role = agent_settings["role"]
        task = agent_settings["task"]
        output_format = agent_settings["output_format"]
        model = agent_settings["model"]
        
        user_info = f"""
        用户信息:
        - 大学: {user_inputs['university']}
        - 专业: {user_inputs['major']}
        - 目标行业: {user_inputs['target_industry']}
        - 目标职位: {user_inputs['target_position']}
        
        成绩单信息:
        {user_inputs['transcript_text']}
        
        知识库信息:
        {kb_data}
        """
        
        messages = [
            {"role": "system", "content": f"{role}\n\n{task}\n\n输出格式要求:\n{output_format}"},
            {"role": "user", "content": user_info}
        ]
        
        # 创建职业规划草稿
        draft_run_id = log_to_langsmith(
            name="生成职业规划草稿",
            inputs={"messages": messages},
            parent_run_id=parent_run_id
        )
        
        # Make API call through OpenRouter
        response = call_openrouter(
            messages=messages, 
            model=model, 
            temperature=0.7,
            run_name="职业规划AI调用",
            parent_run_id=draft_run_id
        )
        
        # 更新草稿运行的结果
        log_to_langsmith(
            name="职业规划草稿结果",
            inputs={},
            outputs={"draft": response[:1000] + ("..." if len(response) > 1000 else "")},
            parent_run_id=draft_run_id
        )
        
        return response
    except Exception as e:
        error_msg = f"报告生成过程中发生错误: {str(e)}"
        print(error_msg)
        return error_msg

# Function to generate final career planning report with LangSmith tracking
def generate_final_report(draft_report, agent_settings):
    try:
        # 确保环境变量设置正确
        langsmith_api_key = st.secrets.get("LANGSMITH_API_KEY")
        if langsmith_api_key:
            os.environ["LANGSMITH_API_KEY"] = langsmith_api_key
            os.environ["LANGCHAIN_PROJECT"] = st.secrets.get("LANGSMITH_PROJECT", "career-planner")
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            
        # 开始记录最终报告生成过程
        parent_run_id = log_to_langsmith(
            name="最终职业规划报告生成",
            inputs={"draft_length": len(draft_report)}
        )
        
        # Prepare the prompt for the submission agent
        role = agent_settings["role"]
        task = agent_settings["task"]
        output_format = agent_settings["output_format"]
        model = agent_settings["model"]
        
        # 更新系统提示，提供更简单的Mermaid图表示例和更严格的语法要求
        system_prompt = f"""{role}

{task}

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
        
        # 记录报告生成过程
        report_gen_run_id = log_to_langsmith(
            name="格式化最终报告",
            inputs={"system_prompt_length": len(system_prompt)},
            parent_run_id=parent_run_id
        )
        
        # Make API call through OpenRouter
        response = call_openrouter(
            messages=messages, 
            model=model, 
            temperature=0.7,
            run_name="报告生成AI调用",
            parent_run_id=report_gen_run_id
        )
        
        # 更新报告生成结果
        log_to_langsmith(
            name="最终报告结果",
            inputs={},
            outputs={"final_report_sample": response[:1000] + ("..." if len(response) > 1000 else "")},
            parent_run_id=report_gen_run_id
        )
        
        # 结束最终报告生成过程
        requests.patch(
            f"https://api.smith.langchain.com/runs/{parent_run_id}",
            headers={
                "Authorization": f"Bearer {os.environ.get('LANGSMITH_API_KEY')}",
                "Content-Type": "application/json"
            },
            json={
                "end_time": datetime.datetime.utcnow().isoformat() + "Z",
                "status": "success"
            }
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
            
            # Display the draft report
            st.subheader("Career Planning Report Draft")
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