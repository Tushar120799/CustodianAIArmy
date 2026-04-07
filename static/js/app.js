// Learning Path Data
const learningPathData = {
    "paths": [
        { name: "React", description: "Build modern, dynamic user interfaces with this popular JavaScript library.", icon: "fab fa-react" },
        { name: "Vue", description: "An approachable, performant and versatile framework for building web user interfaces.", icon: "fab fa-vuejs" },
        { name: "Python", description: "Master the versatile language for web development, data science, and AI.", icon: "fab fa-python" },
        { name: "Python and Data Science", description: "Use Python for data analysis, visualization, and machine learning.", icon: "fas fa-chart-pie" },
        { name: "General", description: "Learn the fundamentals of programming and computer science concepts.", icon: "fas fa-laptop-code" },
        { name: "HTML and CSS", description: "The building blocks of the web. Create and style web pages from scratch.", icon: "fab fa-html5" },
        { name: "JavaScript and TypeScript", description: "Master the core language of the web and its typed superset.", icon: "fab fa-js-square" },
        { name: "Data Types and Data Formats", description: "Understand JSON, XML, CSV, and other common data formats.", icon: "fas fa-file-alt" },
        { name: "Databases", description: "Learn about SQL and NoSQL databases for storing and retrieving data.", icon: "fas fa-database" },
        { name: "Others", description: "Explore various other technologies and programming concepts.", icon: "fas fa-ellipsis-h" }
    ]
};

// Agent UI Enhancement Data
const agentUIData = {
    "CustodianAI": {
        description: "Orchestrates tasks and coordinates all other AI agents to achieve mission objectives.",
        image: "https://i.imgur.com/jJtVq3A.png", // commander icon
        useCases: [
            "\"Summarize the status of all active agents.\"",
            "\"Assign a research task about market trends to the best agent.\"",
            "\"Generate a report based on the latest findings from AnalystAI and ResearchAI.\""
        ]
    },
    "AnalystAI": {
        description: "Specializes in data interpretation, market trends, and statistical analysis.",
        image: "https://i.imgur.com/sUoYyM1.png", // analyst icon
        useCases: [
            "\"Analyze the attached dataset and find correlations.\"",
            "\"What are the current market trends for AI technologies?\""
        ]
    },
    "DataAnalystAI": {
        description: "Focuses on deep data processing, ETL tasks, and complex statistical modeling.",
        image: "https://i.imgur.com/sUoYyM1.png",
        useCases: [
            "\"Clean and normalize this messy CSV file.\"",
            "\"Build a predictive model based on this historical sales data.\""
        ]
    },
    "MarketAnalystAI": {
        description: "Tracks market indicators, competitor analysis, and consumer behavior.",
        image: "https://i.imgur.com/sUoYyM1.png",
        useCases: [
            "\"Provide a competitive analysis for the electric vehicle market.\"",
            "\"What are the projected growth sectors in tech for next year?\""
        ]
    },
    "CreativeAI": {
        description: "Generates novel concepts, content, and visual designs for creative tasks.",
        image: "https://i.imgur.com/yV2zVsm.png", // creative icon
        useCases: [
            "\"Brainstorm 5 unique marketing campaigns for a new product.\"",
            "\"Write a catchy slogan for an eco-friendly brand.\""
        ]
    },
    "WriterAI": {
        description: "Crafts compelling copy, articles, and long-form written content.",
        image: "https://i.imgur.com/yV2zVsm.png",
        useCases: [
            "\"Draft a 500-word blog post about the benefits of remote work.\"",
            "\"Edit this email to sound more professional and persuasive.\""
        ]
    },
    "DesignerAI": {
        description: "Suggests UI/UX improvements, color palettes, and visual design concepts.",
        image: "https://i.imgur.com/yV2zVsm.png",
        useCases: [
            "\"Suggest a modern color palette for a healthcare app.\"",
            "\"How can I improve the user flow of this checkout process?\""
        ]
    },
    "TechnicalAI": {
        description: "Handles code generation, system architecture, and complex technical problem-solving.",
        image: "https://i.imgur.com/O3E2V7A.png", // technical icon
        useCases: [
            "\"Review this architecture diagram and suggest optimizations.\"",
            "\"Explain the tradeoffs between microservices and monoliths.\""
        ]
    },
    "CoderAI": {
        description: "Specializes in writing, debugging, and refactoring code across multiple languages.",
        image: "https://i.imgur.com/O3E2V7A.png",
        useCases: [
            "\"Write a Python script to scrape product prices from a website.\"",
            "\"Find the bug in this React component that's causing a memory leak.\""
        ]
    },
    "ArchitectAI": {
        description: "Designs scalable system architectures and evaluates infrastructure choices.",
        image: "https://i.imgur.com/O3E2V7A.png",
        useCases: [
            "\"Design a highly available database schema for a social network.\"",
            "\"What is the best cloud architecture for a real-time streaming app?\""
        ]
    },
    "ResearchAI": {
        description: "Conducts in-depth research, fact-checking, and information synthesis.",
        image: null,
        useCases: [
            "\"Gather comprehensive research on renewable energy policies in Europe.\"",
            "\"Summarize the key findings of this 50-page academic paper.\""
        ]
    },
    "FactCheckerAI": {
        description: "Verifies claims, cross-references sources, and ensures informational accuracy.",
        image: null,
        useCases: [
            "\"Fact-check the claims made in this news article.\"",
            "\"Find credible sources to support this historical statement.\""
        ]
    },
    "TrendAnalystAI": {
        description: "Identifies emerging patterns and forecasts future trends in various domains.",
        image: null,
        useCases: [
            "\"What are the emerging trends in remote team collaboration tools?\"",
            "\"Analyze social media sentiment to forecast next season's fashion trends.\""
        ]
    }
};

