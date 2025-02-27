"""
Web search tools for LLM-based research.

This module provides tools for searching the web using various search APIs.
"""

import os
import requests
from typing import Dict, List, Optional, Any, Union


class BochaWebSearch:
    """
    Web search using the Bocha API.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Bocha web search.
        
        Args:
            api_key: The Bocha API key (optional, can be set via environment variable)
        """
        self.api_key = api_key or os.environ.get("BOCHA_API_KEY")
        if not self.api_key:
            raise ValueError("Bocha API key is required. Set it via the constructor or BOCHA_API_KEY environment variable.")
        
        self.base_url = "https://api.bochaai.com/v1/web-search"
    
    def search(
        self,
        query: str,
        freshness: str = "noLimit",
        summary: bool = True,
        count: int = 10
    ) -> str:
        """
        Search the web using the Bocha Web Search API.
        
        Args:
            query: The search query
            freshness: Time range for search results (oneDay, oneWeek, oneMonth, oneYear, noLimit)
            summary: Whether to include text summaries
            count: Number of search results to return
            
        Returns:
            Formatted search results with titles, URLs, summaries, etc.
        """
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            "query": query,
            "freshness": freshness,
            "summary": summary,
            "count": count
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=data)
            
            if response.status_code == 200:
                json_response = response.json()
                
                if json_response["code"] != 200 or not json_response["data"]:
                    return f"搜索API请求失败，原因是: {json_response.get('msg', '未知错误')}"
                
                webpages = json_response["data"]["webPages"]["value"]
                if not webpages:
                    return "未找到相关结果。"
                
                formatted_results = ""
                for idx, page in enumerate(webpages, start=1):
                    formatted_results += (
                        f"引用: {idx}\n"
                        f"标题: {page['name']}\n"
                        f"URL: {page['url']}\n"
                        f"摘要: {page['summary']}\n"
                        f"网站名称: {page.get('siteName', 'N/A')}\n"
                        f"网站图标: {page.get('siteIcon', 'N/A')}\n"
                        f"发布时间: {page.get('dateLastCrawled', 'N/A')}\n\n"
                    )
                print('成功返回搜索结果：' , formatted_results)
                return formatted_results.strip()
            else:
                return f"搜索API请求失败，状态码: {response.status_code}, 错误信息: {response.text}"
        
        except Exception as e:
            return f"搜索API请求失败，原因是: {str(e)}"


def get_web_search_tool(api_key: Optional[str] = None) -> BochaWebSearch:
    """
    Get a web search tool instance.
    
    Args:
        api_key: The API key for the search provider (optional)
        
    Returns:
        A web search tool instance
    """
    return BochaWebSearch(api_key=api_key)