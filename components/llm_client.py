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
        self.model = "llama3-70b-8192" 
    
    def process_message(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            prompt = self._build_prompt(user_input, context)
            raw_response = self._call_groq(prompt)
            parsed_response = self._parse_response(raw_response)

            # ✅ Only mark as "saveable" if ready_to_execute is True
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
        """Build the prompt for Groq with date awareness"""
        
        context_str = self._format_context(context)
        current_date = datetime.now().strftime("%A, %B %d, %Y")
        current_date_iso = datetime.now().strftime("%Y-%m-%d")
        
        # Check if we're waiting for email addresses
        awaiting_emails = context.get("awaiting_email_addresses", False)
        current_participants = context.get("entities", {}).get("participants", [])
        
        email_context = ""
        if awaiting_emails and current_participants:
            email_context = f"""
SPECIAL CONTEXT: The user was asked for email addresses for these people: {current_participants}
If the user provides names like "sarah and ahmed", convert them to email format or ask for actual email addresses.
If the user provides email addresses, use those directly.
"""
        
        prompt = f"""You are a conversational assistant that handles meeting bookings and emails.

CURRENT DATE: {current_date} ({current_date_iso})
CURRENT CONTEXT:
{context_str}

{email_context}

USER INPUT: "{user_input}"

IMPORTANT: Respond with VALID JSON ONLY. Use DOUBLE QUOTES for all strings, not single quotes.

CONTEXT RULES:
- When user mentions relative dates, calculate actual date based on current date: {current_date_iso}
- For emails, you need actual email addresses (with @domain.com)
- If user gives names without email addresses, ask for the actual email addresses
- If user says just names like "sarah and ahmed" when asked for emails, ask for their email addresses
- Don't schedule or sent an email before you make sure you have all information
- When user confirms ("yes") but info is still missing, ask for the missing info instead of executing

Respond with valid JSON using DOUBLE QUOTES only:
{{
    "action_type": "new_intent|correction|confirmation|email_address_request",
    "intent": "schedule_meeting|send_email|chitchat",
    "entities": {{
        "title": "meeting title or email subject",
        "date": "YYYY-MM-DD format", 
        "time": "time string",
        "recipient": "email addresses for emails",
        "participants": "participant names for meetings",
        "subject": "email subject",
        "body": "email body"
    }},
    "correction_detected": false,
    "missing_entities": ["field1", "field2"],
    "response": "Your conversational response",
    "needs_confirmation": true,
    "ready_to_execute": false
}}

CALCULATION EXAMPLES:
- "tomorrow" = {(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')}
- "in 2 days" = {(datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')}  
- "next week" = {(datetime.now() + timedelta(weeks=1)).strftime('%Y-%m-%d')}
- "in two weeks" = {(datetime.now() + timedelta(weeks=2)).strftime('%Y-%m-%d')}

RULES:
- Don't schedule a meeting before taking all informatin: date,time, participants emails.
- If user says "actually", "wait", "change", "make it" etc. → correction_detected: true
- For new requests → action_type: "new_intent"
- For "yes"/"no" responses → action_type: "confirmation"
- For corrections → only include changed entities
- For confirmations → set ready_to_execute: true ONLY if all required info is present
- If missing required info → ask for it and set needs_confirmation: false
- When user asks to email people but only gives names, ask for email addresses

EXAMPLES (valid JSON with DOUBLE QUOTES):

Input: "I want to schedule a meeting"
{{"action_type": "new_intent", "intent": "schedule_meeting", "entities": {{"title": "meeting"}}, "missing_entities": ["date", "time", "participants emails"], "response": "I'd be happy to schedule a meeting for you. When would you like to schedule it and what time?", "needs_confirmation": false, "ready_to_execute": false}}

Input: "in 2 days" (when providing missing date info)
{{"action_type": "correction", "intent": "schedule_meeting", "entities": {{"date": "{(datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')}"}}, "correction_detected": true, "missing_entities": ["time"], "response": "Got it, in 2 days. What time would you like to schedule the meeting?", "needs_confirmation": false, "ready_to_execute": false}}

Input: "at 3pm" (providing missing time)
{{"action_type": "correction", "intent": "schedule_meeting", "entities": {{"time": "3pm"}}, "correction_detected": true, "response": "Perfect! Should I schedule the meeting for 2 days from now at 3pm?", "needs_confirmation": true, "ready_to_execute": false}}

Input: "yes" (when confirming but still missing info like time)
{{"action_type": "confirmation", "intent": "schedule_meeting", "entities": {{}}, "missing_entities": ["time"], "response": "Great! What time would you like to schedule the meeting?", "needs_confirmation": false, "ready_to_execute": false}}

Input: "yes" (when all info is complete)
{{"action_type": "confirmation", "ready_to_execute": true, "response": "Perfect! I'll schedule that meeting for you now.", "needs_confirmation": false}}

Input: "sarah and ahmed" (when asked for email addresses)
{{"action_type": "email_address_request", "intent": "send_email", "entities": {{}}, "response": "I need their actual email addresses. Could you provide sarah@company.com and ahmed@company.com (or their actual email addresses)?", "needs_confirmation": false, "ready_to_execute": false}}

Input: "sarah@company.com and ahmed@company.com"
{{"action_type": "new_intent", "intent": "send_email", "entities": {{"recipient": ["sarah@company.com", "ahmed@company.com"]}}, "response": "Perfect! Should I send an email to sarah@company.com and ahmed@company.com?", "needs_confirmation": true, "ready_to_execute": false}}
"""
        
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
                max_tokens=500,
                temperature=0.3,  # Lower temperature for more consistent JSON
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