# WebUI 多步骤推理中间过程显示实现计划

## 概述

本文档详细描述了如何在WebUI中实现多步骤推理中间过程的实时显示。这个功能将使用户能够在对话历史中看到推理的每个步骤，而不仅仅是最终结果，从而提升用户体验和系统透明度。

## 实现步骤

### 1. 增强核心推理引擎 (llm_research/reasoning.py)

#### 1.1 添加任务分解事件

```python
# 在task_decomposition方法中添加分解开始事件
self._log({
    "type": "decomposition_start",
    "message": f"🔍 分析任务: \"{task}\"\n正在将任务分解为子任务...",
    "task": task
})

# 在需要重试时添加重试事件
self._log({
    "type": "decomposition_retry",
    "message": f"⚠️ 生成的子任务数量 ({len(subtasks)}) 远超最大步骤数 ({self.max_steps})\n正在重新分解任务 (尝试 {retry_count}/{max_retries})...",
    "retry_count": retry_count,
    "max_retries": max_retries
})

# 在分解完成时添加完成事件
subtasks_formatted = "\n".join([f"{i+1}. {subtask}" for i, subtask in enumerate(subtasks)])
self._log({
    "type": "decomposition_complete",
    "message": f"📋 已将任务分解为以下子任务:\n{subtasks_formatted}",
    "subtasks": subtasks
})
```

#### 1.2 添加子任务执行事件

```python
# 在execute_subtasks方法中添加子任务开始事件
self._log({
    "type": "subtask_start",
    "message": f"\n🔄 执行子任务 {i+1}/{total_subtasks}: \"{subtask}\"\n思考中...",
    "subtask_index": i,
    "subtask": subtask,
    "total_subtasks": total_subtasks
})

# 在需要重试时添加重试事件
self._log({
    "type": "subtask_retry",
    "message": f"🔁 重试子任务 {i+1} (尝试 {retry_count}/{max_retries})...",
    "subtask_index": i,
    "retry_count": retry_count,
    "max_retries": max_retries
})

# 在验证子任务前添加验证开始事件
self._log({
    "type": "subtask_validation_start",
    "message": f"🔍 验证子任务 {i+1} 是否完成...",
    "subtask_index": i
})

# 在子任务完成时添加完成事件
self._log({
    "type": "subtask_complete",
    "message": f"✅ 子任务 {i+1}/{total_subtasks} 完成",
    "subtask_index": i,
    "subtask": subtask,
    "response": response
})

# 在子任务未完成时添加未完成事件
self._log({
    "type": "subtask_incomplete",
    "message": f"❌ 子任务 {i+1}/{total_subtasks} 未完成",
    "subtask_index": i,
    "subtask": subtask,
    "response": response
})

# 在达到最大重试次数时添加最大重试事件
self._log({
    "type": "subtask_max_retries",
    "message": f"⚠️ 达到最大重试次数 ({max_retries})，使用最后一次结果",
    "subtask_index": i,
    "subtask": subtask,
    "response": response
})
```

#### 1.3 添加结果聚合事件

```python
# 在aggregate_results方法中添加聚合开始事件
self._log({
    "type": "aggregation_start",
    "message": "🧩 整合所有子任务结果\n生成最终答案...",
    "task": task,
    "subtasks_count": len(subtasks)
})

# 在聚合完成时添加完成事件
self._log({
    "type": "aggregation_complete",
    "message": "✨ 任务完成!",
    "result": aggregation
})
```

### 2. 修改WebUI适配器 (llm_research/webui/adapters/reasoning.py)

#### 2.1 添加chat_interface参数

```python
def __init__(
    self,
    llm: BaseLLM,
    max_steps: int = 5,
    temperature: float = 0.7,
    web_search_enabled: bool = True,
    extract_url_content: bool = True,
    ws_handler: Optional[Callable[[Dict[str, Any]], None]] = None,
    chat_interface = None  # 添加chat_interface参数
):
    # ...
    self.chat_interface = chat_interface  # 存储chat_interface引用
    # ...
```

#### 2.2 实现enhanced_ws_handler函数

```python
def solve_task(
    self,
    task: str,
    context: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    max_retries: int = 3
) -> str:
    # 保存原始ws_handler
    original_ws_handler = self.reasoning.ws_handler
    
    def enhanced_ws_handler(log_data):
        # 调用原始ws_handler
        if original_ws_handler:
            original_ws_handler(log_data)
        
        # 如果chat_interface可用，在聊天历史中显示
        if self.chat_interface:
            log_type = log_data.get("type")
            message = log_data.get("message", "")
            
            if log_type == "decomposition_start":
                # 任务分解开始
                self.chat_interface.addMessage('system', f"🔍 {message}")
            
            elif log_type == "decomposition_complete":
                # 任务分解完成
                self.chat_interface.addMessage('assistant', f"📋 {message}")
            
            elif log_type == "subtask_start":
                # 子任务开始
                subtask_index = log_data.get("subtask_index", 0)
                total_subtasks = log_data.get("total_subtasks", 1)
                subtask = log_data.get("subtask", "")
                self.chat_interface.addMessage('system', f"🔄 执行子任务 {subtask_index+1}/{total_subtasks}: \"{subtask}\"")
            
            elif log_type == "subtask_complete":
                # 子任务完成
                response = log_data.get("response", "")
                self.chat_interface.addMessage('assistant', f"✅ {message}\n\n{response}")
            
            elif log_type == "subtask_incomplete" or log_type == "subtask_retry":
                # 子任务未完成或重试
                self.chat_interface.addMessage('system', message)
            
            elif log_type == "aggregation_start":
                # 聚合开始
                self.chat_interface.addMessage('system', message)
            
            elif log_type == "step_error" or log_type == "subtask_max_retries":
                # 错误或达到最大重试次数
                self.chat_interface.addMessage('system', f"❌ {message}")
            
            elif log_type == "log" and message.strip():
                # 普通日志消息
                self.chat_interface.addMessage('system', message)
    
    # 临时替换ws_handler
    self.reasoning.ws_handler = enhanced_ws_handler
    
    try:
        # 执行任务
        result = self.reasoning.solve_task(
            task=task,
            context=context,
            max_tokens=max_tokens,
            temperature=temperature or self.temperature,
            max_retries=max_retries
        )
        
        # 将最终结果添加到聊天
        if self.chat_interface:
            self.chat_interface.addMessage('assistant', f"✨ 最终结果:\n\n{result}")
        
        return result
    finally:
        # 恢复原始ws_handler
        self.reasoning.ws_handler = original_ws_handler
```

