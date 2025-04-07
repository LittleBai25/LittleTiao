import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

# 导入自定义工具
from pdf_parser import PDFParser
from pdf_offer_parser import PDFOfferParser
from excel_parser import ExcelParser

class SimpleProcessor:
    """简化版处理器 - 不依赖于langchain/langgraph等库"""
    
    def __init__(self):
        """初始化处理器"""
        self.pdf_parser = PDFParser()
        self.offer_parser = PDFOfferParser()
        self.excel_parser = ExcelParser()
        
    def process_resume(self, file_path: str) -> Dict[str, Any]:
        """
        处理简历PDF文件
        
        Args:
            file_path: 简历PDF文件路径
            
        Returns:
            提取的文本内容和处理状态
        """
        print(f"\n=== 处理简历文件: {file_path} ===")
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"文件不存在: {file_path}",
                "content": None
            }
            
        # 使用PDF解析器提取文本
        resume_text = self.pdf_parser.extract_text(file_path)
        
        if resume_text is None:
            return {
                "success": False,
                "error": "无法提取简历文本",
                "content": None
            }
            
        # 构建结果
        result = {
            "success": True,
            "error": None,
            "content": resume_text,
            "file_path": file_path,
            "file_type": "resume"
        }
        
        return result
        
    def process_offer(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        处理多个Offer PDF文件
        
        Args:
            file_paths: Offer PDF文件路径列表
            
        Returns:
            处理结果列表
        """
        print(f"\n=== 处理Offer文件: {len(file_paths)}个 ===")
        
        results = []
        
        for file_path in file_paths:
            print(f"正在处理Offer文件: {file_path}")
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                results.append({
                    "success": False,
                    "error": f"文件不存在: {file_path}",
                    "content": None,
                    "file_path": file_path
                })
                continue
                
            # 使用Offer PDF解析器提取文本
            offer_text = self.offer_parser.extract_text(file_path)
            
            if offer_text is None:
                results.append({
                    "success": False,
                    "error": "无法提取Offer文本",
                    "content": None,
                    "file_path": file_path
                })
                continue
                
            # 构建结果
            result = {
                "success": True,
                "error": None,
                "content": offer_text,
                "file_path": file_path,
                "file_type": "offer"
            }
            
            results.append(result)
            
        return results
        
    def process_excel(self, file_path: str, row_index: Optional[int] = None) -> Dict[str, Any]:
        """
        处理Excel文件
        
        Args:
            file_path: Excel文件路径
            row_index: 要处理的行索引，如果不指定则处理整个文件
            
        Returns:
            处理结果
        """
        print(f"\n=== 处理Excel文件: {file_path} ===")
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"文件不存在: {file_path}",
                "content": None
            }
            
        # 使用Excel解析器提取数据
        if row_index is not None:
            content, total_rows = self.excel_parser.extract_row(file_path, row_index)
            
            if content.startswith("错误:"):
                return {
                    "success": False,
                    "error": content,
                    "content": None,
                    "total_rows": total_rows
                }
                
            result = {
                "success": True,
                "error": None,
                "content": content,
                "file_path": file_path,
                "file_type": "excel",
                "row_index": row_index,
                "total_rows": total_rows
            }
        else:
            content = self.excel_parser.extract_data(file_path)
            
            if content.startswith("错误:"):
                return {
                    "success": False,
                    "error": content,
                    "content": None
                }
                
            result = {
                "success": True,
                "error": None,
                "content": content,
                "file_path": file_path,
                "file_type": "excel"
            }
            
        return result
        
    def save_results(self, results: Dict[str, Any], output_path: str) -> bool:
        """
        保存处理结果到JSON文件
        
        Args:
            results: 处理结果
            output_path: 输出文件路径
            
        Returns:
            是否成功保存
        """
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            # 保存结果
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
                
            print(f"结果已保存到: {output_path}")
            return True
        except Exception as e:
            print(f"保存结果时出错: {str(e)}")
            return False
            
    def save_text(self, text: str, output_path: str) -> bool:
        """
        保存文本内容到文件
        
        Args:
            text: 文本内容
            output_path: 输出文件路径
            
        Returns:
            是否成功保存
        """
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            # 保存文本
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
                
            print(f"文本已保存到: {output_path}")
            return True
        except Exception as e:
            print(f"保存文本时出错: {str(e)}")
            return False

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='简化版文件处理工具 - 不依赖于langchain/langgraph等库')
    
    # 添加子命令
    subparsers = parser.add_subparsers(dest='command', help='要执行的命令')
    
    # Resume处理命令
    resume_parser = subparsers.add_parser('resume', help='处理简历PDF文件')
    resume_parser.add_argument('file_path', help='简历PDF文件路径')
    resume_parser.add_argument('--output', '-o', help='输出文件路径')
    
    # Offer处理命令
    offer_parser = subparsers.add_parser('offer', help='处理Offer PDF文件')
    offer_parser.add_argument('file_paths', nargs='+', help='Offer PDF文件路径列表')
    offer_parser.add_argument('--output', '-o', help='输出文件路径')
    
    # Excel处理命令
    excel_parser = subparsers.add_parser('excel', help='处理Excel文件')
    excel_parser.add_argument('file_path', help='Excel文件路径')
    excel_parser.add_argument('--row', '-r', type=int, help='要处理的行索引')
    excel_parser.add_argument('--output', '-o', help='输出文件路径')
    
    # 综合处理命令
    combined_parser = subparsers.add_parser('combined', help='综合处理简历和Offer文件')
    combined_parser.add_argument('--resume', '-r', required=True, help='简历PDF文件路径')
    combined_parser.add_argument('--offers', '-o', nargs='+', help='Offer PDF文件路径列表')
    combined_parser.add_argument('--excel', '-e', help='Excel文件路径')
    combined_parser.add_argument('--output', help='输出文件路径')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    processor = SimpleProcessor()
    
    if args.command == 'resume':
        # 处理简历
        result = processor.process_resume(args.file_path)
        
        # 输出结果
        if result['success']:
            print("\n=== 简历处理成功 ===")
            print(f"提取文本长度: {len(result['content'])}")
            
            # 保存结果
            if args.output:
                if args.output.endswith('.json'):
                    processor.save_results(result, args.output)
                else:
                    processor.save_text(result['content'], args.output)
        else:
            print(f"\n=== 简历处理失败: {result['error']} ===")
            
    elif args.command == 'offer':
        # 处理Offer
        results = processor.process_offer(args.file_paths)
        
        # 统计成功和失败数量
        success_count = sum(1 for r in results if r['success'])
        
        # 输出结果
        print(f"\n=== Offer处理完成: {success_count}/{len(results)}个成功 ===")
        
        # 保存结果
        if args.output:
            if args.output.endswith('.json'):
                processor.save_results(results, args.output)
            else:
                # 保存所有成功提取的文本
                combined_text = "\n\n".join([r['content'] for r in results if r['success']])
                processor.save_text(combined_text, args.output)
                
    elif args.command == 'excel':
        # 处理Excel
        result = processor.process_excel(args.file_path, args.row)
        
        # 输出结果
        if result['success']:
            print("\n=== Excel处理成功 ===")
            if 'row_index' in result:
                print(f"提取第 {result['row_index']+1} 行数据，共 {result['total_rows']} 行")
            
            # 保存结果
            if args.output:
                if args.output.endswith('.json'):
                    processor.save_results(result, args.output)
                else:
                    processor.save_text(result['content'], args.output)
        else:
            print(f"\n=== Excel处理失败: {result['error']} ===")
            
    elif args.command == 'combined':
        # 综合处理简历和Offer
        combined_results = {
            "resume": None,
            "offers": [],
            "excel": None
        }
        
        # 处理简历
        if args.resume:
            resume_result = processor.process_resume(args.resume)
            combined_results["resume"] = resume_result
            
        # 处理Offer
        if args.offers:
            offer_results = processor.process_offer(args.offers)
            combined_results["offers"] = offer_results
            
        # 处理Excel
        if args.excel:
            excel_result = processor.process_excel(args.excel)
            combined_results["excel"] = excel_result
            
        # 输出综合结果
        print("\n=== 综合处理完成 ===")
        if combined_results["resume"] and combined_results["resume"]["success"]:
            print("简历处理成功")
        
        if combined_results["offers"]:
            success_count = sum(1 for r in combined_results["offers"] if r['success'])
            print(f"Offer处理完成: {success_count}/{len(combined_results['offers'])}个成功")
            
        if combined_results["excel"] and combined_results["excel"]["success"]:
            print("Excel处理成功")
            
        # 保存结果
        if args.output:
            processor.save_results(combined_results, args.output)
    else:
        print("请指定要执行的命令: resume, offer, excel 或 combined")
        
if __name__ == "__main__":
    main() 