import pytest
import os
from groq import Groq

@pytest.mark.skipif(not os.getenv("GROQ_API_KEY"), reason="No API key provided")
def test_groq_connection():
    """Test if Groq API is working"""
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "user", "content": "Say 'test successful'"}],
        max_tokens=10
    )
    
    assert response.choices[0].message.content is not None
    assert len(response.choices[0].message.content) > 0

def test_intent_classification():
    """Test if LLM can classify basic intents"""
    # Skip if no API key
    if not os.getenv("GROQ_API_KEY"):
        pytest.skip("No API key")
        
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    prompt = """
    Classify this intent: "Book a meeting with Sara tomorrow"
    Options: schedule_meeting, send_email, chitchat
    Answer with just the intent name.
    """
    
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=20
    )
    
    result = response.choices[0].message.content.strip().lower()
    assert "schedule_meeting" in result or "meeting" in result