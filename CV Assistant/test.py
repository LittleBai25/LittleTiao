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
    try:
        st.set_page_config(
            page_title="CV Assistant",
            page_icon="📝",
            layout="wide"
        )
        
        st.title("CV Writing Assistant")
        st.write("Welcome to the CV Writing Assistant!")
        
        # Add a simple text input
        user_input = st.text_input("Enter your name:")
        if user_input:
            st.write(f"Hello, {user_input}!")
        
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.stop()

if __name__ == "__main__":
    main()
