import streamlit as st
import pandas as pd
from pathlib import Path
import docx
import PyPDF2
import io

def read_docx(file):
    try:
        doc = docx.Document(file)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        st.error(f"Error reading DOCX file: {str(e)}")
        return None

def read_pdf(file):
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Error reading PDF file: {str(e)}")
        return None

def read_file(file):
    try:
        file_extension = Path(file.name).suffix.lower()
        
        if file_extension == '.docx':
            return read_docx(file)
        elif file_extension == '.pdf':
            return read_pdf(file)
        elif file_extension in ['.txt', '.md']:
            return file.getvalue().decode('utf-8')
        elif file_extension in ['.xlsx', '.xls']:
            df = pd.read_excel(file)
            return df.to_string()
        else:
            st.error(f"Unsupported file format: {file_extension}")
            return None
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return None

def main():
    st.set_page_config(page_title="CV Writing Assistant", layout="wide")
    st.title("CV Writing Assistant")

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
        
        if main_cv_file:
            content = read_file(main_cv_file)
            if content:
                st.text_area("Main CV Content Preview", content, height=200)
        
        # Supporting documents upload
        st.subheader("辅助文件（允许多文件）")
        supporting_files = st.file_uploader(
            "Upload supporting documents",
            type=['docx', 'pdf', 'txt', 'md', 'xlsx', 'xls'],
            accept_multiple_files=True,
            key="supporting_files"
        )
        
        if supporting_files:
            for file in supporting_files:
                st.write(f"File: {file.name}")
                content = read_file(file)
                if content:
                    st.text_area(f"Content Preview - {file.name}", content, height=150)

    with tab2:
        st.header("Prompt Debugging")
        prompt = st.text_area(
            "Enter your prompt for debugging",
            height=200,
            placeholder="Enter your prompt here..."
        )
        
        if prompt and st.button("Generate Content"):
            st.info("Content generation will be implemented with OpenRouter API")

if __name__ == "__main__":
    main()
