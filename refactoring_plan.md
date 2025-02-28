# Refactoring Plan: Improving Web Search Results Handling

## Current Implementation

Currently, in the `reasoning.py` file, the `execute_step` method uses `self.web_search.search(query=query)` which returns all search results as a single large text block containing summaries and URLs. This approach has several limitations:

1. It's difficult to iterate through individual URLs programmatically
2. There's no way to selectively choose which URLs to extract content from based on relevance to the query
3. The code has to use regex to extract URLs from the text, which is error-prone
4. The structure of the search results is lost when converted to a text block

## Proposed Changes

### 1. Modify `BochaWebSearch.search()` in `web_search.py`

Change the return type from a formatted string to a structured dictionary:

```python
# Current
def search(...) -> str:
    # Returns a formatted string with all search results

# Proposed
def search(...) -> Dict[str, Any]:
    # Returns a structured dictionary with search results
```

The structured dictionary would contain:
- Success status
- Query information
- List of search result objects, each with URL, title, summary, etc.
- Error information if applicable

### 2. Add a new method to `BochaWebSearch` for formatting

To maintain backward compatibility and separate concerns:

```python
def format_search_results(self, search_results: Dict[str, Any]) -> str:
    # Format the search results as a string for display or inclusion in prompts
```

### 3. Update `execute_step` in `reasoning.py`

Modify the method to work with structured data instead of parsing a string with regex:
- Use the structured data to access URLs directly
- Improve URL selection logic by providing better context to the LLM
- Maintain the same functionality but with cleaner code

## Detailed Implementation

### Changes to `web_search.py`

```python
def search(
    self,
    query: str,
    freshness: str = "noLimit",
    summary: bool = True,
    count: int = 10
) -> Dict[str, Any]:
    """
    Search the web using the Bocha Web Search API.
    
    Args:
        query: The search query
        freshness: Time range for search results (oneDay, oneWeek, oneMonth, oneYear, noLimit)
        summary: Whether to include text summaries
        count: Number of search results to return
        
    Returns:
        Dictionary containing search results with structured data
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
                return {
                    "success": False,
                    "error": f"搜索API请求失败，原因是: {json_response.get('msg', '未知错误')}"
                }
            
            webpages = json_response["data"]["webPages"]["value"]
            if not webpages:
                return {
                    "success": True,
                    "results": [],
                    "message": "未找到相关结果。"
                }
            
            # Return structured data
            return {
                "success": True,
                "query": query,
                "results": webpages
            }
        else:
            return {
                "success": False,
                "error": f"搜索API请求失败，状态码: {response.status_code}, 错误信息: {response.text}"
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"搜索API请求失败，原因是: {str(e)}"
        }

def format_search_results(self, search_results: Dict[str, Any]) -> str:
    """
    Format search results as a string.
    
    Args:
        search_results: The search results dictionary
        
    Returns:
        Formatted search results as a string
    """
    if not search_results["success"]:
        return search_results.get("error", "搜索失败")
    
    if not search_results.get("results", []):
        return "未找到相关结果。"
    
    formatted_results = ""
    for idx, page in enumerate(search_results["results"], start=1):
        formatted_results += (
            f"引用: {idx}\n"
            f"标题: {page['name']}\n"
            f"URL: {page['url']}\n"
            f"摘要: {page['summary']}\n"
            f"网站名称: {page.get('siteName', 'N/A')}\n"
            f"网站图标: {page.get('siteIcon', 'N/A')}\n"
            f"发布时间: {page.get('dateLastCrawled', 'N/A')}\n\n"
        )
    
    return formatted_results.strip()
```

### Changes to `reasoning.py`

The main changes will be in the `execute_step` method, specifically around lines 148-151:

