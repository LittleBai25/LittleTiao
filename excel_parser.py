import pandas as pd
import numpy as np
import os
from typing import Dict, Any, List, Optional, Tuple, Union

class ExcelParser:
    """Excel文件解析工具"""
    
    def __init__(self):
        """初始化Excel解析器"""
        pass
        
    def extract_data(self, excel_path: str, sheet_name: Optional[str] = None) -> str:
        """
        从Excel文件中提取数据
        
        Args:
            excel_path: Excel文件路径
            sheet_name: 工作表名称，如果不指定则读取第一个工作表
            
        Returns:
            提取的文本内容，格式化为便于处理的文本
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(excel_path):
                return f"错误: 文件不存在 - {excel_path}"
                
            # 检查文件扩展名
            _, ext = os.path.splitext(excel_path)
            if ext.lower() not in ['.xls', '.xlsx', '.xlsm', '.csv']:
                return f"错误: 不支持的文件类型 - {ext}"
            
            # 对CSV文件特殊处理
            if ext.lower() == '.csv':
                df = pd.read_csv(excel_path)
                text_content = self._dataframe_to_text(df)
                return text_content
            
            # 读取Excel文件
            try:
                if sheet_name:
                    df = pd.read_excel(excel_path, sheet_name=sheet_name)
                else:
                    # 尝试列出所有工作表
                    excel_file = pd.ExcelFile(excel_path)
                    sheet_names = excel_file.sheet_names
                    
                    if not sheet_names:
                        return "错误: Excel文件中没有找到工作表"
                    
                    # 默认使用第一个工作表
                    df = pd.read_excel(excel_path, sheet_name=sheet_names[0])
                    
                    # 如果只读取了表头，尝试读取其他工作表
                    if len(df) == 0 and len(sheet_names) > 1:
                        for name in sheet_names[1:]:
                            temp_df = pd.read_excel(excel_path, sheet_name=name)
                            if len(temp_df) > 0:
                                df = temp_df
                                break
            except Exception as e:
                return f"读取Excel文件时出错: {str(e)}"
            
            # 检查DataFrame是否为空
            if len(df) == 0 or len(df.columns) == 0:
                return "错误: Excel文件中没有数据"
                
            # 将DataFrame转换为文本格式
            text_content = self._dataframe_to_text(df)
            
            return text_content
        except Exception as e:
            return f"解析Excel数据时出错: {str(e)}"
    
    def extract_row(self, excel_path: str, row_index: int = 0, sheet_name: Optional[str] = None) -> Tuple[str, int]:
        """
        从Excel文件中提取指定行的数据
        
        Args:
            excel_path: Excel文件路径
            row_index: 要提取的行索引（0表示第一行数据，不含表头）
            sheet_name: 工作表名称，如果不指定则读取第一个工作表
            
        Returns:
            (提取的文本内容，总行数) 元组
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(excel_path):
                return f"错误: 文件不存在 - {excel_path}", 0
                
            # 检查文件扩展名
            _, ext = os.path.splitext(excel_path)
            if ext.lower() not in ['.xls', '.xlsx', '.xlsm', '.csv']:
                return f"错误: 不支持的文件类型 - {ext}", 0
            
            # 读取Excel文件
            df = None
            try:
                if ext.lower() == '.csv':
                    df = pd.read_csv(excel_path)
                elif sheet_name:
                    df = pd.read_excel(excel_path, sheet_name=sheet_name)
                else:
                    # 尝试列出所有工作表
                    excel_file = pd.ExcelFile(excel_path)
                    sheet_names = excel_file.sheet_names
                    
                    if not sheet_names:
                        return "错误: Excel文件中没有找到工作表", 0
                    
                    # 默认使用第一个工作表
                    df = pd.read_excel(excel_path, sheet_name=sheet_names[0])
            except Exception as e:
                return f"读取Excel文件时出错: {str(e)}", 0
            
            # 检查DataFrame是否为空
            if df is None or len(df) == 0 or len(df.columns) == 0:
                return "错误: Excel文件中没有数据", 0
                
            # 检查行索引是否有效
            total_rows = len(df)
            if row_index < 0 or row_index >= total_rows:
                return f"错误: 行索引 {row_index} 超出范围，文件共有 {total_rows} 行数据", total_rows
                
            # 提取指定行
            row_df = df.iloc[[row_index]]
            
            # 将单行数据转换为文本格式
            text_content = self._row_to_text(row_df, row_index)
            
            return text_content, total_rows
        except Exception as e:
            return f"解析Excel行数据时出错: {str(e)}", 0
    
    def _row_to_text(self, row_df: pd.DataFrame, row_index: int) -> str:
        """
        将单行DataFrame转换为文本格式
        
        Args:
            row_df: 包含单行数据的DataFrame
            row_index: 原始数据中的行索引
            
        Returns:
            文本表示
        """
        text_lines = []
        
        # 添加基本信息
        text_lines.append(f"Excel数据 - 第 {row_index+1} 行:")
        text_lines.append(f"列名: {', '.join(row_df.columns.astype(str))}")
        text_lines.append("")
        
        # 处理行数据
        row = row_df.iloc[0]  # 获取第一行（唯一的一行）
        for col_name in row_df.columns:
            value = row[col_name]
            # 跳过NaN值
            if pd.notna(value):
                # 处理各种数据类型
                if isinstance(value, (int, float)):
                    if value == int(value):  # 检查是否为整数值的浮点数
                        formatted_value = str(int(value))
                    else:
                        formatted_value = str(value)
                elif isinstance(value, (np.integer, np.floating)):
                    if value == int(value):
                        formatted_value = str(int(value))
                    else:
                        formatted_value = str(value)
                elif isinstance(value, (list, dict)):
                    # 转换复杂类型为字符串
                    formatted_value = str(value)
                else:
                    formatted_value = str(value)
                    
                text_lines.append(f"  {col_name}: {formatted_value}")
        
        return "\n".join(text_lines)
    
    def _dataframe_to_text(self, df: pd.DataFrame) -> str:
        """
        将DataFrame转换为文本格式
        
        Args:
            df: Pandas DataFrame对象
            
        Returns:
            文本表示，每行是"列名: 值"的格式
        """
        try:
            text_lines = []
            
            # 添加列名作为标题
            text_lines.append("Excel数据内容：")
            text_lines.append(f"总行数: {len(df)}")
            text_lines.append(f"列名: {', '.join(df.columns.astype(str))}")
            text_lines.append("")
            
            # 处理每一行数据
            for idx, row in df.iterrows():
                text_lines.append(f"行 {idx+1}:")
                for col_name in df.columns:
                    value = row[col_name]
                    # 跳过NaN值
                    if pd.notna(value):
                        # 处理各种数据类型
                        if isinstance(value, (int, float)):
                            if value == int(value):  # 检查是否为整数值的浮点数
                                formatted_value = str(int(value))
                            else:
                                formatted_value = str(value)
                        elif isinstance(value, (np.integer, np.floating)):
                            if value == int(value):
                                formatted_value = str(int(value))
                            else:
                                formatted_value = str(value)
                        elif isinstance(value, (list, dict)):
                            # 转换复杂类型为字符串
                            formatted_value = str(value)
                        else:
                            formatted_value = str(value)
                            
                        text_lines.append(f"  {col_name}: {formatted_value}")
                        
                text_lines.append("")  # 空行分隔每行数据
                
                # 如果数据量太大，只展示前20行
                if idx >= 19 and len(df) > 20:
                    text_lines.append(f"... 已省略剩余 {len(df) - 20} 行数据 ...")
                    break
                    
            return "\n".join(text_lines)
        except Exception as e:
            return f"格式化DataFrame时出错: {str(e)}" 