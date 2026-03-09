# Test Step KB 项目落地规划

## 1. 目标
- 将 TestRail/Excel 中自然语言步骤转换为可执行 Action Schema。
- 支持大批量（千级到万级）导入、统计、持续优化。
- 通过规则优先 + LLM 兜底模式，持续降低 `UNKNOWN`。

## 2. 当前状态（已完成）
- 已完成解析链路：标准化 -> 模式匹配 -> 参数提取 -> Action Schema 输出。
- 已完成批量导入：支持 txt/csv/xls/xlsx。
- 已完成知识库核心文件：`actions.json`、`step_patterns.json`、`test_steps.json`。
- 已完成高频模式两轮补充，`UNKNOWN` 已显著下降。

## 3. 里程碑

### M1: 规则引擎稳定化（已完成）
- 完成通用解析器和模式库。
- 建立导入统计和未知表达候选池。

### M2: 覆盖率冲刺（进行中）
- 目标：`UNKNOWN` <= 8%。
- 动作：按 `suggested_new_patterns` 频次持续补 pattern。
- 每轮完成后固定输出前后对比报告。

### M3: LLM 兜底与人审闭环（待做）
- 仅对 `UNKNOWN` 语句调用 LLM 生成候选 action/pattern。
- 候选先入“待审核清单”，人工确认后固化到 `step_patterns.json`。

### M4: 工程化落地（待做）
- 增加 CI 校验：JSON 结构、pattern 编译、回归样本通过率。
- 输出版本化发布记录（pattern 版本、覆盖率变化、破坏性变更）。

## 4. 日常运行流程
1. 清空数据集并导入指定 Excel 列。
2. 查看 unknown 报告（TopN）。
3. 扩展 pattern/action。
4. 重建并确认降幅。

## 5. 验收指标
- 解析准确率：关键动作识别准确率 >= 95%（抽样人工复核）。
- 覆盖率：`UNKNOWN` 比例 < 10%（目标 < 8%）。
- 可维护性：新增 pattern 必须带示例与优先级。
- 可复现性：同输入可稳定得到相同统计结果。
