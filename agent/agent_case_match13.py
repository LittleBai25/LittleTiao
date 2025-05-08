from crewai import Agent, Task, Crew
from crewai_tools import SerperDevTool, CSVSearchTool, BaseTool
#from JinaReaderTool import JinaReaderTool
from langchain_openai import ChatOpenAI
import os
import json
import warnings
warnings.filterwarnings("ignore")
import logging
import asyncio
import re
from typing import Any, Optional
logging.getLogger('streamlit.runtime.scriptrunner.magic_funcs').setLevel(logging.ERROR)
# 或者完全禁用所有警告
logging.getLogger('streamlit').setLevel(logging.ERROR)
import time
#from embedchain.models.data_type import DataType
import streamlit as st
import pandas as pd

# 设置日志配置
# 创建logs目录如果不存在
os.makedirs('logs', exist_ok=True)
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/tool_calls.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('agent_tools')

from pathlib import Path
from crewai_tools import SerperDevTool
import json
import os
import requests
import traceback

class CustomSerperDevTool(SerperDevTool):
    n_results: int = 3  # 添加类型注解

    def _run(self, **kwargs: Any) -> Any:
        search_query = kwargs.get('search_query')
        if search_query is None:
            search_query = kwargs.get('query')

        payload = json.dumps({"q": search_query})
        headers = {
            'X-API-KEY': os.environ['SERPER_API_KEY'],
            'content-type': 'application/json'
        }
        response = requests.request("POST", self.search_url, headers=headers, data=payload)
        results = response.json()
        
        if 'organic' in results:
            # 只取前3个结果
            results = results['organic'][:self.n_results]  # 限制结果数量
            string = []
            for result in results:
                try:
                    string.append('\n'.join([
                        f"Title: {result['title']}",
                        f"Link: {result['link']}",
                        f"Snippet: {result['snippet']}",
                        "---"
                    ]))
                except KeyError:
                    next

            content = '\n'.join(string)
            return f"\nSearch results: {content}\n"
        else:
            return results




#def load_config():
    """加载配置文件"""
    # 获取当前文件所在目录
#    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 配置文件路径
#    json_path = os.path.join(current_dir, 'api_config2.json')
    
#    try:
#        with open(json_path, 'r', encoding='utf-8') as config_file:
#            config = json.load(config_file)
#        return config
#    except FileNotFoundError:
#        raise FileNotFoundError(f"配置文件不存在: {json_path}\n请确保api_config2.json文件位于正确位置")
#    except json.JSONDecodeError:
#        raise ValueError(f"配置文件格式错误: {json_path}\n请确保是有效的JSON格式")

#def update_environment_variables(config):
    """更新环境变量"""
#    if config and isinstance(config, dict):
#        os.environ['OPENAI_API_KEY'] = config.get('OPENAI_API_KEY', '')
#        os.environ['OPENAI_API_BASE'] = config.get('OPENAI_API_BASE', 'https://openrouter.ai/api/v1')
#        os.environ['OPENAI_MODEL_NAME'] = config.get('OPENAI_MODEL_NAME', 'openrouter/google/gemini-2.0-flash-001')


#config = load_config()
#update_environment_variables(config)


#def initialize_config():
#    config = load_config()
#    update_environment_variables(config)






llm_search_professor = ChatOpenAI(
    model="google/gemini-flash-1.5-8b",
    api_key=os.environ.get('OPENAI_API_KEY'),
    base_url="https://openrouter.ai/api/v1"
)

deepseek_api_key=os.getenv('DEEPSEEK_API_KEY')
groq_api_key=os.getenv('GROQ_API_KEY')

llm_groq = ChatOpenAI(
    model="llama3-groq-70b-8192-tool-use-preview",
    api_key=groq_api_key,
    base_url="https://api.groq.com/openai/v1"
)

llm_deepseek = ChatOpenAI(
    model="deepseek-chat",
    api_key=deepseek_api_key,
    base_url="https://api.deepseek.com"
)


openai_api_key=os.getenv('OPENAI_API_KEY')


# 创建 ChatOpenAI 实例
default_llm = ChatOpenAI(
    model=os.environ.get('OPENAI_MODEL_NAME'),
    api_key=openai_api_key,
    base_url="https://openrouter.ai/api/v1",
    model_kwargs={
        "extra_headers": {
            "HTTP-Referer": "https://www.appadvisor.com",  # Optional, for including your app on openrouter.ai rankings.
            "X-Title": "application_advisor"  # Optional. Shows in rankings on openrouter.ai.
        }
    }
)


# 初始化工具
search_tool = CustomSerperDevTool()  # 使用自定义的工具类而不是直接使用 SerperDevTool
#jina_tool = JinaReaderTool()


