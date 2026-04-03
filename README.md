
# Custodian AI Army 🤖⚡


A futuristic AI agent orchestration system inspired by Abacus.ai, featuring multiple specialized agents powered by Google's Gemini model. Each main agent can orchestrate sub-agents to handle complex tasks efficiently.

---

## 📝 Project Overview

Custodian AI Army is a modular, multi-agent orchestration platform. It leverages Google's Gemini models for all agent intelligence, with a focus on extensibility, real-time communication, and a modern UI. The system is built with Python (FastAPI backend) and a vanilla JS/CSS frontend.

**Key Agent:** All advanced agent capabilities are now powered by the GeminiAgent (formerly NemotronAgent), using the `gemini-2.5-flash` model for fast, high-quality responses.

---

## 🌟 Features

- **Multi-Agent Architecture**: Main agents with specialized sub-agents
- **Futuristic UI**: Inspired by Abacus.ai with cyberpunk aesthetics
- **Real-time Communication**: WebSocket-based agent communication
- **Task Orchestration**: Intelligent task delegation and synthesis
- **Specialized Agents**: 
  - CommanderAI (Coordinator)
  - AnalystAI (Data & Market Analysis)
  - CreativeAI (Writing & Design)
  - TechnicalAI (Coding & Architecture)
  - ResearchAI (Fact-checking & Trends)

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Gemini API Key (add to .env file)


### Installation & Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd CustodianAIArmy
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Upgrade pip and install setuptools**
   ```bash
   pip install --upgrade pip setuptools wheel
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```


5. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY (from Google Generative Language API)
   # Optionally adjust APP_PORT, DATABASE_URL, etc.
   ```


6. **Run the application**
   ```bash
   python3 main.py
   ```

   Or, for development with auto-reload (if supported):
   ```bash
   uvicorn src.api.routes:app --reload
   ```


7. **Access the interface**
   Open your browser and navigate to [http://localhost:8000](http://localhost:8000)


---

## 🏗️ Architecture & Components


### Agent Hierarchy

```
CommanderAI (Main Coordinator)
├── AnalystAI (Main)
│   ├── DataAnalystAI (Sub)
│   └── MarketAnalystAI (Sub)
├── CreativeAI (Main)
│   ├── WriterAI (Sub)
│   └── DesignerAI (Sub)
├── TechnicalAI (Main)
│   ├── CoderAI (Sub)
│   └── ArchitectAI (Sub)
└── ResearchAI (Main)
   ├── FactCheckerAI (Sub)
   └── TrendAnalystAI (Sub)

**All agent logic is now implemented in `src/agents/gemini_agent.py`.**
```


### System Components

- **FastAPI Backend**: RESTful API for agent management
- **Agent Manager**: Orchestrates all agents and communication
- **Gemini Integration**: Google's Gemini model (all agents use `gemini-2.5-flash`)
- **Futuristic Frontend**: React-like vanilla JS with cyberpunk UI
- **Real-time Updates**: WebSocket communication for live status

## 🎮 Usage

### Dashboard
- Monitor all agents in real-time
- View system statistics and health
- Quick access to main functions

### Agent Army
- Browse all available agents
- View capabilities and specializations
- Monitor agent status and hierarchy

### AI Chat
- Direct communication with any agent
- Context-aware conversations
- Multi-agent collaboration

### Task Center
- Create and execute complex tasks
- Automatic agent selection
- Task result synthesis

### Analytics
- Performance monitoring
- Usage statistics
- Agent efficiency metrics

## 🔧 Configuration

### Environment Variables

```bash
# Google Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_API_URL=https://generativelanguage.googleapis.com/v1beta

# Application Configuration
APP_HOST=localhost
APP_PORT=8000
DEBUG=True

# Database Configuration
DATABASE_URL=sqlite:///./custodian_ai.db

# Redis Configuration (for agent communication)
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your_secret_key_here
JWT_SECRET=your_jwt_secret_here