// Export for tests
if (typeof module !== 'undefined') {
    module.exports = {
    };
}
/**
 * Custodian AI Army - Frontend Application
 * Futuristic AI Agent Management Interface
 */

// Initialize marked with highlight.js
if (typeof marked !== 'undefined' && typeof hljs !== 'undefined') {
    marked.setOptions({
        highlight: function(code, lang) {
            if (lang && hljs.getLanguage(lang)) {
                try {
                    return hljs.highlight(code, { language: lang }).value;
                } catch (err) {}
            }
            return hljs.highlightAuto(code).value;
        },
        breaks: true
    });
}

class CustodianAIApp {
    constructor() {
        this.currentAgent = null;
        this.agents = [];
        this.tasksCompleted = 0;
        this.urlParams = new URLSearchParams(window.location.search);
        this.currentChatId = crypto.randomUUID ? crypto.randomUUID() : 'chat-' + Date.now();
        this.currentMessages = [];
        this.init(); // Make init async
    }

    async init() {
        this.setupEventListeners();
        await this.loadInitialData();

        // URL-based routing
        const section = this.urlParams.get('section') || 'dashboard';
        await this.showSection(section);

        // Handle direct-to-chat agent selection
        const agentId = this.urlParams.get('agent_id');
        if (section === 'chat' && agentId) {
            const agentToSelect = this.agents.find(a => a.agent_id === agentId);
            if (agentToSelect) this.selectChatAgent(agentToSelect);
        }
        this.startPeriodicUpdates();
    }

