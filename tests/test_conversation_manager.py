# tests/test_conversation_manager.py
import pytest
from unittest.mock import Mock, patch
import os
import sys
sys.path.append(os.getcwd())
from components.conversation_manager import ConversationManager
from components.llm_client import LLMClient

class TestConversationManager:
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for testing"""
        mock = Mock(spec=LLMClient)
        return mock
    
    @pytest.fixture
    def conversation_manager(self, mock_llm_client):
        """ConversationManager with mocked LLM"""
        return ConversationManager(mock_llm_client)
    
    def test_initial_state(self, conversation_manager):
        """Test initial conversation state"""
        state = conversation_manager.get_current_state()
        
        assert state["intent"] is None
        assert state["entities"] == {}
        assert state["awaiting_confirmation"] == False
        assert state["history"] == []
    
    def test_process_new_meeting_request(self, conversation_manager, mock_llm_client):
        """Test processing a new meeting request"""
        # Mock LLM response
        mock_llm_client.process_message.return_value = {
            "action_type": "new_intent",
            "intent": "schedule_meeting",
            "entities": {"title": "meeting with Sara", "date": "tomorrow", "time": "3pm"},
            "response": "Should I book a meeting with Sara tomorrow at 3pm?",
            "needs_confirmation": True,
            "ready_to_execute": False,
            "correction_detected": False
        }
        
        # Process message
        result = conversation_manager.process_message("Book meeting with Sara tomorrow at 3pm")
        
        # Check result
        assert result["response"] == "Should I book a meeting with Sara tomorrow at 3pm?"
        assert result["needs_confirmation"] == True
        assert result["ready_to_execute"] == False
        
        # Check state was updated
        state = conversation_manager.get_current_state()
        assert state["intent"] == "schedule_meeting"
        assert state["entities"]["title"] == "meeting with Sara"
        assert state["entities"]["time"] == "3pm"
        assert state["awaiting_confirmation"] == True
    
    def test_handle_correction(self, conversation_manager, mock_llm_client):
        """Test handling corrections like 'actually make it 4pm'"""
        # First, set up existing state
        conversation_manager._update_state({
            "intent": "schedule_meeting",
            "entities": {"title": "meeting with Sara", "date": "tomorrow", "time": "3pm"},
            "awaiting_confirmation": True
        })
        
        # Mock correction response
        mock_llm_client.process_message.return_value = {
            "action_type": "correction",
            "intent": "schedule_meeting",
            "entities": {"time": "4pm"},  # Only the corrected field
            "response": "Updated to 4pm. Should I proceed?",
            "needs_confirmation": True,
            "ready_to_execute": False,
            "correction_detected": True
        }
        
        # Process correction
        result = conversation_manager.process_message("actually make it 4pm")
        
        # Check response
        assert result["response"] == "Updated to 4pm. Should I proceed?"
        assert result["correction_detected"] == True
        
        # Check state - time should be updated, other fields preserved
        state = conversation_manager.get_current_state()
        assert state["entities"]["time"] == "4pm"  # Updated
        assert state["entities"]["title"] == "meeting with Sara"  # Preserved
        assert state["entities"]["date"] == "tomorrow"  # Preserved
    
    def test_confirmation_yes(self, conversation_manager, mock_llm_client):
        """Test handling 'yes' confirmation"""
        # Set up awaiting confirmation state
        conversation_manager._update_state({
            "intent": "schedule_meeting",
            "entities": {"title": "meeting", "date": "tomorrow", "time": "3pm"},
            "awaiting_confirmation": True
        })
        
        # Mock confirmation response
        mock_llm_client.process_message.return_value = {
            "action_type": "confirmation",
            "ready_to_execute": True,
            "response": "Perfect! I'll book that meeting now.",
            "needs_confirmation": False
        }
        
        # Process confirmation
        result = conversation_manager.process_message("yes")
        
        # Check result
        assert result["ready_to_execute"] == True
        assert result["needs_confirmation"] == False
        
        # State should be ready for execution
        state = conversation_manager.get_current_state()
        assert state["awaiting_confirmation"] == False
    
    def test_confirmation_no_cancellation(self, conversation_manager, mock_llm_client):
        """Test handling 'no' - should cancel action"""
        # Set up awaiting confirmation
        conversation_manager._update_state({
            "intent": "schedule_meeting",
            "entities": {"title": "meeting"},
            "awaiting_confirmation": True
        })
        
        # Mock cancellation response
        mock_llm_client.process_message.return_value = {
            "action_type": "cancellation",
            "response": "No problem! The meeting has been cancelled. What else can I help with?",
            "ready_to_execute": False,
            "needs_confirmation": False
        }
        
        result = conversation_manager.process_message("no")
        
        assert "cancelled" in result["response"].lower()
        assert result["ready_to_execute"] == False
    
    def test_email_request(self, conversation_manager, mock_llm_client):
        """Test email sending request"""
        mock_llm_client.process_message.return_value = {
            "action_type": "new_intent",
            "intent": "send_email",
            "entities": {
                "recipient": "john@company.com",
                "body": "I'll be late to the meeting"
            },
            "response": "Should I send an email to john@company.com saying 'I'll be late to the meeting'?",
            "needs_confirmation": True,
            "ready_to_execute": False
        }
        
        result = conversation_manager.process_message("Send email to john@company.com saying I'll be late")
        
        assert result["needs_confirmation"] == True
        
        state = conversation_manager.get_current_state()
        assert state["intent"] == "send_email"
        assert state["entities"]["recipient"] == "john@company.com"
    
    def test_chitchat_handling(self, conversation_manager, mock_llm_client):
        """Test casual conversation"""
        mock_llm_client.process_message.return_value = {
            "action_type": "chitchat",
            "intent": "chitchat",
            "entities": {},
            "response": "Hello! I can help you book meetings or send emails. What would you like to do?",
            "needs_confirmation": False,
            "ready_to_execute": False
        }
        
        result = conversation_manager.process_message("Hello there!")
        
        assert result["ready_to_execute"] == False
        assert result["needs_confirmation"] == False
        assert "hello" in result["response"].lower()
    
    def test_context_is_passed_to_llm(self, conversation_manager, mock_llm_client):
        """Test that conversation context is passed to LLM"""
        # Set some state
        conversation_manager._update_state({
            "intent": "schedule_meeting",
            "entities": {"title": "team sync"},
            "awaiting_confirmation": False
        })
        
        # Process a message
        conversation_manager.process_message("make it tomorrow at 3pm")
        
        # Check that LLM was called with context
        mock_llm_client.process_message.assert_called_once()
        call_args = mock_llm_client.process_message.call_args
        
        # Second argument should be context
        context = call_args[0][1]
        assert context["intent"] == "schedule_meeting"
        assert context["entities"]["title"] == "team sync"
    
    def test_history_tracking(self, conversation_manager, mock_llm_client):
        """Test that conversation history is tracked"""
        # Mock response
        mock_llm_client.process_message.return_value = {
            "action_type": "new_intent",
            "intent": "schedule_meeting",
            "response": "Got it!",
            "entities": {"title": "meeting"}
        }
        
        # Process message
        conversation_manager.process_message("Book a meeting")
        
        # Check history
        state = conversation_manager.get_current_state()
        assert len(state["history"]) == 1
        assert state["history"][0]["user_input"] == "Book a meeting"
        assert state["history"][0]["bot_response"] == "Got it!"
    
    def test_get_state_display(self, conversation_manager):
        """Test state display for UI"""
        # Set some state
        conversation_manager._update_state({
            "intent": "schedule_meeting",
            "entities": {"title": "Team sync", "time": "3pm"},
            "awaiting_confirmation": True
        })
        
        display = conversation_manager.get_state_display()
        
        assert "Intent: schedule_meeting" in display
        assert "Team sync" in display
        assert "3pm" in display
        assert "Awaiting Confirmation: Yes" in display