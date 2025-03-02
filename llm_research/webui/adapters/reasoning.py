"""
Adapter for reasoning functionality.
"""

from typing import List, Dict, Any, Optional, Callable

from llm_research.llm.base import BaseLLM
from llm_research.reasoning import Reasoning as LLMReasoning
from llm_research.web_search import get_web_search_tool

class ReasoningAdapter:
    """
    Adapter for the LLMResearch reasoning functionality.
    
    This class provides a simplified interface to the LLMResearch reasoning
    functionality for use in the WebUI.
    """
    
    def __init__(
        self,
        llm: BaseLLM,
        max_steps: int = 5,
        temperature: float = 0.7,
        web_search_enabled: bool = True,
        extract_url_content: bool = True,
        ws_handler: Optional[Callable[[Dict[str, Any]], None]] = None,
        chat_interface = None  # Add chat_interface parameter
    ):
        """
        Initialize the reasoning adapter.
        
        Args:
            llm: The LLM provider to use
            max_steps: Maximum number of reasoning steps
            temperature: Sampling temperature for LLM calls
            web_search_enabled: Whether to enable web search
            extract_url_content: Whether to extract content from URLs
            ws_handler: WebSocket handler function for sending logs to UI (optional)
            chat_interface: Chat interface for displaying messages (optional)
        """
        self.llm = llm
        self.max_steps = max_steps
        self.temperature = temperature
        self.chat_interface = chat_interface  # Store chat_interface reference
        
        # Initialize web search if enabled
        web_search = None
        if web_search_enabled:
            try:
                web_search = get_web_search_tool()
            except Exception as e:
                print(f"Warning: Failed to initialize web search: {e}")
        
        # Initialize reasoning
        self.reasoning = LLMReasoning(
            llm=llm,
            max_steps=max_steps,
            temperature=temperature,
            web_search=web_search,
            extract_url_content=extract_url_content,
            ws_handler=ws_handler  # Pass ws_handler to reasoning
        )
        
        # Event handlers
        self.on_task_decomposition = None
        self.on_subtask_start = None
        self.on_subtask_complete = None
        self.on_aggregation_start = None
        self.on_aggregation_complete = None
    
    def task_decomposition(
        self,
        task: str,
        context: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> List[str]:
        """
        Decompose a complex task into subtasks.
        
        Args:
            task: The task to decompose
            context: Additional context (optional)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            
        Returns:
            A list of subtasks
        """
        subtasks = self.reasoning.task_decomposition(
            task=task,
            context=context,
            max_tokens=max_tokens,
            temperature=temperature or self.temperature
        )
        
        # Add decomposition results to chat history
        if self.chat_interface:
            decomposition_msg = "任务分解完成，生成以下子任务:\n" + "\n".join(
                [f"{i+1}. {subtask}" for i, subtask in enumerate(subtasks)]
            )
            self.chat_interface.addMessage('assistant', f"🤔 任务分解结果：\n{decomposition_msg}")
        
        # Call event handler if set
        if self.on_task_decomposition:
            self.on_task_decomposition(subtasks)
        
        return subtasks
    
    def execute_step(
        self,
        subtask: str,
        context: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None
    ) -> str:
        """
        Execute a reasoning step.
        
        Args:
            subtask: The subtask to execute
            context: Additional context (optional)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            timeout: Maximum time in seconds for this step
            
        Returns:
            The result of the step
            
        Raises:
            TimeoutError: If the step exceeds the timeout duration
        """
        # Call event handler if set
        if self.on_subtask_start:
            self.on_subtask_start(subtask)
        
        # Construct the prompt
        prompt = f"Task: {subtask}\n\n"
        
        if context:
            prompt += f"Context:\n{context}\n\n"
        
        prompt += "Result:"
        
        try:
            # Add subtask start message to chat
            if self.chat_interface:
                self.chat_interface.addMessage(
                    'system',
                    f"开始子任务 1/1: {subtask}"  # Temporary fixed values for testing
                )
            
            try:
                # Execute the step with timeout
                result = self.reasoning.execute_step(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature or self.temperature,
                    timeout=timeout
                )
                
                # Show reasoning steps in both input area and chat history
                if self.chat_interface:
                    message = f"子任务完成:\n{result}"
                    self.chat_interface.showReasoningSteps(message)
                    self.chat_interface.addMessage('assistant', message)
                    
            except Exception as e:
                error_msg = f"Subtask {i+1} failed: {str(e)}"
                print(error_msg)
                
                # Show error in both input area and chat history
                if self.chat_interface:
                    message = f"子任务 {i+1}/{len(subtasks)} 失败: {error_msg}"
                    self.chat_interface.showReasoningSteps(message)
                    self.chat_interface.addMessage('system', message)
                raise
                
        except TimeoutError as e:
            error_msg = f"Subtask timed out: {str(e)}"
            if self.on_subtask_complete:
                self.on_subtask_complete(subtask, error_msg)
            raise
        except Exception as e:
            error_msg = f"Subtask error: {str(e)}"
            if self.on_subtask_complete:
                self.on_subtask_complete(subtask, error_msg)
            raise
        
        # Call event handler if set
        if self.on_subtask_complete:
            self.on_subtask_complete(subtask, result)
        
        return result
    
    def aggregate_results(
        self,
        task: str,
        subtasks: List[str],
        results: List[str],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Aggregate the results of multiple subtasks.

        Args:
            task: The original task
            subtasks: The subtasks that were executed
            results: The results of each subtask
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            
        Returns:
            The aggregated result
        """
        # Show aggregation start in chat
        if self.chat_interface:
            self.chat_interface.addMessage(
                'system',
                f"开始整合{len(subtasks)}个子任务的结果..."
            )
        # Call event handler if set
        if self.on_aggregation_start:
            self.on_aggregation_start()
        
        # Aggregate the results
        final_result = self.reasoning.aggregate_results(
            task=task,
            subtasks=subtasks,
            results=results,
            max_tokens=max_tokens,
            temperature=temperature or self.temperature
        )
        
        # Call event handler if set
        if self.on_aggregation_complete:
            self.on_aggregation_complete(final_result)
        
        return final_result
    
    def solve_task(
        self,
        task: str,
        context: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        max_retries: int = 3
    ) -> str:
        """
        Solve a complex task using multi-step reasoning.
        
        Args:
            task: The task to solve
            context: Additional context (optional)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            max_retries: Maximum number of retry attempts per subtask
            
        Returns:
            The final result
        """
        # Store chat interface reference to avoid potential issues
        chat_interface = self.chat_interface
        
        # Add custom event handler to display intermediate steps in chat history
        original_ws_handler = self.reasoning.ws_handler
        
        def enhanced_ws_handler(log_data):
            try:
                # Call original ws_handler
                if original_ws_handler:
                    original_ws_handler(log_data)
                
                # Display in chat history if chat_interface is available
                if chat_interface:
                    log_type = log_data.get("type")
                    message = log_data.get("message", "")
                    
                    if log_type == "decomposition_start":
                        # Task decomposition started
                        chat_interface.addMessage('system', f"🔍 {message}")
                    
                    elif log_type == "decomposition_complete":
                        # Task decomposition completed
                        chat_interface.addMessage('assistant', f"📋 {message}")
                    
                    elif log_type == "subtask_start":
                        # Subtask started
                        subtask_index = log_data.get("subtask_index", 0)
                        total_subtasks = log_data.get("total_subtasks", 1)
                        subtask = log_data.get("subtask", "")
                        chat_interface.addMessage('system', f"🔄 执行子任务 {subtask_index+1}/{total_subtasks}: \"{subtask}\"")
                    
                    elif log_type == "subtask_complete":
                        # Subtask completed
                        response = log_data.get("response", "")
                        chat_interface.addMessage('assistant', f"✅ {message}\n\n{response}")
                    
                    elif log_type == "subtask_incomplete" or log_type == "subtask_retry":
                        # Subtask incomplete or retry
                        chat_interface.addMessage('system', message)
                    
                    elif log_type == "aggregation_start":
                        # Aggregation started
                        chat_interface.addMessage('system', message)
                    
                    elif log_type == "aggregation_complete":
                        # Aggregation completed - final result is handled separately
                        pass
                    
                    elif log_type == "step_start":
                        # Step started - more detailed than we need in chat history
                        pass
                    
                    elif log_type == "step_complete":
                        # Step completed - more detailed than we need in chat history
                        pass
                    
                    elif log_type == "step_error" or log_type == "subtask_max_retries":
                        # Error or max retries reached
                        chat_interface.addMessage('system', f"❌ {message}")
                    
                    elif log_type == "log" and message.strip():
                        # Regular log message
                        chat_interface.addMessage('system', message)
            except Exception as e:
                # Log any errors that occur during handling
                import traceback
                print(f"Error in enhanced_ws_handler: {str(e)}")
                print(traceback.format_exc())
        
        # Temporarily replace ws_handler
        self.reasoning.ws_handler = enhanced_ws_handler
        
        try:
            # Execute the task
            result = self.reasoning.solve_task(
                task=task,
                context=context,
                max_tokens=max_tokens,
                temperature=temperature or self.temperature,
                max_retries=max_retries
            )
            
            # Add final result to chat
            if chat_interface:
                chat_interface.addMessage('assistant', f"✨ 最终结果:\n\n{result}")
            
            return result
        except Exception as e:
            # Log any errors that occur during task execution
            import traceback
            print(f"Error in solve_task: {str(e)}")
            print(traceback.format_exc())
            
            # Add error message to chat
            if chat_interface:
                chat_interface.addMessage('system', f"❌ 推理错误: {str(e)}")
            
            # Re-raise the exception
            raise
        finally:
            # Restore original ws_handler
            self.reasoning.ws_handler = original_ws_handler
    
    def get_steps(self) -> List[Dict[str, Any]]:
        """
        Get all reasoning steps.
        
        Returns:
            A list of reasoning steps
        """
        return [
            {
                "prompt": step.prompt,
                "response": step.response,
                "timestamp": step.timestamp
            }
            for step in self.reasoning.get_steps()
        ]