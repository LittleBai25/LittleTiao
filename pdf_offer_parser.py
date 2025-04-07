from typing import Optional
import pdfplumber
from pathlib import Path
import os

class PDFOfferParser:
    """Offer PDF解析工具 - 提取文本供处理"""
    
    def __init__(self):
        pass
        
    def extract_text(self, pdf_path: str) -> Optional[str]:
        """
        从Offer PDF文件中提取文本
        
        Args:
            pdf_path: PDF文件路径或临时文件标识符
            
        Returns:
            提取的文本内容,失败则返回None
        """
        try:
            print(f"开始解析Offer PDF文件: {pdf_path}")
            
            # 添加临时文件查找逻辑
            file_path = self._find_pdf_file(pdf_path)
            if not file_path:
                print(f"找不到PDF文件: {pdf_path}")
                return None
            
            pdf_path = str(file_path)  # 确保路径是字符串类型
            
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    # 提取文本
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                        
                # 清理文本
                text = self._clean_text(text)
                
                print(f"Offer PDF解析完成,提取文本长度: {len(text)}")
                return text
                
        except Exception as e:
            print(f"Offer PDF解析失败: {str(e)}")
            return None
    
    def _find_pdf_file(self, file_identifier: str) -> Optional[Path]:
        """
        查找PDF文件的实际位置
        
        Args:
            file_identifier: 文件标识符(可能是路径或临时ID)
            
        Returns:
            文件路径，找不到则返回None
        """
        # 如果是有效路径则直接返回
        path = Path(file_identifier)
        if path.exists() and path.is_file():
            return path
        
        # 尝试在常见位置查找文件
        possible_locations = [
            Path.cwd() / file_identifier,  # 当前目录
            Path.cwd() / f"{file_identifier}.pdf",  # 添加扩展名
            Path.cwd() / "public" / file_identifier,  # public目录
            Path.cwd() / "public" / f"{file_identifier}.pdf",
            Path.cwd() / "temp_files" / file_identifier,  # 临时文件目录
            Path.cwd() / "public" / "temp" / file_identifier,  # public/temp目录
            Path.cwd() / "tmp" / file_identifier,  # tmp目录
            Path("/tmp") / file_identifier  # Linux/MacOS临时目录
        ]
        
        # 如果是临时文件ID，尝试更多组合
        if file_identifier.startswith("temp_"):
            temp_dirs = [
                Path.cwd() / "temp_files",
                Path.cwd() / "public" / "temp",
                Path.cwd() / "tmp",
                Path("/tmp")
            ]
            
            for temp_dir in temp_dirs:
                if temp_dir.exists():
                    # 查找所有以该ID开头的文件
                    for file_path in temp_dir.glob(f"{file_identifier}*"):
                        if file_path.is_file():
                            print(f"找到匹配的临时文件: {file_path}")
                            return file_path
        
        # 检查所有可能的位置
        for location in possible_locations:
            if location.exists() and location.is_file():
                print(f"找到文件: {location}")
                return location
        
        # 都找不到
        return None
            
    def _clean_text(self, text: str) -> str:
        """
        清理提取的文本
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        if not text:
            return ""
            
        # 1. 删除多余的空白字符
        text = " ".join(text.split())
        
        # 2. 替换特殊字符
        text = text.replace("\x00", "")
        
        # 3. 确保段落之间有空行
        text = text.replace("。", "。\n")
        text = text.replace(".", ".\n")
        
        # 4. 删除重复的换行
        while "\n\n\n" in text:
            text = text.replace("\n\n\n", "\n\n")
            
        return text.strip() 