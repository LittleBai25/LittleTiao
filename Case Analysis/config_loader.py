import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

def load_api_config() -> Dict[str, Any]:
    """
    从api_config.json加载API配置
    
    Returns:
        包含API配置的字典
    """
    try:
        # 首先尝试在当前目录及父目录查找api_config.json
        config_paths = [
            Path("api_config.json"),                # 当前目录
            Path("../api_config.json"),             # 父目录
            Path(__file__).parent / "api_config.json",  # 脚本所在目录
            Path(__file__).parent.parent / "api_config.json",  # 脚本所在目录的父目录
            Path.home() / "api_config.json",        # 用户主目录
            Path("/etc/api_config.json")            # 系统配置目录 (Linux/Mac)
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                print(f"找到配置文件: {config_path}")
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
                    
        print("警告: 未找到api_config.json文件")
        return {}  # 未找到配置文件，返回空字典
        
    except Exception as e:
        print(f"警告: 读取api_config.json时出错: {str(e)}")
        return {} 