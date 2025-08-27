from typing import Dict, Any, List
from datetime import datetime
import copy
import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from .llm_client import LLMClient

class ConversationManager:
    def __init__(self, llm_client: LLMClient):
        """Initialize conversation manager with LLM client"""
        self.llm_client = llm_client
        self.max_history = 12
        
        # Initialize conversation state
        self._reset_state()
    
    def _reset_state(self):
        """Reset conversation state"""
        self.state = {
            "intent": None,
            "entities": {},
            "awaiting_confirmation": False,
            "history": [],
            "session_active": False
        }
    
    def process_message(self, user_input: str) -> Dict[str, Any]:
        """
        Process user message and return response
        
        Args:
            user_input: User's message
            
        Returns:
            Dict with response, confirmation status, etc.
        """
        try:
            # Build context for LLM
            context = self._build_context_for_llm()
            
            # Get LLM response
            llm_response = self.llm_client.process_message(user_input, context)
            
            # Update conversation state based on LLM response
            self._update_state_from_llm_response(llm_response, user_input)
            
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
    
    def _build_context_for_llm(self) -> Dict[str, Any]:
        """Build context dictionary for LLM"""
        return {
            "intent": self.state["intent"],
            "entities": copy.deepcopy(self.state["entities"]),
            "awaiting_confirmation": self.state["awaiting_confirmation"],
            "history": self.state["history"][-5:] if self.state["history"] else [],
            "session_active": self.state["session_active"]
        }
    
    def _update_state_from_llm_response(self, llm_response: Dict[str, Any], user_input: str):
        """Update conversation state based on LLM response"""
        
        # Handle different action types
        action_type = llm_response.get("action_type", "chitchat")
        
        if action_type == "new_intent":
            # New conversation/intent
            self.state["intent"] = llm_response.get("intent")
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
            else:
                # User said no - reset session
                self._reset_state()
                
        elif action_type == "cancellation":
            # User cancelled - reset
            self._reset_state()
            
        elif action_type == "chitchat":
            # Casual conversation - don't change session state much
            if not self.state["session_active"]:
                self.state["intent"] = "chitchat"
    
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
        
        # Status
        if self.state["awaiting_confirmation"]:
            display_parts.append("⏳ **Status:** Awaiting your confirmation")
        elif self.state["session_active"]:
            display_parts.append("🔄 **Status:** Processing your request")
        
        # Recent history count
        if self.state["history"]:
            display_parts.append(f"💭 **Exchanges:** {len(self.state['history'])}")
        
        return "\n\n".join(display_parts) if display_parts else "Ready"
    
    def reset_conversation(self):
        """Reset the entire conversation"""
        self._reset_state()
    
    def is_ready_for_execution(self) -> bool:
        """Check if current action is ready to execute"""
        return (
            self.state["session_active"] and 
            self.state["intent"] in ["schedule_meeting", "send_email"] and
            not self.state["awaiting_confirmation"]
        )
    
    def get_action_for_execution(self) -> Dict[str, Any]:
        """Get the action data ready for execution/saving"""
        if not self.is_ready_for_execution():
            return None
        
        return {
            "type": self.state["intent"],
            "entities": self.state["entities"],
            "timestamp": datetime.now().isoformat(),
            "conversation_id": id(self)  # Simple conversation ID
        }
