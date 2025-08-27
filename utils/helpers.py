# utils/helpers.py
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
import re

def ensure_outbox_exists(outbox_path: str = "outbox") -> str:
    """Ensure the outbox directory exists"""
    if not os.path.exists(outbox_path):
        os.makedirs(outbox_path)
    return outbox_path

def validate_email_addresses(recipients) -> bool:
    """Validate that recipients contain actual email addresses"""
    if not recipients:
        return False
    
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    if isinstance(recipients, str):
        return bool(re.search(email_pattern, recipients))
    elif isinstance(recipients, list):
        return all(re.search(email_pattern, str(recipient)) for recipient in recipients if recipient)
    
    return False

def validate_meeting_data(entities: Dict[str, Any]) -> tuple[bool, list]:
    """
    Validate meeting data has all required components
    Returns: (is_valid, missing_fields)
    """
    required_fields = {
        'title': 'Meeting title',
        'date': 'Meeting date', 
        'time': 'Meeting time'
    }
    
    missing = []
    for field, description in required_fields.items():
        if not entities.get(field) or not str(entities.get(field)).strip():
            missing.append(description)
    
    # Optional but recommended: participants
    if not entities.get('participants'):
        missing.append('Participants (recommended)')
    
    return len(missing) == 0 or (len(missing) == 1 and 'recommended' in missing[0].lower()), missing

def validate_email_data(entities: Dict[str, Any]) -> tuple[bool, list]:
    """
    Validate email data has all required components
    Returns: (is_valid, missing_fields)
    """
    missing = []
    
    # Check recipient (must be actual email addresses)
    recipient = entities.get('recipient')
    if not recipient:
        missing.append('Recipient email address')
    elif not validate_email_addresses(recipient):
        missing.append('Valid email addresses (must contain @domain.com)')
    
    # Check content (need either body or subject, preferably both)
    has_subject = entities.get('subject') and str(entities.get('subject')).strip()
    has_body = entities.get('body') and str(entities.get('body')).strip()
    
    if not has_subject and not has_body:
        missing.append('Email content (subject or body)')
    elif not has_subject:
        missing.append('Subject (recommended)')
    elif not has_body:
        missing.append('Body/message (recommended)')
    
    # Consider valid if we have recipient + (subject or body)
    is_valid = (
        recipient and validate_email_addresses(recipient) and 
        (has_subject or has_body)
    )
    
    return is_valid, missing

def format_recipients_for_email(recipients) -> list:
    """Format recipients as a clean list of email addresses"""
    if not recipients:
        return []
    
    if isinstance(recipients, str):
        # Split by common delimiters and extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, recipients)
        return emails if emails else [recipients]  # Fallback to original if no emails found
    
    elif isinstance(recipients, list):
        formatted = []
        for recipient in recipients:
            if isinstance(recipient, str) and recipient.strip():
                # Try to extract email from each recipient
                email_matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', recipient)
                if email_matches:
                    formatted.extend(email_matches)
                else:
                    formatted.append(recipient.strip())
        return formatted
    
    return [str(recipients)]

def format_participants_for_meeting(participants) -> list:
    """Format participants as a clean list (can be names or emails)"""
    if not participants:
        return []
    
    if isinstance(participants, str):
        # Split by common delimiters
        delimiters = [',', ';', ' and ', ' & ', '\n']
        result = [participants]
        for delimiter in delimiters:
            temp = []
            for item in result:
                temp.extend([part.strip() for part in item.split(delimiter) if part.strip()])
            result = temp
        return result
    
    elif isinstance(participants, list):
        return [str(p).strip() for p in participants if str(p).strip()]
    
    return [str(participants)]

def save_meeting_action(entities: Dict[str, Any], outbox_path: str = "outbox") -> Dict[str, Any]:
    """
    Save meeting action to JSON file
    Returns: result dict with success status and details
    """
    try:
        # Validate meeting data
        is_valid, missing_fields = validate_meeting_data(entities)
        if not is_valid:
            return {
                "success": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}",
                "missing_fields": missing_fields
            }
        
        # Ensure outbox exists
        outbox_path = ensure_outbox_exists(outbox_path)
        
        # Prepare meeting data
        meeting_data = {
            "type": "schedule_meeting",
            "title": entities.get('title', '').strip(),
            "date": entities.get('date', '').strip(),
            "time": entities.get('time', '').strip(),
            "participants": format_participants_for_meeting(entities.get('participants')),
            "location": entities.get('location', '').strip() if entities.get('location') else None,
            "description": entities.get('description', '').strip() if entities.get('description') else None,
            "created_at": datetime.now().isoformat(),
            "status": "scheduled"
        }
        
        # Remove None values
        meeting_data = {k: v for k, v in meeting_data.items() if v is not None}
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_title = re.sub(r'[^\w\-_\.]', '_', entities.get('title', 'meeting'))[:20]
        filename = f"meeting_{safe_title}_{timestamp}.json"
        filepath = os.path.join(outbox_path, filename)
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(meeting_data, f, indent=2, ensure_ascii=False)
        
        return {
            "success": True,
            "filename": filename,
            "filepath": filepath,
            "data": meeting_data,
            "message": f"Meeting '{meeting_data['title']}' saved successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to save meeting: {str(e)}"
        }

