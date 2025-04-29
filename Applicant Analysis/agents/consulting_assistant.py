import os
import re
import requests
from typing import Dict, Any, List, Optional
import json
import streamlit as st
from bs4 import BeautifulSoup
from config.prompts import load_prompts
from agents.serper_client import SerperClient

class ConsultingAssistant:
    """
    Agent responsible for recommending suitable UCL programs based on 
    the competitiveness analysis report.
    """
    
    def __init__(self, model_name=None):
        """
        Initialize the Consulting Assistant agent.
        
        Args:
            model_name: The name of the LLM model to use via OpenRouter
        """
        self.prompts = load_prompts()["consultant"]
        
        # 设置模型名称，如果未提供则使用默认值
        self.model_name = model_name if model_name else "anthropic/claude-3-5-sonnet"
        
        # Get API key from Streamlit secrets (OpenRouter unified API key)
        self.api_key = st.secrets.get("OPENROUTER_API_KEY", "")
        
        # Set API endpoint for OpenRouter
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        # Initialize the Serper client for web search
        self.serper_client = SerperClient()
    
    def search_ucl_programs(self, keywords: List[str]) -> List[Dict[str, str]]:
        """
        Search UCL website for programs matching the given keywords.
        
        Args:
            keywords: List of keywords to search for
            
        Returns:
            List of program information dictionaries
        """
        # Use the Serper client to search for programs
        try:
            # Run the async search method synchronously
            programs = self.serper_client.run_async(
                self.serper_client.search_ucl_programs(keywords)
            )
            return programs if programs else self.get_mock_programs()
        except Exception as e:
            st.error(f"Error using Serper for UCL program search: {e}")
            # Fall back to mock data if search fails
            return self.get_mock_programs()
    
    def get_mock_programs(self) -> List[Dict[str, str]]:
        """
        Get mock program data as a fallback when web search fails.
        
        Returns:
            List of mock program information dictionaries
        """
        # Mock program data
        mock_programs = [
            {
                "department": "Department of Computer Science",
                "program_name": "MSc Computer Science",
                "application_open": "October 2023",
                "application_close": "July 31, 2024",
                "program_url": "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/computer-science-msc"
            },
            {
                "department": "Department of Computer Science",
                "program_name": "MSc Data Science and Machine Learning",
                "application_open": "October 2023",
                "application_close": "March 29, 2024",
                "program_url": "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/data-science-machine-learning-msc"
            },
            {
                "department": "Department of Computer Science",
                "program_name": "MSc Software Systems Engineering",
                "application_open": "October 2023",
                "application_close": "July 31, 2024",
                "program_url": "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/software-systems-engineering-msc"
            },
            {
                "department": "Department of Computer Science",
                "program_name": "MSc Web Technologies and Information Architecture",
                "application_open": "October 2023",
                "application_close": "July 31, 2024",
                "program_url": "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/web-technologies-information-architecture-msc"
            },
            {
                "department": "Department of Statistical Science",
                "program_name": "MSc Statistics",
                "application_open": "October 2023",
                "application_close": "July 31, 2024",
                "program_url": "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/statistics-msc"
            }
        ]
        
        return mock_programs
    
    def extract_keywords_from_report(self, competitiveness_report: str) -> List[str]:
        """
        Extract relevant keywords from the competitiveness report to search for programs.
        
        Args:
            competitiveness_report: The competitiveness analysis report
            
        Returns:
            List of keywords for program search
        """
        # In a real implementation, you would use NLP to extract keywords
        # For now, we'll return mock keywords based on the expected report format
        
        # Mock keywords
        keywords = ["Computer Science", "Software Engineering", "Data Science"]
        
        return keywords
    
    def recommend_projects(self, competitiveness_report: str) -> str:
        """
        Generate program recommendations based on the competitiveness report.
        
        Args:
            competitiveness_report: The competitiveness analysis report
            
        Returns:
            Formatted program recommendations
        """
        try:
            # Extract keywords from the report
            keywords = self.extract_keywords_from_report(competitiveness_report)
            
            # Search for matching programs using Serper web search
            programs = self.search_ucl_programs(keywords)
            
            # Generate recommendations using LLM via OpenRouter
            prompt = f"""
            {self.prompts['role']}
            
            {self.prompts['task']}
            
            Competitiveness Report:
            {competitiveness_report}
            
            Available UCL Programs:
            {json.dumps(programs, indent=2)}
            
            {self.prompts['output']}
            """
            
            # Call OpenRouter API with the selected model
            return self._call_openrouter_api(prompt, programs)
                
        except Exception as e:
            st.error(f"Error generating program recommendations: {str(e)}")
            return self._format_program_recommendations(self.get_mock_programs())
    
    def _call_openrouter_api(self, prompt: str, fallback_programs: List[Dict[str, str]]) -> str:
        """Call OpenRouter API to generate recommendations with selected model."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://applicant-analysis.streamlit.app",  # Optional: Replace with your actual app URL
            "X-Title": "Applicant Analysis Tool"  # Optional: Your application name
        }
        
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1500
        }
        
        with st.spinner(f"Generating program recommendations with {self.model_name}..."):
            response = requests.post(self.api_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                st.error(f"OpenRouter API Error ({self.model_name}): {response.status_code} - {response.text}")
                return self._format_program_recommendations(fallback_programs)
    
    def _format_program_recommendations(self, programs: List[Dict[str, str]]) -> str:
        """
        Format program recommendations as Markdown (fallback method).
        
        Args:
            programs: List of program information dictionaries
            
        Returns:
            Formatted program recommendations as Markdown
        """
        recommendation_items = []
        for program in programs:
            recommendation_items.append(
                f"### {program['program_name']}\n"
                f"**Department**: {program['department']}\n"
                f"**Application Period**: {program['application_open']} to {program['application_close']}\n"
                f"**Program Link**: [{program['program_url']}]({program['program_url']})\n"
            )
        
        recommendations = "# UCL Program Recommendations\n\n" + "\n".join(recommendation_items)
        
        return recommendations 