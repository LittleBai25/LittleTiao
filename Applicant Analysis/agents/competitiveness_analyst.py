import os
import io
from PIL import Image
from typing import Dict, Any, Optional
from langchain.chains import LLMChain
from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from config.prompts import load_prompts

class CompetitivenessAnalyst:
    """
    Agent responsible for analyzing student transcripts and generating competitiveness reports.
    Uses a vision-language model to extract transcript data and analyze competitiveness.
    """
    
    def __init__(self):
        """Initialize the Competitiveness Analyst agent with default settings."""
        self.prompts = load_prompts()["analyst"]
        self.model_name = self.prompts.get("model", "qwen/qwen2.5-vl-72b-instruct")
        
        # We'd initialize the vision model here, but we'll mock it for development
        # In a real implementation, you would use the appropriate client for your chosen model
        # self.vision_model = initialize_vision_model(self.model_name)
    
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
        # Here we would construct a prompt and call the LLM
        # For now, we'll return a mock response
        
        prompt_template = f"""
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
        
        # In a real implementation, you would call the LLM API here
        # For now, we'll return a mock response
        
        # Mock response - in production, replace with actual API call
        mock_report = """
        # Competitiveness Analysis Report

        ## Student Profile
        - **University**: Xi'an Jiaotong-Liverpool University
        - **Major**: Computer Science
        - **Predicted Degree**: First Class
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