# EchoPlanner

**Family Planner AI Agent Assistant**

EchoPlanner is an intelligent family planning assistant that automatically processes emails (text, images, voice) to extract calendar events and manage family schedules. It uses AI agents to understand natural language and multimedia content, then integrates with calendar systems via MCP (Model Context Protocol) connectors.

## 🌟 Features

- **Multi-Modal Email Processing**: Handles text, images, and voice attachments
- **AI-Powered Event Extraction**: Uses OpenAI GPT models to intelligently parse calendar information
- **Family Member Management**: Assign events to specific family members with role-based organization
- **Recurring Events**: Supports daily, weekly, monthly, and yearly recurrence patterns
- **MCP Calendar Integration**: Syncs with external calendar systems using Model Context Protocol
- **RESTful API**: Complete REST API for integration with other applications
- **Command-Line Interface**: Easy-to-use CLI for setup and management
- **Local Storage**: JSON-based local storage with optional external sync

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Email Client  │────│  Email Processor │────│  AI Agents      │
│   (IMAP/POP3)   │    │                  │    │  - Calendar     │
└─────────────────┘    └──────────────────┘    │  - Image OCR    │
                                               │  - Voice STT    │
                                               └─────────────────┘
                                                       │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   REST API      │────│  Main App        │────│  Calendar       │
│   (FastAPI)     │    │  (Coordinator)   │    │  Storage        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                       │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Interface │    │  Configuration   │    │  MCP Connector  │
│                 │    │  Management      │    │  (External Cal) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Email account with IMAP access (Gmail, Outlook, etc.)
- Optional: OpenAI API key for AI features
- Optional: MCP-compatible calendar server

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd echoplanner
   ```

2. **Install dependencies:**
   ```bash
   pip install -e .
   ```

3. **Copy and configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Run initial setup:**
   ```bash
   echoplanner setup
   ```

### Basic Usage

**Start the API server:**
```bash
echoplanner serve
```

**Process emails once:**
```bash
echoplanner process-emails --check-once
```

**Start continuous email monitoring:**
```bash
echoplanner process-emails
```

**Check system status:**
```bash
echoplanner status
```

**Manage family members:**
```bash
echoplanner family add "John Doe" --email john@example.com --role parent
echoplanner family list
```

## 📧 Email Processing

EchoPlanner monitors your email inbox and automatically extracts calendar events from:

### Text Content
- Natural language descriptions of appointments and meetings
- Date and time references in various formats
- Family member mentions and assignments
- Location information

### Image Attachments
- Screenshots of calendar apps
- Photos of handwritten notes or schedules
- Document images with event information
- Uses OCR and AI vision to extract text

### Voice Attachments
- Voice messages with event details
- Audio recordings of meeting plans
- Uses speech-to-text conversion via OpenAI Whisper

### Example Email Processing

**Input Email:**
```
Subject: Soccer Practice This Week

Hi everyone,

Just a reminder that Tommy has soccer practice this Thursday at 4:30 PM 
at Central Park. Sarah also has her piano lesson on Friday at 2:00 PM.

Let me know if you need any changes!
```

**Extracted Events:**
- Tommy's Soccer Practice - Thursday 4:30 PM at Central Park
- Sarah's Piano Lesson - Friday 2:00 PM

## 🔧 Configuration

### Required Settings

Create a `.env` file with these required settings:

```bash
# Email configuration (Required)
EMAIL_HOST=imap.gmail.com
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

# Security (Required)
SECRET_KEY=your-long-random-secret-key
```

### Optional AI Enhancement

```bash
# OpenAI for advanced AI processing
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-3.5-turbo
```

### External Calendar Sync

```bash
# MCP connector for external calendar
MCP_SERVER_URL=https://your-calendar-server.com/api
MCP_API_KEY=your-mcp-api-key
```

## 🔌 API Reference

### Events

**GET /events** - List calendar events
```bash
curl "http://localhost:8000/events?start_date=2024-01-01&end_date=2024-01-31"
```

**POST /events** - Create new event
```bash
curl -X POST "http://localhost:8000/events" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Family Dinner",
    "start_datetime": "2024-01-15T18:00:00",
    "end_datetime": "2024-01-15T19:30:00",
    "assigned_members": ["member-uuid"],
    "tags": ["family", "dinner"]
  }'
```

### Family Management

**GET /family/members** - List family members
**POST /family/members** - Add family member

### Email Processing

**POST /email/process** - Trigger email processing
**GET /email/status** - Check processing status

## 🧪 Development

### Running Tests

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=echoplanner
```

### Code Quality

```bash
# Format code
black src/

# Sort imports
isort src/

# Type checking
mypy src/

# Linting
flake8 src/
```

## 🎯 Use Cases

### Family Scheduling
- Automatically add kids' sports practices from coach emails
- Track medical appointments from clinic confirmations
- Sync vacation plans from travel booking emails

### Work-Life Balance
- Separate work and personal calendar events
- Assign events to appropriate family members
- Set priorities and reminders automatically

### Multi-Modal Input
- Process voice messages about upcoming events
- Extract schedules from screenshot images
- Handle mixed-format communication

## 🔒 Security & Privacy

- **Local-First**: All data stored locally by default
- **Email Security**: Uses secure IMAP/SSL connections
- **API Keys**: Environment variable configuration
- **Data Retention**: Configurable cleanup policies
- **Access Control**: Family member-based event assignment

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: Report bugs or request features via GitHub Issues
- **Documentation**: Check the `/docs` directory for detailed guides
- **API Docs**: Visit `http://localhost:8000/docs` when running the server

## 🗺️ Roadmap

- [ ] **Calendar App Integrations**: Google Calendar, Outlook, Apple Calendar
- [ ] **Mobile App**: React Native companion app
- [ ] **Smart Notifications**: Intelligent reminder system
- [ ] **Natural Language Queries**: "Show me this week's events"
- [ ] **Conflict Detection**: Automatic scheduling conflict resolution
- [ ] **Advanced Recurrence**: Complex recurring patterns
- [ ] **Multi-Tenant**: Support for multiple families/organizations

---

**Made with ❤️ for busy families everywhere**