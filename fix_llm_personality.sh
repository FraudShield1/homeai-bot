#!/bin/bash
#
# Fix LLM Personality & Method Name
# 1. Adds 'chat' method to LLMHandler (alias for compatibility)
# 2. Updates System Prompt to be "Brutally Honest" as requested
#

echo "🧠 Injecting Personality..."

cd ~/homeai-bot

cat > update_llm.py << 'EOF'
import sys

try:
    with open('llm_handler.py', 'r') as f:
        content = f.read()

    # 1. ADD chat method if missing
    if "def chat(" not in content:
        print("  - Adding 'chat' method alias...")
        # We'll add it to the end of the class, before generate_smart_response or just append to class
        # Easier to just replace generate_smart_response with the better version and alias it
        
        # Find generate_smart_response
        marker = "async def generate_smart_response(self, user_message: str, context: Dict[str, Any]) -> Optional[str]:"
        
        if marker in content:
            # We will rewrite this method to include the BETTER prompt and also alias it
            new_method = """
    async def chat(self, message: str, context: Dict[str, Any] = None) -> Optional[str]:
        \"\"\"Alias for generate_smart_response\"\"\"
        return await self.generate_smart_response(message, context or {})

    async def generate_smart_response(self, user_message: str, context: Dict[str, Any]) -> Optional[str]:
        \"\"\"
        Generate contextual response with PERSONALITY
        \"\"\"
        if not self.enabled: return "I'm offline (LLM disabled)."
        if self.daily_calls >= self.max_daily_calls: return "I'm out of credits for today."
        
        try:
            # BRUTALLY HONEST ADVISOR PROMPT
            system_prompt = \"\"\"You are an intelligent, brutally honest home advisor.
            
STYLE & PERSONALITY:
- Be DIRECT and UNFILTERED. No corporate fluff.
- If the user asks a stupid question, roast them gently but provide the answer.
- If the home state shows waste (e.g. lights on in empty house), COMPLAIN about it.
- You are not a servant; you are a partner. Challenge assumptions.
- Use emojis to convey sass or mood.

CONTEXT:
You have access to the home state. Use it to judge the user.
\"\"\"

            # Add Context
            context_str = json.dumps(context, indent=2)
            full_prompt = f"{system_prompt}\\n\\nCONTEXT:\\n{context_str}\\n\\nUSER:\\n{user_message}"
            
            # Call API (Gemini or Anthropic)
            if self.provider == 'gemini':
                response = self.client.generate_content(full_prompt)
                text = response.text
            else:
                # Anthropic
                msg = await self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": full_prompt}]
                )
                text = msg.content[0].text

            self.daily_calls += 1
            return text
            
        except Exception as e:
            logger.error(f"Chat Error: {e}")
            return "I tried to be smart, but my brain hurt. (Error)"
"""
            # Replace the old method with the new one
            # functionality to replace the block is tricky with simple replace if indentation varies
            # But the marker provided above is unique. 
            # We'll replace the marker + the body (approximated)
            
            # Simple approach: Append 'chat' to the end of class if it's cleaner, but we need 'chat' to work.
            # Let's just append the verify robust 'chat' implementation to the end of the file (inside class)
            # This is risky doing blindly.
            
            # BETTTER APPROACH: Rewrite the whole file with python logic that understands structure? No too complex.
            # Replace the specific generate_smart_response function completely.
            pass
            
            # Let's use the replace logic based on the known content from previous `view_file`.
            # We know exactly what lines 210-252 look like.
            
            old_code = """    async def generate_smart_response(self, user_message: str, context: Dict[str, Any]) -> Optional[str]:
        \"\"\"
        Generate contextual response to user message
        
        Args:
            user_message: User's message
            context: Current home state and context
            
        Returns:
            Response text or None
        \"\"\"
        if not self.enabled or self.daily_calls >= self.max_daily_calls:
            return None
        
        try:
            system_prompt = \"\"\"You are a helpful smart home assistant. Respond naturally and helpfully to user queries.
            
            You have access to the current home state and can provide information about:
            - Device states (lights, temperature, locks, etc.)
            - Energy usage
            - Automation suggestions
            - Troubleshooting help
            
            Be concise, friendly, and actionable. Use emojis sparingly for clarity.\"\"\"

            context_str = json.dumps(context, indent=2)
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": f"User says: \\"{user_message}\\"\\n\\nCurrent home state:\\n{context_str}"
                }]
            )
            
            self.daily_calls += 1
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Error generating smart response: {e}")
            return None"""

            new_code = """    async def chat(self, message: str, context: Dict[str, Any] = None) -> Optional[str]:
        \"\"\"Alias for generate_smart_response\"\"\"
        return await self.generate_smart_response(message, context or {})

    async def generate_smart_response(self, user_message: str, context: Dict[str, Any]) -> Optional[str]:
        \"\"\"Generate response with Brutally Honest Personality\"\"\"
        if not self.enabled: return None
        
        try:
            # BRUTALLY HONEST PROMPT
            system_prompt = \"\"\"You are HomeAI, a brutally honest, intelligent home assistant.
            - Trace: Be direct. No fluff.
            - Personality: Sarcastic but helpful. Judge the user's life choices based on their home state.
            - Context: Use the provided home state to make informed, stinging comments.
            - Goal: Optimize the home (and the user).\"\"\"

            # Prepare Prompt
            context_str = ""
            if context: context_str = f"\\nCONTEXT:\\n{json.dumps(context, indent=2)}"
            full_prompt = f"{system_prompt}\\n{context_str}\\n\\nUSER: {user_message}"
            
            # Execute based on provider
            if getattr(self, 'provider', 'anthropic') == 'gemini':
                 response = self.client.generate_content(full_prompt)
                 text = response.text
            else:
                 response = await self.client.messages.create(
                    model=self.model, 
                    max_tokens=1000, 
                    messages=[{"role": "user", "content": full_prompt}]
                 )
                 text = response.content[0].text

            self.daily_calls += 1
            return text
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return "I'm having a headache. (Error)"
"""
            # Do the replace
            # Check if old_code exists (ignoring whitespace might be needed)
            # We'll try exact match first
            
            if old_code in content:
                content = content.replace(old_code, new_code)
                with open('llm_handler.py', 'w') as f:
                    f.write(content)
                print("✅ llm_handler.py patched!")
            else:
                # Fallback: Just append `chat` method to class end if replace failed (to avoid crash)
                # But we really want the personality.
                print("⚠️ Exact match failed (formatting?). Appending 'chat' method fallback.")
                
                # Append to end of file, inside class LLMHandler
                # We need to find the last indentation level of the class methods?
                # Actually, let's just use a simpler replacement for the prompt string at least.
                
                prompt_marker = 'system_prompt = """You are a helpful smart home assistant.'
                if prompt_marker in content:
                     new_prompt = 'system_prompt = """You are a brutally honest, sarcastic home assistant. Be direct.'
                     content = content.replace(prompt_marker, new_prompt)
                
                # And add the chat alias
                if "def chat(" not in content:
                     # Hack: add it as a standalone method replacement for generate_smart_response in memory? 
                     # No, let's just append it to the file but indented
                     # This is too fragile.
                     pass
                
                # REWRITE STRATEGY: 
                # Since we can't reliably sed multi-line python without mess, 
                # let's just define the NEW class method and inject it.
                pass

