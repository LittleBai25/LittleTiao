import sys
import streamlit as st
import os
import logging
import re
import sqlite3
from datetime import datetime
import json

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# 记录程序启动
logger.info("程序开始运行")

# 只在第一次运行时替换 sqlite3
if 'sqlite_setup_done' not in st.session_state:
    try:
        logger.info("尝试设置 SQLite")
        __import__('pysqlite3')
        sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
        st.session_state.sqlite_setup_done = True
        logger.info("SQLite 设置成功")
    except Exception as e:
        logger.error(f"SQLite 设置错误: {str(e)}")
        st.session_state.sqlite_setup_done = True

# 在所有其他导入之前，先初始化环境变量

# 立即设置所有需要的API keys
try:
    logger.info("开始设置 API keys")
    os.environ['OPENAI_API_KEY'] = st.secrets['OPENAI_API_KEY']
    os.environ['OPENAI_API_BASE'] = "https://openrouter.ai/api/v1"
    os.environ['OPENAI_MODEL_NAME'] = st.secrets['OPENAI_MODEL_NAME']
    
    # 如果有其他key，也在这里设置
    if 'GROQ_API_KEY' in st.secrets:
        os.environ['GROQ_API_KEY'] = st.secrets['GROQ_API_KEY']
    if 'DEEPSEEK_API_KEY' in st.secrets:
        os.environ['DEEPSEEK_API_KEY'] = st.secrets['DEEPSEEK_API_KEY']
    logger.info("API keys 设置成功")
except Exception as e:
    logger.error(f"API 密钥配置失败: {str(e)}")
    st.error(f"API密钥配置失败: {str(e)}")
    st.stop()

# 其他导入
import pandas as pd
from agent_case_match13 import (
    TAG_SYSTEM,
    process_student_case,
    process_student_case2,
    process_student_case_with_guide,
    PromptTemplates
)
import io
from operation_points_extractor import OperationPointsExtractor
import traceback
st.set_page_config(
    layout="wide",  # 使用宽布局
    initial_sidebar_state="collapsed"  # 默认折叠侧边栏
)

def load_config():
    """加载配置文件"""
    try:
        # 首先尝试从 Streamlit secrets 获取配置
        if not st.secrets.get("OPENAI_API_KEY"):
            raise ValueError("未在 Streamlit secrets 中找到 OPENAI_API_KEY")
            
        config = {
            "OPENAI_API_KEY": st.secrets["OPENAI_API_KEY"],
            "OPENAI_API_BASE": "https://openrouter.ai/api/v1",
            "OPENAI_MODEL_NAME": "openrouter/google/gemini-2.0-flash-001"
        }
        return config
        
    except Exception as e:
        st.error(f"从 Streamlit secrets 获取配置失败: {str(e)}")
        return None

def initialize_config():
    """初始化配置"""
    try:
        config = load_config()
        if not config:
            raise ValueError("无法加载配置")
        
        # 添加服务指南Excel路径
        config['SERVICE_GUIDE_EXCEL_PATH'] = os.path.join(os.path.dirname(__file__), '服务指南.xlsx')
        
        return config
        
    except Exception as e:
        raise Exception(f"配置初始化失败: {str(e)}")

