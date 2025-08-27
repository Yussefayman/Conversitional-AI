# main.py
import gradio as gr
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Tuple
from dotenv import load_dotenv

from components.llm_client import LLMClient
from components.conversation_manager import ConversationManager
from utils.helpers import list_saved_actions, get_action_summary, clear_outbox

# Load environment variables
load_dotenv()

# Configuration from environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
print(GROQ_API_KEY)
OUTBOX_DIR = os.getenv("OUTBOX_DIR", "outbox")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "10"))
SERVER_PORT = int(os.getenv("SERVER_PORT", "7860"))

# Global storage for conversation managers (one per session)
conversation_managers: Dict[str, ConversationManager] = {}

def validate_configuration():
    """Validate that required configuration is present"""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not found! Please check your .env file.")
    
    if GROQ_API_KEY == "your-groq-api-key-here":
        raise ValueError("Please set your actual Groq API key in the .env file!")

def initialize_components():
    """Initialize LLM client and create outbox directory"""
    validate_configuration()
    os.environ["GROQ_API_KEY"] = GROQ_API_KEY
    os.makedirs(OUTBOX_DIR, exist_ok=True)
    return LLMClient()

def get_conversation_manager(session_id: str) -> ConversationManager:
    """Get or create conversation manager for a session"""
    if session_id not in conversation_managers:
        llm_client = LLMClient()
        conversation_managers[session_id] = ConversationManager(llm_client, OUTBOX_DIR)
    return conversation_managers[session_id]

def process_message(message: str, history: List[List[str]], session_id: str) -> Tuple[List[List[str]], str, str, str]:
    """Process chat message and return updated components"""
    if not message.strip():
        return history, "", get_state_display(session_id), get_actions_display()
    
    try:
        manager = get_conversation_manager(session_id)
        response = manager.process_message(message.strip())
        
        # Format bot response
        bot_response = response['response']
        
        # Add execution info if action was executed
        if response.get("execution_result"):
            exec_result = response["execution_result"]
            if exec_result["success"]:
                bot_response += f"\n\n✅ **Action Completed!**\n📁 Saved as: `{exec_result['filename']}`"
            else:
                bot_response += f"\n\n❌ **Action Failed:** {exec_result['message']}"
        
        # Add error info if needed
        if response.get('parse_error'):
            bot_response += f"\n\n🔧 *Processing issue - please try rephrasing*"
        elif response.get('error'):
            bot_response += f"\n\n⚠️ *Error: {response['error']}*"
        
        # Update history
        history = history or []
        history.append([message, bot_response])
        
        return history, "", get_state_display(session_id), get_actions_display()
        
    except Exception as e:
        error_msg = f"Sorry, I encountered an error: {str(e)}"
        history = history or []
        history.append([message, error_msg])
        return history, "", get_state_display(session_id), get_actions_display()

def get_state_display(session_id: str) -> str:
    """Get current conversation state display"""
    try:
        if session_id not in conversation_managers:
            return "🌟 **Ready to Help!**\n\nStart a conversation to see live status updates here."
        
        manager = conversation_managers[session_id]
        state = manager.get_current_state()
        
        # Build clean status display
        if not state.get("session_active"):
            return "💬 **Idle**\n\nReady for your next request!"
        
        intent = state.get("intent", "")
        entities = state.get("entities", {})
        awaiting_confirmation = state.get("awaiting_confirmation", False)
        
        # Format based on intent
        if intent == "schedule_meeting":
            display = "📅 **Scheduling Meeting**\n\n"
            if entities.get("title"):
                display += f"**Meeting:** {entities['title']}\n"
            if entities.get("date"):
                display += f"**Date:** {entities['date']}\n"
            if entities.get("time"):
                display += f"**Time:** {entities['time']}\n"
            if entities.get("participants"):
                participants = entities['participants']
                if isinstance(participants, list):
                    display += f"**With:** {', '.join(participants)}\n"
                else:
                    display += f"**With:** {participants}\n"
        
        elif intent == "send_email":
            display = "📧 **Composing Email**\n\n"
            if entities.get("recipient"):
                recipients = entities['recipient']
                if isinstance(recipients, list):
                    display += f"**To:** {', '.join(recipients)}\n"
                else:
                    display += f"**To:** {recipients}\n"
            if entities.get("subject"):
                display += f"**Subject:** {entities['subject']}\n"
            if entities.get("body"):
                body = entities['body']
                if len(body) > 50:
                    body = body[:50] + "..."
                display += f"**Message:** {body}\n"
        else:
            display = "💭 **Chatting**\n\n"
        
        # Add status
        if awaiting_confirmation:
            display += "\n⏳ **Waiting for your confirmation**"
        elif manager.is_ready_for_execution():
            display += "\n✅ **Ready to execute**"
        else:
            missing = manager._get_missing_entities()
            if missing:
                display += f"\n📝 **Need:** {', '.join(missing).replace('_', ' ')}"
        
        return display
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