### 3. 更新API和前端代码

#### 3.1 修改API端点 (llm_research/webui/api.py)

```python
# 获取会话ID（如果提供）
conversation_id = data.get('conversation_id')

# 获取聊天界面（如果存在）
chat_interface = None
if conversation_id and conversation_id in conversations:
    chat_interface = conversations[conversation_id]

# 创建推理适配器，传递聊天界面
reasoning = ReasoningAdapter(
    llm,
    max_steps=steps,
    web_search_enabled=web_search_enabled,
    extract_url_content=extract_url_content,
    ws_handler=send_log_to_client,
    chat_interface=chat_interface  # 传递聊天界面
)
```

#### 3.2 更新前端API客户端 (llm_research/webui/static/js/api.js)

```javascript
// 在startReasoning方法中传递当前会话ID
async startReasoning(task, options = {}) {
    try {
        const response = await fetch(`${this.baseUrl}/api/reasoning`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                task: task,
                steps: options.steps || 5,
                provider: options.provider,
                temperature: options.temperature,
                max_tokens: options.max_tokens,
                web_search: options.web_search,
                extract_url: options.extract_url,
                retries: options.retries || 3,
                context_files: options.context_files || [],
                conversation_id: this.activeConversationId  // 传递当前会话ID
            })
        });
        
        // ...
    } catch (error) {
        // ...
    }
}
```

#### 3.3 实现前端日志处理 (llm_research/webui/static/js/reasoning.js)

```javascript
/**
 * 处理推理日志事件
 *
 * @param {Object} data - 事件数据
 */
handleReasoningLog(data) {
    // 处理结构化日志消息
    if (typeof data === 'object' && data.type) {
        // enhanced_ws_handler会处理在聊天历史中显示这些消息
        // 我们只需要根据日志类型更新UI
        
        const message = data.message || '';
        
        // 根据日志类型更新进度条和状态
        switch (data.type) {
            case 'decomposition_start':
                this.reasoningStatus.textContent = '分析任务中...';
                this.reasoningProgressBar.style.width = '10%';
                break;
                
            case 'decomposition_complete':
                this.reasoningStatus.textContent = '任务分解完成';
                this.reasoningProgressBar.style.width = '20%';
                
                // 如果有子任务，更新子任务
                if (data.subtasks && Array.isArray(data.subtasks)) {
                    this.subtasks = data.subtasks;
                    this.currentSubtaskIndex = 0;
                }
                break;
                
            case 'subtask_start':
                if (data.subtask_index !== undefined && data.total_subtasks) {
                    const progress = 20 + (data.subtask_index / data.total_subtasks) * 60;
                    this.reasoningProgressBar.style.width = `${progress}%`;
                    this.reasoningStatus.textContent = `执行子任务 ${data.subtask_index + 1}/${data.total_subtasks}`;
                }
                break;
                
            case 'subtask_complete':
                if (data.subtask_index !== undefined && data.total_subtasks) {
                    const progress = 20 + ((data.subtask_index + 1) / data.total_subtasks) * 60;
                    this.reasoningProgressBar.style.width = `${progress}%`;
                    this.reasoningStatus.textContent = `子任务 ${data.subtask_index + 1}/${data.total_subtasks} 完成`;
                }
                break;
                
            case 'aggregation_start':
                this.reasoningProgressBar.style.width = '80%';
                this.reasoningStatus.textContent = '整合结果中...';
                break;
                
            case 'aggregation_complete':
                this.reasoningProgressBar.style.width = '100%';
                this.reasoningStatus.textContent = '推理完成';
                break;
        }
    } 
    // 处理简单字符串日志消息（旧格式）
    else if (typeof data === 'string' || data.message) {
        const message = typeof data === 'string' ? data : data.message;
        // 只添加非空消息，避免聊天历史混乱
        if (message && message.trim()) {
            this.chatInterface.addMessage('system', message);
        }
    }
}
```

## 测试计划

1. **基本功能测试**
   - 测试简单推理任务，确保所有中间步骤正确显示
   - 验证任务分解、子任务执行和结果聚合的事件是否正确显示

2. **复杂场景测试**
   - 测试包含多个子任务的复杂推理任务
   - 测试需要重试的场景，确保重试事件正确显示
   - 测试达到最大重试次数的场景

3. **错误处理测试**
   - 测试推理过程中的错误处理
   - 验证错误消息是否正确显示在聊天历史中

4. **集成测试**
   - 测试与现有聊天功能的集成
   - 确保推理功能不影响其他功能的正常工作

## 部署计划

1. 在开发环境中实现并测试所有更改
2. 进行代码审查，确保代码质量和一致性
3. 在测试环境中部署并进行全面测试
4. 修复发现的任何问题
5. 部署到生产环境
6. 监控系统性能和用户反馈
7. 根据反馈进行必要的调整和优化