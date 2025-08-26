import os
import json
from groq import Groq
from typing import Dict, Any

class LLMClient:
    def __init__(self, api_key: str = None):
        """Initialize Groq client"""
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.client = Groq(api_key=self.api_key)
        self.model = "llama3-8b-8192" 
    
    def process_message(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user message and return structured response
        
        Args:
            user_input: User's message
            context: Current conversation context
            
        Returns:
            Dict with action_type, intent, entities, response, etc.
        """
        try:
            # Build prompt with context
            prompt = self._build_prompt(user_input, context)
            
            # Call Groq
            raw_response = self._call_groq(prompt)
            
            # Parse JSON response
            parsed_response = self._parse_response(raw_response)
            
            return parsed_response
            
        except Exception as e:
            # Fallback response for errors
            return {
                "action_type": "error",
                "intent": "chitchat",
                "entities": {},
                "response": f"Sorry, I had trouble processing that. Could you try again?",
                "needs_confirmation": False,
                "ready_to_execute": False,
                "error": str(e)
            }
    
    def _build_prompt(self, user_input: str, context: Dict[str, Any]) -> str:
        """Build the prompt for Groq"""
        
        context_str = self._format_context(context)
        
        prompt = f"""You are a conversational assistant that handles meeting bookings, emails and chat.

CURRENT CONTEXT:
{context_str}

USER INPUT: "{user_input}"

Analyze this input and respond with valid JSON only (no other text):
{{
    "action_type": "new_intent|correction|confirmation|chitchat",
    "intent": "schedule_meeting|send_email|chitchat",
    "entities": {{
        "title": "...",
        "date": "...", 
        "time": "...",
        "recipient": "...",
        "subject": "...",
        "body": "..."
    }},
    "correction_detected": true/false,
    "missing_entities": ["time", "date"],
    "response": "Your conversational response to the user",
    "needs_confirmation": true/false,
    "ready_to_execute": true/false
}}

RULES:
- If user says "actually", "wait", "change", "make it" etc. → correction_detected: true
- For new requests → action_type: "new_intent"
- For "yes"/"no" responses → action_type: "confirmation"
- For corrections → only include changed entities
- For confirmations → set ready_to_execute: true if user confirms
- Be conversational and natural in responses
- If missing required info → ask for it and set needs_confirmation: false

EXAMPLES:

Input: "Book meeting with Sara tomorrow at 3pm"
Output: {{"action_type": "new_intent", "intent": "schedule_meeting", "entities": {{"title": "meeting with Sara", "date": "tomorrow", "time": "3pm"}}, "correction_detected": false, "response": "Should I book a meeting with Sara tomorrow at 3pm?", "needs_confirmation": true, "ready_to_execute": false}}

Input: "actually make it 4pm"
Output: {{"action_type": "correction", "intent": "schedule_meeting", "entities": {{"time": "4pm"}}, "correction_detected": true, "response": "Updated to 4pm. Should I proceed?", "needs_confirmation": true, "ready_to_execute": false}}

Input: "yes"
Output: {{"action_type": "confirmation", "ready_to_execute": true, "response": "Perfect! I'll take care of that now.", "needs_confirmation": false}}

Input: "Send email to john@company.com about the delay"
Output: {{"action_type": "new_intent", "intent": "send_email", "entities": {{"recipient": "john@company.com", "body": "about the delay"}}, "response": "Should I send an email to john@company.com with the message: 'about the delay'?", "needs_confirmation": true, "ready_to_execute": false}}
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
History: {context.get('history', [])}
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
                temperature=0.1,
                top_p=3,
                stream=False
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            raise Exception(f"Groq API call failed: {str(e)}")
    
    def _parse_response(self, raw_response: str) -> Dict[str, Any]:
        """Parse the JSON response from Groq"""
        try:
            # Clean up response (remove any markdown formatting)
            clean_response = raw_response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()
            
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
                "raw_response": raw_response
            }