import streamlit as st
import os
from PIL import Image
import io
from datetime import datetime

# Import custom modules
from agents.transcript_analyzer import TranscriptAnalyzer
from agents.competitiveness_analyst import CompetitivenessAnalyst
from agents.consulting_assistant import ConsultingAssistant
from agents.serper_client import SerperClient
from config.prompts import load_prompts, save_prompts

# Set page configuration
st.set_page_config(
    page_title="Applicant Analysis Tool",
    page_icon="🎓",
    layout="wide"
)

# Initialize session state
if "competitiveness_report" not in st.session_state:
    st.session_state.competitiveness_report = None
if "project_recommendations" not in st.session_state:
    st.session_state.project_recommendations = None
if "transcript_content" not in st.session_state:
    st.session_state.transcript_content = None
if "serper_initialized" not in st.session_state:
    st.session_state.serper_initialized = False
if "analyst_model" not in st.session_state:
    st.session_state.analyst_model = "anthropic/claude-3-5-sonnet"
if "consultant_model" not in st.session_state:
    st.session_state.consultant_model = "anthropic/claude-3-5-sonnet"

# Check if necessary API keys are set
def check_api_keys():
    """Check if the necessary API keys are set in Streamlit secrets."""
    api_keys = {
        "OPENROUTER_API_KEY": st.secrets.get("OPENROUTER_API_KEY", None),
        "SERPER_API_KEY": st.secrets.get("SERPER_API_KEY", None),
        "SMITHERY_API_KEY": st.secrets.get("SMITHERY_API_KEY", None)
    }
    
    return {k: bool(v) for k, v in api_keys.items()}

# Asynchronously initialize the Serper client
async def init_serper():
    """Initialize the Serper client asynchronously."""
    serper_client = SerperClient()
    result = await serper_client.initialize()
    st.session_state.serper_initialized = result
    return result

# 支持的模型列表
SUPPORTED_MODELS = [
    "anthropic/claude-3-5-sonnet",
    "anthropic/claude-3-haiku",
    "google/gemini-1.5-pro",
    "mistralai/mistral-large",
    "meta-llama/llama-3-70b-instruct"
]

