 # -*- coding: utf-8 -*-
import pandas as pd
import re
import logging
import os
from typing import List, Dict, Tuple, Any, Optional
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('operation_points_extractor')

class OperationPointsExtractor:
    """
    从用户输入中提取国家、留学类别和专业标签，然后从Excel表格中查询对应的操作要点
    """
    
    def __init__(self, excel_file_path: str):
        """
        初始化提取器
        
        Args:
            excel_file_path: Excel表格文件路径
        """
        self.excel_file_path = excel_file_path
        self._load_excel()
        self._initialize_tag_dictionaries()
        
    def _load_excel(self):
        """加载Excel表格数据"""
        try:
            self._df = pd.read_excel(self.excel_file_path)
            logger.info(f"成功加载Excel文件: {self.excel_file_path}")
        except Exception as e:
            logger.error(f"加载Excel文件出错: {str(e)}")
            self._df = None
            
    def _initialize_tag_dictionaries(self):
        """初始化标签字典"""
        
        # 留学类别标签
        self.study_level_tags = {
            "小学", "初中", "高中", "高中预科", "学前", "证书课程", "语言", "大学预科", "大专文凭", "研究生文凭",
            "硕士预科", "本科文凭", "大学转学分课程","研究生预科", "学士学位", "副学士学位", "博士学位","硕士学位",
            "授课类硕士","研究类硕士"
        }
        
    
        
      
        
            
    def extract_tags_from_text(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        从文本中提取国家、留学类别和专业标签
        
        Args:
            text: 输入文本
            
        Returns:
            包含国家、留学类别和专业标签的元组
        """
        country_tag = None
        study_level_tag = None
        major_tag = None
        

        
        # 查找留学类别标签
        for study_level in self.study_level_tags:
            if study_level in text:
                study_level_tag = study_level
                break
        
                
        logger.info(f"从文本中提取的标签: 国家={country_tag}, 留学类别={study_level_tag}, 专业={major_tag}")
        return country_tag, study_level_tag, major_tag
            
    def get_operation_points(self, text: str,ai_country_tags: List[str] = None, ai_major_tags: List[str] = None) -> str:
        """
        从文本中提取标签并查询对应的操作要点
        
        Args:
            text: 输入文本
            
        Returns:
            操作要点
        """
        try:
            # 从文本中提取标签
            _, study_level_tag, _ = self.extract_tags_from_text(text)

            # 处理国家标签 - 考虑pandas Series的情况
            if isinstance(ai_country_tags, pd.Series):
                country_tags = ai_country_tags.tolist() if not ai_country_tags.empty else []
            elif ai_country_tags is None:
                country_tags = []
            else:
                country_tags = ai_country_tags  # 假设是列表或其他可迭代对象
            
            # 处理专业标签 - 也考虑pandas Series的情况
            if isinstance(ai_major_tags, pd.Series):
                major_tags = ai_major_tags.tolist() if not ai_major_tags.empty else []
            elif ai_major_tags is None:
                major_tags = []
            else:
                major_tags = ai_major_tags  # 假设是列表或其他可迭代对象
        
            
            logger.info(f"使用AI提取的标签: 国家={country_tags}, 专业={major_tags}, 留学类别(正则)={study_level_tag}")
            
            if self._df is None:
                return "Excel文件未成功加载，无法查询操作要点"
            
            # 创建结果列表
            matched_rows = []
            
            # 遍历DataFrame的每一行
            for idx, row in self._df.iterrows():
                # 检查是否有任何一个国家标签匹配
                match_country = any(self._is_match(row['国家标签'], country_tag) for country_tag in country_tags) if country_tags else self._is_match(row['国家标签'], None)
                
                # 检查是否有任何一个专业标签匹配
                match_major = any(self._is_match(row['专业标签'], major_tag) for major_tag in major_tags) if major_tags else self._is_match(row['专业标签'], None)
                
                # 留学类别匹配
                match_study_level = self._is_match(row['留学类别标签'], study_level_tag)
                
                # 记录每行的匹配结果
                logger.debug(f"行 {idx}: 国家匹配={match_country}, 留学类别匹配={match_study_level}, 专业匹配={match_major}")
                
                # 如果三个标签都匹配，则添加到结果中
                if match_country and match_study_level and match_major:
                    matched_rows.append(row)
                    logger.info(f"找到匹配行: {idx}, 内容类型: {row.get('输出内容类型', 'N/A')}")
            
            # 记录匹配结果
            logger.info(f"匹配到 {len(matched_rows)} 条记录")
            
            # 如果没有匹配的行，返回提示信息
            if not matched_rows:
                no_match_msg = f"未找到匹配的操作要点：国家={country_tags}, 留学类别={study_level_tag}, 专业={major_tags}"
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