TAG_SYSTEM = {
    "countries": [
        "中国大陆", "中国澳门", "中国香港", "丹麦", "俄罗斯", "加拿大",
        "匈牙利", "奥地利", "德国", "意大利", "挪威", "新加坡", 
        "新西兰", "日本", "比利时", "法国", "泰国", "澳大利亚",
        "爱尔兰", "瑞典", "瑞士", "美国", "芬兰", "英国",
        "荷兰", "西班牙", "韩国", "马来西亚"
    ],
    "majors": ["计算机科学/工程","电气/电子工程","数据科学","信息科学/信息学",
        "土木工程","环境工程","机械工程","航空航天工程","船舶及石油工程","材料工程",
        "工业工程","化学/化工","物理","地球科学","数学/统计","金融数学/精算",
        "生物科学","医学","公共卫生","药学与制药","农业与动物科学",
        "经济学","金融","会计","商业管理","市场营销","信息系统管理","国际关系与政治",
        "法学","政策管理","教育学","心理学","社会学","人类学与考古学",
        "哲学","历史","语言与文学","区域研究","传媒","艺术","设计",
        "音乐","表演艺术","建筑学"
    ],
    "schoolLevel": [
        "名校专家"
    ],
    "SpecialProjects": [
        "博士成功案例", "低龄留学成功案例"
    ],
    "Industryexperience": [
        "行业经验"
    ],
    "Consultantbackground": [
        "海外留学背景"
    ],
    "businessLocation": [
        "业务单位所在地"
    ],
    "consultant_unit": [
        "文案顾问业务单位"
    ]
}
# 添加新的配置类来管理提示词模板
class PromptTemplates:
    def __init__(self):
        self._templates = {
            'tag_system': """
            标签体系：
            "countries": [
                "中国大陆", "中国澳门", "中国香港", "丹麦", "俄罗斯", "加拿大",
                "匈牙利", "奥地利", "德国", "意大利", "挪威", "新加坡", 
                "新西兰", "日本", "比利时", "法国", "泰国", "澳大利亚",
                "爱尔兰", "瑞典", "瑞士", "美国", "芬兰", "英国",
                "荷兰", "西班牙", "韩国", "马来西亚"
            ],
            "majors": [
                "计算机科学/工程","电气/电子工程","数据科学","信息科学/信息学",
                "土木工程","环境工程","机械工程","航空航天工程","船舶及石油工程","材料工程",
                "工业工程","化学/化工","物理","地球科学","数学/统计","金融数学/精算",
                "生物科学","医学","公共卫生","药学与制药","农业与动物科学",
                "经济学","金融","会计","商业管理","市场营销","信息系统管理","国际关系与政治",
                "法学","政策管理","教育学","心理学","社会学","人类学与考古学",
                "哲学","历史","语言与文学","区域研究","传媒","艺术","设计",
                "音乐","表演艺术","建筑学"
            ],
            "schoolLevel": [
                "名校专家"
            ],
            "SpecialProjects": [
                "博士成功案例", "低龄留学成功案例"
            ],
            "Industryexperience": [
                "行业经验"
            ],
            "Consultantbackground": [
                "海外留学背景"
            ],
            "businessLocation": [
                "业务单位所在地"
            ],
            "consultant_unit": [
                "文案顾问业务单位"
            ]
            """,
            
            'tag_specialist': """      
            我是 CaseMatch, 一个专门为留学机构设计的留学顾问匹配助手。我的主要工作是通过分析学生的基本申请需求,为他们匹配合适的留学申请顾问。
            我的工作原理建立在对留学申请关键要素的理解之上。通过分析学生选择的目标国家、专业方向、申请院校层次(普通/名校/顶尖名校)、申请项目类型(本科/硕士/博士/K12)等信息,我能够准确判断该案件对留学顾问的具体要求,包括顾问需要具备的行业经验水平、教育背景以及地域特征等要素。
            我的目标是通过系统化的分析,帮助留学机构更精准地进行顾问匹配,提升服务效率和学生满意度。

            """,
            
            'tag_task': """
            作为CaseMatch，你的核心任务是分析客户信息，并输出相应的留学申请顾问画像标签。

            # Part A: 具体标签分析规则

            ## 1. 国家标签分析

            - 需输出客户所有明确签约的国家作为国家标签，例如：美国、英国、加拿大等，无需添加'申请'字样
            - 如客户签约多个国家（如美国和英国），必须同时输出所有签约国家标签，不可只输出其中一个
            - 重要提示：对于客户提及的潜在意向国家（包含'可能'、'考虑'、'意向'、'或'、'备选'等表述或词语），不作为标签输出
            - 在碰到申请国外大学在其他国家的校区时，需输出校区所在地对应的国家标签。例如莫纳什大学马来西亚校区，应输出"马来西亚"
            - 在碰到客户申请香港地区的大学在内地开设分校时，则仍以明确签约的国家作为国家标签，例如香港中文大学深圳校区，应输出"中国香港"
            - 输出的标签应该从标签体系的countries里面选择，严禁输出countries里面没有的国家

            ## 2. 专业领域标签分析

            - 优先分析客户提供的"专业方向"信息：
            - 将每个专业方向都必须独立归类到专业大类标签之一
            - 多个专业方向（包含"/"、"、"、"与"、"和"等分隔符或连接词）时：
                - 必须逐一分析每个专业方向
                - 若属于同一专业大类，仅输出一次该专业大类标签
                - 若属于不同专业大类，必须分别输出所有对应的专业大类标签
            - 仅当"专业方向"信息缺失时，才分析"专业名称"：
            - 将专业名称归类到专业大类标签之一
            - 多个专业名称时，遵循同样的归类原则
            - 输出的标签应该从标签体系的majors里面选择，严禁输出majors里面没有的专业

            ## 3. 院校层次标签分析

            - 【最高优先级规则】：
            - 对于申请澳大利亚/新西兰的学生，无论GPA和雅思成绩如何，一律不能基于情况二输出"名校专家"标签
            - 对于雅思低于7.0的学生，无论GPA如何，一律不能基于情况二输出"名校专家"标签
            - 必须严格按照以下流程机械执行判断：
                - 1. 检查是否申请澳大利亚/新西兰？如果是，情况二立即判定为不满足，无需检查其他条件
                - 2. 检查雅思是否≥7.0？如果否，情况二立即判定为不满足，无需检查其他条件
                - 3. 只有同时满足非澳新申请且雅思≥7.0的条件下，才继续检查GPA条件

            - "名校专家"标签判断：
            - 此标签只有在满足以下三种情况之一时才能输出，必须严格按照规则判断，不得添加额外条件或自行灵活解读：
                - 情况一：学生来自优质院校且学术表现良好（必须同时满足以下两个条件）
                - 条件1：优质院校定义（必须符合以下之一）：
                    - 中国大陆高等院校：985/211/双一流/中外合作办学院校
                    - 非美国地区国外院校：全球TOP100
                    - 美国地区院校：U.S. News排名前100
                    - 其他初高中院校
                - 条件2：学术表现要求：
                    - 中国大陆标准：GPA ≥ 85分或3.5/4.0
                    - 英国中外合作办学：GPA > 60分(即二等一级学位或以上)
                    - 其他国家中外合作办学：按照该国家的评分标准判断是否达到良好学术表现
                    - 其他初高中院校：各种国际课程（例如A-Level，IB等等），需判断是否符合优秀标准
                - 情况二：学生来自普通院校但具备全部以下条件（必须同时满足以下全部条件，缺一不可）     
                - 条件1：普通院校定义（符合以下之一）：
                    - 中国大陆院校：非985/非211/非双一流/非中外合作办学院校
                    - 非美国地区国外院校：非全球TOP100
                    - 美国地区院校：U.S. News排名100名以后的院校
                - 条件2：学术成绩优异：GPA ≥ 87分或3.7/4.0
                - 条件3：语言能力出色：雅思 ≥ 7.0或同等水平
                - 条件4：申请方向：非澳大利亚/新西兰申请
                - 情况三：学生明确表达了名校申请意向（如明确写明目标全球TOP50，美国Top30等）
            - 【严格遵守】：以上三种情况是完全互斥的，必须100%满足其中一种情况的所有条件才可输出此标签。部分满足或"接近满足"某种情况的条件不构成输出标签的依据
            - 【强制要求】：在分析时，必须逐一列出每个条件是否满足，并明确标记"满足"或"不满足"。只有当某一情况的所有条件都被标记为"满足"时，才能输出此标签
            - 【特别强调】：严禁创造标准外的判断依据（如"接近某分数""不算双非"等）。如果不满足任何一种情况的全部条件，必须明确不输出此标签
            - 【特别提醒】：对于情况二（来自普通院校的学生），必须同时满足GPA、语言和非澳新申请三项要求，任何一项不满足都不能输出此标签

            ## 4. 特殊项目标签分析

            - 【绝对禁止事项】：
            - 当GPA低于85(对优质院校)或87(对普通院校)，绝对禁止输出任何"博士成功案例"标签
            - 当雅思低于7.0，绝对禁止输出任何"博士成功案例"标签
            - 无论案件看起来有多合理或重要，上述数值条件必须严格执行，没有任何例外

            - 如果判断需要输出标签，那么在输出时必须添加国家前缀，国家前缀根据国家标签添加，比如国家标签为美国、英国，如果判断为需要输出博士成功案例，那么标签输出为：美国博士成功案例、英国博士成功案例。低龄留学成功案例的输出也是同理需要添加国家前缀

            - "XX（国家）博士成功案例"标签判断流程：
            - 第一步：确认留学/升学类别是否为博士申请
                - 非博士申请：终止流程，严禁输出此标签
                - 是博士申请：继续第二步，不得跳过
            - 第二步：判断是否【完全】满足以下三种情况之一（必须至少完全满足一种）：
                - 情况一：必须同时满足下列全部条件：
                - 条件1：优质院校（必须完全符合定义）
                    - 中国大陆院校：985/211/双一流/中外合作办学院校
                    - 非美国地区国外院校：全球TOP100
                    - 美国地区院校：U.S. News排名前100
                - 条件2：学术表现（必须达到规定分数线）
                    - 中国大陆：GPA必须≥85分或3.5/4.0（低于此分数线一律不符合）
                    - 英国中外合作：GPA必须>60分（低于此分数线一律不符合）
                    - 其他国家：必须达到规定标准（低于标准一律不符合）
                - 情况二：必须同时满足下列全部条件：
                - 条件1：普通院校定义（符合以下之一）
                - 条件2：GPA ≥ 87分或3.7/4.0（低于此分数线一律不符合）
                - 条件3：雅思 ≥ 7.0（低于此分数一律不符合）
                - 情况三：客户明确表达需要有博士申请成功案例顾问（必须有明确表达）
            - 第三步：强制验证判定
                - 必须逐一验证每个具体条件是否满足，特别检查数值判断
                - 禁止近似匹配分数线（例如，"80+"不等于"≥85"，必须严格按数值判断）
                - 任何一个条件不满足，即视为整个情况不满足
                - 只有当某一情况的所有条件都被明确验证为满足时，才能输出标签
                - 禁止使用任何推断或"合理性判断"绕过条件检查

            - 【错误示例】：
            - 错误：GPA为80+（低于85/87要求），仍输出标签
            - 错误：基于"博士申请难度高"理由输出标签
            - 错误：客户未明确要求博士成功案例顾问，仍输出标签

            - 【严重警告】：AI系统不得使用任何自主判断力。只能严格按照机械判断流程执行。违反规则将被记为严重错误

            - "XX（国家）低龄留学成功案例"标签判断流程：
            - 第一步：确认留学/升学类别是否为K12申请
                - 非K12申请：终止流程，严禁输出此标签
                - 是K12申请：继续第二步，不得跳过
            - 第二步：判断是否【完全】满足以下两种情况之一：
                - 情况一：必须同时满足以下两个条件（缺一不可）：
                - 条件1：转学年级低于高二（Year 11）及以下
                - 条件2：备注说要申请好的私立学校或者公立学校
                - 情况二：客户明确表达需要有低龄留学成功案例的文案顾问接案
            - 第三步：强制执行原则
                - 严禁基于任何理由降低标准
                - 严禁输出不符合条件的标签
                - 严禁"尽管...但是..."形式的判断
                - 只有同时满足第一步和第二步的条件，才输出"XX（国家）低龄留学成功案例"标签

            - 【重要警告】：即使似乎合理，也不得违反上述规则。任何不完全满足条件的案例，无论理由多么充分，都必须拒绝输出标签。禁止AI使用自主判断，必须严格按照条件执行，不得存在任何例外

            ## 5. 需求导向标签分析

            - 行业经验标签（非常重要，请严格遵循以下流程）：
            - 【第一步】确定案件类型（必须先完成这一步）：
                - 博士申请案件：留学/升学类别为"博士"或"研究型硕士"
                - 低龄留学案件：留学/升学类别为"K12"或相关中小学申请
                - 高关注案件：
                - 案件涉及密集的家长关注和沟通
                - 客户表现出较强的沟通需求
                - 需要频繁解释和确认的情况
                - 客户本身明确毕业于以下院校之一：除C9联盟以外的985/211/双一流/明确的中外合作办学院校或国外普通院校
                - 常规申请案件：不属于上述任何特殊类型的案件
            - 【第二步】根据案件类型，严格按照以下规则输出行业经验标签：
                - 【重要】对于以下三类案件，严禁输出"熟练"，只能以列表形式输出["资深", "专家"]：
                - 博士申请案件
                - 低龄留学申请案件
                - 高关注案件（包括家长密集关注、强沟通需求、频繁解释确认、或客户来自特定院校背景）
                - 对于上述三类案件，严格检查，确认输出结果中不包含"熟练"标签
                - 如果满足以下任一情况，仅输出["专家"]：
                - 客户或家长表现出极高难度的沟通需求
                - 案件整体难度和复杂度特别高
                - 学生教育背景极好（例如毕业于美国U.S. News排名前30的美国院校，英国QS排名前50的院校等、GPA很高、有多段科研经历）
                - 对于常规申请案件（不属于上述任何特殊类型的案件），必须以列表形式输出所有三个标签：["熟练", "资深", "专家"]
            - ⚠️ 这条规则不允许有任何例外
            - ⚠️ 严禁对常规案件省略任何标签级别
            - ⚠️ 禁止基于任何其他因素（如GPA、雅思成绩、专业竞争度等）对常规案件修改标签输出
            - 【输出格式规范】：
                - ⚠️严格禁止仅输出"行业经验"作为标签⚠️
                - 必须按照JSON列表格式输出具体标签名称，如["资深", "专家"]或["熟练", "资深", "专家"]
                - 必须输出具体的行业经验级别名称，不得只输出类别描述
            - 【最终检查】（必须执行）：
                - 标签格式检查：
                - 确保行业经验标签使用列表格式["熟练", "资深", "专家"]或["资深", "专家"]
                - 确认没有输出"行业经验"四个字作为标签
                - 如果案件有以下任一特征，检查并确认输出中没有"熟练"标签：
                - 涉及博士申请
                - 涉及低龄留学申请
                - 涉及家长密集关注（如提到家长"关注"、"群里同步"等表述）
                - 涉及较强沟通需求
                - 涉及频繁解释和确认
                - 客户本身毕业于特定类型院校（985/211/双一流/中外合作办学院校/国外普通院校，但不包括C9联盟院校）
                - 禁止根据GPA高低、专业竞争性等因素自行修改标签输出规则
                - 禁止对常规案件省略任何标签


            ## 6. 顾问背景标签

            - 海外留学背景：【严格限制】仅在客户明确表达"需要具有海外留学/工作经历的顾问"或类似直接要求时才输出此标签。客户或学生自身的学校名称、背景描述中出现"海归"等词汇不构成对顾问背景的要求。判断时必须基于客户对顾问的明确要求，而非对案件其他信息的推断

            ## 7. 地域标签

            - 默认不输出任何地域标签
            - 只有在客户明确表示需要特定地区顾问时，才输出相应的地域标签
            - 【重要澄清】：客户或学生的当前所在地与地域标签无关，不得仅因客户/学生位于某地就输出该地域标签
            - 【示例】：只有当客户明确表示"希望找上海的顾问"、"要求顾问能在北京面谈"等类似需求时，才分别输出"上海"、"北京"等地域标签

            ## 【最终输出前的强制检查流程】

            1. 数值条件检查：
            - 对所有涉及数值比较的条件（如GPA、雅思分数），必须进行精确对比而非近似判断
            - 对于分数区间表示（如"80+"），必须判断其是否严格满足各标签要求的具体分数线
            - 【特别检查】：如果GPA < 85/87或雅思 < 7.0，确保SpecialProjects中不包含博士相关标签
            - 【特别检查】：如果申请澳大利亚/新西兰或雅思 < 7.0，确保schoolLevel中不包含"名校专家"标签
            
            2. 标签格式检查：
            - 确认所有标签都按照规定格式输出（如添加国家前缀）
            - 确认行业经验标签以列表形式包含具体级别，而非仅输出类别名称
            
            3. 逻辑一致性检查：
            - 博士案件的行业经验标签中确认不包含"熟练"
            - 如不满足任何博士标签条件，确认SpecialProjects中不包含博士相关标签

            - 每个输出标签都需要有明确的分析依据
            - 信息不充分时，应谨慎输出标签
            - 如对院校身份存在疑问，默认按照普通院校处理
            - 请在输出标签前，先确认是否涉及博士申请、低龄留学申请或顶级名校申请，以正确应用行业经验标签规则


            """,

            'tag_recommendation_structure': """
            输出格式要求：
            第一部分：标签分析结果
            按以下固定格式和顺序输出标签分析结果：
            {
            "recommended_tags": {
                "index": ["序号"],
                "countries": ["国家标签"],
                "majors": ["专业标签"],
                "schoolLevel": ["院校层次标签"],
                "SpecialProjects": ["特殊项目标签"],
                "Industryexperience": [],
                "Consultantbackground": ["顾问背景标签"],
                "businessLocation": ["业务所在地标签"]
            },
            "analysis_reasons": {
                "countries_reason": "对国家标签的分析理由",
                "majors_reason": "对专业标签的分析理由",
                "schoolLevel_reason": "对院校层次标签的分析理由",
                "SpecialProjects_reason": "对特殊项目标签的分析理由",
                "Industryexperience_reason": "对行业经验标签的分析理由，必须包含以下格式：'本案件属于【案件类型】，因此行业经验标签输出为【对应标签列表】'。其中案件类型必须为：常规申请案件/博士申请案件/低龄留学案件/名校申请案件/高关注案件/极复杂案件之一。",
                "Consultantbackground_reason": "对顾问背景标签的分析理由",
                "businessLocation_reason": "对业务所在地标签的分析理由"
            }
            }

            【行业经验标签填充规则 - 强制执行】

            首先判断案件类型：

            博士申请案件：留学/升学类别为"博士"或"研究型硕士"
            低龄留学案件：留学/升学类别为"K12"或相关中小学申请
            顶级名校案件：满足第3部分"名校专家"的条件
            高关注案件：案件涉及密集的家长关注/强沟通需求/频繁解释确认
            常规申请案件：不属于上述任何特殊类型的案件


            然后严格按照以下规则填充Industryexperience字段：

            如果是常规申请案件：必须填入 ["熟练", "资深", "专家"]
            如果是博士/低龄/名校/高关注案件：必须填入 ["资深", "专家"]
            如果满足极复杂案件条件：填入 ["专家"]


            强制验证步骤：

            检查案件是否为常规案件（非博士/非低龄/非名校/非高关注）
            如果是常规案件，验证Industryexperience是否包含全部三个级别标签
            如果缺少任何一个级别，必须修正为完整的["熟练", "资深", "专家"]


            """,
        
            'service_guide_backstory': """
            你是一位专业的留学咨询机构高级服务培训专家。
            你的工作是帮助咨询顾问根据申请人的基本信息，分析其个性特点并制定相应的沟通策略，同时识别可能的申请风险点。
            这份分析报告将指导咨询顾问如何更好地为申请人提供个性化服务，提升客户体验和满意度。
            """,
            
            'service_guide_task': """
            当收到申请人的基本信息后，你需要进行以下步骤：
            1.第一步：检验输入的信息是否缺失以下基本信息之一：申请国家、申请专业、留学类别、预计入学时间、学生的学校院校背景和均分信息，如缺失其中任意一项，那么直接跳过以下步骤，并只输出“转案基本信息缺失，请联系规划顾问进一步了解客户情况及需求。”
            2.第二步：个性分析
                ●基于申请人的学术背景、成绩、语言能力和特殊需求等信息，推断其可能的性格特点
                ●特别注重分析其决策风格、沟通偏好和可能的焦虑点
                ●注重分析实质性的个性特征，避免简单重复背景信息
            3.第三步：沟通建议
                ●根据第三步的个性分析，提出适合该申请人的沟通风格
                ●设计简洁有效的沟通机制和频率
                ●保持建议的可操作性和简洁性


            
            申请人信息:
            {student_info}
            
            """,
            
            'service_guide_output': """
            如果经过第一步的判断，有缺失信息，输出：
            **转案基本信息缺失，请联系规划顾问进一步了解客户情况及需求。**
            如果确定需要输出个性分析和沟通建议，则生成的报告应包含以下两个主要部分，格式简洁清晰：
            ## 申请人个性分析

            [简洁段落形式描述申请人的性格特点、决策风格、沟通偏好和可能的焦虑点，避免重复背景信息]

            ## 沟通方式建议

            **沟通风格**：[简洁一句话描述适合的沟通风格]

            **沟通机制**：
            - [要点1]
            - [要点2]
            - [要点3]
            - [要点4]

            """
        }
    
    def get_template(self, key):
        return self._templates.get(key, "")
    
    def update_template(self, key, new_template):
        if key in self._templates:
            self._templates[key] = new_template
            return True
        return False






