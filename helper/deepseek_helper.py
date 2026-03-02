import os
import json
import re
import requests
import pandas as pd
import PyPDF2
import docx
from typing import Dict, Any, Optional, Union
from io import BytesIO
import time

class DeepSeekHelper:
    """
    DeepSeek API 助手类
    支持普通对话和读取本地文件内容后以特定格式嵌入提示词的对话
    """

    def __init__(self, api_key: str = None):
        """
        初始化助手类
        
        Args:
            api_key: DeepSeek API 密钥，若不提供则从环境变量 DEEPSEEK_API_KEY 读取
        """
        self._api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self._api_key:
            raise ValueError("请提供 API 密钥或设置环境变量 DEEPSEEK_API_KEY")
        
        # DeepSeek 聊天接口地址（请以官方文档为准）
        self._chat_url = "https://api.deepseek.com/chat/completions"

    def chat(self, input_text: str, system_prompt: str = "You are a helpful assistant", **kwargs) -> Dict[str, Any]:
        """
        普通对话（无文件）
        
        Args:
            input_text: 用户输入
            system_prompt: 系统提示词
            **kwargs: 其他传递给 API 的参数（如 temperature, max_tokens 等）
        
        Returns:
            API 返回的完整响应（JSON 格式）
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}"
        }
        data = {
            "model": "deepseek-chat",  # 或 "deepseek-reasoner"
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_text}
            ],
            **kwargs
        }
        return self._call_chat_api(data, headers)

    def chat_with_files(self, file_paths_and_descs: Dict[str, str], input_text: str,
                        system_prompt: str = "You are a helpful assistant", **kwargs) -> Dict[str, Any]:
        """
        带文件的对话：读取文件内容并按照官方模板构造 prompt
        
        Args:
            file_paths_and_descs: 字典，键为文件路径，值为文件描述（可选，可用于辅助说明）
            input_text: 用户问题
            system_prompt: 系统提示词
            **kwargs: 其他传递给 API 的参数
        
        Returns:
            API 返回的完整响应（JSON 格式）
        """
        if not file_paths_and_descs:
            raise ValueError("至少提供一个文件路径")

        # 1. 构建符合官方推荐的 prompt
        full_prompt = ""
        for file_path, description in file_paths_and_descs.items():
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 读取文件内容（根据类型提取文本）
            file_content = self._extract_text_from_file(file_path)
            file_name = os.path.basename(file_path)
            
            # 附加描述（如果有）
            if description:
                full_prompt += f"[文件描述]: {description}\n"
            
            # 官方推荐格式
            full_prompt += f"[文件名称]: {file_name}\n"
            full_prompt += f"[文件内容开始]\n"
            full_prompt += f"{file_content}\n"
            full_prompt += f"[文件内容结束]\n\n"
        
        # 添加用户问题
        full_prompt += input_text

        # 2. 调用 API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}
            ],
            "temperature": kwargs.get("temperature", 0.6),  # 官方推荐值
            **kwargs
        }
        return self._call_chat_api(data, headers)

    def _extract_text_from_file(self, file_path: str) -> str:
        """
        根据文件扩展名提取文本内容（支持常见格式）
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            elif ext == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    # 格式化 JSON 以便阅读
                    data = json.load(f)
                    return json.dumps(data, ensure_ascii=False, indent=2)
            
            elif ext in ['.xlsx', '.xls']:
                # 读取 Excel 所有工作表为文本
                df_dict = pd.read_excel(file_path, sheet_name=None)
                texts = []
                for sheet_name, df in df_dict.items():
                    texts.append(f"工作表: {sheet_name}")
                    texts.append(df.to_string(index=False))
                return "\n".join(texts)
            
            elif ext == '.pdf':
                # 提取 PDF 文本
                text = ""
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text += page.extract_text() or ""
                return text
            
            elif ext == '.docx':
                # 提取 Word 文档
                doc = docx.Document(file_path)
                return "\n".join([para.text for para in doc.paragraphs])
            
            elif ext == '.csv':
                # 读取 CSV 为文本
                df = pd.read_csv(file_path)
                return df.to_string(index=False)
            
            else:
                # 对于其他二进制文件，尝试以 utf-8 读取，忽略错误
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
        
        except Exception as e:
            raise IOError(f"读取文件 {file_path} 失败: {str(e)}")

    def _call_chat_api(self, data: Dict, headers: Dict, max_retries: int = 3) -> Dict[str, Any]:
        """
        内部方法：调用聊天 API 并处理响应（带重试机制）
        """
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self._chat_url,
                    headers=headers,
                    json=data,
                    timeout=300  # 5分钟，大文件可能需要更长时间
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout:
                if attempt == max_retries - 1:
                    raise IOError("聊天请求超时，请稍后重试")
                time.sleep(2 ** attempt)  # 指数退避
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    # 尝试提取服务器返回的错误信息
                    error_detail = ""
                    if e.response is not None:
                        try:
                            error_detail = e.response.json()
                        except:
                            error_detail = e.response.text
                    raise IOError(f"网络请求失败: {str(e)} - {error_detail}")
                time.sleep(2 ** attempt)
        
        # 不应该执行到这里
        raise IOError("未知错误")

    def _extract_json_payload(self, result: Union[Dict[str, Any], str]) -> Union[Dict[str, Any], list]:
        """
        从 API result 中提取 JSON（支持 ```json 代码块）
        """
        if isinstance(result, dict):
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            content = str(result)

        if not content:
            raise ValueError("result 中没有可解析的 content")

        text = content.strip()
        block = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.IGNORECASE | re.DOTALL)
        if block:
            text = block.group(1).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        first_obj = text.find("{")
        first_arr = text.find("[")
        indexes = [idx for idx in [first_obj, first_arr] if idx != -1]
        if not indexes:
            raise ValueError("content 不是合法 JSON，且未找到 JSON 起始符号")

        trimmed = text[min(indexes):]
        return json.loads(trimmed)

    def export_result_to_excel(self, result: Union[Dict[str, Any], str], output_path: str = "./output/result_converted.xlsx") -> str:
        """
        将 result 中必要内容导出到 Excel
        - Cases: 用例基础信息
        - Preconditions: 前置条件
        - Steps: 步骤
        - Postconditions: 后置条件
        """
        payload = self._extract_json_payload(result)
        cases = payload if isinstance(payload, list) else [payload]

        case_rows = []
        precondition_rows = []
        step_rows = []
        postcondition_rows = []

        for case in cases:
            meta = case.get("meta", {})
            case_id = meta.get("id", "")
            case_name = meta.get("name", "")
            priority = meta.get("priority", "")
            tags = meta.get("tags", [])
            if isinstance(tags, list):
                tags = ", ".join([str(tag) for tag in tags])

            case_rows.append({
                "case_id": case_id,
                "case_name": case_name,
                "priority": priority,
                "tags": tags,
                "preconditions_count": len(case.get("preconditions", []) or []),
                "steps_count": len(case.get("steps", []) or []),
                "postconditions_count": len(case.get("postconditions", []) or []),
            })

            for idx, condition in enumerate(case.get("preconditions", []) or [], start=1):
                precondition_rows.append({
                    "case_id": case_id,
                    "index": idx,
                    "target": condition.get("target", ""),
                    "property": condition.get("property", ""),
                    "operator": condition.get("operator", ""),
                    "value": json.dumps(condition.get("value", ""), ensure_ascii=False),
                })

            for idx, step in enumerate(case.get("steps", []) or [], start=1):
                step_rows.append({
                    "case_id": case_id,
                    "index": idx,
                    "step_id": step.get("id", ""),
                    "type": step.get("type", ""),
                    "target": step.get("target", ""),
                    "operation": step.get("operation", ""),
                    "property": step.get("property", ""),
                    "operator": step.get("operator", ""),
                    "value": json.dumps(step.get("value", ""), ensure_ascii=False),
                    "params": json.dumps(step.get("params", {}), ensure_ascii=False),
                })

            for idx, condition in enumerate(case.get("postconditions", []) or [], start=1):
                postcondition_rows.append({
                    "case_id": case_id,
                    "index": idx,
                    "target": condition.get("target", ""),
                    "property": condition.get("property", ""),
                    "operator": condition.get("operator", ""),
                    "value": json.dumps(condition.get("value", ""), ensure_ascii=False),
                })

        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            pd.DataFrame(case_rows).to_excel(writer, index=False, sheet_name="Cases")
            pd.DataFrame(precondition_rows).to_excel(writer, index=False, sheet_name="Preconditions")
            pd.DataFrame(step_rows).to_excel(writer, index=False, sheet_name="Steps")
            pd.DataFrame(postcondition_rows).to_excel(writer, index=False, sheet_name="Postconditions")

        return output_path


