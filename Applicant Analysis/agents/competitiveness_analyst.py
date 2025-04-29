import os
import io
from PIL import Image
from typing import Dict, Any, Optional
import requests
import json
import streamlit as st
from langchain.chains import LLMChain
from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from config.prompts import load_prompts

class CompetitivenessAnalyst:
    """
    Agent responsible for analyzing student competitiveness and generating competitiveness reports.
    Can use multiple LLM models based on user selection.
    """
    
    # List of supported models
    SUPPORTED_MODELS = [
        "qwen/qwen-max",
        "qwen/qwen3-32b:free",
        "deepseek/deepseek-chat-v3-0324:free",
        "anthropic/claude-3.7-sonnet",
        "openai/gpt-4.1"
    ]
    
    def __init__(self, model_name=None):
        """
        Initialize the Competitiveness Analyst agent.
        
        Args:
            model_name: The name of the LLM model to use
        """
        self.prompts = load_prompts()["analyst"]
        
        # Set model name from parameter or default to first in list
        self.model_name = model_name if model_name in self.SUPPORTED_MODELS else self.SUPPORTED_MODELS[0]
        
        # Get API provider and model from model name
        self.provider, self.model = self._parse_model_name(self.model_name)
        
        # Set API key from Streamlit secrets
        self.api_key = self._get_api_key()
        
        # Set API endpoint based on provider
        self.api_url = self._get_api_endpoint()
    
    def _parse_model_name(self, model_name: str) -> tuple:
        """
        Parse model name to extract provider and model.
        
        Args:
            model_name: The full model name (provider/model)
            
        Returns:
            Tuple of (provider, model)
        """
        parts = model_name.split('/')
        if len(parts) >= 2:
            provider = parts[0]
            model = '/'.join(parts[1:])
            # Remove any tag (e.g., ":free") from model name
            if ':' in model:
                model = model.split(':')[0]
            return provider, model
        else:
            return "qwen", "qwen-max"  # Default
    
    def _get_api_key(self) -> str:
        """
        Get the appropriate API key from Streamlit secrets based on the provider.
        
        Returns:
            API key string
        """
        key_mapping = {
            "qwen": "QWEN_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY"
        }
        
        key_name = key_mapping.get(self.provider, "QWEN_API_KEY")
        return st.secrets.get(key_name, "")
    
    def _get_api_endpoint(self) -> str:
        """
        Get the appropriate API endpoint based on the provider.
        
        Returns:
            API endpoint URL string
        """
        endpoint_mapping = {
            "qwen": "https://api.qwen.ai/v1/chat/completions",
            "anthropic": "https://api.anthropic.com/v1/messages",
            "openai": "https://api.openai.com/v1/chat/completions",
            "deepseek": "https://api.deepseek.com/v1/chat/completions"
        }
        
        return endpoint_mapping.get(self.provider, "https://api.qwen.ai/v1/chat/completions")
    
    def extract_transcript_data(self, image: Image.Image) -> str:
        """
        Extract transcript data from an uploaded image.
        
        Args:
            image: The transcript image uploaded by the user
            
        Returns:
            String representation of the extracted transcript data
        """
        # Convert image to bytes for API processing
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format=image.format if image.format else 'JPEG')
        img_byte_arr = img_byte_arr.getvalue()
        
        # In a real implementation, you would call the vision model API here
        # For now, we'll return a mock response
        
        # Mock response - in production, replace with actual API call
        mock_transcript = """
        Student Name: Zhang Wei
        Student ID: 2022XJU456
        Program: Computer Science
        Academic Year: 2023-2024
        
        Courses:
        - CSE101 Introduction to Programming: A (90%)
        - CSE102 Data Structures and Algorithms: A- (85%)
        - MTH201 Linear Algebra: B+ (78%)
        - CSE201 Database Systems: A (92%)
        - CSE205 Computer Networks: B (75%)
        - ENG101 Academic English: B+ (79%)
        
        Current GPA: 3.76/4.0
        """
        
        return mock_transcript
    
    def generate_report(self, university: str, major: str, predicted_degree: str, transcript_content: str) -> str:
        """
        Generate a competitiveness analysis report based on the provided information.
        
        Args:
            university: The student's university
            major: The student's major
            predicted_degree: The student's predicted degree classification
            transcript_content: The extracted transcript data
            
        Returns:
            A formatted competitiveness analysis report
        """
        try:
            # Prepare prompt with provided information
            prompt = f"""
            {self.prompts['role']}
            
            {self.prompts['task']}
            
            Information:
            University: {university}
            Major: {major}
            Predicted Degree Classification: {predicted_degree}
            Transcript Data:
            {transcript_content}
            
            {self.prompts['output']}
            """
            
            # Call the appropriate API method based on provider
            if self.provider == "qwen":
                return self._call_qwen_api(prompt)
            elif self.provider == "anthropic":
                return self._call_anthropic_api(prompt)
            elif self.provider == "openai":
                return self._call_openai_api(prompt)
            elif self.provider == "deepseek":
                return self._call_deepseek_api(prompt)
            else:
                # Default to mock response if provider not recognized
                return self._get_mock_report(university, major, predicted_degree)
                
        except Exception as e:
            st.error(f"Error generating competitiveness report: {str(e)}")
            return self._get_mock_report(university, major, predicted_degree)
    
    def _call_qwen_api(self, prompt: str) -> str:
        """Call Qwen API to generate report."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1500
        }
        
        with st.spinner(f"Generating competitiveness report with {self.model_name}..."):
            response = requests.post(self.api_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                st.error(f"API Error ({self.model_name}): {response.status_code} - {response.text}")
                return self._get_mock_report("", "", "")
    
    def _call_anthropic_api(self, prompt: str) -> str:
        """Call Anthropic API to generate report."""
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1500
        }
        
        with st.spinner(f"Generating competitiveness report with {self.model_name}..."):
            response = requests.post(self.api_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result["content"][0]["text"]
            else:
                st.error(f"API Error ({self.model_name}): {response.status_code} - {response.text}")
                return self._get_mock_report("", "", "")
    
    def _call_openai_api(self, prompt: str) -> str:
        """Call OpenAI API to generate report."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1500
        }
        
        with st.spinner(f"Generating competitiveness report with {self.model_name}..."):
            response = requests.post(self.api_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                st.error(f"API Error ({self.model_name}): {response.status_code} - {response.text}")
                return self._get_mock_report("", "", "")
    
    def _call_deepseek_api(self, prompt: str) -> str:
        """Call DeepSeek API to generate report."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1500
        }
        
        with st.spinner(f"Generating competitiveness report with {self.model_name}..."):
            response = requests.post(self.api_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                st.error(f"API Error ({self.model_name}): {response.status_code} - {response.text}")
                return self._get_mock_report("", "", "")
    
    def _get_mock_report(self, university: str, major: str, predicted_degree: str) -> str:
        """
        Get a mock competitiveness report as a fallback.
        
        Returns:
            Mock competitiveness report string
        """
        # Fill in with provided data or defaults
        university = university or "Xi'an Jiaotong-Liverpool University"
        major = major or "Computer Science"
        predicted_degree = predicted_degree or "First Class"
        
        mock_report = f"""
        # Competitiveness Analysis Report

        ## Student Profile
        - **University**: {university}
        - **Major**: {major}
        - **Predicted Degree**: {predicted_degree}
        - **Current GPA**: 3.76/4.0

        ## Academic Strengths
        - Strong performance in core Computer Science courses (90-92%)
        - Particularly excellent in Programming and Database Systems
        - Good balance of technical and communication skills

        ## Areas for Improvement
        - Mathematics performance is above average but could be stronger (78%)
        - Computer Networks score (75%) is the lowest among technical subjects

        ## Competitiveness Assessment
        
        ### Overall Rating: ★★★★☆ (4/5) - Strong Candidate
        
        The student demonstrates a strong academic profile with a high GPA of 3.76/4.0, which places them in approximately the top 15% of Computer Science graduates. Their predicted First Class degree further strengthens their application.

        ### Program Suitability
        
        **Highly Competitive For**:
        - MSc Computer Science
        - MSc Software Engineering
        - MSc Data Science
        - MSc Human-Computer Interaction
        
        **Moderately Competitive For**:
        - MSc Artificial Intelligence
        - MSc Machine Learning
        - MSc Advanced Computing
        
        **Less Competitive For**:
        - MSc Computational Statistics and Machine Learning (due to mathematics score)
        - MSc Financial Computing (requires stronger mathematics)

        ## Recommendations for Improvement
        
        1. Consider taking additional mathematics or statistics courses to strengthen quantitative skills
        2. Pursue projects or certifications in networking to address the lower grade in Computer Networks
        3. Gain practical experience through internships or research projects to enhance competitiveness
        4. Consider preparing for standardized tests like GRE to further strengthen applications
        
        ## Additional Notes
        
        The student's academic profile shows consistent performance across multiple academic years, which is viewed favorably by admissions committees. Their strong grades in core Computer Science subjects indicate good preparation for advanced study in the field.
        """
        
        return mock_report 