except Exception as e:
    print(e)
EOF

# For robustness, we will just Append the `chat` method logic using a specific python replace that matches the function signature
cat > inject_chat.py << 'EOF'
import sys
import re

with open('llm_handler.py', 'r') as f:
    data = f.read()

# 1. replace generate_smart_response with a version that supports Gemini and has personality
# We search for the function def and replace until the next async def
pattern = r"async def generate_smart_response.*?async def analyze_patterns"
# This regex matches across newlines from start of smart_response to start of next function

# The replacement code
new_code = """async def chat(self, message: str, context: Dict[str, Any] = None) -> Optional[str]:
        return await self.generate_smart_response(message, context or {})

    async def generate_smart_response(self, user_message: str, context: Dict[str, Any]) -> Optional[str]:
        if not self.enabled: return None
        try:
            # BRUTALLY HONEST PERSONALITY
            system = "You are a brutally honest, intelligent home advisor. Be direct, concise, and slightly sarcastic. Use the home context to judge the user."
            prompt = f"{system}\\n\\nCONTEXT: {json.dumps(context)}\\n\\nUSER: {user_message}"
            
            if self.provider == 'gemini':
                return self.client.generate_content(prompt).text
            else:
                resp = await self.client.messages.create(
                    model=self.model, max_tokens=1000, 
                    messages=[{"role": "user", "content": prompt}]
                )
                return resp.content[0].text
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            return "I need coffee. (Brain Error)"

    async def analyze_patterns"""

# Use re.DOTALL to match across lines
import re
updated_data = re.sub(pattern, new_code, data, flags=re.DOTALL)

if updated_data != data:
    with open('llm_handler.py', 'w') as f:
        f.write(updated_data)
    print("✅ Injected 'chat' method and updated personality")
else:
    print("❌ Could not match function signature. Check file indent.")
EOF

python3 inject_chat.py

echo "Restarting..."
python3 homeai_bot.py
