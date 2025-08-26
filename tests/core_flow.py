import pytest
from unittest.mock import Mock

def test_conversation_state_tracking():
    """Test basic state management"""
    # Simple state object
    state = {
        "intent": None,
        "entities": {},
        "awaiting_confirmation": False
    }
    
    # Simulate processing a message
    state["intent"] = "schedule_meeting"
    state["entities"] = {"title": "meeting", "time": "3pm"}
    
    assert state["intent"] == "schedule_meeting"
    assert state["entities"]["time"] == "3pm"

def test_entity_extraction_basic():
    """Test that we can extract basic info from text"""
    text = "Book meeting with Sara tomorrow at 3pm"
    
    # Simple regex-based extraction for testing
    import re
    
    # Extract email
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    
    # Extract time
    times = re.findall(r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)\b', text)
    
    # For this text, should find time but no email
    assert len(times) == 1
    assert "3pm" in times[0].lower()
    assert len(emails) == 0

def test_confirmation_flow():
    """Test yes/no handling"""
    responses = ["yes", "y", "yeah", "sure", "ok"]
    negative_responses = ["no", "n", "nope", "cancel"]
    
    def is_positive(response):
        return response.lower().strip() in ["yes", "y", "yeah", "sure", "ok", "yep"]
    
    def is_negative(response):
        return response.lower().strip() in ["no", "n", "nope", "cancel", "stop"]
    
    # Test positive responses
    for resp in responses:
        assert is_positive(resp) == True
    
    # Test negative responses  
    for resp in negative_responses:
        assert is_negative(resp) == True