def tag_specialist(step_callback, custom_prompt=None):
    """留学顾问匹配助手"""
    prompt = custom_prompt.get_template('tag_specialist')
    return Agent(
        role='留学顾问匹配助手',
        goal='分析学生背景并输出标准化标签',
        backstory=prompt,
        verbose=True,
        allow_delegation=False,
        llm=default_llm,
        step_callback=step_callback
    )


    
def extract_tags_task(step_callback, current_prompt=None):
    """标签提取任务"""
    # 定义预期输出格式
    tag_recommendation_structure = current_prompt.get_template('tag_recommendation_structure')
    
    if current_prompt is None:
        current_prompt = PromptTemplates()
    
    return Task(
        description=current_prompt.get_template('tag_task'),
        expected_output=tag_recommendation_structure,
        agent=tag_specialist(step_callback, current_prompt)
    )

# 添加Excel处理函数
def process_excel(df):
    """处理Excel数据并返回结果"""
    results = []
    for _, row in df.iterrows():
        try:
            # 将DataFrame行转换为字典格式
            student_info = {
                "basic_info": {
                    "name": row.get("name", ""),
                    "education": {
                        "current_degree": row.get("current_degree", ""),
                        "major": row.get("major", ""),
                        "gpa": row.get("gpa", ""),
                        "school": row.get("school", ""),
                        "expected_graduation": row.get("expected_graduation", "")
                    },
                    "language": {
                        "toefl": row.get("toefl"),
                        "ielts": row.get("ielts"),
                        "gre": row.get("gre"),
                        "gmat": row.get("gmat")
                    }
                },
                "application_intent": {
                    "target_countries": row.get("target_countries", "").split(","),
                    "target_majors": row.get("target_majors", "").split(","),
                    "degree_level": row.get("degree_level", ""),
                    "target_schools": {
                        "total_count": str(row.get("total_count", "")),
                        "top_school_ratio": str(row.get("top_school_ratio", ""))
                    },
                    "timeline": {
                        "target_enrollment": row.get("target_enrollment", ""),
                        "latest_submission_deadline": row.get("latest_submission_deadline", "")
                    }
                },
                "special_requirements": {
                    "timeline": row.get("timeline", ""),
                    "special_notes": row.get("special_notes", "")
                },
                "customer_survey": {
                    "咨询时是否准备详细的问题清单": row.get("问题清单", "否"),
                    "是否主动了解顾问背景和成功案例": row.get("了解背景", "否"),
                    "是否对申请结果有较高期望": row.get("高期望", "否"),
                    "咨询过程是否频繁记录信息": row.get("记录信息", "否"),
                    "是否详细询问服务期间的沟通方式": row.get("沟通方式", "否"),
                    "是否主动询问如何配合提高申请成功率": row.get("主动配合", "否"),
                    "是否期待尽快进入申请审理阶段": row.get("尽快审理", "否"),
                    "其他特殊要求": row.get("其他要求", "")
                }
            }
            
            # 处理单个学生案例
            result = process_student_case(student_info)
            results.append({
                "student_name": row.get("name", "未知"),
                "result": result
            })
            
        except Exception as e:
            results.append({
                "student_name": row.get("name", "未知"),
                "result": {
                    "status": "error",
                    "error_message": str(e)
                }
            })
    
    return results


