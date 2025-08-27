# tests/test_file_operations.py
import pytest
import json
import os
import tempfile
from datetime import datetime
import os
import sys
sys.path.append(os.getcwd())
from utils.helpers import save_action_to_outbox, create_outbox_directory, list_saved_actions

class TestFileOperations:
    
    def test_create_outbox_directory(self):
        """Test creating outbox directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            outbox_path = os.path.join(temp_dir, "outbox")
            
            # Should not exist initially
            assert not os.path.exists(outbox_path)
            
            # Create directory
            result_path = create_outbox_directory(outbox_path)
            
            # Should exist now
            assert os.path.exists(outbox_path)
            assert os.path.isdir(outbox_path)
            assert result_path == outbox_path
    
    def test_save_meeting_action(self):
        """Test saving meeting action to JSON file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test meeting data
            action_data = {
                "type": "schedule_meeting",
                "entities": {
                    "title": "Team Sync",
                    "date": "2025-08-28",
                    "time": "3pm",
                    "participants": ["Sarah", "Ahmed"]
                },
                "timestamp": datetime.now().isoformat(),
                "conversation_id": "test-123"
            }
            
            # Save to file
            result = save_action_to_outbox(action_data, outbox_dir=temp_dir)
            
            # Check result
            assert result["success"] == True
            assert result["filename"].startswith("schedule_meeting_")
            assert result["filename"].endswith(".json")
            assert result["filepath"] == os.path.join(temp_dir, result["filename"])
            
            # Verify file exists
            assert os.path.exists(result["filepath"])
            
            # Verify content
            with open(result["filepath"], 'r') as f:
                loaded_data = json.load(f)
            
            assert loaded_data["type"] == "schedule_meeting"
            assert loaded_data["entities"]["title"] == "Team Sync"
            assert loaded_data["entities"]["time"] == "3pm"
            assert "participants" in loaded_data["entities"]
    
    def test_save_email_action(self):
        """Test saving email action to JSON file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            action_data = {
                "type": "send_email",
                "entities": {
                    "recipient": ["sarah@company.com", "ahmed@company.com"],
                    "subject": "Meeting Reminder",
                    "body": "Don't forget about our meeting tomorrow!"
                },
                "timestamp": datetime.now().isoformat(),
                "conversation_id": "test-456"
            }
            
            result = save_action_to_outbox(action_data, outbox_dir=temp_dir)
            
            # Check result
            assert result["success"] == True
            assert result["filename"].startswith("send_email_")
            
            # Verify content
            with open(result["filepath"], 'r') as f:
                loaded_data = json.load(f)
            
            assert loaded_data["type"] == "send_email"
            assert loaded_data["entities"]["subject"] == "Meeting Reminder"
            assert len(loaded_data["entities"]["recipient"]) == 2
    
    def test_filename_generation(self):
        """Test that filenames are unique and properly formatted"""
        with tempfile.TemporaryDirectory() as temp_dir:
            action_data = {
                "type": "schedule_meeting",
                "entities": {"title": "Meeting 1"},
                "timestamp": datetime.now().isoformat()
            }
            
            # Save two actions
            result1 = save_action_to_outbox(action_data, outbox_dir=temp_dir)
            
            # Slight delay to ensure different timestamp
            import time
            time.sleep(0.1)
            
            action_data["entities"]["title"] = "Meeting 2"
            action_data["timestamp"] = datetime.now().isoformat()
            result2 = save_action_to_outbox(action_data, outbox_dir=temp_dir)
            
            # Filenames should be different
            assert result1["filename"] != result2["filename"]
            
            # Both files should exist
            assert os.path.exists(result1["filepath"])
            assert os.path.exists(result2["filepath"])
    
    def test_list_saved_actions(self):
        """Test listing saved actions from outbox"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save multiple actions
            actions = [
                {
                    "type": "schedule_meeting",
                    "entities": {"title": "Meeting 1", "date": "2025-08-28"},
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "type": "send_email", 
                    "entities": {"recipient": "test@email.com", "subject": "Test"},
                    "timestamp": datetime.now().isoformat()
                }
            ]
            
            saved_files = []
            for action in actions:
                result = save_action_to_outbox(action, outbox_dir=temp_dir)
                saved_files.append(result["filename"])
            
            # List actions
            listed_actions = list_saved_actions(outbox_dir=temp_dir)
            
            # Should find both actions
            assert len(listed_actions) == 2
            
            # Check structure
            for action in listed_actions:
                assert "filename" in action
                assert "type" in action
                assert "timestamp" in action
                assert "entities" in action
            
            # Check types are correct
            types = [action["type"] for action in listed_actions]
            assert "schedule_meeting" in types
            assert "send_email" in types
    
    def test_error_handling_invalid_directory(self):
        """Test error handling for invalid directory"""
        action_data = {
            "type": "schedule_meeting",
            "entities": {"title": "Test"},
            "timestamp": datetime.now().isoformat()
        }
        
        # Try to save to invalid directory
        result = save_action_to_outbox(action_data, outbox_dir="/invalid/path/that/doesnt/exist")
        
        assert result["success"] == False
        assert "error" in result
        assert "filepath" not in result
    
    def test_error_handling_invalid_data(self):
        """Test error handling for invalid action data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Missing required fields
            invalid_data = {"invalid": "data"}
            
            result = save_action_to_outbox(invalid_data, outbox_dir=temp_dir)
            
            assert result["success"] == False
            assert "error" in result
    
    def test_json_formatting(self):
        """Test that saved JSON is properly formatted"""
        with tempfile.TemporaryDirectory() as temp_dir:
            action_data = {
                "type": "schedule_meeting",
                "entities": {
                    "title": "Formatted Meeting",
                    "date": "2025-08-28",
                    "participants": ["Person 1", "Person 2"]
                },
                "timestamp": datetime.now().isoformat()
            }
            
            result = save_action_to_outbox(action_data, outbox_dir=temp_dir)
            
            # Read file as text to check formatting
            with open(result["filepath"], 'r') as f:
                content = f.read()
            
            # Should be properly indented JSON
            assert "{\n" in content  # Should have newlines and indentation
            assert "  \"type\"" in content  # Should be indented
            
            # Should be valid JSON
            parsed = json.loads(content)
            assert parsed["type"] == "schedule_meeting"