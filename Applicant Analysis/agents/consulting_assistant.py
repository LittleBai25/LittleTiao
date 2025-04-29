import os
import re
import requests
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from config.prompts import load_prompts
from agents.serper_client import SerperClient

class ConsultingAssistant:
    """
    Agent responsible for recommending suitable UCL programs based on 
    the competitiveness analysis report.
    """
    
    def __init__(self):
        """Initialize the Consulting Assistant agent with default settings."""
        self.prompts = load_prompts()["consultant"]
        self.model_name = self.prompts.get("model", "gpt-4-turbo")
        
        # Initialize the Serper client for web search
        self.serper_client = SerperClient()
        
        # We'd initialize the LLM here, but we'll mock it for development
        # In a real implementation, you would use the appropriate client for your chosen model
        # self.llm = ChatOpenAI(model_name=self.model_name)
    
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
            print(f"Error using Serper for UCL program search: {e}")
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
        # Extract keywords from the report
        keywords = self.extract_keywords_from_report(competitiveness_report)
        
        # Search for matching programs using Serper web search
        programs = self.search_ucl_programs(keywords)
        
        # Generate recommendations using LLM
        prompt_template = f"""
        {self.prompts['role']}
        
        {self.prompts['task']}
        
        Competitiveness Report:
        {competitiveness_report}
        
        Available UCL Programs:
        {programs}
        
        {self.prompts['output']}
        """
        
        # In a real implementation, you would call the LLM API here
        # For now, we'll format the mock programs
        
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