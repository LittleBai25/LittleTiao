#!/usr/bin/env python
"""
Utility script to create a .env file with placeholders for API keys.
Run this script to create a .env file if one doesn't exist.
"""

import os

def create_env_file():
    """Create a .env file with placeholders for API keys."""
    env_file_path = ".env"
    
    # Check if .env file already exists
    if os.path.exists(env_file_path):
        print(f"{env_file_path} already exists. Skipping creation.")
        return
    
    # Template for .env file
    env_template = """# API keys for AI models
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
QWEN_API_KEY=your_qwen_api_key_here

# Serper MCP server
SERPER_API_KEY=your_serper_api_key_here
SMITHERY_API_KEY=your_smithery_api_key_here
"""
    
    # Write the .env file
    with open(env_file_path, "w") as f:
        f.write(env_template)
    
    print(f"{env_file_path} created with placeholders for API keys.")
    print("Please edit this file to add your actual API keys.")

if __name__ == "__main__":
    create_env_file() 