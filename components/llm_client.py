import os
import json
from groq import Groq
from typing import Dict, Any
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.getcwd())

from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    def __init__(self, api_key: str = None):
        """Initialize Groq client"""
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile" 
    
    def process_message(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            prompt = self._build_prompt(user_input, context)
            raw_response = self._call_groq(prompt)
            parsed_response = self._parse_response(raw_response)

            required_fields = {
                "schedule_meeting": ["date", "time", "participants"],
                "send_email": ["recipient", "subject", "body"]
            }

            intent = parsed_response.get("intent")
            entities = parsed_response.get("entities", {})
            missing = []

            if intent in required_fields:
                for field in required_fields[intent]:
                    if not entities.get(field):
                        missing.append(field)

            if missing:
                parsed_response["ready_to_execute"] = False
                parsed_response["missing_entities"] = missing

            # 🚫 Don’t save prematurely → return only
            return parsed_response

        except Exception as e:
            return {
                "action_type": "error",
                "intent": "chitchat",
                "entities": {},
                "response": "Sorry, I had trouble processing that. Could you try again?",
                "needs_confirmation": False,
                "ready_to_execute": False,
                "error": str(e)
            }


    def _build_prompt(self, user_input: str, context: Dict[str, Any]) -> str:
        """Build concise prompt for Groq"""
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_entities = context.get("entities", {})
        current_intent = context.get("intent")
        
        prompt = f"""You are a meeting and email assistant. Today is {current_date}.

    Current state: {current_intent or "None"}
    Entities: {current_entities}

    User: "{user_input}"


    Rules:
    - Don't assume date or time.
    - For emails: clarify user intention.
    - For meetings: need title, date, time, participants(emails)
    - For emails: need recipient (valid email), subject and body
    - Ask for missing info one at a time
    - Only confirm when you have everything
    - Use DOUBLE QUOTES in JSON

    INTENT SWITCHING RULE:
    - NEVER change intent from send_email to schedule_meeting
    
    Examples:
    "hello" → greeting, offer help
    "book meeting" → ask for title first
    "project sync" → ask for date/time
    "tomorrow 2pm" → ask for participants
    "john@co.com" → confirm if complete, ask for more if not
    "yes" → ready_to_execute: true

    JSON format:
    {{
        "action_type": "greeting|new_intent|correction|confirmation",
        "intent": "schedule_meeting|send_email|chitchat",
        "entities": {{"title": "", "date": "{current_date}", "time": "", "participants": []}},
        "response": "natural response",
        "needs_confirmation": false,
        "ready_to_execute": false
    }}"""
        
        return prompt
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context for the prompt"""
        if not context:
            return "No previous context."
        
        return f"""
Current Intent: {context.get('intent', 'None')}
Current Entities: {context.get('entities', {})}
Awaiting Confirmation: {context.get('awaiting_confirmation', False)}
Awaiting Email Addresses: {context.get('awaiting_email_addresses', False)}
Session Active: {context.get('session_active', False)}
Recent History: {context.get('history', [])[-3:] if context.get('history') else []}
"""
    
    def _call_groq(self, prompt: str) -> str:
        """Make the actual API call to Groq"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a helpful assistant that responds only with valid JSON."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.1,
                top_p=1,
                stream=False
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            raise Exception(f"Groq API call failed: {str(e)}")
    
    def _parse_response(self, raw_response: str) -> Dict[str, Any]:
        """Parse the JSON response from Groq with better cleaning"""
        try:
            # Clean up response (remove any markdown formatting and comments)
            clean_response = raw_response.strip()
            
            # Remove markdown code blocks
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.startswith("```"):
                clean_response = clean_response[3:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            
            clean_response = clean_response.strip()
            
            # Remove JavaScript-style comments (// comments)
            lines = clean_response.split('\n')
            cleaned_lines = []
            for line in lines:
                # Remove comments after //
                if '//' in line:
                    # Find // that's not inside a string
                    in_string = False
                    quote_char = None
                    for i, char in enumerate(line):
                        if char in ['"', "'"] and (i == 0 or line[i-1] != '\\'):
                            if not in_string:
                                in_string = True
                                quote_char = char
                            elif char == quote_char:
                                in_string = False
                                quote_char = None
                        elif char == '/' and i < len(line) - 1 and line[i+1] == '/' and not in_string:
                            line = line[:i].rstrip()
                            break
                cleaned_lines.append(line)
            
            clean_response = '\n'.join(cleaned_lines)
            
            # Fix single quotes to double quotes in JSON (but not inside string values)
            import re
            
            # Replace single quotes with double quotes for JSON keys and empty values
            # Pattern: 'key': or ': '' or '[]' etc
            clean_response = re.sub(r"'([^']*)'(\s*:\s*)", r'"\1"\2', clean_response)  # Keys
            clean_response = re.sub(r":\s*'([^']*)'", r': "\1"', clean_response)  # String values
            clean_response = re.sub(r":\s*''", r': ""', clean_response)  # Empty strings
            
            # Remove any trailing commas before closing braces/brackets
            clean_response = re.sub(r',(\s*[}\]])', r'\1', clean_response)
            
            # Parse JSON
            parsed = json.loads(clean_response)
            
            # Ensure required fields exist
            required_fields = {
                "action_type": "chitchat",
                "intent": "chitchat", 
                "entities": {},
                "response": "I'm not sure how to help with that.",
                "needs_confirmation": False,
                "ready_to_execute": False,
                "correction_detected": False
            }
            
            for field, default in required_fields.items():
                if field not in parsed:
                    parsed[field] = default
            
            return parsed
            
        except json.JSONDecodeError as e:
            # Return fallback response for invalid JSON
            return {
                "action_type": "error",
                "intent": "chitchat",
                "entities": {},
                "response": "I had trouble understanding that. Could you rephrase?",
                "needs_confirmation": False,
                "ready_to_execute": False,
                "correction_detected": False,
                "parse_error": str(e),
                "raw_response": raw_response[:500]  # Truncate for display
            }