import os
import sys
import json
import asyncio
from pathlib import Path
from processor import SimpleProcessor
from llm_processor import LLMProcessor
from config_loader import load_api_config
from qs_usnews_school_dict import qs_school_ranking, usnews_school_ranking

def calculate_student_tags(student_data):
    """
    基于学生数据计算适用的标签(tags)
    
    此函数根据学生的学术成绩、录取学校和奖学金情况，判断学生是否符合以下标签：
    - 奖学金：学生获得了任何形式的奖学金
    - 低分逆袭：学生GPA或语言成绩偏低，但被排名前100的大学录取
    - 低龄留学：学生被K12级别的学校录取
    
    Args:
        student_data (dict): 包含学生信息的字典(处理后的数据)，包括:
            - gpaValue: GPA成绩值
            - testScores: 考试成绩列表
            - admissions: 录取学校列表
        
    Returns:
        str or None: 加号分隔的标签字符串，如果没有任何适用标签则返回None
    """
    # 存储识别出的所有适用标签
    tags = []
    
    # 提取关键数据，用于后续标签判断
    resume_data = student_data.get("resume_analysis", {})
    education = resume_data.get("education", {})
    gpa_value = education.get("gpaValue")  # 从education中获取GPA成绩
    test_scores = resume_data.get("testScores", [])  # 从resume_analysis中获取语言和标准化考试成绩
    
    # 从offer_analyses中提取admissions信息
    admissions = []
    for offer in student_data.get("offer_analyses", []):
        admissions.extend(offer.get("admissions", []))
    
    #--------------------------------------------------
    # 1. 判断'奖学金'标签
    #--------------------------------------------------
    # 只要任何一所学校提供了奖学金，就添加"奖学金"标签
    has_scholarship = False
    for adm in admissions:
        # 检查hasScholarship字段为true或scholarshipAmount字段非空
        if adm.get("hasScholarship") == True or adm.get("scholarshipAmount"):
            has_scholarship = True
            break
    
    if has_scholarship:
        tags.append("奖学金")
    
    #--------------------------------------------------
    # 2. 判断'低分逆袭'标签
    #--------------------------------------------------
    # 低分逆袭需要同时满足两个条件：1) 成绩较低 2) 录取学校排名好
    low_score = False  # 标记成绩是否较低
    good_ranking = False  # 标记是否有排名好的学校录取
    
    # 2.1 检查GPA是否低于3.2
    if gpa_value and isinstance(gpa_value, (int, float, str)):
        try:
            # 尝试将GPA转换为浮点数进行比较
            gpa = float(gpa_value)
            if gpa < 3.2:  # GPA低于3.2被视为"低分"
                low_score = True
        except (ValueError, TypeError):
            pass  # 忽略无法转换为数字的GPA
    
    # 2.2 检查语言成绩是否低
    for test in test_scores:
        test_name = test.get("testName", "").lower()  # 获取考试名称并转小写
        test_score = test.get("testScore")  # 获取考试分数
        
        if test_score and isinstance(test_score, (int, float, str)):
            try:
                # 处理可能的格式: "总分: 88"或直接数字
                score_str = str(test_score)
                # 如果包含冒号，提取冒号后的数字部分
                score_val = float(score_str.split(":")[-1].strip() if ":" in score_str else score_str)
                
                # 检查托福分数是否低于90
                if ("托福" in test_name or "toefl" in test_name) and score_val < 90:
                    low_score = True
                # 检查雅思分数是否低于6.5
                elif ("雅思" in test_name or "ielts" in test_name) and score_val < 6.5:
                    low_score = True
            except (ValueError, TypeError):
                pass  # 忽略无法解析的分数
    
    # 2.3 检查是否有排名前100的学校录取
    for adm in admissions:
        ranking = adm.get("rankingValue")  # 获取学校排名
        if ranking and isinstance(ranking, (int, float, str)):
            try:
                # 尝试将排名转换为浮点数
                rank_val = float(ranking)
                if rank_val < 100:  # 排名小于100被视为"好学校"
                    good_ranking = True
                    break
            except (ValueError, TypeError):
                pass  # 忽略无法转换为数字的排名
    
    # 如果同时满足"成绩较低"和"学校排名好"两个条件，添加"低分逆袭"标签
    if low_score and good_ranking:
        tags.append("低分逆袭")
    
    #--------------------------------------------------
    # 3. 判断'低龄留学'标签
    #--------------------------------------------------
    # K12相关的关键词列表，用于识别K12学校
    k12_keywords = ["K12", "k12", "High School", "high school", "Middle School", 
                   "middle school", "小学", "中学", "高中", "Elementary", "Secondary",
                   "Preparatory", "Prep", "Academy", "Day School", "Grammar School", 
                   "Primary", "Junior"]
    
    # "The X School"模式的正则表达式
    the_x_school_pattern = r"^the\s+[\w\s\-']+\s+school$"
    
    has_k12_school = False
    
    # 遍历所有录取学校
    for adm in admissions:
        # 首先检查是否为OTHER类型 - 这是K12学校的必要条件
        if adm.get("degreeType") == "OTHER":
            # 获取学校名称和项目名称
            school = str(adm.get("school", "")).lower()
            program = str(adm.get("program", "")).lower()
            
            # 方法1: 检查学校名称或项目名称中是否包含K12相关关键词
            for keyword in k12_keywords:
                if keyword.lower() in school or keyword.lower() in program:
                    has_k12_school = True
                    break
            
            # 如果关键词检查没有找到匹配，尝试其他模式匹配
            if not has_k12_school:
                # 方法2: 检查是否符合"The X School"模式且不含"University"或"College"
                if (school.startswith("the ") and school.endswith(" school") and 
                    "university" not in school and "college" not in school):
                    has_k12_school = True
                
                # 方法3: 检查degreeType为OTHER，同时也缺少排名信息和专业具体信息可能是K12
                elif (adm.get("degreeType") == "OTHER" and 
                     (not adm.get("rankingValue") or not adm.get("rankingType")) and
                     (program == "专业未定" or program == "无专业" or "general" in program.lower())):
                    has_k12_school = True
            
            # 如果已确定是K12学校，添加标签并跳出循环
            if has_k12_school:
                tags.append("低龄留学")
                break
    
    # 返回结果：如果有标签则返回加号分隔的标签字符串，否则返回None
    return "+".join(tags) if tags else None

