# Applicant Analysis Tool

An AI-powered application for analyzing applicant competitiveness and recommending suitable UCL programs.

## Features

- **Competitiveness Analysis**: Upload a transcript image and get a detailed analysis of your academic competitiveness
- **Program Recommendations**: Receive personalized UCL program recommendations based on your profile
- **Prompt Debugging**: Fine-tune the prompts used by the AI agents to customize the analysis

## Requirements

- Python 3.8+
- Streamlit
- LangChain
- An API key for the AI model(s) you plan to use (e.g., OpenAI, Anthropic, Qwen)

## Installation

1. Clone this repository
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Set up your API keys as environment variables:
   ```
   # For OpenAI models
   export OPENAI_API_KEY=your_api_key_here
   
   # For Anthropic models
   export ANTHROPIC_API_KEY=your_api_key_here
   
   # For Qwen models
   export QWEN_API_KEY=your_api_key_here
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
   - Upload your transcript image
   - Click "Start Competitiveness Analysis"
   - After receiving the analysis, click "Start Project Recommendation" for UCL program suggestions
4. In the "Prompt Debugging" tab:
   - Modify prompts for the Competitiveness Analyst and Consulting Assistant
   - Choose different AI models
   - Save your changes for future use

## Development Notes

The application is structured as follows:

- `app.py`: Main Streamlit application
- `agents/`: AI agents for different tasks
  - `competitiveness_analyst.py`: Analyzes transcript and generates competitiveness report
  - `consulting_assistant.py`: Recommends UCL programs based on competitiveness
- `config/`: Configuration files
  - `prompts.py`: Manages prompt loading and saving
  - `prompts.json`: Stores the current prompts (created automatically)

## License

This project is licensed under the MIT License - see the LICENSE file for details. 