# Main function
def main():
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Competitiveness Analysis", "Prompt Debugging", "System Status"])
    
    with tab1:
        st.title("Applicant Competitiveness Analysis Tool")
        
        # Form for user inputs
        with st.form("input_form"):
            # University selection (currently only one option)
            university = st.selectbox(
                "Select University",
                ["Xi'an Jiaotong-Liverpool University"],
                index=0
            )
            
            # Major input
            major = st.text_input("Enter Your Major")
            
            # Predicted degree classification
            predicted_degree = st.selectbox(
                "Predicted Degree Classification",
                ["First Class", "Upper Second Class", "Lower Second Class", "Third Class"]
            )
            
            # Transcript upload (only image formats)
            transcript_file = st.file_uploader(
                "Upload Your Transcript (Image format only)",
                type=["jpg", "jpeg", "png"]
            )
            
            # Submit button
            submitted = st.form_submit_button("Submit")
        
        # Process the form submission
        if submitted and transcript_file is not None and major:
            # 从session state获取模型选择
            analyst_model = st.session_state.analyst_model
            consultant_model = st.session_state.consultant_model
            
            # First step: Process the transcript with TranscriptAnalyzer
            with st.spinner("Analyzing transcript with Qwen 2.5 VL via OpenRouter..."):
                # Save and display the uploaded image
                image = Image.open(transcript_file)
                st.image(image, caption="Uploaded Transcript", use_column_width=True)
                
                # Process the transcript with AI
                transcript_analyzer = TranscriptAnalyzer()
                transcript_content = transcript_analyzer.extract_transcript_data(image)
                st.session_state.transcript_content = transcript_content
                
                # Display the extracted transcript data
                st.subheader("Extracted Transcript Data")
                st.text_area("Transcript Content", transcript_content, height=200, disabled=True)
            
            # Second step: Generate competitiveness report
            with st.spinner(f"Generating competitiveness report with {analyst_model} via OpenRouter..."):
                analyst = CompetitivenessAnalyst(model_name=analyst_model)
                st.session_state.competitiveness_report = analyst.generate_report(
                    university=university,
                    major=major,
                    predicted_degree=predicted_degree,
                    transcript_content=transcript_content
                )
                
                # Display competitiveness report
                st.subheader("Competitiveness Analysis Report")
                st.markdown(st.session_state.competitiveness_report)
            
            # Third step: Generate program recommendations
            with st.spinner(f"Generating program recommendations with {consultant_model} via OpenRouter..."):
                consultant = ConsultingAssistant(model_name=consultant_model)
                st.session_state.project_recommendations = consultant.recommend_projects(
                    competitiveness_report=st.session_state.competitiveness_report
                )
                
                # Display program recommendations
                st.subheader("UCL Program Recommendations")
                st.markdown(st.session_state.project_recommendations)
        
        # If not submitted but we have stored results, display them
        elif not submitted:
            if st.session_state.transcript_content:
                st.subheader("Extracted Transcript Data")
                st.text_area("Transcript Content", st.session_state.transcript_content, height=200, disabled=True)
            
            if st.session_state.competitiveness_report:
                st.subheader("Competitiveness Analysis Report")
                st.markdown(st.session_state.competitiveness_report)
            
            if st.session_state.project_recommendations:
                st.subheader("UCL Program Recommendations")
                st.markdown(st.session_state.project_recommendations)
    
    with tab2:
        st.title("AI Model & Prompt Configuration")
        
        # 添加模型选择到提示词调试页面顶部
        st.subheader("Model Selection")
        col1, col2 = st.columns(2)
        
        with col1:
            # Model selection for CompetitivenessAnalyst
            analyst_model = st.selectbox(
                "Select Model for Competitiveness Analysis",
                SUPPORTED_MODELS,
                index=SUPPORTED_MODELS.index(st.session_state.analyst_model) if st.session_state.analyst_model in SUPPORTED_MODELS else 0,
                key="analyst_model_debug"
            )
            st.session_state.analyst_model = analyst_model
            
        with col2:
            # Model selection for ConsultingAssistant
            consultant_model = st.selectbox(
                "Select Model for Program Recommendations",
                SUPPORTED_MODELS,
                index=SUPPORTED_MODELS.index(st.session_state.consultant_model) if st.session_state.consultant_model in SUPPORTED_MODELS else 0,
                key="consultant_model_debug"
            )
            st.session_state.consultant_model = consultant_model
        
        # 添加模型选择说明
        st.info("这些模型设置将应用于竞争力分析和项目推荐。您的选择将保存在会话中。")
        
        st.markdown("---")
        
        # Load current prompts
        prompts = load_prompts()
        
        st.subheader("Transcript Analyzer Settings")
        st.markdown("""
        The Transcript Analyzer uses Qwen 2.5 VL (qwen/qwen2.5-vl-72b-instruct) via OpenRouter.
        
        This model is specifically tuned for visual document analysis and transcript data extraction.
        """)
        
        st.subheader("Competitiveness Analyst (Agent 1)")
        
        analyst_role = st.text_area("Role Description", prompts["analyst"]["role"], height=200)
        analyst_task = st.text_area("Task Description", prompts["analyst"]["task"], height=200)
        analyst_output = st.text_area("Output Format", prompts["analyst"]["output"], height=200)
        
        st.subheader("Consulting Assistant (Agent 2)")
        
        consultant_role = st.text_area("Role Description", prompts["consultant"]["role"], height=200)
        consultant_task = st.text_area("Task Description", prompts["consultant"]["task"], height=200)
        consultant_output = st.text_area("Output Format", prompts["consultant"]["output"], height=200)
        
        # 保存按钮，不使用表单
        if st.button("Save Prompts"):
            # Update prompts dictionary
            prompts["analyst"]["role"] = analyst_role
            prompts["analyst"]["task"] = analyst_task
            prompts["analyst"]["output"] = analyst_output
            
            prompts["consultant"]["role"] = consultant_role
            prompts["consultant"]["task"] = consultant_task
            prompts["consultant"]["output"] = consultant_output
            
            # Save updated prompts
            save_prompts(prompts)
            st.success("提示词已成功保存！")

    with tab3:
        st.title("System Status")
        
        # Check API keys
        api_key_status = check_api_keys()
        
        st.subheader("API Keys")
        
        # Display API key status as a table
        status_data = [
            {"API Key": key, "Status": "✅ 已设置" if status else "❌ 未设置"} 
            for key, status in api_key_status.items()
        ]
        
        st.table(status_data)
        
        # Serper MCP server status
        st.subheader("Serper MCP Server")
        
        # 初始化Serper客户端按钮，不使用表单
        if not st.session_state.serper_initialized:
            if st.button("初始化 Serper 客户端"):
                with st.spinner("正在初始化 Serper 客户端..."):
                    import asyncio
                    asyncio.run(init_serper())
        
        # Display Serper client status
        if st.session_state.serper_initialized:
            st.success("✅ Serper 客户端已成功初始化")
        else:
            st.warning("⚠️ Serper 客户端未初始化。点击上方按钮进行初始化。")
        
        # Add some help text
        st.markdown("""
        ### API 密钥配置
        
        本应用使用 Streamlit secrets 存储 API 密钥。配置 API 密钥的步骤：
        
        1. 创建 `.streamlit/secrets.toml` 文件并添加您的 API 密钥：
           ```toml
           # OpenRouter API (用于访问所有LLM模型，包括视觉模型)
           OPENROUTER_API_KEY = "your_openrouter_api_key"
           
           # Serper Web搜索 API (用于项目推荐)
           SERPER_API_KEY = "your_serper_api_key"
           SMITHERY_API_KEY = "your_smithery_api_key"
           ```
        
        2. 对于 Streamlit Cloud 部署，在 Streamlit Cloud 控制面板中添加这些密钥
        
        ### 常见问题排查
        
        如果遇到问题：
        
        1. 确保所有必需的 API 密钥都已在 Streamlit secrets 中设置
        2. 检查控制台是否有错误消息
        3. 确保您有有效的互联网连接，以便进行 Web 搜索功能
        """)

if __name__ == "__main__":
    main() 