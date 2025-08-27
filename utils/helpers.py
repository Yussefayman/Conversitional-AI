# utils/helpers.py
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

def create_outbox_directory(outbox_path: str = "outbox") -> str:
    """
    Create the outbox directory if it doesn't exist
    
    Args:
        outbox_path: Path to the outbox directory
        
    Returns:
        str: Path to the created directory
    """
    try:
        os.makedirs(outbox_path, exist_ok=True)
        return outbox_path
    except Exception as e:
        raise Exception(f"Failed to create outbox directory: {str(e)}")

def generate_filename(action_type: str, timestamp: Optional[str] = None) -> str:
    """
    Generate a unique filename for the action
    
    Args:
        action_type: Type of action (schedule_meeting, send_email)
        timestamp: Optional timestamp string, uses current time if not provided
        
    Returns:
        str: Generated filename
    """
    if timestamp:
        try:
            # Parse the ISO timestamp and format for filename
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = dt.strftime('%Y%m%d_%H%M%S_%f')[:-3]  # Include milliseconds
        except:
            # Fallback to current time if parsing fails
            time_str = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
    else:
        time_str = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
    
    return f"{action_type}_{time_str}.json"

def validate_action_data(action_data: Dict[str, Any]) -> bool:
    """
    Validate that action data has required fields
    
    Args:
        action_data: Action data dictionary
        
    Returns:
        bool: True if valid, False otherwise
    """
    required_fields = ["type", "entities"]
    
    # Check required top-level fields
    for field in required_fields:
        if field not in action_data:
            return False
    
    # Check that type is valid
    valid_types = ["schedule_meeting", "send_email"]
    if action_data["type"] not in valid_types:
        return False
    
    # Check that entities is a dict
    if not isinstance(action_data["entities"], dict):
        return False
    
    # Type-specific validation
    entities = action_data["entities"]
    
    if action_data["type"] == "schedule_meeting":
        # Meeting should have at least title
        if not entities.get("title"):
            return False
            
    elif action_data["type"] == "send_email":
        # Email should have recipient
        if not entities.get("recipient"):
            return False
    
    return True

def save_action_to_outbox(action_data: Dict[str, Any], outbox_dir: str = "outbox") -> Dict[str, Any]:
    """
    Save action data to a JSON file in the outbox directory
    
    Args:
        action_data: Dictionary containing action data
        outbox_dir: Directory to save the file in
        
    Returns:
        Dict with success status, filename, filepath, and any error info
    """
    try:
        # Validate input data
        if not validate_action_data(action_data):
            return {
                "success": False,
                "error": "Invalid action data format or missing required fields"
            }
        
        # Ensure outbox directory exists
        create_outbox_directory(outbox_dir)
        
        # Generate filename
        filename = generate_filename(
            action_data["type"], 
            action_data.get("timestamp")
        )
        
        filepath = os.path.join(outbox_dir, filename)
        
        # Add metadata to the action data
        save_data = action_data.copy()
        save_data["saved_at"] = datetime.now().isoformat()
        save_data["filename"] = filename
        
        # Save to file with pretty formatting
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        return {
            "success": True,
            "filename": filename,
            "filepath": filepath,
            "message": f"Action saved successfully as {filename}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to save action: {str(e)}"
        }

def list_saved_actions(outbox_dir: str = "outbox", limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    List all saved actions from the outbox directory
    
    Args:
        outbox_dir: Directory to read from
        limit: Maximum number of actions to return (most recent first)
        
    Returns:
        List of action dictionaries
    """
    try:
        if not os.path.exists(outbox_dir):
            return []
        
        actions = []
        
        # Get all JSON files
        json_files = [f for f in os.listdir(outbox_dir) if f.endswith('.json')]
        
        # Sort by filename (which includes timestamp)
        json_files.sort(reverse=True)  # Most recent first
        
        # Apply limit if specified
        if limit:
            json_files = json_files[:limit]
        
        # Read each file
        for filename in json_files:
            filepath = os.path.join(outbox_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    action_data = json.load(f)
                    action_data["filename"] = filename  # Ensure filename is included
                    actions.append(action_data)
            except Exception as e:
                # Skip files that can't be read, but continue with others
                print(f"Warning: Could not read {filename}: {str(e)}")
                continue
        
        return actions
        
    except Exception as e:
        print(f"Error listing saved actions: {str(e)}")
        return []

def get_action_summary(action_data: Dict[str, Any]) -> str:
    """
    Generate a human-readable summary of an action
    
    Args:
        action_data: Action data dictionary
        
    Returns:
        str: Human-readable summary
    """
    try:
        action_type = action_data.get("type", "unknown")
        entities = action_data.get("entities", {})
        
        if action_type == "schedule_meeting":
            title = entities.get("title", "Meeting")
            date = entities.get("date", "TBD")
            time = entities.get("time", "TBD")
            participants = entities.get("participants", [])
            
            summary = f"📅 {title}"
            if date != "TBD" or time != "TBD":
                summary += f" on {date} at {time}"
            if participants:
                if isinstance(participants, list):
                    summary += f" with {', '.join(participants)}"
                else:
                    summary += f" with {participants}"
            
            return summary
            
        elif action_type == "send_email":
            recipient = entities.get("recipient", "Unknown")
            subject = entities.get("subject", entities.get("title", "No subject"))
            
            summary = f"📧 Email to {recipient}"
            if subject:
                summary += f": {subject}"
            
            return summary
        
        else:
            return f"❓ Unknown action: {action_type}"
            
    except Exception:
        return "❓ Could not generate summary"

def clear_outbox(outbox_dir: str = "outbox", confirm: bool = False) -> Dict[str, Any]:
    """
    Clear all files from the outbox directory
    
    Args:
        outbox_dir: Directory to clear
        confirm: Must be True to actually delete files
        
    Returns:
        Dict with success status and info about deleted files
    """
    if not confirm:
        return {
            "success": False,
            "error": "Must set confirm=True to delete files"
        }
    
    try:
        if not os.path.exists(outbox_dir):
            return {
                "success": True,
                "message": "Outbox directory doesn't exist - nothing to clear",
                "files_deleted": 0
            }
        
        json_files = [f for f in os.listdir(outbox_dir) if f.endswith('.json')]
        files_deleted = 0
        
        for filename in json_files:
            filepath = os.path.join(outbox_dir, filename)
            try:
                os.remove(filepath)
                files_deleted += 1
            except Exception as e:
                print(f"Warning: Could not delete {filename}: {str(e)}")
        
        return {
            "success": True,
            "message": f"Cleared {files_deleted} files from outbox",
            "files_deleted": files_deleted
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to clear outbox: {str(e)}"
        }
