from typing import Optional
import pdfplumber
from pathlib import Path

class PDFParser:
    """PDF解析工具 - 提取文本供处理"""
    
    def __init__(self):
        pass
        
    def extract_text(self, pdf_path: str) -> Optional[str]:
        """
        从PDF文件中提取文本
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            提取的文本内容，如果失败则返回None
        """
        try:
            print(f"开始处理PDF文件: {pdf_path}")
            
            if not Path(pdf_path).exists():
                print(f"PDF文件不存在: {pdf_path}")
                return None
                
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    # 调整提取参数
                    page_text = page.extract_text(
                        x_tolerance=1,  # 增加水平容差
                        y_tolerance=1,  # 增加垂直容差
                        layout=True,    # 保持布局
                        keep_blank_chars=True,  # 保留空格
                        use_text_flow=True,     # 使用文本流
                    ) or ""
                    text += page_text + "\n"  # 每页之间添加换行
                    
            if not text.strip():
                print(f"PDF文件内容为空: {pdf_path}")
                return None
                
            # 调用清理文本的方法
            text = self._clean_text(text)
                
            print(f"成功提取PDF文本，长度: {len(text)}")
            return text
            
        except Exception as e:
            print(f"处理PDF文件时出错: {str(e)}")
            return None
            
    def _clean_text(self, text: str) -> str:
        """
        清理提取的文本，保持简单
        """
        if not text:
            return ""
            
        # 1. 分割成行处理
        lines = text.split("\n")
        cleaned_lines = []
        
        for line in lines:
            # 跳过空行
            if not line.strip():
                cleaned_lines.append("")
                continue
                
            # 处理每行文本，确保词之间有空格
            words = [w for w in line.split() if w]
            if words:
                cleaned_lines.append(" ".join(words))
        
        # 2. 重新组合文本
        text = "\n".join(cleaned_lines)
        
        # 3. 确保段落标题前后有空行
        section_headers = [
            "EDUCATION",
            "EXPERIENCE",
            "INTERNSHIP",
            "PROJECT",
            "PUBLICATION",
            "SKILLS",
            "AWARDS",
            "ACTIVITIES",
            "EXTRACURRICULAR"
        ]
        
        for header in section_headers:
            text = text.replace(header, f"\n\n{header}\n")
            
        # 4. 规范化空行
        while "\n\n\n" in text:
            text = text.replace("\n\n\n", "\n\n")
            
        return text.strip() 