# 多步骤推理中间过程显示重构计划

## 问题描述

当前系统可以正常完成单步直接chat或者多步骤推理，但多步骤推理只会在对话历史显示最终的推理结果，而无法显示推理的中间过程信息。用户需要在WebUI的对话历史中实时显示这些中间结果，提升用户体验。

## 解决方案

我们通过以下步骤实现中间推理过程的实时显示：

1. 增强核心推理引擎 (`llm_research/reasoning.py`)，使其发送更详细的事件信息
2. 修改WebUI适配器 (`llm_research/webui/adapters/reasoning.py`)，使其能够处理这些事件并显示在聊天历史中
3. 更新API和前端代码，确保事件能够正确传递和显示
4. 修复Flask应用上下文问题，确保在后台线程中正确访问应用上下文

## 具体实现

### 1. 增强核心推理引擎

在 `llm_research/reasoning.py` 中，我们增加了以下事件：

- **任务分解事件**：
  - `decomposition_start`: 开始分解任务
  - `decomposition_retry`: 重试任务分解（当生成的子任务过多时）
  - `decomposition_complete`: 任务分解完成，包含所有子任务

- **子任务执行事件**：
  - `subtask_start`: 开始执行子任务
  - `subtask_retry`: 重试子任务
  - `subtask_validation_start`: 开始验证子任务是否完成
  - `subtask_complete`: 子任务完成
  - `subtask_incomplete`: 子任务未完成
  - `subtask_max_retries`: 达到最大重试次数

- **结果聚合事件**：
  - `aggregation_start`: 开始聚合结果
  - `aggregation_complete`: 聚合完成，包含最终结果

每个事件都包含详细的信息，如消息内容、任务/子任务索引、响应等。

### 2. 修改WebUI适配器

在 `llm_research/webui/adapters/reasoning.py` 中，我们进行了以下修改：

1. 添加 `chat_interface` 参数，允许推理适配器直接向聊天界面发送消息
2. 实现 `enhanced_ws_handler` 函数，处理各种事件类型并将其显示在聊天历史中
3. 在 `solve_task` 方法中使用这个增强的处理器，确保中间步骤显示在聊天历史中

### 3. 更新API和前端代码

1. 修改 `llm_research/webui/api.py` 中的推理API端点，传递聊天界面到推理适配器
2. 更新 `llm_research/webui/static/js/api.js` 中的 `startReasoning` 方法，传递当前会话ID
3. 在 `llm_research/webui/static/js/reasoning.js` 中实现 `handleReasoningLog` 方法，处理结构化日志消息

## 工作流程

1. 用户在WebUI中启动多步骤推理
2. 前端将当前会话ID传递给后端API
3. 后端创建推理适配器，并传递聊天界面引用
4. 推理引擎执行任务，并发送详细的事件信息
5. 增强的WebSocket处理器接收这些事件，并将其显示在聊天历史中
6. 前端接收WebSocket消息，更新UI显示

## 优势

1. **实时反馈**：用户可以看到推理的每个步骤，而不仅仅是最终结果
2. **透明度**：整个推理过程变得透明，用户可以理解系统是如何得出结论的
3. **调试能力**：如果推理出现问题，用户可以更容易地识别问题所在
4. **用户体验**：提供更丰富的交互体验，让用户感觉系统更加智能和响应迅速

## 测试计划

1. 测试简单推理任务，确保所有中间步骤正确显示
2. 测试复杂推理任务，包含多个子任务和重试
3. 测试错误处理，确保错误信息正确显示
4. 测试与现有聊天功能的集成，确保不影响其他功能