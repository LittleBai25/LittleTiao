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

# Check if necessary API keys are set
def check_api_keys():
    """Check if the necessary API keys are set in Streamlit secrets."""
    api_keys = {
        "SERPER_API_KEY": st.secrets.get("SERPER_API_KEY", None),
        "SMITHERY_API_KEY": st.secrets.get("SMITHERY_API_KEY", None),
        "QWEN_API_KEY": st.secrets.get("QWEN_API_KEY", None),
        "OPENAI_API_KEY": st.secrets.get("OPENAI_API_KEY", None),
        "ANTHROPIC_API_KEY": st.secrets.get("ANTHROPIC_API_KEY", None),
        "DEEPSEEK_API_KEY": st.secrets.get("DEEPSEEK_API_KEY", None)
    }
    
    return {k: bool(v) for k, v in api_keys.items()}

# Asynchronously initialize the Serper client
async def init_serper():
    """Initialize the Serper client asynchronously."""
    serper_client = SerperClient()
    result = await serper_client.initialize()
    st.session_state.serper_initialized = result
    return result

# Main function
def main():
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Competitiveness Analysis", "Prompt Debugging", "System Status"])
    
    with tab1:
        st.title("Applicant Competitiveness Analysis Tool")
        
        # Form for user inputs (without the "Start Competitiveness Analysis" button)
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
            
            # Model selection for CompetitivenessAnalyst
            analyst_model = st.selectbox(
                "Select Model for Competitiveness Analysis",
                CompetitivenessAnalyst.SUPPORTED_MODELS,
                index=0,
                key="analyst_model_select"
            )
            
            # Model selection for ConsultingAssistant
            consultant_model = st.selectbox(
                "Select Model for Program Recommendations",
                ConsultingAssistant.SUPPORTED_MODELS,
                index=0,
                key="consultant_model_select"
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
            # First step: Process the transcript with TranscriptAnalyzer
            with st.spinner("Analyzing transcript with Qwen 2.5 VL..."):
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
            with st.spinner(f"Generating competitiveness report with {analyst_model}..."):
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
            with st.spinner(f"Generating program recommendations with {consultant_model}..."):
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
        st.title("Prompt Debugging")
        
        # Load current prompts
        prompts = load_prompts()
        
        st.subheader("Transcript Analyzer Settings")
        st.markdown("""
        The Transcript Analyzer uses a fixed model: **qwen/qwen2.5-vl-72b-instruct**
        
        This model cannot be changed as it's specifically tuned for visual document analysis.
        """)
        
        st.subheader("Competitiveness Analyst (Agent 1)")
        
        analyst_role = st.text_area("Role Description", prompts["analyst"]["role"], height=200)
        analyst_task = st.text_area("Task Description", prompts["analyst"]["task"], height=200)
        analyst_output = st.text_area("Output Format", prompts["analyst"]["output"], height=200)
        
        st.subheader("Consulting Assistant (Agent 2)")
        
        consultant_role = st.text_area("Role Description", prompts["consultant"]["role"], height=200)
        consultant_task = st.text_area("Task Description", prompts["consultant"]["task"], height=200)
        consultant_output = st.text_area("Output Format", prompts["consultant"]["output"], height=200)
        
        # Save button
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
            st.success("Prompts saved successfully!")

    with tab3:
        st.title("System Status")
        
        # Check API keys
        api_key_status = check_api_keys()
        
        st.subheader("API Keys")
        
        # Display API key status as a table
        status_data = [
            {"API Key": key, "Status": "✅ Set" if status else "❌ Not Set"} 
            for key, status in api_key_status.items()
        ]
        
        st.table(status_data)
        
        # Serper MCP server status
        st.subheader("Serper MCP Server")
        
        # Initialize the Serper client if not already initialized
        if not st.session_state.serper_initialized:
            if st.button("Initialize Serper Client"):
                with st.spinner("Initializing Serper client..."):
                    import asyncio
                    asyncio.run(init_serper())
        
        # Display Serper client status
        if st.session_state.serper_initialized:
            st.success("✅ Serper client initialized successfully")
        else:
            st.warning("⚠️ Serper client not initialized. Click the button above to initialize.")
        
        # Add some help text
        st.markdown("""
        ### API Keys Configuration
        
        This application uses Streamlit secrets for API keys. To configure the API keys:
        
        1. Create a `.streamlit/secrets.toml` file with your API keys:
           ```toml
           QWEN_API_KEY = "your_qwen_api_key"
           OPENAI_API_KEY = "your_openai_api_key"
           ANTHROPIC_API_KEY = "your_anthropic_api_key"
           DEEPSEEK_API_KEY = "your_deepseek_api_key"
           SERPER_API_KEY = "your_serper_api_key"
           SMITHERY_API_KEY = "your_smithery_api_key"
           ```
        
        2. For Streamlit Cloud deployment, add these secrets in the Streamlit Cloud dashboard
        
        ### Troubleshooting
        
        If you're experiencing issues:
        
        1. Make sure all required API keys are set in the Streamlit secrets
        2. Check the console for any error messages
        3. Ensure you have an active internet connection for web search functionality
        """)

if __name__ == "__main__":
    main() 