def get_actions_display() -> str:
    """Get saved actions display"""
    try:
        actions = list_saved_actions(OUTBOX_DIR, limit=8)
        
        if not actions:
            return "📂 **No saved actions**\n\nCompleted meetings and emails will appear here."
        
        display = f"📊 **Recent Actions** ({len(actions)} total)\n\n"
        
        for i, action in enumerate(actions[:5], 1):
            summary = get_action_summary(action)
            timestamp = action.get("saved_at", "")
            
            # Format time
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime("%m/%d %H:%M")
            except:
                time_str = "Recent"
            
            # Clean summary (remove emojis for cleaner look)
            clean_summary = summary.replace("📅 ", "").replace("📧 ", "")
            display += f"**{i}.** {clean_summary}\n"
            display += f"    *{time_str}*\n\n"
        
        if len(actions) > 5:
            display += f"*+ {len(actions) - 5} more actions*\n"
        
        return display
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

def clear_chat(session_id: str) -> Tuple[List[List[str]], str]:
    """Clear current conversation"""
    try:
        if session_id in conversation_managers:
            conversation_managers[session_id].reset_conversation()
        return [], get_state_display(session_id)
    except Exception as e:
        return [], f"Error: {str(e)}"

def clear_actions() -> str:
    """Clear all saved actions"""
    try:
        clear_outbox(OUTBOX_DIR, confirm=True)
        return get_actions_display()
    except Exception as e:
        return f"❌ Error: {str(e)}"