def enrich_school_rankings(analysis_data):
    """
    基于学校名称和排名类型，自动填充rankingValue和rankingTier字段
    
    Args:
        analysis_data (dict): 包含学生信息的字典(LLM处理后的数据)
    
    Returns:
        dict: 更新后的分析数据，包含填充后的排名信息
    """
    # 检查输入是否有效
    if not analysis_data or not isinstance(analysis_data, dict):
        return analysis_data
    
    # 从offer_analyses中提取admissions信息
    offer_analyses = analysis_data.get("offer_analyses", [])
    
    # 遍历所有offer和admission记录
    for offer in offer_analyses:
        admissions = offer.get("admissions", [])
        for admission in admissions:
            # 只处理rankingValue为空的记录
            if not admission.get("rankingValue"):
                school_name = admission.get("school", "")
                ranking_type = admission.get("rankingType", "")
                
                # 根据rankingType选择对应的排名字典
                if ranking_type == "QS":
                    ranking_dict = qs_school_ranking
                elif ranking_type == "US News":
                    ranking_dict = usnews_school_ranking
                else:
                    # 如果没有明确的排名类型，跳过处理
                    continue
                
                # 在排名字典中查找学校
                ranking = None
                for rank, name in ranking_dict.items():
                    # 使用部分匹配，因为学校名称可能不完全一致
                    if school_name.lower() in name.lower() or name.lower() in school_name.lower():
                        ranking = rank
                        break
                
                # 如果找到排名，则更新rankingValue和rankingTier
                if ranking:
                    admission["rankingValue"] = str(ranking)
                    
                    # 设置rankingTier
                    if ranking <= 5:
                        admission["rankingTier"] = "TOP5"
                    elif ranking <= 10:
                        admission["rankingTier"] = "TOP10"
                    elif ranking <= 30:
                        admission["rankingTier"] = "TOP30"
                    elif ranking <= 50:
                        admission["rankingTier"] = "TOP50"
                    elif ranking <= 100:
                        admission["rankingTier"] = "TOP100"
    
    return analysis_data