    setupEventListeners() {
        // Chat input
        const chatInput = document.getElementById('chat-input');
        if (chatInput) {
            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
            // Auto-resize textarea
            chatInput.addEventListener('input', () => {
                chatInput.style.height = 'auto';
                chatInput.style.height = (chatInput.scrollHeight) + 'px';
            });
        }

        const agentModal = document.getElementById('agentSelectModal');
        if (agentModal) {
            this.agentSelectModal = new bootstrap.Modal(agentModal);
        }

        // Task form
        const taskForm = document.getElementById('task-form');
        if (taskForm) {
            taskForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.executeTask();
            });
        }
    }

    async loadInitialData() {
        try {
            // Simplified data loading for the new structure
            await Promise.all([
                this.loadAgents()
            ]);
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showError('Failed to load application data');
        }
    }

    async loadAgents() {
        try {
            const response = await fetch('/api/v1/agents');
            const data = await response.json();
            
            this.agents = data.agents;
            this.updateAgentsGrid(data.agents); // This now populates the homepage
            this.updatePreferredAgentSelect(data.agents);
            this.updateDashboardAgentList(data.agents);
            
            // Update modal agent list with all agents
            this.updateModalAgentList(data.agents);

            // Update the active agents count in the header
            document.getElementById('active-agents').textContent = data.agents.length;
        } catch (error) {
            console.error('Error loading agents:', error);
        }
    }

    updateLearningPathsGrid() {
        const grid = document.getElementById('learning-paths-grid');
        if (!grid) return;

        grid.innerHTML = '';

        const createPathCard = (path) => {
            const card = document.createElement('div');
            card.className = 'learning-path-card'; // Use a new class for styling
            card.innerHTML = `
                <div class="path-icon">
                    <i class="${path.icon} fa-2x"></i>
                </div>
                <div class="path-info">
                    <h4 class="path-title">${path.name}</h4>
                    <p class="path-description">${path.description}</p>
                </div>
                <div class="path-footer">
                    <button class="btn btn-primary btn-sm">Start Learning</button>
                </div>
            `;
            return card;
        };

        // Add Language Paths
        grid.innerHTML += '<h3>Available Learning Paths</h3>';
        learningPathData.paths.forEach(path => grid.appendChild(createPathCard(path)));
    }

    updateAgentsGrid(agents) {
        const grid = document.getElementById('agents-grid');
        if (!grid) return; // This grid is no longer used on the dashboard, but we keep the function for now.

        grid.innerHTML = '';
        
        agents.forEach(agent => {
            const agentCard = document.createElement('div');
            agentCard.className = 'agent-card';
            
            const uiData = agentUIData[agent.name] || { description: "A versatile AI agent ready for any task." };

            const capabilities = agent.capabilities.map(cap => 
                `<span class="capability-tag">${cap.name}</span>`
            ).join('');

            // Direct-to-chat button
            const chatUrl = `/?section=chat&agent_id=${agent.agent_id}`;
            
            agentCard.innerHTML = `
                <div class="agent-card-header">
                    <div class="agent-title-group">
                        <div class="agent-title">${agent.name}</div>
                        <div class="agent-specialization">${agent.specialization || 'General'}</div>
                    </div>
                </div>
                <div class="agent-header">
                    <p class="agent-description">${uiData.description}</p>
                </div>
                <div class="agent-capabilities">
                    ${capabilities}
                </div>
                <div class="agent-footer">
                    <a href="${chatUrl}" class="btn btn-primary btn-sm chat-now-btn">Chat Now <i class="fas fa-comment-dots"></i></a>
                </div>
            `;
            
            grid.appendChild(agentCard);
        });
    }

    updateDashboardAgentList(agents) {
        const list = document.getElementById('dashboard-agent-list');
        if (!list) return;

        list.innerHTML = '';

        agents.forEach(agent => {
            const agentItem = document.createElement('div');
            agentItem.className = 'agent-list-item';
            agentItem.dataset.agentId = agent.agent_id;

            agentItem.innerHTML = `
                <div class="agent-name">${agent.name}</div>
                <div class="agent-specialization">${agent.specialization || 'General'}</div>
            `;

            agentItem.addEventListener('click', () => {
                this.selectChatAgent(agent);
            });

            list.appendChild(agentItem);
        });
    }

    updateModalAgentList(agents) {
        const list = document.getElementById('modal-agent-list');
        if (!list) return;
    
        list.innerHTML = '';
    
        agents.forEach(agent => {
            const agentItem = document.createElement('div');
            agentItem.className = 'agent-list-item modal-agent-item'; // Use same styling
            agentItem.innerHTML = `
                <div class="agent-name">${agent.name}</div>
                <div class="agent-specialization">${agent.specialization || 'General'}</div>
            `;
            agentItem.addEventListener('click', () => {
                this.selectChatAgent(agent);
                // Hide modal and focus input
                if (this.agentSelectModal) {
                    this.agentSelectModal.hide();
                }
            });
            list.appendChild(agentItem);
        });
    }

    updatePreferredAgentSelect(agents) {
        const select = document.getElementById('preferred-agent');
        if (!select) return;

        // Clear existing options except the first one
        while (select.children.length > 1) {
            select.removeChild(select.lastChild);
        }
        
        agents.forEach(agent => {
            const option = document.createElement('option');
            option.value = agent.name;
            option.textContent = `${agent.name} (${agent.specialization || 'General'})`;
            select.appendChild(option);
        });
    }

    selectChatAgent(agent) {
        if (!agent) return;
        // Update UI
        document.querySelectorAll('.agent-list-item').forEach(item => {
            if(item.dataset.agentId === agent.agent_id) item.classList.add('active');
            else item.classList.remove('active');
        });
        
        // Update current agent
        this.currentAgent = agent;
        document.getElementById('current-agent').textContent = 
            `Chatting with ${agent.name} (${agent.specialization || 'General'})`;
        
        // Enable chat input
        const chatInput = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-btn');
        const changeAgentBtn = document.getElementById('change-agent-btn');
        
        chatInput.disabled = false;
        sendBtn.disabled = false;
        changeAgentBtn.disabled = false;
        chatInput.placeholder = `Type your message to ${agent.name}...`;
        
        // Fetch agent details
        const uiData = agentUIData[agent.name] || { description: "A versatile AI assistant ready for any task.", useCases: [] };
        
        // Populate info panel
        const infoPanel = document.getElementById('agent-info-panel');
        if (infoPanel) {
            infoPanel.style.display = 'block';
            
            document.getElementById('info-agent-name').textContent = agent.name;
            document.getElementById('info-agent-spec').textContent = agent.specialization || 'General';
            document.getElementById('info-agent-desc').textContent = uiData.description;
            
            const iconElem = document.getElementById('info-agent-icon');
            if (iconElem) {
                iconElem.style.display = 'none'; // Ensure photo part is hidden from description
            }
            
            const usageElem = document.getElementById('info-agent-usage');
            if (uiData.useCases && uiData.useCases.length > 0) {
                let usageHtml = `<strong>Example use cases:</strong><ul class="mt-2">`;
                uiData.useCases.forEach(uc => {
                    usageHtml += `<li><code>${uc}</code></li>`;
                });
                usageHtml += `</ul>`;
                usageElem.innerHTML = usageHtml;
            } else {
                usageElem.innerHTML = '';
            }
        }

        // Clear welcome message and show chat history
        const messagesContainer = document.getElementById('chat-messages');
        const welcomeText = `Hello! I'm ${agent.name}, your AI assistant. I specialize in ${agent.specialization || 'general tasks'}, helping you to ${uiData.description.charAt(0).toLowerCase() + uiData.description.slice(1)} How can I help you today?`;
        
        messagesContainer.innerHTML = `
            <div class="message agent">
                <div class="message-header">${agent.name}</div>
                <div class="message-content">
                    <p>${welcomeText}</p>
                </div>
            </div>
        `;
        
        // Start a new chat session if switching agents
        this.currentChatId = crypto.randomUUID ? crypto.randomUUID() : 'chat-' + Date.now();
        this.currentMessages = [{ sender: agent.name, content: welcomeText }];
        this.saveChatToDb();
        
        chatInput.focus();
    }

    async sendMessage() {
        if (!this.currentAgent) {
            this.showError('Please select an agent first');
            return;
        }

        const chatInput = document.getElementById('chat-input');
        const message = chatInput.value.trim();
        
        if (!message) return;

        // Reset textarea height
        chatInput.style.height = 'auto';
        // Add user message to chat
        this.addMessageToChat('user', 'You', message);
        chatInput.value = '';
        
        this.currentMessages.push({ sender: 'You', content: message });
        this.saveChatToDb();

        // Show loading
        this.showLoading(true);

        try {
            const response = await fetch('/api/v1/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    agent_name: this.currentAgent.name
                })
            });

            const data = await response.json();
            
            if (response.ok) {
                this.addMessageToChat('agent', data.agent_response.agent_name, data.agent_response.content);
                this.currentMessages.push({ sender: data.agent_response.agent_name, content: data.agent_response.content });
                this.saveChatToDb();
            } else {
                throw new Error(data.detail || 'Failed to send message');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.addMessageToChat('agent', 'System', 'Sorry, I encountered an error processing your message.');
        } finally {
            this.showLoading(false);
        }
    }
    
    async saveChatToDb() {
        const incognitoToggle = document.getElementById('incognitoToggle');
        if (incognitoToggle && incognitoToggle.checked) {
            console.log('Incognito mode active - not saving chat to DB');
            return; // Skip saving completely when incognito is on
        }

        const userStr = localStorage.getItem('custodian_user');
        if (!userStr) return;
        const user = JSON.parse(userStr);
        
        const title = this.currentMessages.length > 1 
            ? this.currentMessages[1].content.substring(0, 30) + '...' 
            : 'New Chat with ' + (this.currentAgent ? this.currentAgent.name : 'Agent');
            
        try {
            await fetch('/api/v1/chats', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: this.currentChatId,
                    user_email: user.email,
                    title: title,
                    messages: this.currentMessages
                })
            });
        } catch (e) {
            console.error("Failed to save chat to DB", e);
        }
    }

    addMessageToChat(type, sender, content) {
        const messagesContainer = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        // Parse markdown if it's from agent or if markdown is available
        let parsedContent = content;
        if (typeof marked !== 'undefined' && type === 'agent') {
            parsedContent = marked.parse(content);
        }
        
        messageDiv.innerHTML = `
            <div class="message-header">${sender}</div>
            <div class="message-content ${type === 'agent' ? 'markdown-body' : ''}">${parsedContent}</div>
        `;
        
        // Add Run Code buttons to pre blocks
        if (type === 'agent') {
            const preBlocks = messageDiv.querySelectorAll('pre');
            preBlocks.forEach((pre, index) => {
                const codeBlock = pre.querySelector('code');
                if (codeBlock) {
                    // Extract language
                    let lang = 'python'; // default
                    const langClass = Array.from(codeBlock.classList).find(c => c.startsWith('language-'));
                    if (langClass) {
                        lang = langClass.replace('language-', '');
                    }
                    
                    const codeToCopy = codeBlock.textContent;
                    
                    const runBtn = document.createElement('button');
                    runBtn.className = 'run-code-btn';
                    runBtn.innerHTML = '<i class="fas fa-play"></i> Run';
                    runBtn.onclick = () => this.runCode(codeToCopy, lang, pre);

                    const copyBtn = document.createElement('button');
                    copyBtn.className = 'copy-code-btn';
                    copyBtn.innerHTML = '<i class="fas fa-copy"></i> Copy';
                    copyBtn.onclick = () => {
                        navigator.clipboard.writeText(codeToCopy).then(() => {
                            copyBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
                            setTimeout(() => { copyBtn.innerHTML = '<i class="fas fa-copy"></i> Copy'; }, 2000);
                        });
                    };
                    
                    pre.style.position = 'relative';
                    pre.appendChild(runBtn);
                }
            });
        }
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    async runCode(code, lang, preElement) {
        // Create or find output container
        let outputContainer = preElement.nextElementSibling;
        if (!outputContainer || !outputContainer.classList.contains('code-output')) {
            outputContainer = document.createElement('div');
            outputContainer.className = 'code-output';
            preElement.parentNode.insertBefore(outputContainer, preElement.nextSibling);
        }
        
        outputContainer.innerHTML = '<div class="loading-spinner"><div class="spinner small"></div> Executing...</div>';
        
        try {
            const response = await fetch('/api/v1/execute-code', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    code: code,
                    language: lang
                })
            });
            
            const data = await response.json();
            
            if (data.error) {
                outputContainer.innerHTML = `<div class="error-output"><strong>Error:</strong><br>${data.error.replace(/\\n/g, '<br>')}</div>`;
            } else {
                outputContainer.innerHTML = `<div class="success-output"><strong>Output:</strong><br><pre>${data.output || '(No output)'}</pre></div>`;
            }
        } catch (error) {
            outputContainer.innerHTML = `<div class="error-output"><strong>Execution failed:</strong> ${error.message}</div>`;
        }
    }

    async executeTask() {
        const description = document.getElementById('task-description').value.trim();
        const taskType = document.getElementById('task-type').value;
        const preferredAgent = document.getElementById('preferred-agent').value;

        if (!description) {
            this.showError('Please enter a task description');
            return;
        }

        this.showLoading(true);

        try {
            const response = await fetch('/api/v1/tasks/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    description: description,
                    task_type: taskType,
                    preferred_agent: preferredAgent || null
                })
            });

            const data = await response.json();
            
            if (response.ok) {
                this.displayTaskResult(data);
                this.tasksCompleted++;
                document.getElementById('tasks-completed').textContent = this.tasksCompleted;
                
                // Clear form
                document.getElementById('task-form').reset();
            } else {
                throw new Error(data.detail || 'Failed to execute task');
            }
        } catch (error) {
            console.error('Error executing task:', error);
            this.showError('Failed to execute task: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    displayTaskResult(taskData) {
        const resultsContainer = document.getElementById('task-results');
        
        // Remove placeholder if it exists
        const placeholder = resultsContainer.querySelector('.results-placeholder');
        if (placeholder) {
            placeholder.remove();
        }

        const resultDiv = document.createElement('div');
        resultDiv.className = 'task-result';
        
        const result = taskData.result;
        
        resultDiv.innerHTML = `
            <div class="task-result-header">
                <div class="task-id">Task ID: ${taskData.task_id}</div>
                <div class="task-status ${result.status}">${result.status.toUpperCase()}</div>
            </div>
            <div class="task-content">
                <p><strong>Agent:</strong> ${result.agent_name} (${result.specialization || 'General'})</p>
                <p><strong>Result:</strong></p>
                <div>${result.result}</div>
            </div>
        `;
        
        resultsContainer.appendChild(resultDiv);
    }

    async showSection(sectionName) {
        // Update navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        
        const navItem = document.querySelector(`[data-section="${sectionName}"]`);
        if (navItem) {
            navItem.classList.add('active');
        }
        
        // Update content sections
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });
        
        const sectionElement = document.getElementById(sectionName);
        if (sectionElement) {
            sectionElement.classList.add('active');
        }
        
        // Load section-specific data
        if (sectionName === 'learn') {
            this.updateLearningPathsGrid();
        }
        // Other sections can have their data loading logic here
    }

    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (show) {
            overlay.classList.add('active');
        } else {
            overlay.classList.remove('active');
        }
    }

    showError(message) {
        // Simple error display - could be enhanced with a proper modal
        alert('Error: ' + message);
    }

    startPeriodicUpdates() {
        // Update army status every 30 seconds
        // This can be re-enabled if needed for live status updates on the dashboard
        // setInterval(() => { this.loadAgents(); }, 30000);
    }
}