def create_interface():
    """Create the modern Gradio interface"""
    
    # Enhanced CSS for modern look
    css = """
    /* Global Styles */
    .gradio-container {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    /* Chat Container */
    .chat-container {
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        background: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* Status Panels */
    .status-panel {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    .actions-panel {
        background: linear-gradient(135deg, #fefce8 0%, #fef3c7 100%);
        border: 1px solid #fbbf24;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* Buttons */
    .control-btn {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .control-btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Input Field */
    .message-input {
        border-radius: 10px;
        border: 2px solid #e5e7eb;
        transition: border-color 0.2s;
    }
    
    .message-input:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    /* Header */
    .header {
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 12px;
        margin-bottom: 20px;
    }
    """
    
    with gr.Blocks(
        title="🤖 Conversational Assistant",
        theme=gr.themes.Default(
            primary_hue="blue",
            secondary_hue="slate",
            neutral_hue="slate",
            radius_size="lg",
            spacing_size="md"
        ),
        css=css
    ) as interface:
        
        # Session management
        session_id = gr.State(value=str(uuid.uuid4()))
        
        # Header Section
        with gr.Column(elem_classes=["header"]):
            gr.HTML("""
                <div style="text-align: center;">
                    <h1 style="margin: 0; font-size: 2.5rem; font-weight: bold;">
                        🤖 Conversational Assistant
                    </h1>
                    <p style="margin: 10px 0 0 0; font-size: 1.1rem; opacity: 0.9;">
                        Schedule meetings and send emails with natural language
                    </p>
                </div>
            """)
        
        # Main Layout
        with gr.Row(equal_height=True):
            # Left Side - Chat Interface
            with gr.Column(scale=3):
                with gr.Group(elem_classes=["chat-container"]):
                    chatbot = gr.Chatbot(
                        value=[],
                        label="💬 Conversation",
                        height=450,
                        show_label=False,
                        container=False,
                        bubble_full_width=False,
                        type="tuples"
                    )
                    
                    with gr.Row():
                        message_box = gr.Textbox(
                            placeholder="💭 Try: 'Book a meeting with Sarah tomorrow at 3pm'",
                            lines=2,
                            scale=5,
                            container=False,
                            elem_classes=["message-input"]
                        )
                        send_button = gr.Button(
                            "Send 🚀",
                            variant="primary",
                            scale=1,
                            elem_classes=["control-btn"]
                        )
                    
                    with gr.Row():
                        clear_button = gr.Button(
                            "🗑️ Clear Chat",
                            variant="secondary",
                            scale=1,
                            elem_classes=["control-btn"]
                        )
                        example_button = gr.Button(
                            "💡 Examples",
                            variant="secondary", 
                            scale=1,
                            elem_classes=["control-btn"]
                        )
            
            # Right Side - Status & Actions
            with gr.Column(scale=2):
                # Current Status Panel
                status_display = gr.Markdown(
                    value="🌟 **Ready to Help!**\n\nStart a conversation to see live status updates here.",
                    label="🎯 Current Status",
                    elem_classes=["status-panel"]
                )
                
                # Saved Actions Panel
                actions_display = gr.Markdown(
                    value="📂 **No saved actions**\n\nCompleted meetings and emails will appear here.",
                    label="📊 Saved Actions",
                    elem_classes=["actions-panel"]
                )
                
                # Action Buttons
                with gr.Row():
                    refresh_button = gr.Button(
                        "🔄 Refresh",
                        variant="secondary",
                        elem_classes=["control-btn"]
                    )
                    clear_actions_button = gr.Button(
                        "🗑️ Clear All",
                        variant="stop",
                        elem_classes=["control-btn"]
                    )
        
        # Examples Section (initially hidden)
        with gr.Row(visible=False) as examples_row:
            with gr.Column():
                gr.Markdown("""
                ### 💡 Try these examples:
                
                **📅 Meeting Examples:**
                - "Book a meeting with John tomorrow at 2pm"
                - "Schedule a team sync next Monday at 10am"
                - "Set up a client call for Friday afternoon"
                
                **📧 Email Examples:**
                - "Send an email to sarah@company.com about the project"
                - "Email the team about tomorrow's deadline"
                - "Send a follow-up to john@client.com"
                
                **🔄 Corrections:**
                - "Actually make it 4pm instead"
                - "Change the recipient to jane@company.com"
                - "Update the subject to 'Urgent: Project Update'"
                """)
        
        # Footer
        with gr.Row():
            gr.Markdown(
                f"""
                <div style="text-align: center; padding: 20px; color: #6b7280; border-top: 1px solid #e5e7eb; margin-top: 20px;">
                    <small>
                        🔧 Powered by <strong>Groq LLaMA</strong> • 
                        💾 Actions saved to <code>{OUTBOX_DIR}/</code> • 
                        🚀 Built with <strong>Gradio</strong>
                    </small>
                </div>
                """,
                elem_id="footer"
            )
        
        # Event Handlers
        def send_message(message, history, session_id):
            return process_message(message, history, session_id)
        
        def toggle_examples(examples_visible):
            return gr.update(visible=not examples_visible)
        
        # Message sending
        send_button.click(
            fn=send_message,
            inputs=[message_box, chatbot, session_id],
            outputs=[chatbot, message_box, status_display, actions_display],
            api_name="send_message"
        )
        
        message_box.submit(
            fn=send_message,
            inputs=[message_box, chatbot, session_id], 
            outputs=[chatbot, message_box, status_display, actions_display]
        )
        
        # Clear chat
        clear_button.click(
            fn=clear_chat,
            inputs=[session_id],
            outputs=[chatbot, status_display]
        )
        
        # Show/hide examples
        examples_visible = gr.State(False)
        example_button.click(
            fn=toggle_examples,
            inputs=[examples_visible],
            outputs=[examples_row]
        ).then(
            fn=lambda x: not x,
            inputs=[examples_visible],
            outputs=[examples_visible]
        )
        
        # Refresh displays
        refresh_button.click(
            fn=lambda session_id: (get_state_display(session_id), get_actions_display()),
            inputs=[session_id],
            outputs=[status_display, actions_display]
        )
        
        # Clear actions
        clear_actions_button.click(
            fn=clear_actions,
            outputs=[actions_display]
        )
        
        # Initialize displays on load
        interface.load(
            fn=lambda session_id: (get_state_display(session_id), get_actions_display()),
            inputs=[session_id],
            outputs=[status_display, actions_display]
        )
    
    return interface

def main():
    """Main function to run the application"""
    try:
        print("🚀 Initializing Conversational Assistant...")
        
        # Initialize components
        initialize_components()
        print("✅ Components initialized!")
        # Create interface
        demo = create_interface()
        
        print("\n" + "="*60)
        print("🎉 CONVERSATIONAL ASSISTANT READY!")
        print("="*60)
        print("📍 Features:")
        print("  • 📅 Smart meeting scheduling")
        print("  • 📧 Intelligent email composition")
        print("  • 🔄 Natural language corrections")
        print("  • 💾 Automatic action saving")
        print("  • 📊 Live conversation tracking")
        print("="*60)
        
        # Launch interface
        demo.launch(
            server_name="127.0.0.1",
            server_port=SERVER_PORT,
            share=False,
            show_error=True,
            quiet=False,
            inbrowser=True
        )
        
    except Exception as e:
        print(f"❌ Failed to start application: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("  1. Check your .env file")
        print("  2. Verify your Groq API key")
        print("  3. Install requirements: pip install -r requirements.txt")

if __name__ == "__main__":
    main()