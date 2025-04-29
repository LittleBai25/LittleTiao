# Applicant Analysis Tool

An AI-powered application for analyzing applicant competitiveness and recommending suitable UCL programs.

## Features

- **Transcript Analysis**: Upload a transcript image and get automatic analysis using Qwen 2.5 VL vision-language model
- **Competitiveness Analysis**: Get a detailed analysis of academic competitiveness from multiple AI model options
- **Program Recommendations**: Receive personalized UCL program recommendations based on your profile
- **Web Search Integration**: Uses Serper MCP server to search for up-to-date information about UCL programs
- **Prompt Debugging**: Fine-tune the prompts used by the AI agents to customize the analysis
- **Multiple LLM Support**: Select from various models for analysis and recommendations

## Supported Models

### Transcript Analyzer
- Fixed: **qwen/qwen2.5-vl-72b-instruct** (specialized for visual document analysis)

### Competitiveness Analyst & Consulting Assistant
- qwen/qwen-max
- qwen/qwen3-32b:free
- deepseek/deepseek-chat-v3-0324:free
- anthropic/claude-3.7-sonnet
- openai/gpt-4.1

## Requirements

- Python 3.8+
- Streamlit
- LangChain
- MCP Client (for Serper integration)
- API keys for various services (see Setup section)

## Installation

1. Clone this repository
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Set up your API keys as Streamlit secrets (create a `.streamlit/secrets.toml` file):
   ```toml
   QWEN_API_KEY = "your_qwen_api_key"
   OPENAI_API_KEY = "your_openai_api_key"
   ANTHROPIC_API_KEY = "your_anthropic_api_key"
   DEEPSEEK_API_KEY = "your_deepseek_api_key"
   SERPER_API_KEY = "your_serper_api_key"
   SMITHERY_API_KEY = "your_smithery_api_key"
   ```

## Usage

1. Run the Streamlit application:
   ```
   streamlit run app.py
   ```
2. Open your web browser and navigate to the URL displayed in the terminal (usually `http://localhost:8501`)
3. In the "Competitiveness Analysis" tab:
   - Select your university
   - Enter your major
   - Select your predicted degree classification
   - Choose AI models for analysis and recommendations
   - Upload your transcript image
   - Click "Submit" to start the complete analysis process
4. The system will automatically:
   - Extract and display transcript data using Qwen 2.5 VL
   - Generate a competitiveness analysis report with your selected model
   - Provide UCL program recommendations based on the analysis
5. In the "Prompt Debugging" tab:
   - Modify prompts for all agents to customize their behavior
   - Save your changes for future use

## Workflow

The application follows this workflow:

1. **Transcript Analysis**: Qwen 2.5 VL extracts structured data from the uploaded transcript image
2. **Competitiveness Analysis**: The selected LLM analyzes the student's profile and generates a competitiveness report
3. **Program Recommendations**: The second LLM searches for and recommends suitable UCL programs

## Serper MCP Server Integration

The application uses the Serper MCP server to perform web searches for UCL program information. This integration:

1. Allows for real-time, up-to-date program information
2. Provides more accurate program recommendations based on current UCL offerings
3. Falls back to mock data if the search fails or API keys are not configured

## Development Notes

The application is structured as follows:

- `app.py`: Main Streamlit application
- `agents/`: AI agents for different tasks
  - `transcript_analyzer.py`: Extracts data from transcript images using Qwen 2.5 VL
  - `competitiveness_analyst.py`: Analyzes student competitiveness
  - `consulting_assistant.py`: Recommends UCL programs based on competitiveness
  - `serper_client.py`: Client for the Serper MCP server integration
- `config/`: Configuration files
  - `prompts.py`: Manages prompt loading and saving
  - `prompts.json`: Stores the current prompts (created automatically)

## License

This project is licensed under the MIT License - see the LICENSE file for details. 