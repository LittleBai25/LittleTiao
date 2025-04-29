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
    
    # List of supported models (same as CompetitivenessAnalyst)
    SUPPORTED_MODELS = [
        "qwen/qwen-max",
        "qwen/qwen3-32b:free",
        "deepseek/deepseek-chat-v3-0324:free",
        "anthropic/claude-3.7-sonnet",
        "openai/gpt-4.1"
    ]
    
    def __init__(self, model_name=None):
        """
        Initialize the Consulting Assistant agent.
        
        Args:
            model_name: The name of the LLM model to use
        """
        self.prompts = load_prompts()["consultant"]
        
        # Set model name from parameter or default to first in list
        self.model_name = model_name if model_name in self.SUPPORTED_MODELS else self.SUPPORTED_MODELS[0]
        
        # Get API provider and model from model name
        self.provider, self.model = self._parse_model_name(self.model_name)
        
        # Set API key from Streamlit secrets
        self.api_key = self._get_api_key()
        
        # Set API endpoint based on provider
        self.api_url = self._get_api_endpoint()
        
        # Initialize the Serper client for web search
        self.serper_client = SerperClient()
    
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
            
            # Generate recommendations using LLM
            prompt = f"""
            {self.prompts['role']}
            
            {self.prompts['task']}
            
            Competitiveness Report:
            {competitiveness_report}
            
            Available UCL Programs:
            {json.dumps(programs, indent=2)}
            
            {self.prompts['output']}
            """
            
            # Call the appropriate API method based on provider
            if self.provider == "qwen":
                return self._call_qwen_api(prompt, programs)
            elif self.provider == "anthropic":
                return self._call_anthropic_api(prompt, programs)
            elif self.provider == "openai":
                return self._call_openai_api(prompt, programs)
            elif self.provider == "deepseek":
                return self._call_deepseek_api(prompt, programs)
            else:
                # Default to formatting programs directly if provider not recognized
                return self._format_program_recommendations(programs)
                
        except Exception as e:
            st.error(f"Error generating program recommendations: {str(e)}")
            return self._format_program_recommendations(self.get_mock_programs())
    
    def _call_qwen_api(self, prompt: str, fallback_programs: List[Dict[str, str]]) -> str:
        """Call Qwen API to generate recommendations."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1500
        }
        
        with st.spinner(f"Generating program recommendations with {self.model_name}..."):
            response = requests.post(self.api_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                st.error(f"API Error ({self.model_name}): {response.status_code} - {response.text}")
                return self._format_program_recommendations(fallback_programs)
    
    def _call_anthropic_api(self, prompt: str, fallback_programs: List[Dict[str, str]]) -> str:
        """Call Anthropic API to generate recommendations."""
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
        
        with st.spinner(f"Generating program recommendations with {self.model_name}..."):
            response = requests.post(self.api_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result["content"][0]["text"]
            else:
                st.error(f"API Error ({self.model_name}): {response.status_code} - {response.text}")
                return self._format_program_recommendations(fallback_programs)
    
    def _call_openai_api(self, prompt: str, fallback_programs: List[Dict[str, str]]) -> str:
        """Call OpenAI API to generate recommendations."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1500
        }
        
        with st.spinner(f"Generating program recommendations with {self.model_name}..."):
            response = requests.post(self.api_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                st.error(f"API Error ({self.model_name}): {response.status_code} - {response.text}")
                return self._format_program_recommendations(fallback_programs)
    
    def _call_deepseek_api(self, prompt: str, fallback_programs: List[Dict[str, str]]) -> str:
        """Call DeepSeek API to generate recommendations."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1500
        }
        
        with st.spinner(f"Generating program recommendations with {self.model_name}..."):
            response = requests.post(self.api_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                st.error(f"API Error ({self.model_name}): {response.status_code} - {response.text}")
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