def main():
    """测试LLM处理器与简化版处理器的集成"""
    print("=== 测试LLM处理器与简化版处理器的集成 ===")
    
    # 加载配置
    config = load_api_config()
    
    # 检查API配置
    if not config or "OPENAI_API_KEY" not in config:
        print("警告: 配置文件中未找到OPENAI_API_KEY")
        print("尝试从环境变量获取...")
        
        # 尝试从环境变量获取
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("错误: 未能获取API密钥，请确保api_config.json包含OPENAI_API_KEY或设置环境变量")
            return
    
    # 创建处理器实例
    processor = SimpleProcessor()
    
    # 创建LLM处理器实例
    try:
        llm_processor = LLMProcessor()
        print("LLM处理器初始化成功")
    except ValueError as e:
        print(f"LLM处理器初始化失败: {e}")
        return
    
    # 获取当前目录及其父目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    
    # 查找工作目录中的PDF文件
    pdf_files = []
    for root, dirs, files in os.walk(os.path.join(parent_dir, 'simple_processor')):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    
    if not pdf_files:
        print("未找到PDF文件，请确保文件夹中包含PDF文件")
        return
    
    # 显示找到的文件
    print(f"\n找到 {len(pdf_files)} 个PDF文件:")
    for i, file in enumerate(pdf_files):
        print(f"{i+1}. {file}")
    
    # 如果找到多个文件，让用户选择
    selected_resume = None
    selected_offer = None
    
    if len(pdf_files) == 1:
        # 只有一个文件，将其作为简历处理
        print("\n只找到一个PDF文件，将其作为简历处理")
        selected_resume = pdf_files[0]
    else:
        # 有多个文件，让用户选择
        print("\n请选择简历文件(输入编号):")
        try:
            resume_index = int(input("> ")) - 1
            if 0 <= resume_index < len(pdf_files):
                selected_resume = pdf_files[resume_index]
                
                print("\n请选择Offer文件(输入编号，或输入0跳过):")
                offer_index = int(input("> ")) - 1
                if 0 <= offer_index < len(pdf_files) and offer_index != resume_index:
                    selected_offer = pdf_files[offer_index]
            else:
                print("输入的编号无效，将只处理简历文件")
                selected_resume = pdf_files[0] if pdf_files else None
        except ValueError:
            print("输入无效，将只处理第一个PDF文件作为简历")
            selected_resume = pdf_files[0] if pdf_files else None
    
    # 处理简历
    if selected_resume:
        print(f"\n=== 处理简历文件: {selected_resume} ===")
        resume_result = processor.process_resume(selected_resume)
        
        if resume_result["success"]:
            print("简历文本提取成功")
            print(f"提取文本长度: {len(resume_result['content'])}")
            print("\n文本预览(前200字符):")
            print(resume_result["content"][:200] + "...")
            
            # 使用LLM处理简历文本
            print("\n=== 使用LLM分析简历 ===")
            resume_analysis = llm_processor.analyze_resume(resume_result["content"])
            
            # 检查是否有错误
            if "error" in resume_analysis:
                print(f"LLM分析失败: {resume_analysis.get('error')}")
                if "details" in resume_analysis:
                    print(f"详细信息: {resume_analysis.get('details')}")
            else:
                print("LLM分析成功，结果如下:")
                # 使用ensure_ascii=False确保中文字符正确显示
                result_str = json.dumps(resume_analysis, ensure_ascii=False, indent=2)
                print(result_str)
                
                # 保存分析结果
                output_file = os.path.join(current_dir, "resume_analysis.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result_str)
                print(f"\n分析结果已保存到: {output_file}")
        else:
            print(f"简历处理失败: {resume_result['error']}")
    
    # 处理Offer
    if selected_offer:
        print(f"\n=== 处理Offer文件: {selected_offer} ===")
        offer_result = processor.process_resume(selected_offer)  # 使用resume方法提取文本
        
        if offer_result["success"]:
            print("Offer文本提取成功")
            print(f"提取文本长度: {len(offer_result['content'])}")
            print("\n文本预览(前200字符):")
            print(offer_result["content"][:200] + "...")
            
            # 使用LLM处理Offer文本
            print("\n=== 使用LLM分析Offer ===")
            offer_analysis = llm_processor.analyze_offer(offer_result["content"])
            
            # 检查是否有错误
            if "error" in offer_analysis:
                print(f"LLM分析失败: {offer_analysis.get('error')}")
                if "details" in offer_analysis:
                    print(f"详细信息: {offer_analysis.get('details')}")
            else:
                print("LLM分析成功，结果如下:")
                # 使用ensure_ascii=False确保中文字符正确显示
                result_str = json.dumps(offer_analysis, ensure_ascii=False, indent=2)
                print(result_str)
                
                # 保存分析结果
                output_file = os.path.join(current_dir, "offer_analysis.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result_str)
                print(f"\n分析结果已保存到: {output_file}")
        else:
            print(f"Offer处理失败: {offer_result['error']}")

async def test_async_processing():
    """测试异步并行处理简历和Offer文件"""
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 创建处理器实例
    processor = SimpleProcessor()
    llm_processor = LLMProcessor()
    
    # 寻找样本文件
    pdf_files = []
    for file in os.listdir(current_dir):
        if file.lower().endswith('.pdf'):
            pdf_files.append(os.path.join(current_dir, file))
    
    # 显示找到的文件
    print(f"\n找到 {len(pdf_files)} 个PDF文件:")
    for i, file in enumerate(pdf_files):
        print(f"{i+1}. {file}")
    
    # 如果找到多个文件，让用户选择
    selected_resume = None
    selected_offers = []
    
    if len(pdf_files) == 1:
        # 只有一个文件，将其作为简历处理
        print("\n只找到一个PDF文件，将其作为简历处理")
        selected_resume = pdf_files[0]
    else:
        # 有多个文件，让用户选择
        print("\n请选择简历文件(输入编号):")
        try:
            resume_index = int(input("> ")) - 1
            if 0 <= resume_index < len(pdf_files):
                selected_resume = pdf_files[resume_index]
                
                print("\n请选择一个或多个Offer文件(输入编号，用逗号分隔，如'1,3,4'，或输入0跳过):")
                offer_input = input("> ")
                if offer_input != "0":
                    offer_indices = [int(idx.strip()) - 1 for idx in offer_input.split(",")]
                    for idx in offer_indices:
                        if 0 <= idx < len(pdf_files) and idx != resume_index:
                            selected_offers.append(pdf_files[idx])
            else:
                print("输入的编号无效，将只处理简历文件")
                selected_resume = pdf_files[0] if pdf_files else None
        except ValueError:
            print("输入无效，将只处理第一个PDF文件作为简历")
            selected_resume = pdf_files[0] if pdf_files else None
    
    if not selected_resume:
        print("未选择任何简历文件，退出测试")
        return
    
    # 提取简历文本
    print(f"\n=== 提取简历文本: {selected_resume} ===")
    resume_result = processor.process_resume(selected_resume)
    
    if not resume_result["success"]:
        print(f"简历处理失败: {resume_result['error']}")
        return
    
    print("简历文本提取成功")
    print(f"提取文本长度: {len(resume_result['content'])}")
    
    # 提取所有Offer文本
    offer_texts = []
    for offer_file in selected_offers:
        print(f"\n=== 提取Offer文本: {offer_file} ===")
        offer_result = processor.process_resume(offer_file)  # 使用resume方法提取文本
        
        if offer_result["success"]:
            print(f"Offer文本提取成功，长度: {len(offer_result['content'])}")
            offer_texts.append(offer_result["content"])
        else:
            print(f"Offer处理失败: {offer_result['error']}")
    
    # 如果没有有效的Offer文本，则只处理简历
    if not offer_texts:
        print("\n=== 没有有效的Offer文本，只处理简历 ===")
        # 使用异步方法处理简历
        resume_analysis = await llm_processor.analyze_resume_async(resume_result["content"])
        print("\n简历分析结果:")
        print(json.dumps(resume_analysis, ensure_ascii=False, indent=2))
        return
    
    # 使用异步方法并行处理简历和所有Offer
    print("\n=== 开始异步并行处理简历和所有Offer ===")
    start_time = asyncio.get_event_loop().time()
    
    combined_result = await llm_processor.process_documents(
        resume_text=resume_result["content"],
        offer_texts=offer_texts
    )
    
    elapsed = asyncio.get_event_loop().time() - start_time
    print(f"\n异步处理完成! 总耗时: {elapsed:.2f}秒")
    
    # 打印结果
    print("\n=== 简历分析结果 ===")
    print(json.dumps(combined_result["resume_analysis"], ensure_ascii=False, indent=2))
    
    print("\n=== Offer分析结果 ===")
    for i, offer_analysis in enumerate(combined_result["offer_analyses"]):
        print(f"\nOffer #{i+1} 分析结果:")
        print(json.dumps(offer_analysis, ensure_ascii=False, indent=2))
    
    # 增强学校排名信息
    combined_result = enrich_school_rankings(combined_result)
    
    # 计算标签
    tags = calculate_student_tags(combined_result)
    combined_result["tags"] = tags
    print(f"\n添加标签: {tags}")
    
    # 保存结果
    output_file = os.path.join(current_dir, "combined_analysis.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(combined_result, f, ensure_ascii=False, indent=2)
    print(f"\n组合分析结果已保存到: {output_file}")

if __name__ == "__main__":
    # 根据命令行参数选择运行同步或异步版本
    if len(sys.argv) > 1 and sys.argv[1] == "--async":
        print("运行异步版本的测试...")
        asyncio.run(test_async_processing())
    else:
        print("运行同步版本的测试...")
        main() 
        
# 运行方式
#    python test_llm.py --async  # 异步模式
#    python test_llm.py          # 同步模式