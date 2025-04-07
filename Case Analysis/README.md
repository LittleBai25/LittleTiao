# 简化文件处理工具

该工具是一个用于内部网络环境的简化文件处理系统，主要用于处理简历 PDF 文件、Offer PDF 文件和 Excel 文件。

## 功能特点

- PDF 简历解析：从 PDF 文件中提取文本内容
- PDF Offer 解析：从 PDF 文件中提取 Offer 相关信息
- Excel 文件处理：读取和写入 Excel 文件
- LLM 集成：使用大型语言模型分析简历和 Offer 内容

## 项目结构

```
simple_processor/
├── processor.py          # 简化处理器主类
├── pdf_parser.py         # PDF解析模块
├── pdf_offer_parser.py   # PDF Offer解析模块
├── excel_parser.py       # Excel解析模块
├── llm_processor.py      # LLM处理器模块
├── config_loader.py      # 配置加载模块
├── test_processor.py     # 基础功能测试脚本
├── test_llm.py           # LLM功能测试脚本
└── api_config.json.example # API配置示例文件
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置 API

要使用 LLM 功能，你需要创建一个`api_config.json`文件。可以复制示例文件并填写你的 API 信息：

```bash
cp simple_processor/api_config.json.example simple_processor/api_config.json
```

然后编辑`api_config.json`文件，填入你的 OpenAI API 密钥和其他配置信息：

```json
{
  "OPENAI_API_KEY": "your-api-key-here",
  "OPENAI_API_BASE": "https://openrouter.ai/api/v1",
  "OPENAI_MODEL": "openai/gpt-4o-mini",
  "MAX_TOKENS": 4000,
  "TEMPERATURE": 0.3
}
```

## 使用方法

### 基础功能测试

运行以下命令测试基础功能：

```bash
cd simple_processor
python test_processor.py
```

### LLM 功能测试

运行以下命令测试 LLM 集成功能：

```bash
cd simple_processor
python test_llm.py
```

## 注意事项

1. 请确保处理的 PDF 文件是文本型的，而非扫描图片型
2. 测试前请确保已正确配置`api_config.json`文件或设置环境变量`OPENAI_API_KEY`
3. LLM 处理可能需要一定的时间，取决于网络状况和 API 响应速度
4. 所有解析结果将保存在脚本运行目录下的相应文件中

## 依赖库

- PyPDF2：用于 PDF 文件处理
- pandas：用于 Excel 文件处理
- openpyxl：用于 Excel 文件读写
- requests：用于 API 通信
