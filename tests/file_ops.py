import pytest
import json
import os
import tempfile
from datetime import datetime

def test_json_save_meeting():
    """Test saving meeting to JSON file"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test data
        meeting_data = {
            "type": "schedule_meeting",
            "title": "Team Sync",
            "date": "tomorrow",
            "time": "3pm",
            "timestamp": datetime.now().isoformat()
        }
        
        # Save to file
        filename = f"meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(temp_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(meeting_data, f, indent=2)
        
        # Verify file exists
        assert os.path.exists(filepath)
        
        # Verify content
        with open(filepath, 'r') as f:
            loaded_data = json.load(f)
        
        assert loaded_data["type"] == "schedule_meeting"
        assert loaded_data["title"] == "Team Sync"
        assert loaded_data["time"] == "3pm"

def test_json_save_email():
    """Test saving email to JSON file"""
    with tempfile.TemporaryDirectory() as temp_dir:
        email_data = {
            "type": "send_email",
            "recipient": "john@example.com",
            "subject": "Meeting Update",
            "body": "The meeting is postponed",
            "timestamp": datetime.now().isoformat()
        }
        
        filename = f"email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(temp_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(email_data, f)
        
        # Verify
        assert os.path.exists(filepath)
        
        with open(filepath, 'r') as f:
            loaded = json.load(f)
        
        assert loaded["recipient"] == "john@example.com"
        assert loaded["type"] == "send_email"

def test_outbox_directory_creation():
    """Test that outbox directory can be created"""
    with tempfile.TemporaryDirectory() as temp_dir:
        outbox_path = os.path.join(temp_dir, "outbox")
        
        # Should not exist initially
        assert not os.path.exists(outbox_path)
        
        # Create directory
        os.makedirs(outbox_path, exist_ok=True)
        
        # Should exist now
        assert os.path.exists(outbox_path)
        assert os.path.isdir(outbox_path)