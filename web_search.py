"""
Web Search Module for HomeAI Bot
Provides real-time internet data access using DuckDuckGo
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    from duckduckgo_search import DDGS
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False
    logging.warning("Web search not available - install duckduckgo-search")

logger = logging.getLogger(__name__)


class WebSearch:
    """Handles web searches for real-time information"""
    
    def __init__(self, enabled: bool = True):
        """
        Initialize web search
        
        Args:
            enabled: Whether to enable web search
        """
        self.enabled = enabled and SEARCH_AVAILABLE
        
        if self.enabled:
            self.ddg = DDGS()
            logger.info("Web search initialized with DuckDuckGo")
        else:
            logger.warning("Web search disabled")
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Search the web for a query
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of search results with title, snippet, link
        """
        if not self.enabled:
            return []
        
        try:
            results = []
            for r in self.ddg.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "link": r.get("href", "")
                })
            
            logger.info(f"Search for '{query}' returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def quick_answer(self, query: str) -> Optional[str]:
        """
        Get a quick answer for factual queries
        
        Args:
            query: Question to answer
            
        Returns:
            Quick answer or None
        """
        if not self.enabled:
            return None
        
        try:
            # Try instant answer first
            answer = self.ddg.answers(query)
            if answer:
                return answer[0].get("text", "")
            
            # Fallback to first search result
            results = self.search(query, max_results=1)
            if results:
                return results[0]["snippet"]
            
            return None
            
        except Exception as e:
            logger.error(f"Quick answer error: {e}")
            return None
    
    def news(self, query: str = "latest news", max_results: int = 5) -> List[Dict[str, str]]:
        """
        Get latest news
        
        Args:
            query: News topic
            max_results: Maximum number of results
            
        Returns:
            List of news articles
        """
        if not self.enabled:
            return []
        
        try:
            results = []
            for r in self.ddg.news(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "source": r.get("source", ""),
                    "date": r.get("date", ""),
                    "link": r.get("url", "")
                })
            
            logger.info(f"News search for '{query}' returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"News search error: {e}")
            return []
    
    def format_results(self, results: List[Dict[str, str]], max_length: int = 500) -> str:
        """
        Format search results for display
        
        Args:
            results: Search results
            max_length: Maximum length of formatted text
            
        Returns:
            Formatted results string
        """
        if not results:
            return "No results found."
        
        formatted = ""
        for i, result in enumerate(results[:3], 1):  # Top 3 results
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            
            formatted += f"{i}. **{title}**\n"
            formatted += f"{snippet[:150]}...\n\n"
            
            if len(formatted) > max_length:
                break
        
        return formatted.strip()
    
    def should_search(self, query: str) -> bool:
        """
        Determine if a query requires web search
        
        Args:
            query: User query
            
        Returns:
            True if search is needed
        """
        # Keywords that indicate need for current information
        search_keywords = [
            "latest", "current", "today", "now", "recent",
            "news", "weather", "price", "stock",
            "what is", "who is", "when is", "where is",
            "how much", "how many"
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in search_keywords)
    
    def search_and_summarize(self, query: str) -> Optional[str]:
        """
        Search and provide a summarized answer
        
        Args:
            query: Search query
            
        Returns:
            Summarized answer with sources
        """
        if not self.enabled:
            return None
        
        try:
            # Try quick answer first
            quick = self.quick_answer(query)
            if quick:
                return quick
            
            # Get search results
            results = self.search(query, max_results=3)
            if not results:
                return "I couldn't find any information about that."
            
            # Format with sources
            summary = "Here's what I found:\n\n"
            summary += self.format_results(results)
            
            return summary
            
        except Exception as e:
            logger.error(f"Search and summarize error: {e}")
            return None


class SmartSearch:
    """Intelligent search that combines web search with LLM"""
    
    def __init__(self, web_search: WebSearch, llm_handler=None):
        """
        Initialize smart search
        
        Args:
            web_search: WebSearch instance
            llm_handler: LLM handler for processing results
        """
        self.web_search = web_search
        self.llm = llm_handler
    
    async def answer_with_search(self, question: str) -> Optional[str]:
        """
        Answer a question using web search + LLM
        
        Args:
            question: User's question
            
        Returns:
            Intelligent answer with sources
        """
        if not self.web_search.enabled:
            return None
        
        try:
            # Get search results
            results = self.web_search.search(question, max_results=3)
            
            if not results:
                return "I couldn't find any information about that."
            
            # If LLM available, use it to synthesize answer
            if self.llm and self.llm.enabled:
                context = {
                    "search_results": results,
                    "question": question
                }
                
                prompt = f"""Based on these search results, answer the question concisely and accurately.

Question: {question}

Search Results:
{self.web_search.format_results(results)}

Provide a direct answer citing the sources."""
                
                answer = await self.llm.chat(prompt, context=context)
                return answer
            else:
                # Fallback to formatted results
                return self.web_search.format_results(results)
                
        except Exception as e:
            logger.error(f"Smart search error: {e}")
            return None
