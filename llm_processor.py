import os
import json
import requests
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from config_loader import load_api_config
import re

class LLMProcessor:
    """简单的LLM处理器 - 使用OpenAI API直接与LLM交互"""
    
    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None, model_name: Optional[str] = None):
        """
        初始化LLM处理器
        
        Args:
            api_key: OpenAI API密钥，如果为None则尝试从环境变量OPENAI_API_KEY或api_config.json获取
            api_base: API基础URL，如果为None则尝试从api_config.json获取，否则使用OpenAI默认URL
            model_name: 模型名称，如果为None则尝试从api_config.json获取，否则使用gpt-3.5-turbo
        """
        # 加载配置
        config = load_api_config()
        
        # 设置API密钥
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or config.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("未提供API密钥，且环境变量OPENAI_API_KEY和api_config.json中均未设置")
        
        # 设置API基础URL
        self.api_base = api_base or config.get("OPENAI_API_BASE") or "https://api.openai.com/v1"
        
        # 设置模型名称
        self.model_name = model_name or config.get("OPENAI_MODEL_NAME") or config.get("OPENAI_MODEL") or "gpt-3.5-turbo"
        
        # 检查是否使用OpenRouter
        self.is_openrouter = "openrouter.ai" in self.api_base
        
        print(f"LLM配置: API基础URL={self.api_base}, 模型={self.model_name}")
        print(f"使用OpenRouter API: {self.is_openrouter}")
        
    def analyze_resume(self, resume_text: str) -> Dict[str, Any]:
        """
        分析简历文本
        
        Args:
            resume_text: 提取的简历文本
            
        Returns:
            分析结果，包含结构化的简历信息
        """
        # 调用同步方法
        return self._call_llm(self._get_resume_prompt(resume_text))
    
    async def analyze_resume_async(self, resume_text: str) -> Dict[str, Any]:
        """
        异步分析简历文本
        
        Args:
            resume_text: 提取的简历文本
            
        Returns:
            分析结果，包含结构化的简历信息
        """
        # 调用异步方法
        return await self._call_llm_async(self._get_resume_prompt(resume_text))
    
    def _get_resume_prompt(self, resume_text: str) -> str:
        """生成简历分析提示词"""
        return f"""You are an expert at extracting information from resumes.
        
Given the text content of a resume, extract and format the following information as a JSON object.
You must respond with ONLY the JSON object, no other text.

{{
    "studentName": "只写姓氏首字母+同学，比如'Z同学'",
    "education": {{
        "institution": "学校名称(用中文,如:'北京大学')",
        "major": "专业名称(用中文,如:'计算机科学与技术')",
        "gpaValue": "GPA成绩(数字格式,如:3.38)",
        "gpaOriginal": "原始GPA格式(如:'3.38/4.0')",
         "institutionType": "院校类型(枚举值:'DOMESTIC_C9','DOMESTIC_985','DOMESTIC_211','DOMESTIC_COOPERATIVE','OVERSEAS_UNIVERSITY','DOMESTIC_UNIVERSITY','HONGKONG_MACAO_TAIWAN', 'OVERSEAS_K12','DOMESTIC_K12')"
    }},
    "testScores": [ 
        {{
            "testType": "LANGUAGE or STANDARDIZED or OTHER",
            "testName": "考试名称",
            "testScore": "总分",
            "detailScores": {{
                "分项名称": "分项分数"
            }}
        }}
    ],
    "experiences": [
        {{
            "type": "INTERNSHIP/RESEARCH/COMPETITION/OTHER",
            "description": "一句话概述经历类型和性质",
            "organization": "机构档次描述",
            "role": "担任角色(必填,如果简历中未明确说明,请根据工作内容推断)",
            "duration": "持续时间",
            "achievement": "成果描述"
        }}
    ]
}}

Resume text:
{resume_text}

Please return only the JSON format analysis result without additional explanation text.
"""
        
    def analyze_offer(self, offer_text: str) -> Dict[str, Any]:
        """
        分析Offer文本
        
        Args:
            offer_text: 提取的Offer文本
            
        Returns:
            分析结果，包含结构化的Offer信息
        """
        # 调用同步方法
        return self._call_llm(self._get_offer_prompt(offer_text))
    
    async def analyze_offer_async(self, offer_text: str) -> Dict[str, Any]:
        """
        异步分析Offer文本
        
        Args:
            offer_text: 提取的Offer文本
            
        Returns:
            分析结果，包含结构化的Offer信息
        """
        # 调用异步方法
        return await self._call_llm_async(self._get_offer_prompt(offer_text))
    
    def _get_offer_prompt(self, offer_text: str) -> str:
        """生成Offer分析提示词"""
        return f"""You are an expert at extracting information from university admission offer letters and gathering additional program information.
        
Follow these steps exactly:
1. First analyze the offer letter text to extract basic information
2. Extract rankings if mentioned in the text
3. Combine all information into a JSON response

The response must be a valid JSON object with this exact structure:
{{
    "admissions": [
        {{
            "school": "the full university name in English",
            "country": "学校所在国家(用中文,如:'美国'/'英国'/'新加坡')",
            "program": "the full program name in English",
            "majorCategory": "专业类别(用中文,如:'计算机科学'/'工商管理'/'数据科学')",
            "degreeType": "UNDERGRADUATE/MASTER/PHD/OTHER",
            "rankingType": "排名类型(需要综合排名,美国学校用'US News',其他用'QS')",
            "rankingValue": "排名数值",
            "rankingTier": "排名层级,例如：TOP100/TOP50/TOP30/TOP20/TOP10",
            "enrollmentSeason": "入学季节(如：Spring/Fall/Summer/Winter 2025)",
            "hasScholarship": true/false,
            "scholarshipAmount": "奖学金金额(包含年度信息,如:'$7,000/year'/'￥50,000/semester')",
            "scholarshipNote": "额外的奖学金说明(如获奖原因、续期条件等)"
        }}
    ]
}}

Offer letter text:
{offer_text}

Please return only the JSON format analysis result without additional explanation text.
"""
    
    async def process_documents(self, resume_text: str, offer_texts: list) -> Dict[str, Any]:
        """
        异步处理所有文档
        
        Args:
            resume_text: 简历文本
            offer_texts: Offer文本列表
            
        Returns:
            包含简历和所有Offer分析结果的字典
        """
        # 创建任务列表
        tasks = [
            self.analyze_resume_async(resume_text)
        ]
        
        # 添加所有offer分析任务
        for offer_text in offer_texts:
            tasks.append(self.analyze_offer_async(offer_text))
        
        # 并行执行所有任务
        results = await asyncio.gather(*tasks)
        
        # 构建结果字典
        combined_result = {
            "resume_analysis": results[0],
            "offer_analyses": results[1:] if len(results) > 1 else []
        }
        
        return combined_result
        
    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """
        同步调用LLM API
        
        Args:
            prompt: 提示文本
            
        Returns:
            LLM响应的JSON对象
        """
        headers = {
            "Content-Type": "application/json; charset=utf-8",  # 显式指定UTF-8编码
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 添加OpenRouter特有的headers
        if self.is_openrouter:
            headers["HTTP-Referer"] = "https://localhost"  # OpenRouter需要的refer头
            headers["X-Title"] = "ResumeAnalyzer"  # 应用标题
        
        # 准备请求数据和API端点
        data, api_endpoint = self._prepare_request_data(prompt)
        
        try:
            # 打印请求信息
            print(f"调用LLM API: {api_endpoint}")
            print(f"使用模型: {self.model_name}")
            
            # 显式将数据转换为UTF-8编码的JSON字符串
            json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            
            # 使用data参数而不是json参数来发送请求
            response = requests.post(
                api_endpoint,
                headers=headers,
                data=json_data,  # 使用data参数传递UTF-8编码的JSON
                timeout=60
            )
            
            # 处理响应
            return self._process_response(response)
                
        except requests.exceptions.Timeout:
            return {"error": "API请求超时"}
        except requests.exceptions.ConnectionError:
            return {"error": "无法连接到API服务器"}
        except Exception as e:
            return {"error": f"调用LLM API时出错: {str(e)}"}
    
    async def _call_llm_async(self, prompt: str) -> Dict[str, Any]:
        """
        异步调用LLM API
        
        Args:
            prompt: 提示文本
            
        Returns:
            LLM响应的JSON对象
        """
        headers = {
            "Content-Type": "application/json; charset=utf-8",  # 显式指定UTF-8编码
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 添加OpenRouter特有的headers
        if self.is_openrouter:
            headers["HTTP-Referer"] = "https://localhost"  # OpenRouter需要的refer头
            headers["X-Title"] = "ResumeAnalyzer"  # 应用标题
        
        # 准备请求数据和API端点
        data, api_endpoint = self._prepare_request_data(prompt)
        
        try:
            # 打印请求信息
            print(f"异步调用LLM API: {api_endpoint}")
            print(f"使用模型: {self.model_name}")
            
            # 显式将数据转换为UTF-8编码的JSON字符串
            json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            
            # 异步发送请求
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    api_endpoint,
                    headers=headers,
                    data=json_data,  # 使用data参数传递UTF-8编码的JSON
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    # 处理响应
                    if response.status != 200:
                        return {
                            "error": f"API请求失败: HTTP {response.status}",
                            "details": await response.text()
                        }
                    
                    # 解析JSON
                    result = await response.json()
                    print(f"API响应状态: {response.status}")
                    
                    # 从结果中提取内容
                    content = self._extract_content_from_result(result)
                    
                    # 处理内容
                    if content is None:
                        return {
                            "error": "无法从响应中提取内容",
                            "raw_response": "响应格式异常"
                        }
                    
                    # 解析JSON内容
                    return self._parse_content_to_json(content)
                
        except asyncio.TimeoutError:
            return {"error": "API请求超时"}
        except aiohttp.ClientError:
            return {"error": "无法连接到API服务器"}
        except Exception as e:
            return {"error": f"调用LLM API时出错: {str(e)}"}
    
    def _prepare_request_data(self, prompt: str) -> tuple:
        """准备请求数据和API端点"""
        if self.is_openrouter:
            # OpenRouter特定格式
            data = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "response_format": {"type": "json_object"}
            }
            
            # 确定API端点
            if self.api_base.endswith('/v1'):
                api_endpoint = f"{self.api_base}/chat/completions"
            else:
                api_endpoint = self.api_base
        else:
            # 标准OpenAI格式
            data = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "response_format": {"type": "json_object"}
            }
            api_endpoint = f"{self.api_base}/chat/completions"
        
        return data, api_endpoint
    
    def _process_response(self, response) -> Dict[str, Any]:
        """处理HTTP响应"""
        # 检查HTTP错误
        if response.status_code != 200:
            return {
                "error": f"API请求失败: HTTP {response.status_code}",
                "details": response.text
            }
        
        # 解析JSON
        result = response.json()
        print(f"API响应状态: {response.status_code}")
        
        # 从结果中提取内容
        content = self._extract_content_from_result(result)
        
        # 处理内容
        if content is None:
            return {
                "error": "无法从响应中提取内容",
                "raw_response": "响应格式异常"
            }
        
        # 解析JSON内容
        return self._parse_content_to_json(content)
    
    def _extract_content_from_result(self, result) -> Optional[str]:
        """从API响应结果中提取内容"""
        content = None
        
        # 1. 标准OpenAI格式
        if "choices" in result and len(result["choices"]) > 0:
            if "message" in result["choices"][0]:
                content = result["choices"][0]["message"].get("content")
            elif "text" in result["choices"][0]:
                content = result["choices"][0].get("text")
        
        # 2. OpenRouter特定格式
        if content is None and "output" in result:
            content = result.get("output", {}).get("content")
        
        # 3. 直接查找内容
        if content is None and "content" in result:
            content = result.get("content")
        
        # 4. 检查response字段
        if content is None and "response" in result:
            content = result.get("response")
        
        return content
    
    def _parse_content_to_json(self, content: str) -> Dict[str, Any]:
        """解析内容为JSON"""
        try:
            parsed_json = json.loads(content)
            print("成功解析JSON响应")
            return parsed_json
        except json.JSONDecodeError:
            # 尝试从文本中提取JSON
            print("尝试从文本中提取JSON")
            extracted_json = self._extract_json_from_text(content)
            try:
                parsed_json = json.loads(extracted_json)
                print("成功提取并解析JSON")
                return parsed_json
            except Exception as e:
                return {
                    "error": "无法将LLM响应解析为JSON",
                    "raw_content": "格式无效"
                }
    
    def _extract_json_from_text(self, text: str) -> str:
        """从文本中提取JSON部分"""
        if text is None:
            return "{}"
        
        # 方法1: 寻找```json ... ``` 格式的代码块
        json_code_block_pattern = re.compile(r'```(?:json)?\s*\n(.*?)\n```', re.DOTALL)
        matches = json_code_block_pattern.findall(text)
        
        if matches:
            # 找到了代码块，尝试解析最后一个（通常是修正后的）
            for potential_json in reversed(matches):
                try:
                    # 尝试解析找到的代码块
                    json.loads(potential_json.strip())
                    print("从代码块中提取到有效JSON")
                    return potential_json.strip()
                except json.JSONDecodeError:
                    # 这个代码块不是有效JSON，继续尝试
                    continue
        
        # 方法2: 寻找文本中的JSON格式内容 (使用正则表达式查找嵌套的{}结构)
        try:
            # 特殊情况：如果文本中有多个无嵌套的JSON对象，找出最长的一个
            json_pattern = re.compile(r'(\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\})')
            json_candidates = json_pattern.findall(text)
            
            if json_candidates:
                # 按长度排序，优先尝试最长的可能JSON
                json_candidates.sort(key=len, reverse=True)
                
                for candidate in json_candidates:
                    try:
                        json.loads(candidate)
                        print(f"从正则表达式找到有效JSON，长度：{len(candidate)}")
                        return candidate
                    except:
                        continue
        except Exception as e:
            print(f"正则提取JSON发生错误: {str(e)}")
        
        # 方法3: 寻找第一个{和最后一个}，提取中间部分
        start = text.find("{")
        end = text.rfind("}")
        
        if start != -1 and end != -1 and end > start:
            try:
                json_text = text[start:end+1]
                # 验证提取的内容是否可以解析为JSON
                json.loads(json_text)
                print(f"从文本中提取到完整JSON，长度: {len(json_text)}")
                return json_text
            except json.JSONDecodeError:
                # 尝试进一步处理和修复JSON
                pass
        
        # 方法4: 尝试通过行解析来提取JSON结构
        lines = text.split('\n')
        json_lines = []
        json_started = False
        
        for line in lines:
            line = line.strip()
            if not json_started and line.startswith('{'):
                json_started = True
                json_lines.append(line)
            elif json_started:
                json_lines.append(line)
                if line.endswith('}'):
                    # 可能找到了完整的JSON
                    try:
                        json_text = '\n'.join(json_lines)
                        json.loads(json_text)
                        print(f"通过逐行解析找到有效JSON，长度: {len(json_text)}")
                        return json_text
                    except:
                        # 继续寻找结束括号
                        continue
        # 返回空JSON对象作为后备
        print("无法提取有效JSON，返回空对象")
        return "{}"
    