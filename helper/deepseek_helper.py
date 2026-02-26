import requests

"""
DeepSeek helper
"""
class DeepSeekHelper:

    _api_key = ""
    _upload_url = "https://api.deepseek.com/upload"  # 请以官方文档为准
    _chat_url = "https://api.deepseek.com/chat/completions"

    def __init__(self, api_key):
        self._api_key = api_key

    """
    upload file
    return file_id
    """
    def upload_file(self, file_path):
        headers = {
            "Authorization": f"Bearer {self._api_key}"
        }
        # 注意：这里用 files 参数，而不是 data
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(self._upload_url, headers=headers, files=files)

        if response.status_code == 200:
            file_info = response.json()
            file_id = file_info.get("id")  # 假设返回的 JSON 中包含文件 ID
            print(f"upload successfully: file_id={file_id}")
            return file_id
        else:
            print(f"upload failed: {response.text}")
            raise IOError(f"upload failed: {response.text}")


    """
    chat with files
    file_ids_map = {
        "file_id_1": "file_id_1 description",
        "file_id_2": "file_id_2 description",
        "file_id_3": "file_id_3 description",
        "file_id_4": "file_id_4 description",
        "file_id_5": "file_id_5 description"
    }
    """
    def chat_with_files(self, file_ids_map, input_text):
        # validate file_ids_map
        if file_ids_map is None or len(file_ids_map) == 0:
            return ""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}"
        }

        content_array = []

        # append into content
        for file_id in file_ids_map:
            content_array.append({
                "type": "file",
                "file_id": file_id
            })

        # generate input question
        question = "files already uploaded. \n"
        for file_id in file_ids_map:
            question += f"The description of file id {file_id} is: {file_ids_map[file_id]}. \n"
        question += input_text
        content_array.append({
            "type": "text",
            "text": question
        })

        data = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "content": "You are a helpful assistant",
                    "role": "system"
                },
                {
                    "role": "user",
                    "content": content_array
                }
            ],
            # "temperature": 0.7,  # 可选参数
            # "max_tokens": 4000  # 可选参数
        }

        response = requests.post(self._chat_url, headers=headers, json=data)

        if response.status_code == 200:
            result = response.json()
            return result
        else:
            print(f"请求失败: {response.text}")
            raise IOError(f"chat failed: {response.text}")

    def chat(self, input_text):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self._api_key}"
        }

        data = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "content": "You are a helpful assistant",
                    "role": "system"
                },
                {
                    "content": input_text,
                    "role": "user"
                }
            ],
        }

        response = requests.post(self._chat_url, headers=headers, json=data)

        if response.status_code == 200:
            result = response.json()
            return result
        else:
            print(f"请求失败: {response.text}")
            raise IOError(f"chat failed: {response.text}")


if __name__ == "__main__":
    api_key = "your_deepseek_api_key"
    helper = DeepSeekHelper(api_key)
    output = helper.chat("hello")
    file_id = helper.upload_file("../sample/test_case_sample.xlsx")
    file_id2 = helper.upload_file("../schema/test_ir_schema.json")
    file_ids_map = {
        file_id: "test case file，format is excel, includes 4 columes (case name, precondition, step, expected result).",
        file_id2: "schema file, The output must conform to the definition in this schema file."
    }
    input_text = """
        two files provided, one is test case file, another is schema file.
        Please translate the test case into formatted json content.
        The output format must conform to the definition in this schema file.
        """
    result = helper.chat_with_files(file_ids_map, input_text)
    print(result)