# Logging
LOG_LEVEL=INFO
```

## 📡 API Endpoints

### Agent Management
- `GET /api/v1/agents` - List all agents
- `GET /api/v1/agents/{agent_id}` - Get agent details
- `GET /api/v1/army/status` - Get army status

### Communication
- `POST /api/v1/chat` - Chat with agents
- `POST /api/v1/messages/send` - Send direct messages
- `POST /api/v1/messages/broadcast` - Broadcast to all agents

### Task Execution
- `POST /api/v1/tasks/execute` - Execute tasks
- `GET /api/v1/specializations` - Get available specializations

## 🎨 UI Features

### Futuristic Design Elements
- **Cyberpunk Color Scheme**: Neon blues, cyans, and purples
- **Animated Components**: Smooth transitions and hover effects
- **Particle Background**: Dynamic particle system
- **Glowing Effects**: CSS-based neon glow effects
- **Responsive Design**: Mobile-friendly interface

### Interactive Components
- **Real-time Status Updates**: Live agent monitoring
- **Drag & Drop**: Task assignment interface
- **Voice Commands**: Speech-to-text integration (planned)
- **Dark Theme**: Optimized for extended use

## 🔮 Agent Specializations

### CommanderAI (Coordinator)
- Task delegation and orchestration
- System-wide coordination
- Resource management

### AnalystAI (Analysis)
- Data analysis and interpretation
- Market research and trends
- Statistical modeling

### CreativeAI (Creative)
- Content creation and writing
- Design and visual concepts
- Creative problem solving

### TechnicalAI (Technical)
- Code generation and review
- System architecture design
- Technical documentation

### ResearchAI (Research)
- Information gathering and verification
- Trend analysis and forecasting
- Fact-checking and validation

## 🚀 Advanced Features

### Task Orchestration
- **Intelligent Routing**: Automatic agent selection based on task type
- **Sub-agent Delegation**: Main agents can delegate to specialized sub-agents
- **Result Synthesis**: Combine outputs from multiple agents
- **Error Handling**: Graceful failure recovery and retry logic

### Communication System
- **Message Queue**: Asynchronous message processing
- **Broadcasting**: System-wide announcements
- **Context Preservation**: Maintain conversation history
- **Real-time Updates**: Live status and progress tracking

## 🛠️ Development

### Project Structure
```
CustodianAIArmy/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment configuration template
├── src/
│   ├── agents/            # Agent implementations
│   ├── api/               # FastAPI routes and endpoints
│   └── core/              # Core utilities and configuration
└── static/
    ├── index.html         # Main UI
    ├── css/styles.css     # Futuristic styling
    └── js/app.js          # Frontend application logic
```


### Adding New Agents

1. **Create Agent Class**
   ```python
   from src.agents.gemini_agent import GeminiAgent
   
   class CustomAgent(GeminiAgent):
       def __init__(self):
           super().__init__(
               name="CustomAgent",
               specialization="custom",
               agent_type=AgentType.MAIN
           )
   ```

2. **Register with Manager**
   ```python
   # In agent_manager.py
   custom_agent = CustomAgent()
   self.register_agent(custom_agent)
   ```

3. **Update UI**
   - Add agent to frontend display
   - Update specialization mappings
   - Add custom capabilities


---

## 🔒 Security

- **API Key Management**: Secure storage of Gemini API keys
- **Input Validation**: Comprehensive request validation
- **Rate Limiting**: Prevent API abuse
- **Error Handling**: Secure error messages
- **CORS Configuration**: Controlled cross-origin requests


---

## 📊 Monitoring

### Health Checks
- Agent status monitoring
- API endpoint health
- System resource usage
- Error rate tracking

### Logging
- Structured logging with timestamps
- Agent activity tracking
- Performance metrics
- Error reporting


---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request


---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.


---

## 🙏 Acknowledgments

- **Google** for the Gemini model
- **Abacus.ai** for UI inspiration

---

## 🏁 Quick Run Steps (Summary)

1. Clone the repo and enter the directory.
2. Create and activate a Python virtual environment.
3. Install dependencies with `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and add your Gemini API key.
5. Run `python3 main.py`.
6. Open [http://localhost:8000](http://localhost:8000) in your browser.

**All agents are now powered by GeminiAgent and the `gemini-2.5-flash` model for best speed and quality.**
- **FastAPI** for the excellent web framework
- **The open-source community** for various libraries and tools

## 🔮 Future Roadmap

- [ ] Voice interface integration
- [ ] Advanced analytics dashboard
- [ ] Custom agent creation UI
- [ ] Multi-language support
- [ ] Mobile application
- [ ] Plugin system for extensions
- [ ] Advanced task scheduling
- [ ] Agent learning and adaptation

---

**Built with ❤️ for the future of AI orchestration**