// Global functions for HTML onclick handlers
window.showSection = function(sectionName) {
    if (window.app) {
        window.app.showSection(sectionName);
    }
};

window.sendMessage = function() {
    if (window.app) {
        window.app.sendMessage();
    }
};

// Authentication functions
window.updateUserProfile = function(user) {
    const profileIcon = document.getElementById('user-profile-img');
    const profileName = document.getElementById('user-profile-name');
    const editNameInput = document.getElementById('profileNameInput');
    const editEmailInput = document.getElementById('profileEmailInput');
    
    if (profileIcon && user.picture) profileIcon.src = user.picture;
    if (profileName && user.name) profileName.textContent = user.name.split(' ')[0]; // Show first name
    
    if (editNameInput) editNameInput.value = user.name || '';
    if (editEmailInput) editEmailInput.value = user.email || '';
    
    // Save to localStorage for session persistence
    localStorage.setItem('custodian_user', JSON.stringify(user));
};

window.saveProfileDetails = async function() {
    const newName = document.getElementById('profileNameInput').value;
    const userStr = localStorage.getItem('custodian_user');
    if (userStr) {
        const user = JSON.parse(userStr);
        user.name = newName;
        localStorage.setItem('custodian_user', JSON.stringify(user));
        updateUserProfile(user);
    }
};

