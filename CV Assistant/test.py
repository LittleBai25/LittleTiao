import streamlit as st
import pandas as pd
from pathlib import Path
import docx
import PyPDF2
import io
import httpx
from markitdown import MarkItDown

class CVAssistant:
    def __init__(self):
        self.md = MarkItDown()
        self.api_key = None
        
    def read_docx(self, file):
        try:
            doc = docx.Document(file)
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)
            # Also extract tables
            for table in doc.tables:
                table_data = []
                for row in table.rows:
                    row_data = [cell.text for cell in row.cells]
                    table_data.append(row_data)
                if table_data:
                    df = pd.DataFrame(table_data[1:], columns=table_data[0])
                    full_text.append(df.to_markdown())
            return '\n'.join(full_text)
        except Exception as e:
            st.error(f"Error reading DOCX file: {str(e)}")
            return None

    def read_pdf(self, file):
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            st.error(f"Error reading PDF file: {str(e)}")
            return None

    def read_file(self, file):
        try:
            file_extension = Path(file.name).suffix.lower()
            
            if file_extension == '.docx':
                return self.read_docx(file)
            elif file_extension == '.pdf':
                return self.read_pdf(file)
            elif file_extension in ['.txt', '.md']:
                return file.getvalue().decode('utf-8')
            elif file_extension in ['.xlsx', '.xls']:
                df = pd.read_excel(file)
                return df.to_markdown()
            else:
                st.error(f"Unsupported file format: {file_extension}")
                return None
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
            return None

    def generate_content(self, prompt, content):
        # This function will be used for API calls to OpenRouter
        # The actual implementation will depend on the specific API endpoint and requirements
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            # API call implementation will go here
            # No token limit will be set as per requirements
            return "Content generation will be implemented with OpenRouter API"
        except Exception as e:
            st.error(f"Error generating content: {str(e)}")
            return None

def main():
    st.set_page_config(page_title="CV Writing Assistant", layout="wide")
    st.title("CV Writing Assistant")

    # Initialize the assistant
    if 'assistant' not in st.session_state:
        st.session_state.assistant = CVAssistant()

    # API Key input in sidebar
    with st.sidebar:
        api_key = st.text_input("Enter OpenRouter API Key", type="password")
        if api_key:
            st.session_state.assistant.api_key = api_key

    tab1, tab2 = st.tabs(["Document Upload", "Prompt Debugging"])

    with tab1:
        st.header("Document Upload")
        
        # Main CV document upload
        st.subheader("个人简历素材表（单文件）")
        main_cv_file = st.file_uploader(
            "Upload your main CV document",
            type=['docx', 'pdf', 'txt', 'md', 'xlsx', 'xls'],
            key="main_cv"
        )
        
        if 'main_cv_content' not in st.session_state:
            st.session_state.main_cv_content = None
            
        if main_cv_file:
            st.session_state.main_cv_content = st.session_state.assistant.read_file(main_cv_file)
            if st.session_state.main_cv_content:
                st.text_area("Main CV Content Preview", st.session_state.main_cv_content, height=200)
        
        # Supporting documents upload
        st.subheader("辅助文件（允许多文件）")
        supporting_files = st.file_uploader(
            "Upload supporting documents",
            type=['docx', 'pdf', 'txt', 'md', 'xlsx', 'xls'],
            accept_multiple_files=True,
            key="supporting_files"
        )
        
        if 'supporting_contents' not in st.session_state:
            st.session_state.supporting_contents = []
            
        if supporting_files:
            st.session_state.supporting_contents = []
            for file in supporting_files:
                st.write(f"File: {file.name}")
                content = st.session_state.assistant.read_file(file)
                if content:
                    st.session_state.supporting_contents.append(content)
                    st.text_area(f"Content Preview - {file.name}", content, height=150)

    with tab2:
        st.header("Prompt Debugging")
        prompt = st.text_area(
            "Enter your prompt for debugging",
            height=200,
            placeholder="Enter your prompt here..."
        )
        
        if prompt and st.button("Generate Content"):
            if not st.session_state.assistant.api_key:
                st.error("Please enter your OpenRouter API key in the sidebar first.")
            else:
                with st.spinner("Generating content..."):
                    # Combine main CV content and supporting contents for context
                    all_content = ""
                    if st.session_state.main_cv_content:
                        all_content += st.session_state.main_cv_content + "\n\n"
                    if st.session_state.supporting_contents:
                        all_content += "\n\n".join(st.session_state.supporting_contents)
                    
                    # Generate content using the assistant
                    result = st.session_state.assistant.generate_content(prompt, all_content)
                    if result:
                        st.write(result)

if __name__ == "__main__":
    main()
