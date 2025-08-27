import pytest
import os
from unittest.mock import Mock, patch
import os
import sys
sys.path.append(os.getcwd())
from components.llm_client import LLMClient


class TestLLMClient:
    
    def test_llm_client_initialization(self):
        """Test LLM client can be created"""
        client = LLMClient()
        assert client is not None
        assert hasattr(client, 'process_message')
    
    @pytest.mark.skipif(not os.getenv("GROQ_API_KEY"), reason="No API key")
    def test_real_groq_connection(self):
        """Test actual Groq API call"""
        client = LLMClient()
        
        response = client.process_message(
            user_input="Hello", 
            context={"intent": None, "entities": {}}
        )
        
        assert response is not None
        assert "response" in response
        assert isinstance(response, dict)
    
    def test_intent_classification_format(self):
        """Test that response has correct format"""
        client = LLMClient()
        
        # Mock the Groq response
        with patch.object(client, '_call_groq') as mock_groq:
            mock_groq.return_value = '''{
                "action_type": "new_intent",
                "intent": "schedule_meeting",
                "entities": {"title": "meeting", "time": "3pm"},
                "response": "Should I book a meeting at 3pm?",
                "needs_confirmation": true,
                "ready_to_execute": false
            }'''
            
            result = client.process_message("Book meeting at 3pm", {})
            
            # Check format
            assert result["action_type"] == "new_intent"
            assert result["intent"] == "schedule_meeting"
            assert result["entities"]["time"] == "3pm"
            assert result["needs_confirmation"] == True
    
    def test_correction_handling(self):
        """Test correction detection and handling"""
        client = LLMClient()
        
        context = {
            "intent": "schedule_meeting",
            "entities": {"title": "meeting", "time": "3pm"},
            "awaiting_confirmation": True
        }
        
        with patch.object(client, '_call_groq') as mock_groq:
            mock_groq.return_value = '''{
                "action_type": "correction",
                "correction_detected": true,
                "entities": {"time": "4pm"},
                "response": "Updated to 4pm. Should I proceed?",
                "needs_confirmation": true
            }'''
            
            result = client.process_message("actually make it 4pm", context)
            
            assert result["correction_detected"] == True
            assert result["entities"]["time"] == "4pm"