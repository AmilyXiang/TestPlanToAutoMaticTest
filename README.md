# TestPlayToAutoMaticTest

## 目录结构
- **schema**：文件格式定义
  - test_ir_schema.json : LLM 输出格式定义，输入excel测试用例，输出json 测试内容
  - api_capability_schema.json : 测试平台API定义，输入 test_ir json 测试内容，输出代码测试用例
  - object_model_schema.json : 对象Model定义，定义对象状态等枚举值，用于扩展
- **sample**：实例
  - test_case_sample.xlsx ； excel 测试用例
  - test_case_ir_sample.json : excel 测试用例生成的 test_case_ir json 数据
  - api_capability_sample.json : api capability 例子
- **skill**: 技能文件
  - SKILL.md : OXE/pleiades 测试专家的技能文件
- **helper**: LLM helper
  - deepseek_helpser.py : deepseek helper 类，提供chat / upload file 接口（TODO）

## Usage
- **deepseek usage**
  - deepseek chat
  - upload SKILL.md
  - upload test_case_sample.xlsx
  - upload test_ir_schema.json
  - prompt: 按照上传技能，转换 test_case_sample.xlsx 文件的测试用例为 json 格式的测试步骤，测试步骤符合test_ir_schema.json 定义。