def save_email_action(entities: Dict[str, Any], outbox_path: str = "outbox") -> Dict[str, Any]:
    """
    Save email action to JSON file
    Returns: result dict with success status and details
    """
    try:
        # Validate email data
        is_valid, missing_fields = validate_email_data(entities)
        if not is_valid:
            return {
                "success": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}",
                "missing_fields": missing_fields
            }
        
        # Ensure outbox exists
        outbox_path = ensure_outbox_exists(outbox_path)
        
        # Prepare email data
        recipients = format_recipients_for_email(entities.get('recipient'))
        
        email_data = {
            "type": "send_email",
            "recipients": recipients,
            "subject": entities.get('subject', '').strip() or f"Message from Assistant",
            "body": entities.get('body', '').strip() or entities.get('subject', '').strip(),
            "cc": format_recipients_for_email(entities.get('cc')) if entities.get('cc') else [],
            "bcc": format_recipients_for_email(entities.get('bcc')) if entities.get('bcc') else [],
            "priority": entities.get('priority', 'normal'),
            "created_at": datetime.now().isoformat(),
            "status": "ready_to_send"
        }
        
        # Remove empty lists
        if not email_data["cc"]:
            del email_data["cc"]
        if not email_data["bcc"]:
            del email_data["bcc"]
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_subject = re.sub(r'[^\w\-_\.]', '_', email_data['subject'])[:20]
        filename = f"email_{safe_subject}_{timestamp}.json"
        filepath = os.path.join(outbox_path, filename)
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(email_data, f, indent=2, ensure_ascii=False)
        
        return {
            "success": True,
            "filename": filename,
            "filepath": filepath,
            "data": email_data,
            "message": f"Email to {', '.join(recipients[:2])}{'...' if len(recipients) > 2 else ''} saved successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to save email: {str(e)}"
        }

def save_action_to_outbox(action_data: Dict[str, Any], outbox_path: str = "outbox") -> Dict[str, Any]:
    """
    Main function to save any action to outbox
    Routes to appropriate save function based on action type
    """
    if not action_data:
        return {
            "success": False,
            "error": "No action data provided"
        }
    
    action_type = action_data.get('type')
    entities = action_data.get('entities', {})
    
    if action_type == "schedule_meeting":
        return save_meeting_action(entities, outbox_path)
    elif action_type == "send_email":
        return save_email_action(entities, outbox_path)
    else:
        return {
            "success": False,
            "error": f"Unknown action type: {action_type}"
        }

def list_saved_actions(outbox_path: str = "outbox") -> Dict[str, Any]:
    """List all saved actions in outbox"""
    try:
        if not os.path.exists(outbox_path):
            return {
                "success": True,
                "actions": [],
                "message": "No actions saved yet"
            }
        
        files = []
        for filename in os.listdir(outbox_path):
            if filename.endswith('.json'):
                filepath = os.path.join(outbox_path, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    files.append({
                        "filename": filename,
                        "type": data.get('type', 'unknown'),
                        "created_at": data.get('created_at'),
                        "summary": _get_action_summary(data)
                    })
                except Exception as e:
                    files.append({
                        "filename": filename,
                        "type": "error",
                        "error": str(e)
                    })
        
        # Sort by creation time (newest first)
        files.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return {
            "success": True,
            "actions": files,
            "count": len(files)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to list actions: {str(e)}"
        }

def _get_action_summary(data: Dict[str, Any]) -> str:
    """Get a summary of an action for display"""
    action_type = data.get('type', 'unknown')
    
    if action_type == "schedule_meeting":
        title = data.get('title', 'Untitled Meeting')
        date = data.get('date', 'No date')
        time = data.get('time', 'No time')
        return f"{title} on {date} at {time}"
    
    elif action_type == "send_email":
        recipients = data.get('recipients', [])
        subject = data.get('subject', 'No subject')
        recipient_str = ', '.join(recipients[:2])
        if len(recipients) > 2:
            recipient_str += f" and {len(recipients) - 2} others"
        return f"To {recipient_str}: {subject}"
    
    return "Unknown action"
