import os
import json
import streamlit as st
import asyncio
from pathlib import Path
from tempfile import NamedTemporaryFile

# Import your existing components
from processor import SimpleProcessor
from llm_processor import LLMProcessor
from config_loader import load_api_config
from qs_usnews_school_dict import qs_school_ranking, usnews_school_ranking

# Import the student tags calculator function
from test_llm import calculate_student_tags, enrich_school_rankings

# Set page configuration
st.set_page_config(
    page_title="简历和Offer分析工具",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Function to save uploaded file to a temporary location
def save_uploaded_file(uploaded_file):
    try:
        with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(uploaded_file.getvalue())
            return temp_file.name
    except Exception as e:
        st.error(f"上传文件时出错: {str(e)}")
        return None

# Create a function to process files and display results
async def process_files(resume_file, offer_files, api_key=None):
    # Create processor instances
    processor = SimpleProcessor()
    
    try:
        llm_processor = LLMProcessor(api_key=api_key)
        st.success("LLM处理器初始化成功")
    except ValueError as e:
        st.error(f"LLM处理器初始化失败: {e}")
        return
    
    # Process resume file
    with st.spinner("正在处理简历..."):
        resume_temp_path = save_uploaded_file(resume_file)
        resume_result = processor.process_resume(resume_temp_path)
        
        if not resume_result["success"]:
            st.error(f"简历处理失败: {resume_result['error']}")
            if resume_temp_path:
                os.unlink(resume_temp_path)
            return
        
        st.success("简历文本提取成功")
        st.text_area("简历文本预览", resume_result["content"][:1000] + "...", height=200)
    
    # Process offer files
    offer_texts = []
    offer_temp_paths = []
    
    if offer_files:
        with st.spinner("正在处理Offer文件..."):
            for i, offer_file in enumerate(offer_files):
                offer_temp_path = save_uploaded_file(offer_file)
                offer_temp_paths.append(offer_temp_path)
                
                offer_result = processor.process_resume(offer_temp_path)  # Using resume method for text extraction
                
                if offer_result["success"]:
                    st.success(f"Offer {i+1} 文本提取成功")
                    with st.expander(f"Offer {i+1} 文本预览"):
                        st.text_area(f"Offer {i+1}", offer_result["content"][:1000] + "...", height=200)
                    offer_texts.append(offer_result["content"])
                else:
                    st.error(f"Offer {i+1} 处理失败: {offer_result['error']}")
    
    # Use async method to process documents in parallel
    with st.spinner("正在使用LLM分析文档..."):
        start_time = asyncio.get_event_loop().time()
        
        combined_result = await llm_processor.process_documents(
            resume_text=resume_result["content"],
            offer_texts=offer_texts
        )
        
        elapsed = asyncio.get_event_loop().time() - start_time
        st.success(f"LLM分析完成! 总耗时: {elapsed:.2f}秒")
    
    # Enrich school rankings and add tags
    combined_result = enrich_school_rankings(combined_result)
    tags = calculate_student_tags(combined_result)
    combined_result["tags"] = tags
    
    # Display results
    st.header("分析结果", divider="blue")
    
    # Display tags if any
    if tags:
        st.subheader("🏷️ 学生标签")
        for tag in tags.split("+"):
            st.markdown(f"<span style='background-color: #e6f3ff; padding: 5px 10px; border-radius: 15px; margin-right: 10px;'>{tag}</span>", unsafe_allow_html=True)
    
    # Resume analysis
    st.subheader("简历分析")
    resume_analysis = combined_result["resume_analysis"]
    
    # Display basic info
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**学生**: {resume_analysis.get('studentName', 'N/A')}")
    
    # Display education info
    education = resume_analysis.get("education", {})
    if education:
        st.markdown("#### 教育背景")
        edu_cols = st.columns(3)
        with edu_cols[0]:
            st.markdown(f"**学校**: {education.get('institution', 'N/A')}")
        with edu_cols[1]:
            st.markdown(f"**专业**: {education.get('major', 'N/A')}")
        with edu_cols[2]:
            st.markdown(f"**GPA**: {education.get('gpaOriginal', 'N/A')}")
    
    # Display test scores
    test_scores = resume_analysis.get("testScores", [])
    if test_scores:
        st.markdown("#### 考试成绩")
        for score in test_scores:
            st.markdown(f"**{score.get('testName', 'N/A')}**: {score.get('testScore', 'N/A')}")
            if score.get("detailScores"):
                details = score.get("detailScores", {})
                detail_text = ", ".join([f"{k}: {v}" for k, v in details.items()])
                st.markdown(f"*详细分数*: {detail_text}")
    
    # Display experiences
    experiences = resume_analysis.get("experiences", [])
    if experiences:
        st.markdown("#### 经历")
        for i, exp in enumerate(experiences):
            with st.expander(f"{exp.get('type', 'N/A')} - {exp.get('organization', 'N/A')}"):
                st.markdown(f"**角色**: {exp.get('role', 'N/A')}")
                st.markdown(f"**时长**: {exp.get('duration', 'N/A')}")
                st.markdown(f"**描述**: {exp.get('description', 'N/A')}")
                st.markdown(f"**成就**: {exp.get('achievement', 'N/A')}")
    
    # Offer analysis
    if combined_result["offer_analyses"]:
        st.subheader("Offer分析")
        
        # Create tabs for each offer
        offer_tabs = st.tabs([f"Offer {i+1}" for i in range(len(combined_result["offer_analyses"]))])
        
        for i, (tab, offer_analysis) in enumerate(zip(offer_tabs, combined_result["offer_analyses"])):
            with tab:
                admissions = offer_analysis.get("admissions", [])
                for j, adm in enumerate(admissions):
                    st.markdown(f"#### 录取 {j+1}")
                    
                    # School and program info
                    cols = st.columns(3)
                    with cols[0]:
                        st.markdown(f"**学校**: {adm.get('school', 'N/A')}")
                        st.markdown(f"**国家**: {adm.get('country', 'N/A')}")
                    with cols[1]:
                        st.markdown(f"**项目**: {adm.get('program', 'N/A')}")
                        st.markdown(f"**类别**: {adm.get('majorCategory', 'N/A')}")
                    with cols[2]:
                        st.markdown(f"**学位**: {adm.get('degreeType', 'N/A')}")
                        st.markdown(f"**入学季节**: {adm.get('enrollmentSeason', 'N/A')}")
                    
                    # Ranking info
                    rank_cols = st.columns(3)
                    with rank_cols[0]:
                        st.markdown(f"**排名类型**: {adm.get('rankingType', 'N/A')}")
                    with rank_cols[1]:
                        st.markdown(f"**排名**: {adm.get('rankingValue', 'N/A')}")
                    with rank_cols[2]:
                        st.markdown(f"**排名层级**: {adm.get('rankingTier', 'N/A')}")
                    
                    # Scholarship info
                    if adm.get("hasScholarship"):
                        st.markdown("💰 **获得奖学金**")
                        st.markdown(f"**金额**: {adm.get('scholarshipAmount', 'N/A')}")
                        if adm.get("scholarshipNote"):
                            st.markdown(f"**备注**: {adm.get('scholarshipNote')}")
    
    # Option to download results as JSON
    st.download_button(
        label="下载完整分析结果 (JSON)",
        data=json.dumps(combined_result, ensure_ascii=False, indent=2),
        file_name="分析结果.json",
        mime="application/json"
    )
    
    # Clean up temporary files
    if resume_temp_path:
        os.unlink(resume_temp_path)
    for path in offer_temp_paths:
        os.unlink(path)

# Main app
def main():
    st.title("📝 简历和Offer分析工具")
    
    # Sidebar for API configuration
    st.sidebar.header("API设置")
    
    # Try to load API key from config
    config = load_api_config()
    default_api_key = config.get("OPENAI_API_KEY", "")
    
    # API key input
    api_key = st.sidebar.text_input(
        "OpenAI API密钥", 
        value=default_api_key,
        type="password",
        help="输入你的OpenAI API密钥，用于LLM分析"
    )
    
    # About section in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 关于")
    st.sidebar.info(
        "这个应用可以分析简历和Offer文件，提取关键信息，"
        "并使用LLM进行深度分析。"
    )

    # File upload section
    st.header("上传文件", divider="gray")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Resume upload
        resume_file = st.file_uploader("上传简历 (PDF格式)", type=["pdf"], help="请上传简历PDF文件")
    
    with col2:
        # Offer upload
        offer_files = st.file_uploader("上传Offer文件 (PDF格式，可多选)", type=["pdf"], accept_multiple_files=True, help="可以上传一个或多个Offer PDF文件")
    
    # Process button
    if st.button("开始分析", disabled=not resume_file):
        if not api_key:
            st.error("请提供OpenAI API密钥才能开始分析")
        elif not resume_file:
            st.error("请至少上传一个简历文件")
        else:
            # Use asyncio to run the async processing function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(process_files(resume_file, offer_files, api_key))
            finally:
                loop.close()

if __name__ == "__main__":
    main()
