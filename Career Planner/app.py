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
        "role": "You are an experienced career planning consultant with rich industry knowledge and insights.",
        "task": "Based on the user's academic background, major, desired industry and position, analyze their career development path and provide specific, feasible suggestions.",
        "output_format": "Please provide a structured career planning analysis including:\n1. Background Analysis\n2. Career Path Suggestions\n3. Skills Development Direction\n4. Industry Outlook\n5. Short-term and Long-term Goals",
        "model": "qwen/qwen-max"
    }

if 'submission_agent_settings' not in st.session_state:
    st.session_state.submission_agent_settings = {
        "role": "You are a professional career planning report editor, skilled at integrating information and creating visually appealing reports.",
        "task": "Based on the career planning draft, supplement with relevant industry data and information to create a complete report with text descriptions and visualizations.",
        "output_format": "Please provide a professional career planning report including:\n1. Executive Summary\n2. Detailed Analysis\n3. Data-Supported Charts\n4. Action Plan\n5. Resource Recommendations",
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
            os.environ["LANGSMITH_API_KEY"] = langsmith_key  # Make sure key is set in env 
            os.environ["LANGCHAIN_PROJECT"] = st.secrets.get("LANGSMITH_PROJECT", "career-planner")
            os.environ["LANGCHAIN_TRACING_V2"] = "true"  # Enable tracing
            
            client = Client(api_key=langsmith_key)
            # Just try to access the API
            _ = client.list_projects(limit=1)
            st.session_state.api_status["langsmith"] = True
        else:
            st.session_state.api_status["langsmith"] = False
    except Exception as e:
        st.error(f"LangSmith API error: {str(e)}")
        st.session_state.api_status["langsmith"] = False

# Initialize LangSmith client if enabled
def init_langsmith():
    try:
        langsmith_api_key = st.secrets.get("LANGSMITH_API_KEY")
        if not langsmith_api_key:
            return None
            
        langsmith_project = st.secrets.get("LANGSMITH_PROJECT", "career-planner")
        # Set environment variables for LangSmith
        os.environ["LANGSMITH_API_KEY"] = langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = langsmith_project
        os.environ["LANGCHAIN_TRACING_V2"] = "true"  # Enable tracing
        
        # Return client
        return Client(api_key=langsmith_api_key)
    except Exception as e:
        st.error(f"LangSmith initialization error: {str(e)}")
        return None

# Function to call OpenRouter for API requests
def call_openrouter(messages, model, temperature=0.7, is_vision=False):
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
        
        # For vision models, we might need additional parameters
        if is_vision:
            # Additional vision-specific settings if needed
            pass
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            return f"Request failed: {str(result)}"
    except Exception as e:
        return f"Error during request: {str(e)}"

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
        User Information:
        - University: {user_inputs['university']}
        - Major: {user_inputs['major']}
        - Target Industry: {user_inputs['target_industry']}
        - Target Position: {user_inputs['target_position']}
        
        Transcript Information:
        {user_inputs['transcript_text']}
        
        Knowledge Base Information:
        {kb_data}
        """
        
        messages = [
            {"role": "system", "content": f"{role}\n\n{task}\n\nOutput Format Requirements:\n{output_format}"},
            {"role": "user", "content": user_info}
        ]
        
        # Track with LangSmith if available
        if langsmith_client:
            # Start the run manually
            run_tree = RunTree(
                name="career_planning_draft",
                run_type="chain",
                inputs={"user_inputs": user_inputs, "agent_settings": agent_settings},
                client=langsmith_client
            )
            
            # Start the run explicitly
            run_tree.post()
            
            # Make API call through OpenRouter
            response = call_openrouter(
                messages=messages, 
                model=model, 
                temperature=0.7
            )
            
            # Record the end of the run
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
        return f"Error during generation: {str(e)}"

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
        
        # 更新系统提示，提供更明确的Mermaid语法指导（改为中文）
        system_prompt = f"""{role}

{task}

输出格式要求:
{output_format}

请在适当的位置包含Mermaid图表。创建Mermaid图表时，请注意以下几点：
1. 将图表代码包裹在```mermaid和```标签中
2. 使用有效的Mermaid语法
3. 至少创建一个展示职业发展路径的图表（使用流程图flowchart或思维导图mindmap）
4. 创建一个展示推荐行动的时间线图表
5. 保持图表简洁，确保遵循Mermaid语法规则
6. 在包含图表前检查语法

有效Mermaid代码示例：
```mermaid
flowchart TD
    A[开始] --> B[过程]
    B --> C[结束]
```

另一个示例：
```mermaid
mindmap
  root((职业))
    路径1
      技能A
      技能B
    路径2
      技能C
```
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"这是职业规划报告草稿：\n\n{draft_report}\n\n基于这份草稿，请补充相关信息，创建一份包含文字和图表的完整报告。"}
        ]
        
        # Track with LangSmith if available
        if langsmith_client:
            # Start the run manually
            run_tree = RunTree(
                name="final_report_generation",
                run_type="chain",
                inputs={"draft_report": draft_report, "agent_settings": agent_settings},
                client=langsmith_client
            )
            
            # Start the run explicitly
            run_tree.post()
            
            # Make API call through OpenRouter
            response = call_openrouter(
                messages=messages, 
                model=model, 
                temperature=0.7
            )
            
            # Record the end of the run
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
        return f"Error during generation: {str(e)}"

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
            
            # 更新处理图表的方式
            try:
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
                        with st.expander("View Diagram Code"):
                            st.code(mermaid_code, language="mermaid")
                        
                        try:
                            # Render diagram with error handling
                            render_mermaid(mermaid_code)
                        except Exception as e:
                            st.error(f"Failed to render diagram: {str(e)}")
                            st.code(mermaid_code, language="mermaid")
                        
                        # Display the text that follows
                        st.write(remaining_text)
                    else:
                        # No closing marker found, just display as text
                        st.write(part)
            except Exception as e:
                # 如果解析失败，直接显示完整报告
                st.error(f"Error processing diagrams: {str(e)}")
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
        status = "✅ Connected" if st.session_state.api_status["openrouter"] else "❌ Not Connected"
        st.metric("OpenRouter API", status)
        
        if not st.session_state.api_status["openrouter"]:
            st.warning("Please check if the OPENROUTER_API_KEY is correctly set in Streamlit Secrets")
    
    with col2:
        status = "✅ Connected" if st.session_state.api_status["langsmith"] else "❌ Not Connected"
        st.metric("LangSmith", status)
        
        if not st.session_state.api_status["langsmith"]:
            st.warning("Please check if the LANGSMITH_API_KEY is correctly set in Streamlit Secrets")
    
    # Add a refresh button for API status
    if st.button("Refresh Status"):
        with st.spinner("Checking API status..."):
            check_api_status()
        st.rerun() 