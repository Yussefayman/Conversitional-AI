from typing import Dict, Any, List, Optional
from datetime import datetime
import copy
from .llm_client import LLMClient
from utils.helpers import save_action_to_outbox, validate_email_addresses

class ConversationManager:
    """Streamlined conversation manager with clear confirmation flow"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.max_history = 10
        self._reset_state()
    
    def _reset_state(self):
        """Reset to empty state"""
        self.state = {
            "intent": None,
            "entities": {},
            "awaiting_confirmation": False,
            "user_confirmed": False,
            "history": [],
            "session_active": False
        }
    
    # Main Processing
    def process_message(self, user_input: str) -> Dict[str, Any]:
        """Process user message and return response"""
        try:
            context = self._build_context()
            llm_response = self.llm_client.process_message(user_input, context)
            self._update_state(llm_response, user_input)
            self._add_to_history(user_input, llm_response["response"])
            return llm_response
        except Exception as e:
            error_response = {
                "action_type": "error",
                "response": "Sorry, I encountered an error. Could you try again?",
                "error": str(e)
            }
            self._add_to_history(user_input, error_response["response"])
            return error_response
    
    def _build_context(self) -> Dict[str, Any]:
        """Build context for LLM"""
        return {
            "intent": self.state["intent"],
            "entities": copy.deepcopy(self.state["entities"]),
            "awaiting_confirmation": self.state["awaiting_confirmation"],
            "user_confirmed": self.state["user_confirmed"],
            "session_active": self.state["session_active"],
            "missing_entities": self._get_missing_entities(),
            "has_all_required": self._has_all_required_entities()
        }
    
    def _update_state(self, llm_response: Dict[str, Any], user_input: str):
        """Update state based on LLM response"""
        action_type = llm_response.get("action_type", "chitchat")
        
        if action_type == "new_intent":
            self.state["intent"] = llm_response.get("intent")
            self.state["entities"] = llm_response.get("entities", {})
            self.state["session_active"] = True
            self.state["awaiting_confirmation"] = False
            self.state["user_confirmed"] = False
        
        elif action_type == "correction":
            corrected_entities = llm_response.get("entities", {})
            self.state["entities"].update(corrected_entities)
            
            # If we now have everything, prepare for confirmation
            if self._has_all_required_entities() and not self.state["awaiting_confirmation"]:
                self.state["awaiting_confirmation"] = True
                # Override response with confirmation
                confirmation_msg = self._build_confirmation_message()
                llm_response["response"] = confirmation_msg
                llm_response["needs_confirmation"] = True
        
        elif action_type == "confirmation":
            if self._is_positive_response(user_input):
                if self._has_all_required_entities():
                    self.state["user_confirmed"] = True
                    self.state["awaiting_confirmation"] = False
                    llm_response["ready_to_execute"] = True
                    llm_response["response"] = "Perfect! I'll take care of that now."
                else:
                    llm_response["response"] = "I need more information first."
            else:
                self._reset_state()
                llm_response["response"] = "No problem! Cancelled. What else can I help with?"
        
        elif action_type == "greeting":
            if not self.state["session_active"]:
                self.state["intent"] = "chitchat"
    
    # Validation
    def _has_all_required_entities(self) -> bool:
        """Check if we have all required info including email addresses"""
        entities = self.state["entities"]
        
        if self.state["intent"] == "schedule_meeting":
            # Must have title, date, time, and participants with email addresses
            required_fields = ["title", "date", "time", "participants"]
            
            # Check basic fields exist
            for field in required_fields:
                if not entities.get(field) or not str(entities.get(field)).strip():
                    return False
            
            # Check participants have email addresses
            participants = entities.get("participants", [])
            if isinstance(participants, list):
                # At least one participant must have valid email
                return any("@" in str(p) for p in participants if p)
            else:
                return "@" in str(participants)
        
        elif self.state["intent"] == "send_email":
            recipient = entities.get("recipient")
            has_valid_recipient = recipient and validate_email_addresses(recipient)
            has_content = (entities.get("subject") or entities.get("body"))
            return has_valid_recipient and has_content
        
        return True
    
    def _get_missing_entities(self) -> List[str]:
        """Get specific missing fields"""
        entities = self.state["entities"]
        missing = []
        
        if self.state["intent"] == "schedule_meeting":
            if not entities.get("title"):
                missing.append("title")
            if not entities.get("date"):
                missing.append("date")
            if not entities.get("time"):
                missing.append("time")
            if not entities.get("participants"):
                missing.append("participants")
            elif entities.get("participants"):
                # Check if participants have email addresses
                participants = entities.get("participants", [])
                if isinstance(participants, list):
                    has_emails = any("@" in str(p) for p in participants if p)
                else:
                    has_emails = "@" in str(participants)
                
                if not has_emails:
                    missing.append("participant_emails")
        
        elif self.state["intent"] == "send_email":
            recipient = entities.get("recipient")
            if not recipient:
                missing.append("recipient")
            elif not validate_email_addresses(recipient):
                missing.append("valid_email")
            
            if not (entities.get("subject") or entities.get("body")):
                missing.append("content")
        
        return missing
    
    def _build_confirmation_message(self) -> str:
        """Build specific confirmation message"""
        intent = self.state["intent"]
        entities = self.state["entities"]
        
        if intent == "schedule_meeting":
            title = entities.get("title", "meeting")
            date = entities.get("date", "")
            time = entities.get("time", "")
            participants = entities.get("participants", [])
            
            if isinstance(participants, list):
                participants_str = ", ".join(participants)
            else:
                participants_str = str(participants)
            
            date_display = self._format_date(date)
            return f"Should I schedule the '{title}' meeting for {date_display} at {time} with {participants_str}?"
        
        elif intent == "send_email":
            recipients = entities.get("recipient", [])
            subject = entities.get("subject", "")
            body = entities.get("body", "")
            
            if isinstance(recipients, list):
                recipients_str = ", ".join(recipients)
            else:
                recipients_str = str(recipients)
            
            if subject and body:
                return f"Should I send an email to {recipients_str} with subject '{subject}' and message '{body[:30]}...'?"
            elif subject:
                return f"Should I send an email to {recipients_str} with subject '{subject}'?"
            else:
                return f"Should I send an email to {recipients_str} with message '{body[:50]}...'?"
        
        return "Should I proceed?"
    
    def _format_date(self, date_str: str) -> str:
        """Format date for display"""
        try:
            if len(date_str) == 10 and date_str.count('-') == 2:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                today = datetime.now().date()
                if date_obj.date() == today:
                    return "today"
                elif date_obj.date() == today + timedelta(days=1):
                    return "tomorrow"
                else:
                    return date_obj.strftime('%B %d')
        except:
            pass
        return date_str
    
    def _is_positive_response(self, user_input: str) -> bool:
        """Check if response is positive"""
        positive = {"yes", "y", "yeah", "sure", "ok", "okay", "go ahead", "do it"}
        negative = {"no", "n", "nope", "don't", "cancel", "stop"}
        
        clean_input = user_input.lower().strip()
        
        if clean_input in positive:
            return True
        elif clean_input in negative:
            return False
        
        return "yes" in clean_input or "go" in clean_input
    
    # Execution
    def is_ready_for_execution(self) -> bool:
        """Check if ready to execute"""
        return (
            self.state["session_active"] and
            self.state["intent"] in ["schedule_meeting", "send_email"] and
            self._has_all_required_entities() and
            self.state["user_confirmed"] and
            not self.state["awaiting_confirmation"]
        )
    
    def get_action_for_execution(self) -> Optional[Dict[str, Any]]:
        """Get action data for execution"""
        if not self.is_ready_for_execution():
            return None
        
        return {
            "type": self.state["intent"],
            "entities": copy.deepcopy(self.state["entities"]),
            "timestamp": datetime.now().isoformat()
        }
    
    def execute_action(self) -> Dict[str, Any]:
        """Execute the action"""
        if not self.is_ready_for_execution():
            return {
                "success": False,
                "error": "Not ready for execution",
                "missing": self._get_missing_entities()
            }
        
        action_data = self.get_action_for_execution()
        result = save_action_to_outbox(action_data)
        
        if result["success"]:
            self._reset_state()
        
        return result
    
    # State Management
    def get_current_state(self) -> Dict[str, Any]:
        """Get current state"""
        return copy.deepcopy(self.state)
    
    def get_state_display(self) -> str:
        """Get formatted state display"""
        if not self.state["session_active"]:
            return "Ready for new conversation\n\nTry: 'book a meeting' or 'send an email'"
        
        display_parts = []
        
        # Intent
        if self.state["intent"]:
            emoji = "📅" if self.state["intent"] == "schedule_meeting" else "📧"
            display_parts.append(f"{emoji} **{self.state['intent']}**")
        
        # Entities
        if self.state["entities"]:
            display_parts.append("**Details:**")
            for key, value in self.state["entities"].items():
                if value:
                    if key == "date":
                        value = self._format_date(str(value))
                    elif isinstance(value, list):
                        value = ", ".join(str(v) for v in value)
                    display_parts.append(f"  • {key.title()}: {value}")
        
        # Status
        if self.state["awaiting_confirmation"]:
            status = "⏳ Awaiting confirmation"
        elif self.state["user_confirmed"]:
            status = "✅ Ready to execute"
        elif not self._has_all_required_entities():
            missing = self._get_missing_entities()
            status = f"📝 Need: {', '.join(missing)}"
        else:
            status = "🔄 Processing"
        
        display_parts.append(f"**Status:** {status}")
        
        if self.state["history"]:
            display_parts.append(f"**Exchanges:** {len(self.state['history'])}")
        
        return "\n\n".join(display_parts)
    
    def reset_conversation(self):
        """Reset conversation"""
        self._reset_state()
    
    # History
    def _add_to_history(self, user_input: str, bot_response: str):
        """Add to history"""
        self.state["history"].append({
            "user_input": user_input,
            "bot_response": bot_response,
            "timestamp": datetime.now().isoformat()
        })
        
        if len(self.state["history"]) > self.max_history:
            self.state["history"] = self.state["history"][-self.max_history:]
    
    # Debug
    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug info"""
        return {
            "state": self.get_current_state(),
            "is_ready": self.is_ready_for_execution(),
            "has_required": self._has_all_required_entities(),
            "missing": self._get_missing_entities()
        }