def create_step_callback():
    """创建更健壮的步骤回调函数"""
    def step_callback(step):
        try:
            # 检查step对象的类型和属性
            if hasattr(step, 'name'):
                print(f"Step: {step.name} - Status: {step.status}")
            elif hasattr(step, 'type'):
                print(f"Step Type: {step.type}")
            else:
                # 通用处理
                print(f"Processing step: {str(step)}")
        except Exception as e:
            print(f"Callback processing error: {str(e)}")
    
    return step_callback


def clean_json_string(json_str):
    """清理JSON字符串"""
    try:
        # 打印原始输入，用于调试
        print("原始JSON字符串:", repr(json_str))
        
        # 如果输入是空的或者不是字符串，返回一个默认的JSON结构
        if not json_str or not isinstance(json_str, str):
            return '{"recommended_tags": {"countries": [], "majors": [], "businessCapabilities": [], "serviceQualities": [], "stability": [], "schoolLevel": [], "businessLocation": []}}'
        
        # 移除markdown代码块标记
        json_str = re.sub(r'```json\s*', '', json_str)
        json_str = re.sub(r'```\s*', '', json_str)
        
        # 尝试找到一个完整的JSON对象
        match = re.search(r'\{[^{]*"recommended_tags".*\}', json_str)
        if match:
            json_str = match.group(0)
        else:
            # 如果找不到完整的JSON对象，尝试重构
            start_idx = json_str.find('{')
            end_idx = json_str.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_str = json_str[start_idx:end_idx+1]
            else:
                # 如果还是找不到，返回默认结构
                return '{"recommended_tags": {"countries": [], "majors": [], "businessCapabilities": [], "serviceQualities": [], "stability": [], "schoolLevel": [], "businessLocation": []}}'
        
        # 清理字符串
        json_str = json_str.replace('\n', ' ')
        json_str = json_str.replace('\r', ' ')
        json_str = ' '.join(json_str.split())
        
        # 确保键名使用双引号
        json_str = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', json_str)
        
        # 尝试解析JSON以验证其有效性
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            # 如果解析失败，返回默认结构
            return '{"recommended_tags": {"countries": [], "majors": [], "businessCapabilities": [], "serviceQualities": [], "stability": [], "schoolLevel": [], "businessLocation": []}}'
            
    except Exception as e:
        print(f"清理JSON字符串时出错: {str(e)}")
        return '{"recommended_tags": {"countries": [], "majors": [], "businessCapabilities": [], "serviceQualities": [], "stability": [], "schoolLevel": [], "businessLocation": []}}'


