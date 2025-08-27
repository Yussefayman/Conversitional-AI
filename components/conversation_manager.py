# components/conversation_manager.py
from typing import Dict, Any, List
from datetime import datetime
import copy
from .llm_client import LLMClient
from utils.helpers import save_action_to_outbox, list_saved_actions, get_action_summary

class ConversationManager:
    def __init__(self, llm_client: LLMClient, outbox_dir: str = "outbox"):
        """Initialize conversation manager with LLM client and outbox directory"""
        self.llm_client = llm_client
        self.outbox_dir = outbox_dir
        self.max_history = 10  # Keep last 10 exchanges
        
        # Initialize conversation state
        self._reset_state()
    
    def _reset_state(self):
        """Reset conversation state"""
        self.state = {
            "intent": None,
            "entities": {},
            "awaiting_confirmation": False,
            "awaiting_email_addresses": False,  # Flag for email address requests
            "history": [],
            "session_active": False,
            "last_saved_action": None  # Track the last saved action
        }
    
    def process_message(self, user_input: str) -> Dict[str, Any]:
        """
        Process user message and return response
        
        Args:
            user_input: User's message
            
        Returns:
            Dict with response, confirmation status, execution info, etc.
        """
        try:
            # Build context for LLM
            context = self._build_context_for_llm()
            
            # Get LLM response
            llm_response = self.llm_client.process_message(user_input, context)
            
            # Update conversation state based on LLM response
            self._update_state_from_llm_response(llm_response, user_input)
            
            # Check if action is ready for execution and auto-save
            execution_result = self._handle_action_execution()
            
            # Add execution info to response
            if execution_result:
                llm_response["execution_result"] = execution_result
            
            # Add to history
            self._add_to_history(user_input, llm_response["response"])
            
            return llm_response
            
        except Exception as e:
            # Fallback for errors
            error_response = {
                "action_type": "error",
                "intent": "chitchat",
                "entities": {},
                "response": "Sorry, I encountered an error. Could you try again?",
                "needs_confirmation": False,
                "ready_to_execute": False,
                "error": str(e)
            }
            
            self._add_to_history(user_input, error_response["response"])
            return error_response
    
    def _handle_action_execution(self) -> Dict[str, Any]:
        """
        Handle automatic execution (saving) of ready actions
        
        Returns:
            Dict with execution result info, or None if not ready
        """
        if not self.is_ready_for_execution():
            return None
        
        try:
            # Get action data
            action_data = self.get_action_for_execution()
            if not action_data:
                return None
            
            # Save to outbox
            save_result = save_action_to_outbox(action_data, self.outbox_dir)
            
            if save_result["success"]:
                # Mark this action as saved
                self.state["last_saved_action"] = {
                    "filename": save_result["filename"],
                    "filepath": save_result["filepath"],
                    "action_type": action_data["type"],
                    "summary": get_action_summary(action_data),
                    "saved_at": datetime.now().isoformat()
                }
                
                # Reset session after successful save
                self._reset_session_after_execution()
                
                return {
                    "success": True,
                    "action_executed": True,
                    "filename": save_result["filename"],
                    "filepath": save_result["filepath"],
                    "summary": get_action_summary(action_data),
                    "message": f"✅ {action_data['type'].replace('_', ' ').title()} saved successfully!"
                }
            else:
                return {
                    "success": False,
                    "action_executed": False,
                    "error": save_result["error"],
                    "message": f"❌ Failed to save {action_data['type']}: {save_result['error']}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "action_executed": False,
                "error": str(e),
                "message": f"❌ Execution error: {str(e)}"
            }
    
    def _reset_session_after_execution(self):
        """Reset session state after successful action execution, but keep history"""
        history = self.state["history"].copy()  # Preserve history
        last_saved = self.state["last_saved_action"].copy()  # Preserve last saved action
        
        self._reset_state()
        
        self.state["history"] = history
        self.state["last_saved_action"] = last_saved
    
    def _build_context_for_llm(self) -> Dict[str, Any]:
        """Build context dictionary for LLM"""
        return {
            "intent": self.state["intent"],
            "entities": copy.deepcopy(self.state["entities"]),
            "awaiting_confirmation": self.state["awaiting_confirmation"],
            "awaiting_email_addresses": self.state["awaiting_email_addresses"],
            "session_active": self.state["session_active"],
            "history": self.state["history"][-5:] if self.state["history"] else [],  # Last 5 for context
        }
    
    def _update_state_from_llm_response(self, llm_response: Dict[str, Any], user_input: str):
        """Update conversation state based on LLM response"""
        
        # Handle different action types
        action_type = llm_response.get("action_type", "chitchat")
        
        if action_type == "new_intent":
            # Check if we're switching intents and need to ask for missing info
            new_intent = llm_response.get("intent")
            missing_entities = llm_response.get("missing_entities", [])
            
            # Special handling for email address requests
            if (new_intent == "send_email" and 
                self.state.get("intent") == "schedule_meeting" and 
                "email_addresses" in missing_entities):
                
                # Don't fully switch intent yet, ask for missing info first
                self.state["awaiting_confirmation"] = False
                self.state["awaiting_email_addresses"] = True
                
            elif (new_intent == "send_email" and 
                  self.state.get("awaiting_email_addresses")):
                # User just provided email addresses
                if llm_response.get("entities", {}).get("recipient"):
                    self.state["entities"]["recipient"] = llm_response["entities"]["recipient"]
                    self.state["intent"] = "send_email"
                    self.state["awaiting_email_addresses"] = False
                    self.state["awaiting_confirmation"] = llm_response.get("needs_confirmation", True)
            else:
                # Normal new intent processing
                self.state["intent"] = new_intent
                self.state["entities"] = llm_response.get("entities", {})
                self.state["awaiting_confirmation"] = llm_response.get("needs_confirmation", False)
                self.state["session_active"] = True
                
        elif action_type == "correction":
            # Update only the corrected entities, keep others
            if llm_response.get("correction_detected"):
                corrected_entities = llm_response.get("entities", {})
                self.state["entities"].update(corrected_entities)
                self.state["awaiting_confirmation"] = llm_response.get("needs_confirmation", True)
            
        elif action_type == "confirmation":
            # Handle yes/no responses
            if llm_response.get("ready_to_execute"):
                self.state["awaiting_confirmation"] = False
                # Note: Actual execution handled in _handle_action_execution()
            else:
                # User said no - reset session
                self._reset_state()
                
        elif action_type == "cancellation":
            # User cancelled - reset
            self._reset_state()
            
        elif action_type == "email_address_request":
            # User provided names when we asked for emails
            self.state["awaiting_email_addresses"] = True
            self.state["awaiting_confirmation"] = False
            
        elif action_type == "chitchat":
            # Casual conversation - don't change session state much
            if not self.state["session_active"]:
                self.state["intent"] = "chitchat"
    
    def _has_required_entities(self) -> bool:
        """Check if we have all required entities for current intent"""
        entities = self.state["entities"]
        
        if self.state["intent"] == "schedule_meeting":
            required_fields = ["title", "date", "time"]
            return all(
                entities.get(field) and str(entities.get(field)).strip() 
                for field in required_fields
            )
            
        elif self.state["intent"] == "send_email":
            has_recipient = entities.get("recipient") and str(entities.get("recipient")).strip()
            has_content = (entities.get("body") and str(entities.get("body")).strip()) or \
                         (entities.get("subject") and str(entities.get("subject")).strip())
            return has_recipient and has_content
        
        return True

    def _get_missing_entities(self) -> list:
        """Get list of missing required entities"""
        entities = self.state["entities"]
        missing = []
        
        if self.state["intent"] == "schedule_meeting":
            required_fields = ["title", "date", "time"]
            for field in required_fields:
                if not (entities.get(field) and str(entities.get(field)).strip()):
                    missing.append(field)
                    
        elif self.state["intent"] == "send_email":
            if not (entities.get("recipient") and str(entities.get("recipient")).strip()):
                missing.append("recipient")
            if not ((entities.get("body") and str(entities.get("body")).strip()) or 
                    (entities.get("subject") and str(entities.get("subject")).strip())):
                missing.append("body_or_subject")
        
        return missing
    
    def _update_state(self, new_state: Dict[str, Any]):
        """Helper method to update state (for testing)"""
        self.state.update(new_state)
    
    def _add_to_history(self, user_input: str, bot_response: str):
        """Add exchange to conversation history"""
        self.state["history"].append({
            "user_input": user_input,
            "bot_response": bot_response,
            "timestamp": datetime.now().isoformat(),
            "state_snapshot": copy.deepcopy(self.state["entities"])  # For debugging
        })
        
        # Keep history manageable
        if len(self.state["history"]) > self.max_history:
            self.state["history"] = self.state["history"][-self.max_history:]
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current conversation state"""
        return copy.deepcopy(self.state)
    
    def get_state_display(self) -> str:
        """Get formatted state for UI display"""
        if not self.state["session_active"] and not self.state["intent"]:
            return "💬 **Status:** Ready for new conversation\n\n*Start by saying something like:*\n- Book a meeting with...\n- Send an email to...\n- Hello!"
        
        # Format current session info
        display_parts = []
        
        # Intent
        if self.state["intent"]:
            intent_emoji = "📅" if self.state["intent"] == "schedule_meeting" else "📧" if self.state["intent"] == "send_email" else "💬"
            display_parts.append(f"{intent_emoji} **Intent:** {self.state['intent']}")
        
        # Entities
        if self.state["entities"]:
            display_parts.append("**📋 Details:**")
            for key, value in self.state["entities"].items():
                if value:  # Only show non-empty values
                    display_parts.append(f"  • {key.title()}: {value}")
        
        # Status with more detail
        if self.state["awaiting_confirmation"]:
            display_parts.append("⏳ **Status:** Awaiting your confirmation")
        elif self.state.get("awaiting_email_addresses"):
            display_parts.append("📧 **Status:** Waiting for email addresses")
        elif not self._has_required_entities():
            missing = self._get_missing_entities()
            missing_str = ", ".join(missing).replace("_", " ").title()
            display_parts.append(f"📝 **Status:** Need more info ({missing_str})")
        elif self.state["session_active"]:
            if self.is_ready_for_execution():
                display_parts.append("✅ **Status:** Ready to execute")
            else:
                display_parts.append("🔄 **Status:** Processing your request")
        
        # Show last saved action if any
        if self.state.get("last_saved_action"):
            last_saved = self.state["last_saved_action"]
            display_parts.append(f"💾 **Last Saved:** {last_saved['summary']}")
        
        # Recent history count
        if self.state["history"]:
            display_parts.append(f"💭 **Exchanges:** {len(self.state['history'])}")
        
        return "\n\n".join(display_parts) if display_parts else "Ready"
    
    def reset_conversation(self):
        """Reset the entire conversation"""
        self._reset_state()
    
    def is_ready_for_execution(self) -> bool:
        """Check if current action is ready to execute"""
        if not (self.state["session_active"] and 
                self.state["intent"] in ["schedule_meeting", "send_email"]):
            return False
        
        # Check required entities based on intent
        entities = self.state["entities"]
        
        if self.state["intent"] == "schedule_meeting":
            # Meeting needs at least title, date, and time
            required_fields = ["title", "date", "time"]
            has_all_required = all(
                entities.get(field) and str(entities.get(field)).strip() 
                for field in required_fields
            )
            return has_all_required and not self.state["awaiting_confirmation"]
            
        elif self.state["intent"] == "send_email":
            # Email needs recipient and either subject+body or body
            has_recipient = entities.get("recipient") and str(entities.get("recipient")).strip()
            has_content = (entities.get("body") and str(entities.get("body")).strip()) or \
                         (entities.get("subject") and str(entities.get("subject")).strip())
            return has_recipient and has_content and not self.state["awaiting_confirmation"]
        
        return False
    
    def get_action_for_execution(self) -> Dict[str, Any]:
        """Get the action data ready for execution/saving"""
        if not self.is_ready_for_execution():
            return None
        
        return {
            "type": self.state["intent"],
            "entities": self.state["entities"],
            "timestamp": datetime.now().isoformat(),
            "conversation_id": f"conv_{id(self)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
    
    def get_saved_actions_summary(self, limit: int = 5) -> List[str]:
        """Get a summary of recently saved actions"""
        try:
            actions = list_saved_actions(self.outbox_dir, limit=limit)
            return [get_action_summary(action) for action in actions]
        except Exception as e:
            return [f"❌ Error loading saved actions: {str(e)}"]
    
    def get_outbox_stats(self) -> Dict[str, Any]:
        """Get statistics about the outbox"""
        try:
            actions = list_saved_actions(self.outbox_dir)
            
            total = len(actions)
            meeting_count = len([a for a in actions if a.get("type") == "schedule_meeting"])
            email_count = len([a for a in actions if a.get("type") == "send_email"])
            
            return {
                "total_actions": total,
                "meetings": meeting_count,
                "emails": email_count,
                "last_saved": actions[0].get("saved_at") if actions else None
            }
        except Exception as e:
            return {"error": str(e)}