```python
for idx, query in search_queries:
    print(f"🌐 搜索查询: \"{query}\"")
    search_results = self.web_search.search(query=query)
    
    # Extract content from URLs if enabled
    if self.extract_url_content and self.url_extractor:
        # No need to parse the search results to find URLs anymore
        extracted_contents = []
        
        # Check if search was successful
        if search_results["success"] and search_results.get("results"):
            urls = []
            url_summaries = []
            
            # Collect URLs and their summaries
            for result in search_results["results"]:
                urls.append(result["url"])
                url_summaries.append({
                    "url": result["url"],
                    "title": result["name"],
                    "summary": result["summary"]
                })
            
            if urls:
                print(f"📄 从搜索结果中发现 {len(urls)} 个URL，提取内容...")
                
                # Create a prompt to ask the LLM which URLs to extract content from
                url_selection_prompt = f"Based on the following search results for the query '{query}', which URLs would be most relevant to extract full content from? Select up to 3 URLs that seem most promising based on their summaries.\n\n"
                
                # Add formatted summaries for the LLM to evaluate
                for i, summary in enumerate(url_summaries, start=1):
                    url_selection_prompt += f"{i}. {summary['title']}\n   URL: {summary['url']}\n   Summary: {summary['summary']}\n\n"
                
                url_selection_prompt += "List the numbers of the most relevant URLs (e.g., '1, 3, 5'):"
                
                # Get the LLM's recommendation on which URLs to extract
                url_selection_response = self.llm.generate(
                    prompt=url_selection_prompt,
                    max_tokens=50,
                    temperature=0.3
                )
                
                # Parse the response to get the selected URL indices
                selected_indices = []
                selection_text = url_selection_response["text"].strip()
                
                # Try to parse numbers from the response
                for num in re.findall(r'\d+', selection_text):
                    try:
                        idx = int(num) - 1  # Convert to 0-based index
                        if 0 <= idx < len(urls):
                            selected_indices.append(idx)
                    except ValueError:
                        continue
                
                # Limit to at most 3 URLs
                selected_indices = selected_indices[:3]
                
                # Extract content from the selected URLs
                for url_idx in selected_indices:
                    url = urls[url_idx]
                    try:
                        print(f"📥 提取URL内容: {url}")
                        content = self.url_extractor.extract_content(url, output_format="markdown")
                        
                        # Truncate content if it's too long (to avoid token limits)
                        max_content_length = 4000
                        if len(content) > max_content_length:
                            content = content[:max_content_length] + "...\n[Content truncated due to length]"
                        
                        extracted_contents.append(f"Extracted content from {url}:\n\n{content}\n\n")
                        print(f"✅ 成功提取内容，长度: {len(content)} 字符")
                    except Exception as e:
                        print(f"❌ 提取内容失败: {str(e)}")
    
    # Format the search results for inclusion in the prompt
    formatted_search_results = self.web_search.format_search_results(search_results)
    
    # Add the extracted contents to the formatted search results
    if extracted_contents:
        formatted_search_results += "\n\n" + "\n".join(extracted_contents)
    
    # Replace the search line with the query and results
    lines[idx] = f"SEARCH: {query}\n\nSearch Results:\n{formatted_search_results}\n"
```

## Benefits of This Refactoring

1. **Structured Data**: Returns search results as structured data, making it easier to work with programmatically.
2. **Improved URL Selection**: Better evaluation of URL relevance by providing clearer context to the LLM.
3. **Maintainability**: Cleaner separation of concerns between data retrieval and formatting.
4. **Extensibility**: Makes it easier to add new features like filtering or sorting search results.
5. **Backward Compatibility**: Maintains compatibility with existing code through the `format_search_results` method.
6. **Error Handling**: More explicit error handling with structured response.

## Implementation Steps

1. Modify `web_search.py` to return structured data and add the formatting method.
2. Update `reasoning.py` to work with the structured data.
3. Test the changes with existing examples to ensure functionality is preserved.
4. Update documentation to reflect the new API.

## Future Enhancements

Once this refactoring is complete, additional improvements could include:

1. Adding relevance scoring for search results
2. Implementing more sophisticated URL selection algorithms
3. Adding caching for search results to improve performance
4. Supporting pagination for large result sets