def add_custom_css():
    st.markdown("""
    <style>
    /* 强制扩展整个应用的宽度 */
    .appview-container {
        width: 100vw !important;
        max-width: 100% !important;
    }
    
    /* 扩展主容器宽度 */
    .main .block-container {
        max-width: 100% !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        width: 100% !important;
    }
    
    /* 隐藏侧边栏 */
    .css-1d391kg, .css-12oz5g7, .css-eczf16, .css-jjjwou {
        display: none !important;
    }
    
    /* 移除所有边距和填充限制 */
    .reportview-container .main {
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* 确保内容使用全部可用空间 */
    .stTabs [data-baseweb="tab-panel"] {
        width: 100% !important;
    }
    
    /* 强制所有容器使用全宽 */
    .element-container, .stMarkdown, .stDataFrame, .stTable {
        width: 100% !important;
        max-width: 100% !important;
    }
    
    /* 其他样式保持不变 */
    /* 标题样式 */
    h1, h2, h3 {
        color: #1e3a8a;
        font-weight: 600;
    }
    
    /* 卡片样式 */
    .stTabs [data-baseweb="tab-panel"] {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        margin-top: 10px;
    }
    
    /* 按钮样式 */
    .stButton>button {
        background-color: #1e3a8a;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        font-weight: 500;
        border: none;
        width: 100%;
    }
    
    .stButton>button:hover {
        background-color: #2e4a9a;
    }
    
    /* 输入框样式 */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        border-radius: 5px;
        border: 1px solid #ddd;
    }
    
    /* 文件上传区域样式 */
    .stFileUploader>div>button {
        background-color: #f1f3f9;
        color: #1e3a8a;
        border: 1px dashed #1e3a8a;
        border-radius: 5px;
    }
    
    /* 成功消息样式 */
    .stSuccess {
        background-color: #d1fae5;
        color: #065f46;
        padding: 10px;
        border-radius: 5px;
    }
    
    /* 警告消息样式 */
    .stWarning {
        background-color: #fef3c7;
        color: #92400e;
        padding: 10px;
        border-radius: 5px;
    }
    
    /* 错误消息样式 */
    .stError {
        background-color: #fee2e2;
        color: #b91c1c;
        padding: 10px;
        border-radius: 5px;
    }
    
    /* 下拉选择框样式 */
    .stSelectbox>div>div {
        border-radius: 5px;
        border: 1px solid #ddd;
    }
    
    /* 页面标题样式 */
    .page-title {
        text-align: center;
        font-size: 2rem;
        margin-bottom: 20px;
        color: #1e3a8a;
        font-weight: bold;
    }
    
    /* 卡片容器样式 */
    .card-container {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        margin-bottom: 20px;
        width: 100%;
    }
    
    /* 分隔线样式 */
    hr {
        margin-top: 20px;
        margin-bottom: 20px;
        border: 0;
        border-top: 1px solid #eee;
    }
    
    /* 模型信息样式 */
    .model-info {
        background-color: #f0f7ff;
        padding: 8px 12px;
        border-radius: 5px;
        margin-top: 10px;
        margin-bottom: 15px;
        display: inline-block;
        font-size: 0.9rem;
    }
    
    /* 表格样式优化 */
    .dataframe {
        width: 100%;
        border-collapse: collapse;
    }
    
    .dataframe th {
        background-color: #f1f3f9;
        padding: 8px;
    }
    
    .dataframe td {
        padding: 8px;
        border-bottom: 1px solid #eee;
    }
    
    /* 匹配结果卡片样式 */
    .match-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        background-color: white;
    }
    
    .match-card-header {
        display: flex;
        justify-content: space-between;
        border-bottom: 1px solid #eee;
        padding-bottom: 10px;
        margin-bottom: 10px;
    }
    
    .match-score {
        color: #1e3a8a;
        font-weight: bold;
        font-size: 1.2rem;
    }
    
    /* 计算公式样式 */
    .formula-box {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
        font-family: monospace;
    }
    
    /* 调整列宽度 */
    .column-adjust {
        padding: 0 5px !important;
    }
    
    /* 强制展开器内容宽度 */
    .streamlit-expanderContent {
        width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)

def init_db():
    """初始化数据库"""
    try:
        # 使用 Streamlit 持久化目录
        db_path = './.streamlit/data.db'
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # 创建交互记录表
        c.execute('''
            CREATE TABLE IF NOT EXISTS interactions
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             input_text TEXT,
             output_result TEXT,
             interaction_type TEXT,
             timestamp DATETIME,
             model TEXT,
             business_unit TEXT,
             created_at DATETIME DEFAULT CURRENT_TIMESTAMP)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("数据库初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")

def save_interaction(input_text, output_result, business_unit, interaction_type="tag_matching"):
    """保存交互记录到数据库"""
    try:
        db_path = './.streamlit/data.db'
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # 准备数据
        data = (
            input_text,
            json.dumps(output_result, ensure_ascii=False),
            interaction_type,
            datetime.utcnow().isoformat(),
            st.session_state.current_model,
            business_unit
        )
        
        # 插入数据
        c.execute('''
            INSERT INTO interactions 
            (input_text, output_result, interaction_type, timestamp, model, business_unit)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', data)
        
        conn.commit()
        conn.close()
        logger.info(f"{interaction_type} 交互记录已保存到数据库")
    except Exception as e:
        logger.error(f"保存交互记录失败: {str(e)}")

def get_interactions(limit=100):
    """获取历史交互记录"""
    try:
        db_path = './.streamlit/data.db'
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # 明确指定字段顺序
        c.execute('''
            SELECT 
                id,             -- record[0]
                input_text,     -- record[1]
                output_result,  -- record[2]
                interaction_type, -- record[3]
                timestamp,      -- record[4]
                model,         -- record[5]
                business_unit   -- record[6]
            FROM interactions
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        records = c.fetchall()
        conn.close()
        return records
    except Exception as e:
        logger.error(f"获取历史记录失败: {str(e)}")
        return []

# 在主流程前添加健壮的标签提取函数
def safe_extract_recommended_tags(raw_output):
    try:
        start_idx = raw_output.find('{')
        end_idx = raw_output.rfind('}')
        if start_idx != -1 and end_idx != -1:
            json_part = raw_output[start_idx:end_idx + 1]
            json_part = json_part.replace('```json', '').replace('```', '').strip()
            output_dict = json.loads(json_part)
            # 兼容 recommended_tag / recommended_tags
            tags = None
            if "recommended_tag" in output_dict:
                tags = output_dict["recommended_tag"]
            elif "recommended_tags" in output_dict:
                tags = output_dict["recommended_tags"]
            else:
                tags = output_dict
            # 兼容单复数字段名
            def get_tag(keys, default=[]):
                for k in keys:
                    if k in tags:
                        return tags[k]
                return default
            norm_tags = {
                "countries": get_tag(["countries", "country"]),
                "majors": get_tag(["majors", "major"]),
                "schoolLevel": get_tag(["schoolLevel"]),
                "SpecialProjects": get_tag(["SpecialProjects", "SpecialProject"]),
                "Industryexperience": get_tag(["Industryexperience"]),
                "Consultantbackground": get_tag(["Consultantbackground"]),
                "businessLocation": get_tag(["businessLocation"])
            }
            # 类型强制
            for key in norm_tags:
                val = norm_tags[key]
                if not isinstance(val, list):
                    if val is None:
                        norm_tags[key] = []
                    else:
                        norm_tags[key] = [str(val)]
            return {"recommended_tags": norm_tags}
    except Exception as e:
        pass
    # 返回空结构
    return {"recommended_tags": {
        "countries": [],
        "majors": [],
        "schoolLevel": [],
        "SpecialProjects": [],
        "Industryexperience": [],
        "Consultantbackground": [],
        "businessLocation": []
    }}

def main():
    """主函数"""
    logger.info("进入主函数")
    
    # 初始化数据库
    init_db()
    
    add_custom_css()

    # 初始化 session_state 变量
    if 'tagged_data' not in st.session_state:
        st.session_state.tagged_data = None
    if 'merged_df' not in st.session_state:
        st.session_state.merged_df = None
    if 'prompt_templates' not in st.session_state:
        st.session_state.prompt_templates = PromptTemplates()
    
    # 初始化模型选择的session state
    if 'current_model' not in st.session_state:
        st.session_state.current_model = st.secrets['OPENAI_MODEL_NAME']  # 默认值
    
    langsmith_api_key = st.secrets["LANGCHAIN_API_KEY"]
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = "agent_case_match2"

    # 在输入区域前定义业务单位
    business_units = [
        "新通国际", "北京中心", "成都", "福州", "广州", "杭州留学",
        "合肥", "济南", "南昌", "南京", "宁波留学", "厦门", "山西", "深圳", "苏州",
        "天津", "温州", "武汉", "西安", "新通温哥华", "长春", "郑州", "重庆", "舟山"
    ]

    # 创建四个标签页
    system_tab1, system_tab2, system_tab3, system_tab4 = st.tabs([
        "标签匹配系统", 
        "标签匹配AI提示词设置", 
        "顾问匹配系统",
        "历史记录查询"
    ])
    
    with system_tab1:
        st.title("留学申请标签匹配系统")
        # 初始化配置
        try:
            config = initialize_config()
            if not config:
                st.error("配置初始化失败：无法获取配置")
                return
            
            if not config.get("OPENAI_API_KEY"):
                st.error("未找到 OpenAI API 密钥，请检查配置")
                return
            
            # 创建提示词模板实例并存储在session_state中
            if 'prompt_templates' not in st.session_state:
                logger.info("初始化提示词模板")
                st.session_state.prompt_templates = PromptTemplates()
            
            # 使用session_state中的prompt_templates
            prompt_templates = st.session_state.prompt_templates
            
            try:
                # 确认Excel文件路径
                excel_path = os.path.join(os.path.dirname(__file__), '服务指南.xlsx')
                if os.path.exists(excel_path):
                    logger.info(f"找到Excel文件: {excel_path}")
                    st.session_state.points_extractor = OperationPointsExtractor(excel_path)
                    logger.info("操作要点提取器初始化成功")
                else:
                    logger.warning(f"Excel文件不存在: {excel_path}")
                    st.session_state.points_extractor = None
            except Exception as e:
                logger.error(f"初始化操作要点提取器出错: {str(e)}")
                st.session_state.points_extractor = None
            
            # 第一行：预计入学时间、申请国家、申请专业、留学类别
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                year = st.selectbox("入学年份", [str(y) for y in range(2024, 2035)], key="year", index=0)
            with col2:
                season = st.selectbox("入学季节", ["春", "夏", "秋", "冬"], key="season", index=0)
            with col3:
                country = st.text_input("申请国家", key="country")
            with col4:
                major = st.text_input("申请专业", key="major")

            # 第二行：留学类别
            study_type = st.selectbox(
                "留学类别",
                [
                    "学前", "小学", "初中", "高中", "大学预科", "大专文凭", "硕士预科", "本科文凭",
                    "大学转学分课程", "学士学位", "副学士学位", "硕士学位", "授课类硕士", "研究类硕士", "博士学位"
                ],
                key="study_type"
            )

            st.markdown("---")

            # 客户背景信息和其他信息左右显示，输入框高度调大
            col_bg, col_other = st.columns(2)
            with col_bg:
                st.markdown("#### 客户背景信息")
                default_background = (
                    "学生基本信息：\n"
                    "- 当前学校：\n"
                    "- 专业：\n"
                    "- 平均成绩：\n"
                    "- 语言成绩：\n"
                )
                background = st.text_area("请填写客户背景信息", value=default_background, height=130, key="background")
            with col_other:
                st.markdown("#### 其他信息")
                other_info = st.text_area('如该部分信息为空，小助理不会输出"个性化服务指南"', height=130, key="other_info")

            st.markdown("---")

            # 业务单位选择和生成个性服务指南分两行
            selected_unit = st.selectbox(
                "请选择业务单位",
                options=business_units,
                index=0
            )
            generate_service_guide = st.checkbox("生成个性服务指南", value=True)

            # 在分析按钮逻辑前
            if 'analysis_done' not in st.session_state:
                st.session_state.analysis_done = False

            # 在点击"开始分析"按钮时，重置为False
            if st.button("开始分析", key="start_analysis"):
                st.session_state.analysis_done = False
                if not (year and season and country and major and study_type and background.strip()):
                    st.warning("请填写所有必填项！")
                else:
                    # 组装 student_case 字符串，传递给后续处理逻辑
                    student_case = f"""
学生基本信息：
{background.strip()}

申请意向：
- 申请国家：{country}
- 申请专业：{major}
- 留学类别：{study_type}
- 时间规划：{year}年{season}季

其他信息或需求：
{other_info.strip()}
"""
                    # 在分析按钮下方、st.spinner前显示小号猫 emoji，不居中
                    with st.spinner("正在分析..."):
                        try:
                            tag_result = process_student_case2(student_case)
                            result = tag_result
                            if generate_service_guide and tag_result["status"] == "success" and other_info.strip():
                                excel_path = os.path.join(os.path.dirname(__file__), '服务指南.xlsx')
                                if not os.path.exists(excel_path):
                                    result['service_guide'] = "⚠️ 服务指南Excel文件不存在，只生成标签"
                                else:
                                    backstory = st.session_state.get('service_guide_backstory', prompt_templates.get_template('service_guide_backstory'))
                                    task = st.session_state.get('service_guide_task', prompt_templates.get_template('service_guide_task'))
                                    output = st.session_state.get('service_guide_output', prompt_templates.get_template('service_guide_output'))
                                    formatted_task = task.format(student_info=student_case)
                                    guide_prompt = f"{backstory}\n\n{formatted_task}\n\n{output}"
                                    try:
                                        guide_result = process_student_case_with_guide(
                                            student_case,
                                            guide_prompt,
                                            excel_path
                                        )
                                        if isinstance(guide_result, dict) and 'service_guide' in guide_result:
                                            result['service_guide'] = guide_result['service_guide']
                                        else:
                                            result['service_guide'] = "无法生成服务指南"
                                    except Exception as e:
                                        result['service_guide'] = f"生成服务指南出错: {str(e)}"
                            if result["status"] == "success":
                                with st.expander("查看原始输出（调试用）", expanded=False):
                                    st.subheader("模型输出结果")
                                    st.code(result["raw_output"], language="json")
                                json_str = result["raw_output"]
                                output_dict = safe_extract_recommended_tags(json_str)
                                st.subheader("📊 分析结果")
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write("🎯 **匹配标签**")
                                    if "recommended_tags" in output_dict:
                                        tags = output_dict["recommended_tags"]
                                        if tags.get("countries"):
                                            st.write("**国家标签：**", ", ".join(tags["countries"]))
                                        if tags.get("majors"):
                                            st.write("**专业标签：**", ", ".join(tags["majors"]))
                                        if tags.get("schoolLevel"):
                                            st.write("**院校层次：**", ", ".join(tags["schoolLevel"]))
                                        if tags.get("SpecialProjects"):
                                            st.write("**特殊项目：**", ", ".join(tags["SpecialProjects"]))
                                with col2:
                                    if "recommended_tags" in output_dict:
                                        tags = output_dict["recommended_tags"]
                                        if tags.get("Industryexperience"):
                                            st.write("**行业经验：**", ", ".join(tags["Industryexperience"]))
                                        if tags.get("Consultantbackground"):
                                            st.write("**顾问背景：**", ", ".join(tags["Consultantbackground"]))
                                        if tags.get("businessLocation"):
                                            st.write("**业务单位所在地：**", ", ".join(tags["businessLocation"]))
                                if 'service_guide' in result:
                                    st.subheader("📝 个性服务指南")
                                    st.markdown(result['service_guide'])
                                df = pd.DataFrame({
                                    "文案顾问业务单位": [selected_unit],
                                    "国家标签": [', '.join(output_dict["recommended_tags"]["countries"])],
                                    "专业标签": [', '.join(output_dict["recommended_tags"]["majors"])],
                                    "名校专家": [', '.join(output_dict["recommended_tags"]["schoolLevel"])],
                                    "特殊项目标签": [', '.join(output_dict["recommended_tags"]["SpecialProjects"])],
                                    "行业经验": [', '.join(output_dict["recommended_tags"]["Industryexperience"])],
                                    "文案背景": [', '.join(output_dict["recommended_tags"]["Consultantbackground"])],
                                    "业务单位所在地": [', '.join(output_dict["recommended_tags"]["businessLocation"])],
                                })
                                st.session_state.tagged_data = df
                                try:
                                    ai_country_tag = df["国家标签"]
                                    ai_major_tag = df["专业标签"]
                                    logger.info(f"ai_country_tag: {ai_country_tag}")
                                    logger.info(f"ai_major_tag: {ai_major_tag}")
                                    if st.session_state.points_extractor is not None:
                                        operation_points = st.session_state.points_extractor.get_operation_points(
                                            student_case,
                                            ai_country_tag,
                                            ai_major_tag
                                        )
                                        result['operation_points'] = operation_points
                                except Exception as e:
                                    result['operation_points'] = f"⚠️ 算法提取操作要点出错: {str(e)}"
                                if 'operation_points' in result:
                                    st.subheader("📝 操作要点")
                                    st.markdown(result['operation_points'])
                                with st.expander("查看标签数据表格", expanded=False):
                                    st.dataframe(df)
                                save_interaction(
                                    input_text=student_case,
                                    output_result=result,
                                    business_unit=selected_unit,
                                    interaction_type="tag_matching"
                                )
                                st.success("✅ 数据已处理并保存到内存中，可用于后续匹配")
                            else:
                                st.error("处理模型输出时出错: 未返回成功状态")
                        except Exception as e:
                            st.error(f"处理过程中出错: {str(e)}")
                        st.session_state.analysis_done = True
                
        except Exception as e:
            logger.error(f"配置初始化失败: {str(e)}")
            st.error(f"配置初始化失败: {str(e)}")
            return

    with system_tab2:
        st.title("标签匹配AI提示词设置")
        
        if st.secrets.get("OPENAI_API_KEY"):
            logger.info("API 配置验证成功")
            st.success("✅ API配置成功")
        st.markdown(f"<div class='model-info'>🤖 当前使用模型: <b>{st.session_state.current_model}</b></div>", unsafe_allow_html=True)
        
        # 使用session_state中的prompt_templates
        prompt_templates = st.session_state.prompt_templates
        
        # Agent backstory
        st.subheader("标签专家角色设定")
        tag_backstory = st.text_area(
            "角色设定",
            value=prompt_templates.get_template('tag_specialist'),
            height=400
        )

        # Task description
        st.subheader("标签提取任务说明")
        tag_task = st.text_area(
            "任务说明",
            value=prompt_templates.get_template('tag_task'),
            height=400
        )

        st.subheader("标签输出结构")
        tag_recommendation_structure = st.text_area(
            "标签输出结构",
            value=prompt_templates.get_template('tag_recommendation_structure'),
            height=400
        )
        
        # 添加个性服务指南提示词编辑 - 分为三个部分
        st.subheader("个性服务指南提示词")
        
        # 创建三个tab用于编辑不同部分的提示词
        guide_tab1, guide_tab2, guide_tab3 = st.tabs(["角色设定", "任务说明", "输出格式"])
        
        with guide_tab1:
            if 'service_guide_backstory' not in st.session_state:
                # 初始化个性服务指南角色设定
                st.session_state.service_guide_backstory = prompt_templates.get_template('service_guide_backstory')
            
            service_guide_backstory = st.text_area(
                "个性服务指南角色设定",
                value=st.session_state.service_guide_backstory,
                height=300
            )
            
            if service_guide_backstory != st.session_state.service_guide_backstory:
                st.session_state.service_guide_backstory = service_guide_backstory
                prompt_templates.update_template('service_guide_backstory', service_guide_backstory)
                st.success("个性服务指南角色设定已更新")
        
        with guide_tab2:
            if 'service_guide_task' not in st.session_state:
                # 初始化个性服务指南任务说明
                st.session_state.service_guide_task = prompt_templates.get_template('service_guide_task')
            
            service_guide_task = st.text_area(
                "个性服务指南任务说明",
                value=st.session_state.service_guide_task,
                height=400
            )
            
            if service_guide_task != st.session_state.service_guide_task:
                st.session_state.service_guide_task = service_guide_task
                prompt_templates.update_template('service_guide_task', service_guide_task)
                st.success("个性服务指南任务说明已更新")
        
        with guide_tab3:
            if 'service_guide_output' not in st.session_state:
                # 初始化个性服务指南输出格式
                st.session_state.service_guide_output = prompt_templates.get_template('service_guide_output')
            
            service_guide_output = st.text_area(
                "个性服务指南输出格式",
                value=st.session_state.service_guide_output,
                height=300
            )
            
            if service_guide_output != st.session_state.service_guide_output:
                st.session_state.service_guide_output = service_guide_output
                prompt_templates.update_template('service_guide_output', service_guide_output)
                st.success("个性服务指南输出格式已更新")

        # 更新按钮
        if st.button("更新提示词", key="update_prompts"):
            prompt_templates.update_template('tag_specialist', tag_backstory)
            prompt_templates.update_template('tag_task', tag_task)
            prompt_templates.update_template('tag_recommendation_structure', tag_recommendation_structure)
            st.session_state.prompt_templates = prompt_templates
            st.success("✅ 提示词已更新！")
            
            # 显示更新后的提示词
            with st.expander("查看更新后的提示词"):
                st.write("更新后的角色设定：", st.session_state.prompt_templates.get_template('tag_specialist'))
                st.write("更新后的任务说明：", st.session_state.prompt_templates.get_template('tag_task'))
                st.write("更新后的输出结构：", st.session_state.prompt_templates.get_template('tag_recommendation_structure'))
                st.write("更新后的个性服务指南角色设定：", st.session_state.prompt_templates.get_template('service_guide_backstory'))
                st.write("更新后的个性服务指南任务说明：", st.session_state.prompt_templates.get_template('service_guide_task'))
                st.write("更新后的个性服务指南输出格式：", st.session_state.prompt_templates.get_template('service_guide_output'))

    with system_tab3:
        from match7 import (
            label_merge,
            Consultant_matching
        )
        st.title("顾问匹配系统")
        
        # 检查是否有必要的数据
        if st.session_state.tagged_data is None:
            st.warning("请先在标签匹配系统中处理数据")
            return
            
        # 文件上传区域
        with st.container():
            st.subheader("数据上传")
            uploaded_consultant_tags = st.file_uploader("请上传文案顾问标签汇总", type=['xlsx'], key='consultant')
                
            if uploaded_consultant_tags is not None:
                consultant_tags_file = pd.read_excel(uploaded_consultant_tags)
                st.success("顾问标签汇总上传成功")
            
        # 数据处理区域
        with st.container():
            st.subheader("数据处理")
            
            # 标签转换处理按钮
            if st.button("开始标签转换处理"):
                if st.session_state.tagged_data is not None:
                    try:
                        st.session_state.merged_df = label_merge(st.session_state.tagged_data)
                        st.success("标签转换处理完成！")
                        # 显示合并后的数据预览
                        st.write("转换后数据预览：")
                        st.dataframe(st.session_state.merged_df.head())
                            
                        # 添加下载按钮
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            st.session_state.merged_df.to_excel(writer, index=False, sheet_name='标签转换结果')
                        st.download_button(
                            label="下载标签转换结果",
                            data=buffer.getvalue(),
                            file_name="标签转换结果.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    except Exception as e:
                        st.error(f"标签转换处理出错: {str(e)}")
                else:
                    st.warning("请先完成标签处理")
            
            st.markdown("---")  # 添加分隔线
            
            # 添加补偿机制设置表格
            st.subheader("补偿机制设置")
            
            # 初始化 session state
            if 'compensation_data' not in st.session_state:
                st.session_state.compensation_data = pd.DataFrame(columns=[
                    '文案顾问',
                    '名校专家使用次数',
                    '博士成功案例使用次数',
                    '低龄留学成功案例使用次数'
                ])
            
            # 如果有顾问数据，更新补偿机制表格
            if uploaded_consultant_tags is not None:
                # 获取所有顾问名单
                consultants = consultant_tags_file['文案顾问'].unique()
                
                # 如果是新的顾问列表，更新 session state
                current_consultants = set(st.session_state.compensation_data['文案顾问'].values)
                new_consultants = set(consultants) - current_consultants
                
                if new_consultants:
                    new_data = pd.DataFrame({
                        '文案顾问': list(new_consultants),
                        '名校专家使用次数': [0] * len(new_consultants),
                        '博士成功案例使用次数': [0] * len(new_consultants),
                        '低龄留学成功案例使用次数': [0] * len(new_consultants)
                    })
                    st.session_state.compensation_data = pd.concat([
                        st.session_state.compensation_data,
                        new_data
                    ]).reset_index(drop=True)
            
            # 创建可编辑的数据表格
            edited_df = st.data_editor(
                st.session_state.compensation_data,
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "文案顾问": st.column_config.TextColumn(
                        "文案顾问",
                        help="顾问姓名",
                        required=True
                    ),
                    "名校专家使用次数": st.column_config.NumberColumn(
                        "名校专家使用次数",
                        help="该顾问的名校专家标签被使用的次数",
                        min_value=0,
                        default=0
                    ),
                    "博士成功案例使用次数": st.column_config.NumberColumn(
                        "博士成功案例使用次数",
                        help="该顾问的博士成功案例标签被使用的次数",
                        min_value=0,
                        default=0
                    ),
                    "低龄留学成功案例使用次数": st.column_config.NumberColumn(
                        "低龄留学成功案例使用次数",
                        help="该顾问的低龄留学成功案例标签被使用的次数",
                        min_value=0,
                        default=0
                    )
                }
            )
            
            # 更新按钮
            if st.button("更新补偿数据"):
                st.session_state.compensation_data = edited_df
                st.success("✅ 补偿数据已更新！")
                
                # 显示更新后的数据预览
                with st.expander("查看更新后的补偿数据"):
                    st.dataframe(st.session_state.compensation_data)
            
            st.markdown("---")  # 添加分隔线
            
            # 顾问匹配按钮
            if st.button("开始顾问匹配"):
                if uploaded_consultant_tags is not None and st.session_state.merged_df is not None:
                    try:
                        merge_df = st.session_state.merged_df
                        # 确保补偿数据格式正确
                        compensation_data = st.session_state.compensation_data.to_dict('records')
                        
                        # 调用匹配函数
                        matching_results, area = Consultant_matching(
                            consultant_tags_file,
                            merge_df,
                            compensation_data
                        )
                        st.success("顾问匹配完成！")

                        
                        # 保存匹配结果到数据库
                        save_interaction(
                            input_text=json.dumps(merge_df.to_dict(), ensure_ascii=False),
                            output_result=matching_results,
                            business_unit=selected_unit,
                            interaction_type="consultant_matching"
                        )
                        
                        # 显示匹配结果
                        st.markdown("<div class='card-container'>", unsafe_allow_html=True)
                        st.subheader("🔍 匹配结果")

                        for case, consultants in matching_results.items():
                            for i, consultant in enumerate(consultants):
                                # 创建一个漂亮的卡片来显示每个顾问的匹配结果
                                st.markdown(f"""
                                <div style="margin-bottom: 15px; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                                    <h3 style="color: #1e3a8a; margin-top: 0;">
                                        {consultant['name']} ({consultant['score']:.1f}分)
                                    </h3>
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                        <span><strong>业务单位:</strong> {consultant.get('businessunits', '未知')}</span>
                                        <span><strong>文案方向:</strong> {consultant.get('文案方向', '未知')}</span>
                                        <span><strong>匹配范围:</strong> {"本地匹配" if consultant.get('area', False) else "全国大池里匹配"}</span>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # 添加一个展开按钮来查看详细信息
                                with st.expander(f"查看 {consultant['name']} 的详细匹配信息"):
                                    # 创建两列布局，调整列宽比例为4:6，让右侧有更多空间显示计算过程
                                    col1, col2 = st.columns([4, 6])
                                    
                                    # 第一列：顾问原始标签（简化显示）
                                    with col1:
                                        st.markdown("<h4 style='color: #1e3a8a;'>顾问原始标签</h4>", unsafe_allow_html=True)
                                        
                                        # 国家标签
                                        st.markdown("<div style='margin-bottom: 15px;'>", unsafe_allow_html=True)
                                        st.markdown("<strong>国家标签(绝对高频国家、相对高频国家):</strong>", unsafe_allow_html=True)
                                        if consultant['绝对高频国家']:
                                            st.markdown(f"<span>• 绝对高频国家: {consultant['绝对高频国家']}</span>", unsafe_allow_html=True)
                                        if consultant['相对高频国家']:
                                            st.markdown(f"<span>• 相对高频国家: {consultant['相对高频国家']}</span>", unsafe_allow_html=True)
                                        st.markdown("</div>", unsafe_allow_html=True)
                                        
                                        # 专业标签
                                        st.markdown("<div style='margin-bottom: 15px;'>", unsafe_allow_html=True)
                                        st.markdown("<strong>专业标签(绝对高频专业、相对高频专业):</strong>", unsafe_allow_html=True)
                                        if consultant['绝对高频专业']:
                                            st.markdown(f"<span>• 绝对高频专业: {consultant['绝对高频专业']}</span>", unsafe_allow_html=True)
                                        if consultant['相对高频专业']:
                                            st.markdown(f"<span>• 相对高频专业: {consultant['相对高频专业']}</span>", unsafe_allow_html=True)
                                        st.markdown("</div>", unsafe_allow_html=True)
                                        
                                        # 特殊标签
                                        special_tags = [
                                            ('名校专家', '名校专家'),
                                            ('博士成功案例', '博士成功案例'), 
                                            ('低龄留学成功案例', '低龄留学成功案例')
                                        ]
                                        
                                        has_special_tags = any(tag_key in consultant and consultant[tag_key] for _, tag_key in special_tags)
                                        if has_special_tags:
                                            st.markdown("<div style='margin-bottom: 15px;'>", unsafe_allow_html=True)
                                            st.markdown("<strong>特殊标签(名校专家、博士成功案例、低龄留学成功案例):</strong>", unsafe_allow_html=True)
                                            for tag_name, tag_key in special_tags:
                                                if tag_key in consultant and consultant[tag_key]:
                                                    st.markdown(f"<span>• {tag_name}: {consultant[tag_key]}</span>", unsafe_allow_html=True)
                                            st.markdown("</div>", unsafe_allow_html=True)
                                        
                                        # 其他标签
                                        st.markdown("<div style='margin-bottom: 15px;'>", unsafe_allow_html=True)
                                        st.markdown("<strong>其他信息(行业经验、文案背景、业务单位所在地):</strong>", unsafe_allow_html=True)
                                        if consultant['行业经验']:
                                            st.markdown(f"<span>• 行业经验: {consultant['行业经验']}</span>", unsafe_allow_html=True)
                                        if consultant['文案背景']:
                                            st.markdown(f"<span>• 文案背景: {consultant['文案背景']}</span>", unsafe_allow_html=True)
                                        if consultant['业务单位所在地']:
                                            st.markdown(f"<span>• 业务单位所在地: {consultant['业务单位所在地']}</span>", unsafe_allow_html=True)
                                        st.markdown("</div>", unsafe_allow_html=True)
                                        #工作量
                                        st.markdown("<div style='margin-bottom: 15px;'>", unsafe_allow_html=True)
                                        st.markdown("<strong>工作量:</strong>", unsafe_allow_html=True)
                                        st.markdown(f"<span>• 学年负荷: {consultant['学年负荷']}</span>", unsafe_allow_html=True)
                                        st.markdown(f"<span>• 近两周负荷: {consultant['近两周负荷']}</span>", unsafe_allow_html=True)
                                        st.markdown(f"<span>• 文书完成率: {consultant['文书完成率']}</span>", unsafe_allow_html=True)
                                        st.markdown(f"<span>• 申请完成率: {consultant['申请完成率']}</span>", unsafe_allow_html=True)
                                        st.markdown(f"<span>• 个人意愿: {consultant['个人意愿']}</span>", unsafe_allow_html=True)
                                        st.markdown("</div>", unsafe_allow_html=True)

                                        st.markdown("<h4 style='color: #1e3a8a;'>案例需求详情</h4>", unsafe_allow_html=True)
                                        # 案例需求
                                        st.markdown("<div style='margin-bottom: 15px;'>", unsafe_allow_html=True)
                                        st.markdown("<strong>案例需求:</strong>", unsafe_allow_html=True)
                                        
                                        # 获取当前案例的标签数据
                                        case_id = list(matching_results.keys()).index(case) if case in matching_results else 0
                                        
                                        # 安全地尝试获取对应行的数据
                                        if 'merged_df' in st.session_state and not st.session_state.merged_df.empty:
                                            try:
                                                case_data = st.session_state.merged_df.iloc[case_id]
                                                
                                                # 显示指定列的数据
                                                target_columns = ['文案顾问业务单位','国家标签', '专业标签', '名校专家', 
                                                                '博士成功案例', '低龄留学成功案例', '行业经验','文案背景'
                                                                '业务单位所在地']
                                                
                                                for col in target_columns:
                                                    if col in case_data.index and pd.notna(case_data[col]) and case_data[col]:
                                                        st.markdown(f"<span>• {col}: {case_data[col]}</span>", unsafe_allow_html=True)
                                            except Exception as e:
                                                st.error(f"获取案例数据时出错: {str(e)}")
                                        else:
                                            st.warning("没有可用的案例标签数据")
                                        st.markdown("</div>", unsafe_allow_html=True)
                                    
                                    # 第二列：匹配详情
                                    with col2:
                                        st.markdown("<h4 style='color: #1e3a8a;'>匹配得分详情</h4>", unsafe_allow_html=True)
                                        
                                        # 标签匹配得分表格
                                        if 'tag_score_dict' in consultant:
                                            st.markdown("<div style='margin-bottom: 15px;'>", unsafe_allow_html=True)
                                            st.markdown("<strong>标签匹配得分:</strong>", unsafe_allow_html=True)
                                            
                                            # 创建一个表格来显示标签匹配情况
                                            tag_details = consultant['tag_score_dict']
                                            tag_data = []
                                            for tag, score in tag_details.items():
                                                tag_status = "✅" if score > 0 else "❌"
                                                tag_data.append({"标签": tag, "状态": tag_status, "得分": f"{score}分"})
                                            
                                            # 使用DataFrame显示表格
                                            tag_df = pd.DataFrame(tag_data)
                                            st.dataframe(tag_df, hide_index=True, use_container_width=True)
                                            st.markdown("</div>", unsafe_allow_html=True)
                                            
                                            # 匹配率与覆盖率
                                            st.markdown("<div style='margin-bottom: 15px;'>", unsafe_allow_html=True)
                                            st.markdown("<strong>匹配率与覆盖率:</strong>", unsafe_allow_html=True)
                                            
                                            # 获取已计算好的匹配标签比例数据
                                            country_match_ratio = consultant.get('country_match_ratio', 0)
                                            special_match_ratio = consultant.get('special_match_ratio', 0)
                                            country_coverage_ratio = consultant.get('country_coverage_ratio', 0)
                                            special_coverage_ratio = consultant.get('special_coverage_ratio', 0)
                                            country_count_need = consultant.get('country_count_need', 0)
                                            country_count_total = consultant.get('country_count_total', 1)
                                            special_count_need = consultant.get('special_count_need', 0)
                                            special_count_total = consultant.get('special_count_total', 1)
                                            tag_score_dict = consultant.get('tag_score_dict', {})
                                            major_tags =['绝对高频专业','相对高频专业','做过专业']
                                            major_tags_score = 0
                                            for tag in major_tags:
                                                major_tags_score += tag_score_dict.get(tag, 0)
                                            
                                            other_tags = ['行业经验','文案背景','业务单位所在地']
                                            other_tags_score = 0
                                            for tag in other_tags:
                                                other_tags_score += tag_score_dict.get(tag, 0)
                                            # 创建一个表格来显示匹配率和覆盖率
                                            ratio_data = [
                                                #{"类别": "国家标签", "匹配率": f"{country_match_ratio:.2f} ({country_count_need}/{country_count_total})", "覆盖率": f"{country_coverage_ratio:.2f}"},
                                                {"类别": "特殊标签", "匹配率": f"{special_match_ratio:.2f} ({special_count_need}/{special_count_total})", "覆盖率": f"{special_coverage_ratio:.2f}"}
                                            ]
                                            ratio_df = pd.DataFrame(ratio_data)
                                            st.dataframe(ratio_df, hide_index=True, use_container_width=True)
                                            st.markdown("</div>", unsafe_allow_html=True)
                                            
                                            # 第五行：得分计算
                                            st.markdown("#### 得分计算")

                                            # 创建一个包含公式和计算过程的表格
                                            score_calculation = [
                                                {
                                                    "项目": "国家标签得分",
                                                    "得分": f"{consultant.get('country_tags_score', 0)}分",
                                                    "计算公式": "国家得分 ",
                                                    "详细计算": f"({consultant.get('country_tags_score', 0):.1f}) * 0.5 = {consultant.get('country_tags_score', 0) * 0.5:.1f}分"
                                                },
                                                {
                                                    "项目": "专业标签得分",
                                                    "得分": f"{major_tags_score}分",
                                                    "计算公式": "专业得分 × 0.5",
                                                    "详细计算": f"({major_tags_score:.1f}) × 0.5 = {major_tags_score * 0.5:.1f}分"
                                                },
                                                {
                                                    "项目": "特殊标签得分",
                                                    "得分": f"{consultant.get('special_tags_score', 0)}分",
                                                    "计算公式": "特殊得分 × 特殊匹配率 × 特殊覆盖率 × 0.5",
                                                    "详细计算": f"({consultant.get('special_tags_score', 0):.1f}) × ({consultant.get('special_match_ratio', 0):.2f}) × ({consultant.get('special_coverage_ratio', 0):.2f}) × 0.5 = {consultant.get('special_tags_score', 0) * consultant.get('special_match_ratio', 0) * consultant.get('special_coverage_ratio', 0) * 0.5:.1f}分"
                                                },
                                                {
                                                    "项目": "其他标签得分",
                                                    "得分": f"{other_tags_score}分",
                                                    "计算公式": "其他标签得分 × 0.5",
                                                    "详细计算": f"({other_tags_score:.1f}) × 0.5 = {other_tags_score * 0.5:.1f}分"
                                                },
                                                {
                                                    "项目": "工作量评分",
                                                    "得分": f"{consultant.get('workload_score', 0)}分",
                                                    "计算公式": "工作量得分 × 0.3",
                                                    "详细计算": f"({consultant.get('workload_score', 0):.1f}) × 0.3 = {consultant.get('workload_score', 0) * 0.3:.1f}分"
                                                },
                                                {
                                                    "项目": "个人意愿评分",
                                                    "得分": f"{consultant.get('personal_score', 0)}分",
                                                    "计算公式": "个人意愿得分 × 0.2",
                                                    "详细计算": f"({consultant.get('personal_score', 0):.1f}) × 0.2 = {consultant.get('personal_score', 0) * 0.2:.1f}分"
                                                }
                                            ]

                                            # 创建DataFrame并显示
                                            score_df = pd.DataFrame(score_calculation)
                                            st.dataframe(score_df, hide_index=True, use_container_width=True)

                                            # 计算总分
                                            country_weighted = consultant.get('country_tags_score', 0) * consultant.get('country_match_ratio', 0) * consultant.get('country_coverage_ratio', 0) * 0.5
                                            special_weighted = consultant.get('special_tags_score', 0) * consultant.get('special_match_ratio', 0) * consultant.get('special_coverage_ratio', 0) * 0.5
                                            other_weighted = consultant.get('other_tags_score', 0) * 0.5
                                            workload_weighted = consultant.get('workload_score', 0) * 0.3
                                            personal_weighted = consultant.get('personal_score', 0) * 0.2

                                            

                                            # 最终得分
                                            st.success(f"#### 最终得分: {consultant['score']:.1f}分")

                        st.markdown("</div>", unsafe_allow_html=True)
                        # 保存匹配结果到 session_state
                        st.session_state.matching_results = matching_results
                        
                    except Exception as e:
                        st.error(f"顾问匹配出错2: {str(e)}")
                else:
                    st.warning("请先上传顾问标签汇总并完成标签处理")

            # 显示处理状态
            st.markdown("<div class='card-container'>", unsafe_allow_html=True)
            st.subheader("处理状态")
            
            # 使用更美观的状态指示器
            col1, col2 = st.columns(2)
            with col1:
                if st.session_state.merged_df is not None:
                    st.markdown("**标签处理状态:** <span style='color:green;'>✅ 完成</span>", unsafe_allow_html=True)
                else:
                    st.markdown("**标签处理状态:** <span style='color:orange;'>⏳ 待处理</span>", unsafe_allow_html=True)
            
            with col2:
                if 'matching_results' in st.session_state:
                    st.markdown("**顾问匹配状态:** <span style='color:green;'>✅ 完成</span>", unsafe_allow_html=True)
                else:
                    st.markdown("**顾问匹配状态:** <span style='color:orange;'>⏳ 待处理</span>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # 添加历史记录标签页内容
    with system_tab4:
        st.title("历史记录查询")
        
        # 添加过滤选项
        col1, col2, col3 = st.columns(3)
        with col1:
            records_limit = st.number_input("显示记录数量", min_value=1, max_value=1000, value=100)
        with col2:
            business_unit_filter = st.selectbox(
                "按业务单位筛选",
                options=["全部"] + business_units,
                index=0
            )
        with col3:
            record_type_filter = st.selectbox(
                "记录类型",
                options=["全部", "标签匹配", "顾问匹配"],
                index=0
            )
        
        # 获取并显示历史记录
        records = get_interactions(limit=records_limit)
        
        if records:
            for record in records:
                # 应用筛选条件
                if business_unit_filter != "全部" and record[6] != business_unit_filter:
                    continue
                
                record_type = "标签匹配" if record[3] == "tag_matching" else "顾问匹配"
                if record_type_filter != "全部" and record_type != record_type_filter:
                    continue
                
                # 主记录的expander
                with st.expander(f"{record_type} 记录 #{record[0]} - {record[4]}", expanded=False):
                    # 输入信息
                    st.markdown("### 输入信息")
                    if record[3] == "tag_matching":
                        st.text_area(
                            "案例内容",
                            record[1],
                            height=200,
                            disabled=True,
                            key=f"input_text_{record[0]}"
                        )
                    else:
                        try:
                            input_data = json.loads(record[1])
                            st.dataframe(pd.DataFrame.from_dict(input_data))
                        except:
                            st.text_area(
                                "输入数据",
                                record[1],
                                height=200,
                                disabled=True,
                                key=f"input_data_{record[0]}"
                            )
                        st.markdown(f"**业务单位:** {record[6]}")
                        st.markdown(f"**使用模型:** {record[5]}")
                    
                    # 输出结果
                    st.markdown("### 输出结果")
                    try:
                        output_dict = json.loads(record[2])
                        if record[3] == "consultant_matching":
                            # 为每个匹配的案例创建结果显示
                            for case, consultants in output_dict.items():
                                st.markdown(f"#### {case} 匹配结果")
                                
                                # 创建所有顾问的数据列表
                                all_consultants_data = []
                                for consultant in consultants:
                                    tag_scores = consultant.get('tag_score_dict', {})
                                    
                                    # 计算各项得分
                                    country_score = consultant.get('country_tags_score', 0)
                                    special_score = consultant.get('special_tags_score', 0)
                                    special_match_ratio = consultant.get('special_match_ratio', 0)
                                    special_coverage_ratio = consultant.get('special_coverage_ratio', 0)
                                    workload_score = consultant.get('workload_score', 0)
                                    personal_score = consultant.get('personal_score', 0)
                                    
                                    consultant_data = {
                                        "文案顾问": consultant['name'],
                                        "总得分": f"{consultant['score']:.1f}",
                                        "业务单位": consultant.get('businessunits', '未知'),
                                        "文案方向": consultant.get('文案方向', '未知'),
                                        "匹配范围": "本地匹配" if consultant.get('area', False) else "全国匹配",
                                        # 标签得分
                                        "绝对高频国家": f"{tag_scores.get('绝对高频国家', 0):.1f}",
                                        "相对高频国家": f"{tag_scores.get('相对高频国家', 0):.1f}",
                                        "做过国家": f"{tag_scores.get('做过国家', 0):.1f}",
                                        "绝对高频专业": f"{tag_scores.get('绝对高频专业', 0):.1f}",
                                        "相对高频专业": f"{tag_scores.get('相对高频专业', 0):.1f}",
                                        "做过专业": f"{tag_scores.get('做过专业', 0):.1f}",
                                        "名校专家": f"{tag_scores.get('名校专家', 0):.1f}",
                                        "博士成功案例": f"{tag_scores.get('博士成功案例', 0):.1f}",
                                        "低龄留学成功案例": f"{tag_scores.get('低龄留学成功案例', 0):.1f}",
                                        "行业经验": f"{tag_scores.get('行业经验', 0):.1f}",
                                        "文案背景": f"{tag_scores.get('文案背景', 0):.1f}",
                                        "业务单位所在地": f"{tag_scores.get('业务单位所在地', 0):.1f}",
                                        # 匹配率和覆盖率
                                        "匹配率": f"{special_match_ratio:.2f}",
                                        "覆盖率": f"{special_coverage_ratio:.2f}",
                                        # 各项得分
                                        "国家标签得分": f"{country_score:.1f}",
                                        "专业标签得分": f"{sum(tag_scores.get(tag, 0) for tag in ['绝对高频专业','相对高频专业','做过专业']):.1f}",
                                        "特殊标签得分": f"{special_score:.1f}",
                                        "其他标签得分": f"{sum(tag_scores.get(tag, 0) for tag in ['行业经验','文案背景','业务单位所在地']):.1f}",
                                        "工作量评分": f"{workload_score:.1f}",
                                        "个人意愿评分": f"{personal_score:.1f}",
                                        # 详细得分计算
                                        "得分计算详情": (
                                            f"国家标签: ({country_score:.1f}) × 0.5 = {country_score * 0.5:.1f}\n"
                                            f"专业标签: ({sum(tag_scores.get(tag, 0) for tag in ['绝对高频专业','相对高频专业','做过专业']):.1f}) × 0.5 = {sum(tag_scores.get(tag, 0) for tag in ['绝对高频专业','相对高频专业','做过专业']) * 0.5:.1f}\n"
                                            f"特殊标签: ({special_score:.1f}) × ({special_match_ratio:.2f}) × ({special_coverage_ratio:.2f}) × 0.5 = {special_score * special_match_ratio * special_coverage_ratio * 0.5:.1f}\n"
                                            f"其他标签: ({sum(tag_scores.get(tag, 0) for tag in ['行业经验','文案背景','业务单位所在地']):.1f}) × 0.5 = {sum(tag_scores.get(tag, 0) for tag in ['行业经验','文案背景','业务单位所在地']) * 0.5:.1f}\n"
                                            f"工作量: ({workload_score:.1f}) × 0.3 = {workload_score * 0.3:.1f}\n"
                                            f"个人意愿: ({personal_score:.1f}) × 0.2 = {personal_score * 0.2:.1f}"
                                        )
                                    }
                                    all_consultants_data.append(consultant_data)
                                
                                # 创建并显示DataFrame
                                df = pd.DataFrame(all_consultants_data)
                                
                                # 设置列的显示顺序
                                columns_order = [
                                    "文案顾问", "总得分", "业务单位", "文案方向", "匹配范围",
                                    "绝对高频国家", "相对高频国家", "做过国家",
                                    "绝对高频专业", "相对高频专业", "做过专业",
                                    "名校专家", "博士成功案例", "低龄留学成功案例",
                                    "行业经验", "文案背景", "业务单位所在地",
                                    "匹配率", "覆盖率",
                                    "国家标签得分", "专业标签得分", "特殊标签得分", "其他标签得分",
                                    "工作量评分", "个人意愿评分",
                                    "得分计算详情"
                                ]
                                
                                # 重新排序列并显示
                                df = df[columns_order]
                                st.dataframe(df, hide_index=True, use_container_width=True)

                        else:
                            st.json(output_dict)
                    except Exception as e:
                        st.error(f"解析输出结果时出错: {str(e)}")
                        st.text_area(
                            "原始输出数据",
                            record[2],
                            height=200,
                            disabled=True,
                            key=f"output_data_{record[0]}"
                        )
        else:
            st.info("暂无历史记录")

if __name__ == "__main__":
    logger.info("开始运行应用")
    main()
    logger.info("应用运行结束")

#streamlit run agent/streamlit_app.py