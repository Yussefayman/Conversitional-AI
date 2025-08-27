# test_conversation.py
import os
import sys
from datetime import datetime, timedelta
from components.llm_client import LLMClient
from components.conversation_manager import ConversationManager

GROQ_API_KEY = ""

def format_date_for_display(date_str):
    """Format dates for better display in test output"""
    try:
        if isinstance(date_str, str) and len(date_str) == 10 and date_str.count('-') == 2:
            # It's a YYYY-MM-DD format
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            today = datetime.now().date()
            date_only = date_obj.date()
            
            # Calculate days difference
            days_diff = (date_only - today).days
            
            # Format with relative info
            if days_diff == 0:
                relative = "Today"
            elif days_diff == 1:
                relative = "Tomorrow"
            elif days_diff == -1:
                relative = "Yesterday"
            elif days_diff > 1 and days_diff <= 7:
                relative = f"In {days_diff} days"
            elif days_diff < -1 and days_diff >= -7:
                relative = f"{abs(days_diff)} days ago"
            elif days_diff > 7:
                weeks = days_diff // 7
                if weeks == 1:
                    relative = "Next week"
                else:
                    relative = f"In {weeks} weeks"
            else:
                relative = f"{abs(days_diff)} days ago"
            
            return f"{date_str} ({date_obj.strftime('%A, %B %d')}) - {relative}"
        return date_str
    except:
        return date_str

def format_entity_value(key, value):
    """Format entity values for display"""
    if not value:
        return value
    
    # Special formatting for different entity types
    if key == 'date':
        return format_date_for_display(value)
    elif key == 'recipient' and isinstance(value, list):
        return ', '.join(value)
    elif key == 'participants' and isinstance(value, list):
        return ', '.join(value)
    else:
        return value

def show_current_date_info():
    """Show current date context"""
    now = datetime.now()
    print(f"📅 Current Date: {now.strftime('%A, %B %d, %Y')}")
    print(f"📅 Tomorrow: {(now + timedelta(days=1)).strftime('%A, %B %d, %Y')}")
    print(f"📅 In 1 week: {(now + timedelta(weeks=1)).strftime('%A, %B %d, %Y')}")
    print(f"📅 In 2 weeks: {(now + timedelta(weeks=2)).strftime('%A, %B %d, %Y')}")

def test_conversation():
    """Interactive conversation test with date awareness"""
    
    # Set API key
    os.environ["GROQ_API_KEY"] = GROQ_API_KEY
    
    # Check if API key is set
    if GROQ_API_KEY == "your-groq-api-key-here":
        print("❌ Please set your GROQ_API_KEY in the file!")
        print("Edit test_conversation.py and replace 'your-groq-api-key-here' with your actual key")
        return
    
    try:
        # Initialize components
        print("🚀 Initializing Conversational Assistant...")
        llm_client = LLMClient()
        conversation_manager = ConversationManager(llm_client)
        print("✅ Ready!\n")
        
        # Show current date context
        show_current_date_info()
        
        
        conversation_count = 0
        
        while True:
            try:
                # Get user input
                print("\n" + "-" * 60)
                user_input = input("👤 You: ").strip()
                
                # Check for quit
                if user_input.lower() in ['quit', 'exit', 'q', 'bye']:
                    print("👋 Goodbye!")
                    break
                
                if not user_input:
                    print("Please enter a message.")
                    continue
                
                conversation_count += 1
                print(f"\n🤖 Processing message #{conversation_count}...")
                
                # Process message
                response = conversation_manager.process_message(user_input)
                
                # Display response
                print(f"\n🤖 Bot: {response['response']}")
                
                # Show technical details in a clean box
                print(f"\n📊 DETAILS:")
                print(f"┌─ Action: {response.get('action_type', 'N/A')}")
                print(f"├─ Intent: {response.get('intent', 'N/A')}")
                print(f"├─ Needs Confirmation: {response.get('needs_confirmation', False)}")
                print(f"└─ Ready to Execute: {response.get('ready_to_execute', False)}")
                
                # Show entities if present
                if response.get('entities'):
                    print(f"\n📋 ENTITIES:")
                    for key, value in response['entities'].items():
                        if value:  # Only show non-empty
                            formatted_value = format_entity_value(key, value)
                            print(f"   • {key.title()}: {formatted_value}")
                
                # Show missing entities if any
                if response.get('missing_entities'):
                    print(f"\n❓ MISSING INFO:")
                    missing = response['missing_entities']
                    for item in missing:
                        if item == 'email_addresses':
                            print(f"   • 📧 Email addresses needed")
                        else:
                            print(f"   • {item.replace('_', ' ').title()}")
                
                # Show correction info
                if response.get('correction_detected'):
                    print(f"\n🔄 CORRECTION DETECTED!")
                
                # Show current conversation state
                print(f"\n📱 CURRENT STATE:")
                state_display = conversation_manager.get_state_display()
                # Format the state display nicely
                for line in state_display.split('\n'):
                    if line.strip():
                        print(f"   {line}")
                
                # Show if ready for execution
                if conversation_manager.is_ready_for_execution():
                    action_data = conversation_manager.get_action_for_execution()
                    print(f"\n🎯 READY FOR EXECUTION:")
                    print(f"   📝 Type: {action_data['type']}")
                    print(f"   📦 Data:")
                    
                    # Format execution data nicely
                    for key, value in action_data['entities'].items():
                        if value:
                            formatted_value = format_entity_value(key, value)
                            print(f"      • {key.title()}: {formatted_value}")
                    
                    # Show filename that would be created
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{action_data['type']}_{timestamp}.json"
                    print(f"   💾 Would save to: /outbox/{filename}")
                
                # Show error if any
                if 'error' in response:
                    print(f"\n⚠️  ERROR: {response['error']}")
                
                # Show parse error details if any
                if 'parse_error' in response:
                    print(f"\n🐛 PARSE ERROR: {response['parse_error']}")
                    if 'raw_response' in response:
                        print(f"   Raw LLM Response: {response['raw_response'][:200]}...")
                
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted by user. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                print("Continuing...")
                
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        print("Check your API key and make sure components/ files exist")
        return

# Additional helper function to test date parsing
def test_date_examples():
    """Test various date formats"""
    print("🧪 Testing Date Parsing Examples")
    print("-" * 40)
    
    now = datetime.now()
    examples = [
        ("tomorrow", now + timedelta(days=1)),
        ("in 2 days", now + timedelta(days=2)),
        ("next week", now + timedelta(weeks=1)),
        ("in two weeks", now + timedelta(weeks=2)),
        ("in 10 days", now + timedelta(days=10)),
    ]
    
    for description, date_obj in examples:
        formatted = format_date_for_display(date_obj.strftime('%Y-%m-%d'))
        print(f"'{description}' → {formatted}")

if __name__ == "__main__":
    print("🧪 Interactive Conversation Test - Date Aware Version")
    print("-" * 50)
    
    # Show example of date parsing
    print("\n🗓️  Date Format Examples:")
    test_date_examples()
    print("-" * 50)
    
    # Run main test
    test_conversation()