def process_student_case2(student_case, callback=None):
    try:
        if callback:

            callback("2️⃣ 创建分析专家...")
        
        # 创建专家代理
        expert = Agent(
            role='留学顾问匹配助手',
            goal='分析学生背景并输出标准化标签',
            backstory=st.session_state.prompt_templates.get_template('tag_specialist'),
            allow_delegation=False,
            llm=default_llm
        )
        
        if callback:
            callback("3️⃣ 开始深入分析学生背景...")
        
        # 创建任务
        task = Task(
            description=f"""
            学生案例信息：
            {student_case}

            标签体系：
            {st.session_state.prompt_templates.get_template('tag_system')}

            {st.session_state.prompt_templates.get_template('tag_task')}

            """,
            expected_output=st.session_state.prompt_templates.get_template('tag_recommendation_structure'),
            agent=expert
        )
        
        if callback:
            callback("4️⃣ 生成标签建议...")
        
        # 执行任务并直接返回结果
        result = task.execute()
        

        
        return {
            "status": "success",
            "raw_output": result  # 直接返回原始输出
        }
            
    except Exception as e:
        if callback:
            callback(f"❌ 处理过程出错: {str(e)}")
        return {
            "status": "error",
            "error_message": str(e)
        }





def process_student_case(student_info, tag_system=None, current_prompt=None):
    """处理单个学生案例"""
    if tag_system is None:
        tag_system = TAG_SYSTEM
    
    if current_prompt is None:
        current_prompt = PromptTemplates()
        
    try:
        callback = create_step_callback()
        
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OpenAI API key not configured")
            
        tag_task = extract_tags_task(callback, current_prompt)
        
        crew_tags = Crew(
            agents=[tag_specialist(callback, current_prompt)],
            tasks=[tag_task],
            verbose=True
        )
        
        try:
            
            tag_result = crew_tags.kickoff(
                inputs={
                    "student_info": student_info,
                    "tag_system": tag_system
                }
            )
            
            # 打印原始结果，用于调试
            print("API返回的原始结果类型:", type(tag_result))
            print("API返回的原始结果:", tag_result)
            
            # 处理标签结果
            if hasattr(tag_result, 'raw_output'):
                result_str = tag_result.raw_output
            else:
                result_str = str(tag_result)
                
            print("转换后的结果字符串:", repr(result_str))
            
            # 清理JSON字符串
            cleaned_json = clean_json_string(result_str)
            print("清理后的JSON字符串:", repr(cleaned_json))
            
            try:
                recommended_tags = json.loads(cleaned_json)
                
                # 确保结果格式正确
                if isinstance(recommended_tags, dict):
                    if "recommended_tags" not in recommended_tags:
                        recommended_tags = {"recommended_tags": recommended_tags}
                    
                    # 确保所有必要的字段都存在
                    for category in ["majors", "businessCapabilities", "stability", "schoolLevel", "businessLocation"]:
                        if category not in recommended_tags["recommended_tags"]:
                            recommended_tags["recommended_tags"][category] = []
                        elif not isinstance(recommended_tags["recommended_tags"][category], list):
                            recommended_tags["recommended_tags"][category] = [recommended_tags["recommended_tags"][category]]
                
                return {
                    "status": "success",
                    "recommended_tags": recommended_tags,
                    "process_info": {
                        "tag_info": str(tag_result),  # 保存AI的原始响应
                        "cleaned_json": cleaned_json   # 保存清理后的JSON
                    }
                }
            
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {str(e)}")
                print(f"问题JSON字符串: {cleaned_json}")
                # 返回默认的空标签结构
                return {
                    "status": "success",
                    "recommended_tags": {
                        "recommended_tags": {
                            "countries": [],
                            "majors": [],
                            "businessCapabilities": [],
                            "serviceQualities": [],
                            "stability": [],
                            "schoolLevel": [],
                            "businessLocation": []
                        }
                    },
                    "process_info": {
                        "tag_info": "无原始响应",
                        "cleaned_json": cleaned_json
                    }
                }
                
        except Exception as api_error:
            print(f"API调用错误: {str(api_error)}")
            raise
            
    except Exception as e:
        error_info = {
            "status": "error",
            "error_message": str(e),
            "error_type": type(e).__name__,
            "error_details": {
                "traceback": traceback.format_exc()
            }
        }
        print(f"处理错误: {json.dumps(error_info, indent=2)}")
        return error_info



