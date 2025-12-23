"""
LLM Handler for HomeAI Bot
Integrates Anthropic Claude for intelligent responses and analysis
"""

import os
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
import json

try:
    from anthropic import Anthropic, AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logging.warning("Anthropic library not installed. Claude features will be disabled.")

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("Google Generative AI library not installed. Gemini features will be disabled.")

logger = logging.getLogger(__name__)


class LLMHandler:
    """Handler for LLM-powered intelligent responses"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-haiku-20241022"):
        """
        Initialize LLM handler
        
        Args:
            api_key: API key (Anthropic or Google)
            model: Model to use
        """
        # Determine provider
        self.provider = os.getenv('LLM_PROVIDER', 'anthropic').lower()
        
        # Try Gemini first if configured
        gemini_key = os.getenv('GOOGLE_API_KEY')
        if gemini_key and GEMINI_AVAILABLE:
            self.provider = 'gemini'
            self.enabled = True
            genai.configure(api_key=gemini_key)
            self.model = os.getenv('LLM_MODEL', 'gemini-1.5-flash')
            self.client = genai.GenerativeModel(self.model)
            logger.info(f"LLM handler initialized with Google Gemini: {self.model}")
        # Fallback to Anthropic
        elif api_key and ANTHROPIC_AVAILABLE:
            self.provider = 'anthropic'
            self.enabled = True
            self.model = model
            self.client = AsyncAnthropic(api_key=api_key)
            logger.info(f"LLM handler initialized with Anthropic: {model}")
        else:
            self.enabled = False
            self.client = None
            logger.warning("LLM handler disabled (no API key or library not installed)")
        
        self.daily_calls = 0
        self.max_daily_calls = int(os.getenv('MAX_DAILY_LLM_CALLS', '100'))
    
    async def analyze_command(self, command: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Analyze user command with LLM
        
        Args:
            command: User's command text
            context: Additional context (current states, user preferences, etc.)
            
        Returns:
            Parsed command structure or None
        """
        if not self.enabled or self.daily_calls >= self.max_daily_calls:
            return None
        
        try:
            if self.provider == 'gemini':
                return await self._analyze_with_gemini(command, context)
            else:
                return await self._analyze_with_anthropic(command, context)
        except Exception as e:
            logger.error(f"Error analyzing command with LLM: {e}")
            return None
    
    async def _analyze_with_gemini(self, command: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Analyze command using Google Gemini"""
        prompt = f"""Parse this smart home command into JSON:

Command: "{command}"

Return ONLY valid JSON with:
- action: turn_on, turn_off, set_temperature, status, etc.
- domain: light, climate, lock, cover, etc.
- target: device or room name
- value: any value needed (temperature, brightness, etc.)
- confidence: 0-1 score

Examples:
"turn on bedroom lights" -> {{"action": "turn_on", "domain": "light", "target": "bedroom", "confidence": 0.95}}
"set living room to 21" -> {{"action": "set_temperature", "domain": "climate", "target": "living_room", "value": 21, "confidence": 0.9}}
"""
        
        if context:
            prompt += f"\n\nContext: {json.dumps(context)}"
        
        response = self.client.generate_content(prompt)
        self.daily_calls += 1
        
        # Extract JSON from response
        text = response.text
        if '{' in text and '}' in text:
            json_start = text.index('{')
            json_end = text.rindex('}') + 1
            json_str = text[json_start:json_end]
            return json.loads(json_str)
        
        return None
    
    async def _analyze_with_anthropic(self, command: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Analyze command using Anthropic Claude"""
        system_prompt = """You are a smart home assistant. Parse user commands into structured actions.
            
Return JSON with:
- action: the action to perform (turn_on, turn_off, set_temperature, status, etc.)
- domain: device domain (light, climate, lock, cover, etc.)
- target: specific device or room name
- value: any value needed (temperature, brightness, etc.)
- confidence: 0-1 confidence score

Examples:
"turn on bedroom lights" -> {"action": "turn_on", "domain": "light", "target": "bedroom", "confidence": 0.95}
"set living room to 21 degrees" -> {"action": "set_temperature", "domain": "climate", "target": "living_room", "value": 21, "confidence": 0.9}
"is the door locked?" -> {"action": "status", "domain": "lock", "target": "door", "confidence": 0.85}
"""
            
        context_str = ""
        if context:
            context_str = f"\n\nCurrent context:\n{json.dumps(context, indent=2)}"
            
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=500,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": f"Parse this command: \"{command}\"{context_str}"
            }]
        )
            
        self.daily_calls += 1
            
        # Extract JSON from response
        content = response.content[0].text
        # Try to find JSON in the response
        if '{' in content and '}' in content:
            json_start = content.index('{')
            json_end = content.rindex('}') + 1
            json_str = content[json_start:json_end]
            return json.loads(json_str)
            
        return None
    
    async def generate_energy_analysis(self, usage_data: Dict[str, Any]) -> Optional[str]:
        """
        Generate energy usage analysis and optimization suggestions
        
        Args:
            usage_data: Energy usage data with history and breakdowns
            
        Returns:
            Analysis text or None
        """
        if not self.enabled or self.daily_calls >= self.max_daily_calls:
            return None
        
        try:
            prompt = f"""Analyze this home energy usage data and provide optimization suggestions:

{json.dumps(usage_data, indent=2)}

Provide:
1. Key findings about usage patterns
2. Specific optimization opportunities
3. Estimated savings for each suggestion
4. Priority ranking of recommendations

Format as a clear, actionable report for a homeowner."""

            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            self.daily_calls += 1
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Error generating energy analysis: {e}")
            return None
    
    async def generate_smart_response(self, user_message: str, context: Dict[str, Any]) -> Optional[str]:
        """
        Generate contextual response to user message
        
        Args:
            user_message: User's message
            context: Current home state and context
            
        Returns:
            Response text or None
        """
        if not self.enabled or self.daily_calls >= self.max_daily_calls:
            return None
        
        try:
            if self.provider == 'gemini':
                # GEMINI IMPLEMENTATION
                system_prompt = """You are a helpful smart home assistant. Respond naturally and helpfully to user queries.
                
You have access to the current home state and can provide information about:
- Device states (lights, temperature, locks, etc.)
- Energy usage
- Automation suggestions
- Troubleshooting help

Be concise, friendly, and actionable. Use emojis sparingly for clarity.
"""
                context_str = json.dumps(context, indent=2)
                full_prompt = f"{system_prompt}\n\nUser says: \"{user_message}\"\n\nCurrent home state:\n{context_str}"
                
                response = self.client.generate_content(full_prompt)
                self.daily_calls += 1
                return response.text

            else:
                # ANTHROPIC IMPLEMENTATION
                system_prompt = """You are a helpful smart home assistant. Respond naturally and helpfully to user queries.
                
You have access to the current home state and can provide information about:
- Device states (lights, temperature, locks, etc.)
- Energy usage
- Automation suggestions
- Troubleshooting help

Be concise, friendly, and actionable. Use emojis sparingly for clarity."""

                context_str = json.dumps(context, indent=2)
                
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    system=system_prompt,
                    messages=[{
                        "role": "user",
                        "content": f"User says: \"{user_message}\"\n\nCurrent home state:\n{context_str}"
                    }]
                )
                
                self.daily_calls += 1
                return response.content[0].text
            
        except Exception as e:
            logger.error(f"Error generating smart response: {e}")
            return None
    
    async def analyze_patterns(self, command_history: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Analyze command history to detect patterns
        
        Args:
            command_history: List of recent commands
            
        Returns:
            Pattern analysis or None
        """
        if not self.enabled or self.daily_calls >= self.max_daily_calls:
            return None
        
        try:
            prompt = f"""Analyze this smart home command history to detect patterns and suggest automations:

{json.dumps(command_history[-50:], indent=2)}

Identify:
1. Recurring time-based patterns (e.g., "lights on at 6 PM every day")
2. Sequential patterns (e.g., "when leaving, always locks door then turns off lights")
3. Conditional patterns (e.g., "if temperature > 25°C, turns on AC")

Return JSON with:
{{
  "patterns": [
    {{
      "type": "time_based|sequential|conditional",
      "description": "human readable description",
      "confidence": 0-1,
      "suggested_automation": "automation description"
    }}
  ]
}}"""

            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            self.daily_calls += 1
            
            content = response.content[0].text
            if '{' in content and '}' in content:
                json_start = content.index('{')
                json_end = content.rindex('}') + 1
                json_str = content[json_start:json_end]
                return json.loads(json_str)
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing patterns: {e}")
            return None
    
    async def generate_weekly_report(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Generate weekly intelligence report
        
        Args:
            data: Week's data (commands, energy, patterns, etc.)
            
        Returns:
            Report text or None
        """
        if not self.enabled or self.daily_calls >= self.max_daily_calls:
            return None
        
        try:
            prompt = f"""Generate a weekly smart home intelligence report based on this data:

{json.dumps(data, indent=2)}

Include:
1. Usage summary and highlights
2. Detected patterns and routines
3. Energy usage trends
4. Optimization suggestions
5. Notable events or anomalies

Format as a friendly, informative report with emojis and clear sections."""

            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2500,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            self.daily_calls += 1
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
            return None
    
    def reset_daily_counter(self):
        """Reset daily API call counter (call this at midnight)"""
        self.daily_calls = 0
        logger.info("LLM daily call counter reset")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            "enabled": self.enabled,
            "daily_calls": self.daily_calls,
            "max_daily_calls": self.max_daily_calls,
            "remaining_calls": max(0, self.max_daily_calls - self.daily_calls),
            "model": self.model
        }
