# Applicant Analysis Tool

通过AI驱动的应用程序分析申请人竞争力并推荐合适的UCL项目。

## 功能特点

- **成绩单分析**：上传成绩单图片，通过OpenRouter访问Qwen 2.5 VL视觉语言模型自动进行分析
- **竞争力分析**：通过多种可选AI模型获取详细的学术竞争力分析
- **项目推荐**：基于个人档案获取个性化的UCL项目推荐
- **网络搜索集成**：使用Serper MCP服务器搜索有关UCL项目的最新信息
- **提示词调试**：微调AI代理使用的提示词以自定义分析
- **多LLM支持**：通过OpenRouter选择各种模型进行分析和推荐

## 支持的模型

### 成绩单分析器
- 固定使用：**qwen/qwen2.5-vl-72b-instruct**（通过OpenRouter访问，专门用于视觉文档分析）

### 竞争力分析和咨询助手
- anthropic/claude-3-5-sonnet
- anthropic/claude-3-haiku
- google/gemini-1.5-pro
- mistralai/mistral-large
- meta-llama/llama-3-70b-instruct

## 技术要求

- Python 3.8+
- Streamlit
- LangChain
- MCP Client（用于Serper集成）
- 各种服务的API密钥（参见安装部分）

## 安装步骤

1. 克隆此存储库
2. 安装所需的软件包：
   ```
   pip install -r requirements.txt
   ```
3. 设置API密钥作为Streamlit secrets（创建`.streamlit/secrets.toml`文件）：
   ```toml
   # OpenRouter API (用于访问所有LLM模型，包括视觉模型)
   OPENROUTER_API_KEY = "your_openrouter_api_key"
   
   # Serper Web搜索 API (用于项目推荐)
   SERPER_API_KEY = "your_serper_api_key"
   SMITHERY_API_KEY = "your_smithery_api_key"
   ```

## 使用方法

1. 运行Streamlit应用程序：
   ```
   streamlit run app.py
   ```
2. 在浏览器中打开终端中显示的URL（通常为`http://localhost:8501`）
3. 在"竞争力分析"选项卡中：
   - 选择您的大学
   - 输入您的专业
   - 选择预测的学位分类
   - 为分析和推荐选择AI模型
   - 上传您的成绩单图片
   - 点击"提交"开始完整的分析过程
4. 系统将自动：
   - 使用Qwen 2.5 VL提取并显示成绩单数据
   - 使用您选择的模型生成竞争力分析报告
   - 基于分析提供UCL项目推荐
5. 在"提示词调试"选项卡中：
   - 修改所有代理的提示词以自定义其行为
   - 保存更改以供将来使用

## 工作流程

应用程序遵循以下工作流程：

1. **成绩单分析**：Qwen 2.5 VL从上传的成绩单图片中提取结构化数据
2. **竞争力分析**：选定的LLM分析学生的档案并生成竞争力报告
3. **项目推荐**：第二个LLM搜索并推荐合适的UCL项目

## Serper MCP服务器集成

应用程序使用Serper MCP服务器执行UCL项目信息的Web搜索。此集成：

1. 允许获取实时、最新的项目信息
2. 根据当前UCL提供的内容提供更准确的项目推荐
3. 如果搜索失败或API密钥未配置，则回退到模拟数据

## 开发说明

应用程序的结构如下：

- `app.py`：主Streamlit应用程序
- `agents/`：用于不同任务的AI代理
  - `transcript_analyzer.py`：使用Qwen 2.5 VL从成绩单图片中提取数据
  - `competitiveness_analyst.py`：分析学生竞争力
  - `consulting_assistant.py`：基于竞争力推荐UCL项目
  - `serper_client.py`：Serper MCP服务器集成的客户端
- `config/`：配置文件
  - `prompts.py`：管理提示词加载和保存
  - `prompts.json`：存储当前提示词（自动创建）

## 许可证

该项目根据MIT许可证授权 - 参见LICENSE文件了解详情。 