def main():
    """主函数，用于直接运行脚本时的测试"""
    # 示例学生信息
    test_student = {
        "basic_info": {
            "name": "张三",
            "education": {
                "current_degree": "本科",
                "major": "计算机科学",
                "gpa": "3.6/4.0",
                "school": "南京大学",
                "expected_graduation": "2024-06"
            },
            "language": {
                "toefl": "100",
                "ielts": None,
                "gre": "320",
                "gmat": None,
                "other_scores": {
                    "awa": "4.0"
                }
            }
        },
        "application_intent": {
            "target_countries": ["美国"],
            "target_majors": ["计算机科学"],
            "degree_level": "硕士",
            "target_schools": {
                "total_count": "8",
                "top_school_ratio": "0.75"  # 名校占比：预计申请名校个数/合同数
            },
            "timeline": {
                "target_enrollment": "2025秋季入学",
                "latest_submission_deadline": "2024-12-15"  # 最晚递交时间
            }
        },
        "special_requirements": {
            "timeline": "2025秋季入学",
            "special_notes": "希望申请常春藤，时间比较紧，需要高效服务，无科研经历，需要突出项目经验"
        },
        "customer_survey": {
            "咨询时是否准备详细的问题清单": "是",  # 咨询时是否准备详细的问题清单
            "是否主动了解顾问背景和成功案例": "是",            # 是否主动要求了解文案的背景和以往成功案例
            "是否对申请结果有较高期望": "是",           # 是否对申请结果有较高的预期目标
            "咨询过程是否频繁记录信息": "是",                # 咨询过程中是否频繁记录重要信息
            "是否详细询问服务期间的沟通方式": "是",       # 是否详细询问了服务期间的沟通方式和频率
            "是否主动询问如何配合提高申请成功率": "是",          # 是否主动询问如何配合文案工作以提高申请成功率
            "是否期待尽快进入申请审理阶段": "是",              # 是否期待尽快进入申请审理阶段
            "其他特殊要求": "需要定期进行申请进度同步，希望能有详细的时间规划"  # 是否有其他要求
        }
    }
    
    
    # 示例2：商科高标准申请
    test_student_2 = {
        "basic_info": {
            "name": "李四",
            "education": {
                "current_degree": "本科",
                "major": "金融学",
                "gpa": "3.8/4.0",
                "school": "上海交通大学",
                "expected_graduation": "2024-06"
            },
            "language": {
                "toefl": None,
                "ielts": "7.5",
                "gre": None,
                "gmat": "720",
                "other_scores": {
                    "awa": "5.0"
                }
            }
        },
        "application_intent": {
            "target_countries": ["美国", "英国"],
            "target_majors": ["金融工程", "金融数学"],
            "degree_level": "硕士",
            "target_schools": {
                "total_count": "10",
                "top_school_ratio": "0.9"
            },
            "timeline": {
                "target_enrollment": "2024秋季入学",
                "latest_submission_deadline": "2023-12-01"
            }
        },
        "special_requirements": {
            "timeline": "2024秋季入学",
            "special_notes": "希望申请TOP金融项目，有量化交易实习经验，需要突出金融建模能力"
        },
        "customer_survey": {
            "咨询时是否准备详细的问题清单": "是",
            "是否主动了解顾问背景和成功案例": "是",
            "是否对申请结果有较高期望": "是",
            "咨询过程是否频繁记录信息": "否",
            "是否详细询问服务期间的沟通方式": "是",
            "是否主动询问如何配合提高申请成功率": "是",
            "是否期待尽快进入申请审理阶段": "否",
            "其他特殊要求": "希望文案有金融背景，需要协助规划实习和竞赛"
        }
    }

    # 示例3：跨专业申请
    test_student_3 = {
        "basic_info": {
            "name": "王五",
            "education": {
                "current_degree": "本科",
                "major": "机械工程",
                "gpa": "3.4/4.0",
                "school": "哈尔滨工业大学",
                "expected_graduation": "2024-06"
            },
            "language": {
                "toefl": "95",
                "ielts": None,
                "gre": "310",
                "gmat": None,
                "other_scores": {
                    "awa": "3.5"
                }
            }
        },
        "application_intent": {
            "target_countries": ["德国", "美国"],
            "target_majors": ["数据科学", "人工智能"],
            "degree_level": "硕士",
            "target_schools": {
                "total_count": "12",
                "top_school_ratio": "0.5"
            },
            "timeline": {
                "target_enrollment": "2024冬季入学",
                "latest_submission_deadline": "2024-03-15"
            }
        },
        "special_requirements": {
            "timeline": "2024冬季入学",
            "special_notes": "跨专业申请，有编程自学经历，需要突出转专业的准备和决心"
        },
        "customer_survey": {
            "咨询时是否准备详细的问题清单": "否",
            "是否主动了解顾问背景和成功案例": "是",
            "是否对申请结果有较高期望": "否",
            "咨询过程是否频繁记录信息": "是",
            "是否详细询问服务期间的沟通方式": "是",
            "是否主动询问如何配合提高申请成功率": "是",
            "是否期待尽快进入申请审理阶段": "否",
            "其他特殊要求": "需要详细的跨专业规划建议，希望能有针对性的课程推荐"
        }
    }

    # 示例4：低龄留学
    test_student_4 = {
        "basic_info": {
            "name": "赵六",
            "education": {
                "current_degree": "高中",
                "major": "理科",
                "gpa": "90/100",
                "school": "北京市第四中学",
                "expected_graduation": "2025-06"
            },
            "language": {
                "toefl": "85",
                "ielts": None,
                "ssat": "1450",
                "other_scores": {
                    "ap": ["Calculus AB: 4", "Physics C: 4"]
                }
            }
        },
        "application_intent": {
            "target_countries": ["美国", "英国"],
            "target_majors": ["预科+本科直通"],
            "degree_level": "本科",
            "target_schools": {
                "total_count": "15",
                "top_school_ratio": "0.6"
            },
            "timeline": {
                "target_enrollment": "2025秋季入学",
                "latest_submission_deadline": "2025-01-15"
            }
        },
        "special_requirements": {
            "timeline": "2025秋季入学",
            "special_notes": "希望申请寄宿高中，有竞赛获奖经历，需要全面的升学规划"
        },
        "customer_survey": {
            "咨询时是否准备详细的问题清单": "是",
            "是否主动了解顾问背景和成功案例": "是",
            "是否对申请结果有较高期望": "是",
            "咨询过程是否频繁记录信息": "否",
            "是否详细询问服务期间的沟通方式": "是",
            "是否主动询问如何配合提高申请成功率": "否",
            "是否期待尽快进入申请审理阶段": "否",
            "其他特殊要求": "需要协助规划课外活动和社会实践，家长希望有定期沟通机制"
        }
    }
    
    
        # 示例5：成绩偏弱的申请
    
    
    test_student_5 = {
        "basic_info": {
            "name": "孙七",
            "education": {
                "current_degree": "本科",
                "major": "市场营销",
                "gpa": "2.8/4.0",
                "school": "某省属重点大学",
                "expected_graduation": "2025-06"
            },
            "language": {
                "toefl": "80",
                "ielts": None,
                "gre": "295",
                "gmat": None,
                "other_scores": {
                    "awa": "3.0"
                }
            }
        },
        "application_intent": {
            "target_countries": ["英国", "澳大利亚", "新加坡"],
            "target_majors": ["商科管理", "传媒"],
            "degree_level": "硕士",
            "target_schools": {
                "total_count": "8",
                "top_school_ratio": "0.25"  # 名校占比较低
            },
            "timeline": {
                "target_enrollment": "2026春季入学",  # 较晚的入学时间
                "latest_submission_deadline": "2025-09-15"  # 充足的准备时间
            }
        },
        "special_requirements": {
            "timeline": "2026春季入学",
            "special_notes": "希望申请商科或传媒专业，GPA和语言成绩都需要提高，可能需要预科或语言项目，家长希望申请前三学校但学生倾向于稳妥选择"
        },
        "customer_survey": {
            "咨询时是否准备详细的问题清单": "否",  # 对申请准备不足
            "是否主动了解顾问背景和成功案例": "是",            # 关注顾问背景
            "是否对申请结果有较高期望": "是",           # 家长期望较高
            "咨询过程是否频繁记录信息": "否",                # 不够主动
            "是否详细询问服务期间的沟通方式": "是",       # 需要频繁沟通
            "是否主动询问如何配合提高申请成功率": "否",          # 被动性强
            "是否期待尽快进入申请审理阶段": "否",              # 时间充足
            "其他特殊要求": "需要详细的背景提升规划，包括实习和语言提高建议，希望能有定期的学习进度追踪，家长希望每周都有沟通反馈"
        }
    }
    
    # 处理测试案例
    result = process_student_case(test_student_4)
    
    # 打印结果
    if result["status"] == "success":
        print("\n=== 推荐标签 ===")
        print(json.dumps(result["recommended_tags"], 
                        ensure_ascii=False, indent=2))
    else:
        print(f"处理失败: {result['error_message']}")