if __name__ == "__main__":
    # ========== 使用示例 ==========
    # 请先设置环境变量 DEEPSEEK_API_KEY，或直接传入密钥
    # export DEEPSEEK_API_KEY="sk-xxx"
    
    helper = DeepSeekHelper()  # 默认从环境变量读取
    
    '''
    # 1. 普通对话测试
    try:
        result = helper.chat("介绍一下 DeepSeek")
        print("普通对话回复:", result['choices'][0]['message']['content'])
    except Exception as e:
        print(f"普通对话失败: {e}")
    '''
    # 2. 带文件的对话测试
    # 假设存在这些文件，请根据实际情况修改路径
    file_map = {
        "./sample/test_case_sample.xlsx": "测试用例 Excel 文件，包含四列",
        "./schema/test_ir_schema.json": "定义输出格式的 JSON Schema 文件"
        # ./skill/SKILL.md 可以添加技能文件，但目前示例中不使用
    }
    question = "请根据测试用例文件和 schema 文件，将测试用例转换为符合 schema 定义的 JSON 格式。"
    
    try:
        result = helper.chat_with_files(file_map, question)
        print("带文件对话回复:", result['choices'][0]['message']['content'])
        excel_path = helper.export_result_to_excel(result, "./output/result_converted.xlsx")
        print(f"Excel 已导出: {excel_path}")
    except Exception as e:
        print(f"带文件对话失败: {e}")