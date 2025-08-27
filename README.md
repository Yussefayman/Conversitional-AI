# 🤖 Conversational Assistant

A smart conversational assistant built with Python and Gradio that can schedule meetings and send emails using natural language processing.

## ✨ Features

- **📅 Smart Meeting Scheduling**: Book meetings with natural language
- **📧 Intelligent Email Composition**: Draft and send emails conversationally  
- **🔄 Natural Language Corrections**: Make changes with simple phrases like "actually make it 4pm"
- **✅ Confirmation System**: Always confirms before executing actions
- **📊 Live Status Tracking**: Real-time display of conversation state
- **💾 Action History**: All completed actions saved to JSON files
- **🎯 Intent Classification**: Automatically detects what you want to do
- **🧠 Entity Extraction**: Extracts dates, times, recipients, and other details

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Groq API Key (free at [console.groq.com](https://console.groq.com))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Yussefayman/Conversitional-AI
   cd conversational-assistant
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   OUTBOX_DIR=outbox
   MAX_HISTORY=10
   SERVER_PORT=7860
   ```

4. **Run the application**
   ```bash
   python main.py
   ```

5. **Open your browser**
   
   The app will automatically open at `http://127.0.0.1:7860`

## 💬 Usage Examples

### Meeting Scheduling
```
You: "Book a meeting with Sarah tomorrow at 3pm"
Bot: "Should I schedule the meeting for tomorrow at 3pm with Sarah?"
You: "Yes"
Bot: "Perfect! Meeting scheduled and saved to outbox."
```

### Email Composition
```
You: "Send an email to john@company.com about the project update"
Bot: "What would you like to say in the email?"
You: "The project is on track and will be completed by Friday"
Bot: "Should I send an email to john@company.com with the message about project completion?"
You: "Yes"
Bot: "Email drafted and saved to outbox!"
```

### Making Corrections
```
You: "Book a meeting tomorrow at 2pm"
Bot: "What's the meeting about and who should attend?"
You: "Project sync with the team"
Bot: "Should I schedule 'Project sync with the team' for tomorrow at 2pm?"
You: "Actually make it 3pm instead"
Bot: "Updated to 3pm. Should I proceed with the meeting?"
```

## 🏗️ Project Structure

```
conversational-assistant/
├── main.py                    # Main application entry point
├── components/
│   ├── conversation_manager.py # Core conversation logic
│   └── llm_client.py          # Groq LLM integration
├── utils/
│   └── helpers.py             # Utility functions
├── tests/                     # Test suite
├── outbox/                    # Saved actions (created automatically)
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables
└── README.md                  # This file
```

## 🧪 Testing

Run the test suite:
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_ui_basic.py -v        # UI tests
python -m pytest tests/test_conversation_manager.py -v  # Core logic tests
python -m pytest tests/test_file_operations.py -v       # File handling tests
```

Interactive conversation testing:
```bash
python test_conversation.py
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | *required* | Your Groq API key |
| `OUTBOX_DIR` | `outbox` | Directory for saved actions |
| `MAX_HISTORY` | `10` | Max conversation history length |
| `SERVER_PORT` | `7860` | Gradio server port |

### Supported Intents

1. **schedule_meeting** - Book meetings and appointments
2. **send_email** - Compose and send emails  
3. **chitchat** - General conversation and help

### Required Entities

**For Meetings:**
- Title/subject
- Date (supports "tomorrow", "next Monday", etc.)
- Time (supports "3pm", "14:30", etc.)
- Participants (names or email addresses)

**For Emails:**
- Recipient email address
- Subject or body content

## 📁 Output Format

Actions are saved as JSON files in the outbox directory:

**Meeting Example:**
```json
{
  "type": "schedule_meeting",
  "title": "Project Sync",
  "date": "2025-08-29",
  "time": "3pm", 
  "participants": ["sarah@company.com", "john@company.com"],
  "created_at": "2025-08-28T10:30:00",
  "status": "scheduled"
}
```

**Email Example:**
```json
{
  "type": "send_email",
  "recipients": ["john@company.com"],
  "subject": "Project Update",
  "body": "The project is on track for Friday delivery.",
  "created_at": "2025-08-28T10:30:00",
  "status": "ready_to_send"
}
```

## 🛠️ Development

### Adding New Intents

1. Update the LLM prompt in `components/llm_client.py`
2. Add entity validation in `components/conversation_manager.py`
3. Create save function in `utils/helpers.py`
4. Add tests in `tests/`


## 📋 Requirements

See `requirements.txt` for the complete list of dependencies. Key libraries:

- **gradio**: Web interface framework
- **groq**: LLM API client  
- **python-dotenv**: Environment variable management
- **pytest**: Testing framework