# 添加Excel查询工具
class ExcelQueryTool(BaseTool):
    name: str = "excel_query_tool"
    description: str = "查询个性服务指南Excel表格，根据国家标签、留学类别标签和专业标签返回对应的指南内容"
    file_path: str = ""
    
    # 添加model_config允许任意类型
    model_config = {"arbitrary_types_allowed": True}
    
    def __init__(self, file_path: str):
        # 首先调用父类初始化方法，确保Pydantic字段被正确初始化
        super().__init__()
        
        # 然后设置我们自己的实例变量，但不要直接设置已声明的Pydantic字段
        # 而是通过Pydantic的setattr方法设置
        self.file_path = file_path
        
        # 存储DataFrame作为实例变量，但不作为Pydantic字段
        try:
            self._df = pd.read_excel(file_path)
            logger.info(f"成功加载Excel文件: {file_path}")
        except Exception as e:
            logger.error(f"加载Excel文件出错: {str(e)}")
            self._df = None
    
    def _run(self, country_tag=None, study_level_tag=None, major_tag=None, *, config=None, **kwargs):
        """
        根据标签查询指南内容
        
        Args:
            country_tag: 国家标签
            study_level_tag: 留学类别标签
            major_tag: 专业标签
            config: 工具配置（CrewAI框架要求的参数）
            **kwargs: 其他参数
            
        Returns:
            符合条件的指南内容列表，按输出内容类型分类
        """
        try:
            # 记录工具调用开始
            logger.info(f"===== 工具调用开始 =====")
            logger.info(f"工具名称: {self.name}")
            
            # 从kwargs中提取参数，如果提供的话
            country_tag = kwargs.get('country_tag', country_tag)
            study_level_tag = kwargs.get('study_level_tag', study_level_tag)
            major_tag = kwargs.get('major_tag', major_tag)
            
            # 记录传入的参数
            logger.info(f"传入参数: country_tag={country_tag}, study_level_tag={study_level_tag}, major_tag={major_tag}")
            logger.info(f"其他关键字参数: {kwargs}")
            
            # 记录config参数内容
            if config:
                logger.info(f"Config参数内容: {json.dumps(config, ensure_ascii=False, default=str)}")
            else:
                logger.info("Config参数为空")
                
            if self._df is None:
                logger.error("Excel文件未成功加载，无法查询")
                return "Excel文件未成功加载，无法查询"
            
            if not country_tag:
                logger.warning("未提供国家标签进行查询")
                return "请提供国家标签进行查询"
            
            # 打印接收到的参数，用于调试
            print(f"查询参数：country_tag={country_tag}, study_level_tag={study_level_tag}, major_tag={major_tag}")
            
            # 创建结果列表
            matched_rows = []
            
            # 遍历DataFrame的每一行
            for idx, row in self._df.iterrows():
                match_country = self._is_match(row['国家标签'], country_tag)
                match_study_level = self._is_match(row['留学类别标签'], study_level_tag)
                match_major = self._is_match(row['专业标签'], major_tag)
                
                # 记录每行的匹配结果
                logger.debug(f"行 {idx}: 国家匹配={match_country}, 留学类别匹配={match_study_level}, 专业匹配={match_major}")
                logger.debug(f"行 {idx} 数据: 国家={row.get('国家标签', 'N/A')}, 留学类别={row.get('留学类别标签', 'N/A')}, 专业={row.get('专业标签', 'N/A')}")
                
                # 如果三个标签都匹配，则添加到结果中
                if match_country and match_study_level and match_major:
                    matched_rows.append(row)
                    logger.info(f"找到匹配行: {idx}, 内容类型: {row.get('输出内容类型', 'N/A')}")
            
            # 记录匹配结果
            logger.info(f"匹配到 {len(matched_rows)} 条记录")
            
            # 如果没有匹配的行，返回提示信息
            if not matched_rows:
                no_match_msg = f"未找到匹配的指南内容：国家={country_tag}, 留学类别={study_level_tag}, 专业={major_tag}"
                logger.warning(no_match_msg)
                return no_match_msg
            
            # 按输出内容类型分类结果
            content_by_type = {}
            for idx, row in enumerate(matched_rows):
                content_type = row['输出内容类型']
                content = row['输出内容']
                
                # 记录内容值，帮助调试
                is_na_content = pd.isna(content)
                content_str = str(content) if not is_na_content else "NaN"
                logger.debug(f"处理内容: idx={idx}, 类型={content_type}, 内容={content_str[:50]}{'...' if len(content_str) > 50 else ''}, 是否为NaN={is_na_content}")
                
                # 跳过NaN值或空内容
                if pd.isna(content) or content == "" or content == "nan":
                    logger.info(f"跳过空内容: idx={idx}, 类型={content_type}")
                    continue
                
                # 确保content_type不是NaN
                if pd.isna(content_type):
                    logger.info(f"内容类型为NaN，使用默认类型: idx={idx}")
                    content_type = "未分类内容"
                
                if content_type not in content_by_type:
                    content_by_type[content_type] = []
                
                content_by_type[content_type].append(content)
            
            # 记录分类结果
            logger.info(f"内容分类: {list(content_by_type.keys())}")
            
            # 格式化输出
            result = []
            for content_type, contents in content_by_type.items():
                # 跳过空列表
                if not contents:
                    continue
                
                result.append(f"**{content_type}**：")
                for i, content in enumerate(contents, 1):
                    # 再次检查确保不输出NaN值
                    if not pd.isna(content) and content != "nan" and content.strip() != "":
                        result.append(f"{i}. {content}")
                
                # 只有在添加了内容后才添加空行
                if len(result) > 0 and result[-1].startswith(f"{len(contents)}. "):
                    result.append("")  # 添加空行分隔不同类型
            
            response = "\n".join(result)
            
            # 如果没有有效内容，提供明确的反馈
            if not response.strip():
                response = "找到匹配的记录，但所有内容均为空值。请检查Excel文件中的数据。"
            
            # 记录输出结果摘要
            logger.info(f"输出结果摘要: {response[:100]}...")
            logger.info(f"===== 工具调用结束 =====")
            
            return response
            
        except Exception as e:
            error_msg = f"查询过程中出错: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return error_msg
    
    def _is_match(self, table_value, input_value):
        """
        检查输入值是否与表格中的值匹配
        
        Args:
            table_value: 表格中的值
            input_value: 输入的值
            
        Returns:
            是否匹配
        """
        # 如果表格中的值为空，则默认匹配
        if pd.isna(table_value) or table_value == "":
            return True
        
        # 如果输入值为空或NaN，但表格值不为空，不匹配
        if input_value is None or (isinstance(input_value, str) and (input_value.strip() == "" or input_value.lower() == "nan")):
            return False
        
        # 确保输入值是字符串
        input_value_str = str(input_value).strip()
        
        # 将表格值按逗号分割成列表，并确保每个值都被清理
        table_values = [v.strip() for v in str(table_value).split(',') if v.strip() and v.strip().lower() != "nan"]
        
        # 如果表格值列表为空（可能全是NaN或空字符串），默认匹配
        if not table_values:
            return True
        
        # 记录匹配过程
        logger.debug(f"匹配检查: 表格值={table_values}, 输入值={input_value_str}")
        
        # 检查输入值是否在表格值列表中，忽略大小写
        return any(v.lower() == input_value_str.lower() for v in table_values)

