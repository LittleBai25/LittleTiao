import streamlit as st
import os
import json
import tempfile
import asyncio
from pathlib import Path

# Import your existing code modules
from processor import SimpleProcessor
from llm_processor import LLMProcessor
from pdf_parser import PDFParser
from pdf_offer_parser import PDFOfferParser
from test_llm import enrich_school_rankings, calculate_student_tags

# Set page config
st.set_page_config(
    page_title="Resume & Offer Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# App title and description
st.title("Resume & Offer Analyzer")
st.markdown("""
This app analyzes resumes and university offer letters to extract structured information.
Upload your documents to get started!
""")

# Initialize processors
@st.cache_resource
def initialize_processors():
    processor = SimpleProcessor()
    
    # Initialize LLM processor with API key from secrets
    api_key = st.secrets.get("OPENAI_API_KEY", None)
    api_base = st.secrets.get("OPENAI_API_BASE", None)
    model_name = st.secrets.get("OPENAI_MODEL_NAME", None)
    
    try:
        llm_processor = LLMProcessor(api_key, api_base, model_name)
        return processor, llm_processor
    except ValueError as e:
        st.error(f"Failed to initialize LLM processor: {e}")
        return processor, None

processor, llm_processor = initialize_processors()

# Check if LLM processor is available
if llm_processor is None:
    st.warning("LLM processing is not available. Please check your API configuration.")

# Create sidebar for file uploads
with st.sidebar:
    st.header("Upload Documents")
    
    # Resume upload
    resume_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])
    
    # Offer letter upload(s)
    st.subheader("Upload Offer Letter(s)")
    offer_files = st.file_uploader("Upload one or more offer letters (PDF)", 
                                 type=["pdf"], accept_multiple_files=True)
    
    # Process button
    process_button = st.button("Analyze Documents", type="primary")
    
    # Settings section
    st.header("Settings")
    enable_school_ranking = st.checkbox("Enable School Ranking Enrichment", value=True)
    enable_student_tags = st.checkbox("Calculate Student Tags", value=True)

