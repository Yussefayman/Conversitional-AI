# tests/test_ui_basic.py
import pytest

def test_gradio_import():
    """Test that Gradio can be imported"""
    try:
        import gradio as gr
        assert True
    except ImportError:
        pytest.fail("Gradio not installed")

def test_basic_gradio_interface():
    """Test that we can create a basic interface"""
    import gradio as gr
    
    def dummy_chat(message, history):
        return history + [[message, f"Echo: {message}"]]
    
    # Should not raise an error
    try:
        interface = gr.ChatInterface(fn=dummy_chat)
        assert interface is not None
    except Exception as e:
        pytest.fail(f"Failed to create Gradio interface: {e}")

def test_conversation_id_generation():
    """Test UUID generation for conversation tracking"""
    import uuid
    
    # Generate two IDs
    id1 = str(uuid.uuid4())
    id2 = str(uuid.uuid4())
    
    # Should be different
    assert id1 != id2
    assert len(id1) > 0
    assert len(id2) > 0