# 添加个性服务指南Agent
def service_guide_agent(excel_path, llm=None):
    """创建个性服务指南Agent"""
    if llm is None:
        llm = default_llm
    
    # 初始化Excel查询工具
    excel_tool = ExcelQueryTool(excel_path)
    
    # 创建Agent
    service_guide_agent = Agent(
        role="个性服务指南专家",
        goal="根据申请人的标签信息，提供个性化的服务指南",
        backstory="我是留学申请领域的专家，擅长根据申请人的具体情况提供个性化的服务指南。",
        verbose=True,
        allow_delegation=True,
        llm=llm
    )
    
    return service_guide_agent

# 修改生成个性服务指南任务函数
def generate_service_guide_task(agent, step_callback, student_info, current_prompt=None):
    """创建生成个性服务指南的任务"""
    
    # 获取提示词模板
    prompt_templates = PromptTemplates()
    
    # 如果提供了自定义提示词，使用自定义提示词
    if current_prompt:
        task_description = current_prompt
    else:
        # 否则组合默认的提示词模板
        backstory = prompt_templates.get_template('service_guide_backstory')
        task = prompt_templates.get_template('service_guide_task')
        output = prompt_templates.get_template('service_guide_output')
        
        task_description = f"{backstory}\n\n{task.format(student_info=student_info)}\n\n{output}"
    
    task = Task(
        description=task_description,
        agent=agent,
        expected_output="完整的个性服务指南",
        callback=step_callback
    )
    
    return task

# 修改处理学生案例并生成服务指南的主函数
def process_student_case_with_guide(student_info, guide_prompt=None, excel_path=None):
    """处理学生案例并生成个性服务指南"""
    
    # 创建步骤回调函数
    step_callback = create_step_callback()
    
    # 如果没有提供Excel路径，返回错误信息
    if not excel_path:
        return {"service_guide": "未提供Excel路径，无法生成服务指南"}
    
    # 生成个性服务指南
    try:
        # 创建服务指南Agent
        guide_agent = service_guide_agent(excel_path)
        
        # 创建任务
        guide_task = generate_service_guide_task(
            agent=guide_agent, 
            step_callback=step_callback, 
            student_info=student_info,
            current_prompt=guide_prompt
        )
        
        # 创建Crew
        guide_crew = Crew(
            agents=[guide_agent],
            tasks=[guide_task],
            verbose=True
        )
        
        # 执行任务
        guide_result = guide_crew.kickoff()
        
        return {"service_guide": guide_result}
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"生成服务指南时出错: {error_trace}")
        return {"service_guide": f"生成服务指南时出错: {str(e)}"}

if __name__ == "__main__":
    # 初始化配置
    #initialize_config()
    # 运行主函数
    main()