window.logout = async function() {
    try {
        await fetch('/api/v1/auth/logout', { method: 'POST' });
    } catch (err) {
        console.error("Logout error", err);
    } finally {
        localStorage.removeItem('custodian_user');
        location.reload();
    }
};

// Check authentication status on page load
document.addEventListener('DOMContentLoaded', async () => {
    // Initialize the app
    window.app = new CustodianAIApp();
    
    // Check authentication status from backend
    try {
        const response = await fetch('/api/v1/auth/status');
        const data = await response.json();
        
        if (data.authenticated && data.user) {
            updateUserProfile(data.user);
        }
    } catch (err) {
        console.error("Failed to check auth status", err);
    }
});

// Add some futuristic visual effects
document.addEventListener('DOMContentLoaded', () => {
    // Add particle effect to background (optional)
    createParticleEffect();
    
    // Add typing effect to headers
    addTypingEffect();
});

function createParticleEffect() {
    // Simple particle effect for futuristic feel
    const canvas = document.createElement('canvas');
    canvas.style.position = 'fixed';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.pointerEvents = 'none';
    canvas.style.zIndex = '-1';
    canvas.style.opacity = '0.1';
    
    document.body.appendChild(canvas);
    
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    
    const particles = [];
    
    for (let i = 0; i < 50; i++) {
        particles.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            vx: (Math.random() - 0.5) * 0.5,
            vy: (Math.random() - 0.5) * 0.5,
            size: Math.random() * 2 + 1
        });
    }
    
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#00d4ff';
        
        particles.forEach(particle => {
            particle.x += particle.vx;
            particle.y += particle.vy;
            
            if (particle.x < 0 || particle.x > canvas.width) particle.vx *= -1;
            if (particle.y < 0 || particle.y > canvas.height) particle.vy *= -1;
            
            ctx.beginPath();
            ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
            ctx.fill();
        });
        
        requestAnimationFrame(animate);
    }
    
    animate();
    
    window.addEventListener('resize', () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    });
}

function addTypingEffect() {
    const headers = document.querySelectorAll('.section-header h2');
    
    headers.forEach(header => {
        const text = header.textContent;
        header.textContent = '';
        
        let i = 0;
        const typeInterval = setInterval(() => {
            header.textContent += text.charAt(i);
            i++;
            
            if (i >= text.length) {
                clearInterval(typeInterval);
            }
        }, 100);
    });
}