# Main content area
if process_button:
    if resume_file is None and not offer_files:
        st.error("Please upload at least one document to analyze.")
    else:
        with st.spinner("Processing documents..."):
            # Create a temporary directory to save uploaded files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Process resume if uploaded
                resume_result = None
                resume_analysis = None
                if resume_file is not None:
                    # Save the uploaded resume to a temporary file
                    resume_path = temp_path / "resume.pdf"
                    with open(resume_path, "wb") as f:
                        f.write(resume_file.getvalue())
                    
                    # Process the resume
                    resume_result = processor.process_resume(str(resume_path))
                    
                    if resume_result["success"] and llm_processor is not None:
                        # Analyze the resume with LLM
                        resume_analysis = llm_processor.analyze_resume(resume_result["content"])
                
                # Process offer letters if uploaded
                offer_results = []
                offer_analyses = []
                
                for i, offer_file in enumerate(offer_files):
                    # Save the uploaded offer letter to a temporary file
                    offer_path = temp_path / f"offer_{i}.pdf"
                    with open(offer_path, "wb") as f:
                        f.write(offer_file.getvalue())
                    
                    # Process the offer letter
                    offer_result = processor.process_resume(str(offer_path))
                    offer_results.append(offer_result)
                    
                    if offer_result["success"] and llm_processor is not None:
                        # Analyze the offer with LLM
                        offer_analysis = llm_processor.analyze_offer(offer_result["content"])
                        offer_analyses.append(offer_analysis)
                
                # Combine the results
                combined_result = {
                    "resume_analysis": resume_analysis,
                    "offer_analyses": offer_analyses
                }
                
                # Enrich school rankings if enabled
                if enable_school_ranking and llm_processor is not None:
                    combined_result = enrich_school_rankings(combined_result)
                
                # Calculate student tags if enabled
                if enable_student_tags and llm_processor is not None and resume_analysis is not None:
                    tags = calculate_student_tags(combined_result)
                    combined_result["tags"] = tags
        
        # Display the results
        st.header("Analysis Results")
        
        # Display student tags if available
        if "tags" in combined_result and combined_result["tags"]:
            st.success(f"Student Tags: {combined_result['tags']}")
        
        # Display resume results if available
        if resume_analysis:
            st.subheader("Resume Analysis")
            
            # Create tabs for different sections
            resume_tab1, resume_tab2, resume_tab3 = st.tabs(["Overview", "Extracted Text", "JSON Result"])
            
            with resume_tab1:
                # Basic information
                if "studentName" in resume_analysis:
                    st.write(f"**Student:** {resume_analysis['studentName']}")
                
                # Education
                if "education" in resume_analysis:
                    education = resume_analysis["education"]
                    st.write("### Education")
                    st.write(f"**Institution:** {education.get('institution', 'N/A')}")
                    st.write(f"**Major:** {education.get('major', 'N/A')}")
                    st.write(f"**GPA:** {education.get('gpaOriginal', 'N/A')}")
                    st.write(f"**Institution Type:** {education.get('institutionType', 'N/A')}")
                
                # Test scores
                if "testScores" in resume_analysis and resume_analysis["testScores"]:
                    st.write("### Test Scores")
                    for score in resume_analysis["testScores"]:
                        st.write(f"**{score.get('testName', 'N/A')}:** {score.get('testScore', 'N/A')}")
                        if "detailScores" in score and score["detailScores"]:
                            for key, value in score["detailScores"].items():
                                st.write(f"  - {key}: {value}")
                
                # Experiences
                if "experiences" in resume_analysis and resume_analysis["experiences"]:
                    st.write("### Experiences")
                    for exp in resume_analysis["experiences"]:
                        st.write(f"**{exp.get('type', 'N/A')}:** {exp.get('description', 'N/A')}")
                        st.write(f"**Organization:** {exp.get('organization', 'N/A')}")
                        st.write(f"**Role:** {exp.get('role', 'N/A')}")
                        st.write(f"**Duration:** {exp.get('duration', 'N/A')}")
                        st.write(f"**Achievement:** {exp.get('achievement', 'N/A')}")
                        st.write("---")
            
            with resume_tab2:
                if resume_result and "content" in resume_result:
                    st.text_area("Extracted Resume Text", resume_result["content"], height=300)
                else:
                    st.info("No resume text extracted.")
            
            with resume_tab3:
                st.json(resume_analysis)
        
        # Display offer results if available
        if offer_analyses:
            st.subheader("Offer Letter Analysis")
            
            # Create tabs for each offer
            offer_tabs = st.tabs([f"Offer {i+1}" for i in range(len(offer_analyses))])
            
            for i, (offer_tab, offer_analysis, offer_result) in enumerate(zip(offer_tabs, offer_analyses, offer_results)):
                with offer_tab:
                    if "admissions" in offer_analysis and offer_analysis["admissions"]:
                        for j, admission in enumerate(offer_analysis["admissions"]):
                            st.write(f"### Admission {j+1}")
                            st.write(f"**School:** {admission.get('school', 'N/A')}")
                            st.write(f"**Country:** {admission.get('country', 'N/A')}")
                            st.write(f"**Program:** {admission.get('program', 'N/A')}")
                            st.write(f"**Major Category:** {admission.get('majorCategory', 'N/A')}")
                            st.write(f"**Degree Type:** {admission.get('degreeType', 'N/A')}")
                            
                            # Ranking information
                            st.write("#### Ranking")
                            st.write(f"**Ranking Type:** {admission.get('rankingType', 'N/A')}")
                            st.write(f"**Ranking Value:** {admission.get('rankingValue', 'N/A')}")
                            st.write(f"**Ranking Tier:** {admission.get('rankingTier', 'N/A')}")
                            
                            # Enrollment and scholarship information
                            st.write("#### Enrollment & Scholarship")
                            st.write(f"**Enrollment Season:** {admission.get('enrollmentSeason', 'N/A')}")
                            
                            if admission.get('hasScholarship'):
                                st.write(f"**Scholarship Amount:** {admission.get('scholarshipAmount', 'N/A')}")
                                if admission.get('scholarshipNote'):
                                    st.write(f"**Scholarship Note:** {admission.get('scholarshipNote')}")
                            else:
                                st.write("**Scholarship:** None")
                            
                            st.write("---")
                    
                    # Add a section for raw text and JSON
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("#### Extracted Text")
                        if "content" in offer_result:
                            st.text_area(f"Offer {i+1} Text", offer_result["content"], height=200)
                    
                    with col2:
                        st.write("#### JSON Result")
                        st.json(offer_analysis)
        
        # Download button for the combined results
        st.download_button(
            label="Download Analysis Results (JSON)",
            data=json.dumps(combined_result, indent=2, ensure_ascii=False),
            file_name="analysis_results.json",
            mime="application/json"
        )

# Footer
st.markdown("---")
st.markdown("© 2025 Resume & Offer Analyzer - Built with Streamlit")
