// ─────────────────────────────────────────────────────────────────────────────
// LANGUAGE STATE
// ─────────────────────────────────────────────────────────────────────────────
let currentLanguage = localStorage.getItem('custodian_lang') || 'en';

function setLanguage(lang) {
    currentLanguage = lang;
    localStorage.setItem('custodian_lang', lang);
    // Update header button states
    const enBtn = document.getElementById('lang-en-btn');
    const deBtn = document.getElementById('lang-de-btn');
    if (enBtn) enBtn.className = lang === 'en' ? 'btn btn-sm btn-outline-info active' : 'btn btn-sm btn-outline-secondary';
    if (deBtn) deBtn.className = lang === 'de' ? 'btn btn-sm btn-outline-info active' : 'btn btn-sm btn-outline-secondary';
    // Update learn-section button states (keep in sync)
    const learnEnBtn = document.getElementById('learn-lang-en-btn');
    const learnDeBtn = document.getElementById('learn-lang-de-btn');
    if (learnEnBtn) learnEnBtn.className = lang === 'en' ? 'btn btn-sm btn-outline-info active' : 'btn btn-sm btn-outline-secondary';
    if (learnDeBtn) learnDeBtn.className = lang === 'de' ? 'btn btn-sm btn-outline-info active' : 'btn btn-sm btn-outline-secondary';
    // Refresh course list if on learn section
    if (window.app) {
        window.app.currentLang = lang;
        window.app.updateLearningPathsGrid();
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// COURSE FILTER
// ─────────────────────────────────────────────────────────────────────────────
let currentCategoryFilter = 'all';

function filterCourses(category, btn) {
    currentCategoryFilter = category;
    // Update button states
    document.querySelectorAll('#category-filter-bar button').forEach(b => {
        b.className = 'btn btn-sm btn-outline-info';
    });
    if (btn) btn.className = 'btn btn-sm btn-info active';
    if (window.app) window.app.updateLearningPathsGrid();
}

// Agent UI Enhancement Data
const agentUIData = {
    "CustodianAI": {
        description: "Orchestrates tasks and coordinates all other AI agents to achieve mission objectives.",
        image: "https://i.imgur.com/jJtVq3A.png",
        useCases: [
            "\"Summarize the status of all active agents.\"",
            "\"Assign a research task about market trends to the best agent.\"",
            "\"Generate a report based on the latest findings from AnalystAI and ResearchAI.\""
        ]
    },
    "AnalystAI": {
        description: "Specializes in data interpretation, market trends, and statistical analysis.",
        image: "https://i.imgur.com/sUoYyM1.png",
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
        image: "https://i.imgur.com/yV2zVsm.png",
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
        image: "https://i.imgur.com/O3E2V7A.png",
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
        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.loadInitialData();

        const section = this.urlParams.get('section') || 'dashboard';
        await this.showSection(section);

        const agentId = this.urlParams.get('agent_id');
        if (section === 'chat' && agentId) {
            const agentToSelect = this.agents.find(a => a.agent_id === agentId);
            if (agentToSelect) this.selectChatAgent(agentToSelect);
        }
        this.startPeriodicUpdates();
    }

    setupEventListeners() {
        const chatInput = document.getElementById('chat-input');
        if (chatInput) {
            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
            chatInput.addEventListener('input', () => {
                chatInput.style.height = 'auto';
                chatInput.style.height = (chatInput.scrollHeight) + 'px';
            });
        }

        const agentModal = document.getElementById('agentSelectModal');
        if (agentModal) {
            this.agentSelectModal = new bootstrap.Modal(agentModal);
        }

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
            const response = await fetch('/api/v1/agents', {
                credentials: 'include'
            });
            const data = await response.json();
            
            this.agents = data.agents;
            this.updateAgentsGrid(data.agents);
            this.updatePreferredAgentSelect(data.agents);
            this.updateDashboardAgentList(data.agents);
            this.updateModalAgentList(data.agents);

            document.getElementById('active-agents').textContent = data.agents.length;
        } catch (error) {
            console.error('Error loading agents:', error);
        }
    }

    updateAgentsGrid(agents) {
        const grid = document.getElementById('agents-grid');
        if (!grid) return;

        grid.innerHTML = '';
        
        agents.forEach(agent => {
            const agentCard = document.createElement('div');
            agentCard.className = 'agent-card';
            
            const uiData = agentUIData[agent.name] || { description: "A versatile AI agent ready for any task." };

            const capabilities = agent.capabilities.map(cap => 
                `<span class="capability-tag">${cap.name}</span>`
            ).join('');

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
            agentItem.className = 'agent-list-item modal-agent-item';
            agentItem.innerHTML = `
                <div class="agent-name">${agent.name}</div>
                <div class="agent-specialization">${agent.specialization || 'General'}</div>
            `;
            agentItem.addEventListener('click', () => {
                this.selectChatAgent(agent);
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
        document.querySelectorAll('.agent-list-item').forEach(item => {
            if(item.dataset.agentId === agent.agent_id) item.classList.add('active');
            else item.classList.remove('active');
        });
        
        this.currentAgent = agent;

        const chatInput = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-btn');
        const changeAgentBtn = document.getElementById('change-agent-btn');
        
        chatInput.disabled = false;
        sendBtn.disabled = false;
        changeAgentBtn.disabled = false;
        chatInput.placeholder = `Type your message to ${agent.name}...`;
        
        const uiData = agentUIData[agent.name] || { description: "A versatile AI assistant ready for any task.", useCases: [] };
        
        const infoPanel = document.getElementById('agent-info-panel');
        if (infoPanel) {
            infoPanel.style.display = 'block';
            
            document.getElementById('info-agent-name').textContent = agent.name;
            document.getElementById('info-agent-spec').textContent = agent.specialization || 'General';
            document.getElementById('info-agent-desc').textContent = uiData.description;
            
            const iconElem = document.getElementById('info-agent-icon');
            if (iconElem) {
                iconElem.style.display = 'none';
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
        
        this.currentChatId = crypto.randomUUID ? crypto.randomUUID() : 'chat-' + Date.now();
        this.currentMessages = [{ sender: agent.name, content: welcomeText }];
        this.saveChatToDb();

        // Update active agent banner
        const banner = document.getElementById('active-agent-banner');
        const bannerName = document.getElementById('active-agent-name');
        const bannerSpec = document.getElementById('active-agent-spec');
        if (banner) banner.style.display = 'block';
        if (bannerName) bannerName.textContent = agent.name;
        if (bannerSpec) bannerSpec.textContent = agent.specialization ? '· ' + agent.specialization : '';

        // Update API Keys modal active agent/provider display
        this._updateApiKeysAgentDisplay(agent);

        // Update model display in chat-options-bar
        const provider = _getAgentProvider(agent);
        const savedModel = localStorage.getItem('custodian_model_override_' + provider);
        this.currentModelOverride = savedModel || null;
        const models = _providerModels[provider] || [];
        const defaultModel = models[0];
        const activeModel = savedModel ? models.find(m => m.id === savedModel) : defaultModel;
        const modelDisplayEl = document.getElementById('active-model-display');
        const modelNameEl = document.getElementById('active-model-name');
        if (modelDisplayEl) modelDisplayEl.classList.remove('d-none');
        if (modelNameEl) modelNameEl.textContent = activeModel ? activeModel.label.replace(' (default)', '') : (defaultModel ? defaultModel.label.replace(' (default)', '') : '');

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

        chatInput.style.height = 'auto';
        this.addMessageToChat('user', 'You', message);
        chatInput.value = '';
        
        this.currentMessages.push({ sender: 'You', content: message });
        this.saveChatToDb();

        this.showLoading(true);

        // Determine endpoint: try authenticated first, fall back to guest if 401
        // This handles the case where localStorage is empty but session cookie is valid
        const isGuest = !localStorage.getItem('custodian_user');
        const primaryEndpoint = '/api/v1/chat';
        const guestEndpoint = '/api/v1/chat/guest';

        const requestBody = JSON.stringify({
            message: message,
            agent_name: this.currentAgent.name,
            agent_id: this.currentAgent.agent_id
        });

        let response, data, usedGuestEndpoint = false;

        try {
            // Always try authenticated endpoint first
            response = await fetch(primaryEndpoint, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: requestBody
            });

            // If 401 (not authenticated), fall back to guest endpoint
            if (response.status === 401) {
                usedGuestEndpoint = true;
                response = await fetch(guestEndpoint, {
                    method: 'POST',
                    credentials: 'include',
                    headers: { 'Content-Type': 'application/json' },
                    body: requestBody
                });
            }

            data = await response.json();

            if (response.ok) {
                const agentResp = data.agent_response;
                // Check if rate limited (backend returns 200 with rate_limited flag)
                if (agentResp && agentResp.metadata && agentResp.metadata.rate_limited) {
                    this.addMessageToChat('agent', agentResp.agent_name || 'System', agentResp.content);
                    this.currentMessages.push({ sender: agentResp.agent_name || 'System', content: agentResp.content });
                    // Show rate limit popup
                    this._showRateLimitModal(data.plan_info);
                } else {
                    this.addMessageToChat('agent', agentResp.agent_name || this.currentAgent.name, agentResp.content);
                    this.currentMessages.push({ sender: agentResp.agent_name || this.currentAgent.name, content: agentResp.content });
                    this.saveChatToDb();
                }
                // Silently refresh plan info in background so My Plan modal shows updated count
                fetch('/api/v1/user/plan', { credentials: 'include' })
                    .then(r => r.json())
                    .then(planData => {
                        // Update the plan body if the modal is currently open
                        const planBody = document.getElementById('my-plan-body');
                        if (planBody && planBody.querySelector('.progress-bar')) {
                            // Modal is open — reload it
                            if (typeof loadMyPlan === 'function') loadMyPlan();
                        }
                    })
                    .catch(() => {});
            } else {
                throw new Error(data.detail || 'Failed to send message');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.addMessageToChat('agent', 'System', 'Sorry, I encountered an error processing your message. Please try again.');
        } finally {
            this.showLoading(false);
        }
    }
    
    async saveChatToDb() {
        const incognitoToggle = document.getElementById('incognitoToggle');
        if (incognitoToggle && incognitoToggle.checked) {
            console.log('Incognito mode active - not saving chat to DB');
            return;
        }

        // Try to get user from localStorage first, then fall back to auth status check
        let userEmail = null;
        const userStr = localStorage.getItem('custodian_user');
        if (userStr) {
            try {
                const user = JSON.parse(userStr);
                userEmail = user.email;
            } catch(e) {}
        }

        // If no localStorage user, check if we have a valid session cookie
        if (!userEmail) {
            try {
                const authResp = await fetch('/api/v1/auth/status', { credentials: 'include' });
                const authData = await authResp.json();
                if (authData.authenticated && authData.user) {
                    userEmail = authData.user.email;
                    // Cache it in localStorage for future calls
                    localStorage.setItem('custodian_user', JSON.stringify(authData.user));
                }
            } catch(e) {}
        }

        if (!userEmail) {
            console.log('User not authenticated - not saving chat to DB');
            return;
        }

        const title = this.currentMessages.length > 1
            ? this.currentMessages[1].content.substring(0, 30) + '...'
            : 'New Chat with ' + (this.currentAgent ? this.currentAgent.name : 'Agent');

        try {
            await fetch('/api/v1/auth/user/chats', {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: this.currentChatId,
                    user_email: userEmail,
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
        
        let parsedContent = content;
        if (typeof marked !== 'undefined' && type === 'agent') {
            parsedContent = marked.parse(content);
        }
        
        messageDiv.innerHTML = `
            <div class="message-header">${sender}</div>
            <div class="message-content ${type === 'agent' ? 'markdown-body' : ''}">${parsedContent}</div>
        `;
        
        if (type === 'agent') {
            const preBlocks = messageDiv.querySelectorAll('pre');
            preBlocks.forEach((pre, index) => {
                const codeBlock = pre.querySelector('code');
                if (codeBlock) {
                    let lang = 'python';
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
                credentials: 'include',
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
                credentials: 'include',
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
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        
        const navItem = document.querySelector(`[data-section="${sectionName}"]`);
        if (navItem) {
            navItem.classList.add('active');
        }
        
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });
        
        const sectionElement = document.getElementById(sectionName);
        if (sectionElement) {
            sectionElement.classList.add('active');
        }

        // Toggle body class so CSS can hide/show header controls per section
        const learnSections = ['learn', 'course-detail'];
        if (learnSections.includes(sectionName)) {
            document.body.classList.add('section-learn');
        } else {
            document.body.classList.remove('section-learn');
        }

        // Sync learn-section lang buttons with current language state
        const lang = currentLanguage || 'en';
        const learnEnBtn = document.getElementById('learn-lang-en-btn');
        const learnDeBtn = document.getElementById('learn-lang-de-btn');
        if (learnEnBtn) learnEnBtn.className = lang === 'en' ? 'btn btn-sm btn-outline-info active' : 'btn btn-sm btn-outline-secondary';
        if (learnDeBtn) learnDeBtn.className = lang === 'de' ? 'btn btn-sm btn-outline-info active' : 'btn btn-sm btn-outline-secondary';

        if (sectionName === 'learn') {
            this.updateLearningPathsGrid();
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // COURSE NAVIGATION SYSTEM
    // ─────────────────────────────────────────────────────────────────────────

    async updateLearningPathsGrid() {
        const grid = document.getElementById('learning-paths-grid');
        if (!grid) return;
        grid.innerHTML = '<div class="text-center text-muted py-4"><div class="spinner"></div><p>Loading courses...</p></div>';

        try {
            const lang = this.currentLang || currentLanguage || 'en';
            const response = await fetch(`/api/v1/courses?lang=${lang}`, { credentials: 'include' });
            const data = await response.json();
            let courses = data.courses || [];

            // Apply category filter
            if (currentCategoryFilter && currentCategoryFilter !== 'all') {
                courses = courses.filter(c => c.category === currentCategoryFilter);
            }

            grid.innerHTML = '';
            if (courses.length === 0) {
                grid.innerHTML = '<p class="text-muted text-center py-4">No courses found for the selected filters.</p>';
                return;
            }

            // Load user progress
            let progressMap = {};
            try {
                const pResp = await fetch('/api/v1/progress', { credentials: 'include' });
                if (pResp.ok) {
                    const pData = await pResp.json();
                    (pData.progress || []).forEach(p => {
                        progressMap[`${p.course_id}:${p.lang}`] = p;
                    });
                }
            } catch(e) { /* guest user, no progress */ }

            courses.forEach(course => {
                const key = `${course.id}:${course.lang}`;
                const progress = progressMap[key];
                const completedCount = progress ? (progress.completed_sections || []).length : 0;
                const totalCount = course.section_count || 1;
                const pct = Math.round((completedCount / totalCount) * 100);

                const card = document.createElement('div');
                card.className = 'course-card';
                card.innerHTML = `
                    <div class="course-card-icon">
                        <i class="${course.icon || 'fas fa-book'} fa-2x"></i>
                    </div>
                    <div class="course-card-body">
                        <div class="d-flex justify-content-between align-items-start mb-1">
                            <h4 class="course-card-title">${course.title}</h4>
                            <span class="badge bg-secondary ms-2">${course.lang.toUpperCase()}</span>
                        </div>
                        <span class="badge bg-info text-dark mb-2">${course.category}</span>
                        <p class="course-card-desc">${course.description}</p>
                        <div class="course-card-meta">
                            <span><i class="fas fa-layer-group me-1"></i>${course.section_count} modules</span>
                            <span><i class="fas fa-file-alt me-1"></i>${course.slide_count} slides</span>
                        </div>
                        ${completedCount > 0 ? `
                        <div class="mt-2">
                            <div class="d-flex justify-content-between small text-muted mb-1">
                                <span>Progress</span><span>${pct}%</span>
                            </div>
                            <div class="progress" style="height:4px;">
                                <div class="progress-bar bg-info" style="width:${pct}%"></div>
                            </div>
                        </div>` : ''}
                    </div>
                    <div class="course-card-footer">
                        <button class="btn btn-info btn-sm w-100" onclick="window.app.openCourse('${course.id}', '${course.lang}')">
                            <i class="fas fa-play me-1"></i> ${completedCount > 0 ? 'Continue' : 'Start'} Learning
                        </button>
                    </div>
                `;
                grid.appendChild(card);
            });
        } catch(e) {
            console.error('Error loading courses:', e);
            grid.innerHTML = '<p class="text-danger text-center py-4">Failed to load courses. Please try again.</p>';
        }
    }

    async openCourse(courseId, lang) {
        this.currentCourseId = courseId;
        this.currentCourseLang = lang;
        this.currentSectionIndex = 0;
        this.completedSections = [];

        // Load progress
        try {
            const pResp = await fetch('/api/v1/progress', { credentials: 'include' });
            if (pResp.ok) {
                const pData = await pResp.json();
                const prog = (pData.progress || []).find(p => p.course_id === courseId && p.lang === lang);
                if (prog) {
                    this.currentSectionIndex = prog.section_index || 0;
                    this.completedSections = prog.completed_sections || [];
                }
            }
        } catch(e) { /* guest */ }

        // Load course data
        try {
            const resp = await fetch(`/api/v1/courses/${courseId}?lang=${lang}`, { credentials: 'include' });
            const course = await resp.json();
            this.currentCourse = course;

            // Update sidebar
            document.getElementById('course-sidebar-title').textContent = course.title;
            this.renderModuleList(course.sections);
            this.updateProgressDisplay();

            // Show course detail section
            await this.showSection('course-detail');

            // Load first/current section
            await this.loadSection(this.currentSectionIndex);
        } catch(e) {
            console.error('Error opening course:', e);
            alert('Failed to load course. Please try again.');
        }
    }

    renderModuleList(sections) {
        const list = document.getElementById('course-module-list');
        if (!list) return;
        list.innerHTML = '';
        sections.forEach((section, i) => {
            const isCompleted = this.completedSections.includes(i);
            const isCurrent = i === this.currentSectionIndex;
            const item = document.createElement('div');
            item.className = `course-module-item ${isCurrent ? 'active' : ''} ${isCompleted ? 'completed' : ''}`;
            item.dataset.index = i;
            item.innerHTML = `
                <span class="module-status-icon">
                    ${isCompleted ? '<i class="fas fa-check-circle text-success"></i>' : `<span class="module-number">${i + 1}</span>`}
                </span>
                <span class="module-title">${section.title}</span>
            `;
            item.addEventListener('click', () => this.loadSection(i));
            list.appendChild(item);
        });
    }

    async loadSection(index) {
        if (!this.currentCourse) return;
        const sections = this.currentCourse.sections || [];
        if (index < 0 || index >= sections.length) return;

        this.currentSectionIndex = index;
        const section = sections[index];

        // Update header
        document.getElementById('course-section-title').textContent = section.title;
        document.getElementById('course-lang-badge').textContent = (this.currentCourseLang || 'en').toUpperCase();
        document.getElementById('course-section-badge').textContent = `${index + 1} / ${sections.length}`;

        // Update nav buttons
        document.getElementById('prev-section-btn').disabled = index === 0;
        document.getElementById('next-section-btn').disabled = index === sections.length - 1;

        // Update mark complete button
        const isCompleted = this.completedSections.includes(index);
        const markBtn = document.getElementById('mark-complete-btn');
        if (markBtn) {
            markBtn.innerHTML = isCompleted
                ? '<i class="fas fa-check-circle me-1"></i> Completed'
                : '<i class="fas fa-check me-1"></i> Mark Complete';
            markBtn.className = isCompleted ? 'btn btn-sm btn-success' : 'btn btn-sm btn-outline-info';
        }

        // Load slide content
        const contentEl = document.getElementById('course-slide-content');
        contentEl.innerHTML = '<div class="text-center py-4"><div class="spinner"></div></div>';

        try {
            const resp = await fetch(`/api/v1/courses/${this.currentCourseId}/slides/${this.currentCourseLang}/${index}`, { credentials: 'include' });
            const data = await resp.json();
            const md = data.content || '*No content available for this section.*';
            if (typeof marked !== 'undefined') {
                contentEl.innerHTML = marked.parse(md);
                // Apply syntax highlighting
                contentEl.querySelectorAll('pre code').forEach(block => {
                    if (typeof hljs !== 'undefined') hljs.highlightElement(block);
                });
                // Add run buttons to code blocks
                contentEl.querySelectorAll('pre').forEach(pre => {
                    const code = pre.querySelector('code');
                    if (code) {
                        const runBtn = document.createElement('button');
                        runBtn.className = 'run-code-btn';
                        runBtn.innerHTML = '<i class="fas fa-play"></i> Run';
                        runBtn.onclick = () => {
                            // Open terminal with the code pre-populated
                            this.openCourseTerminal(code.textContent);
                        };
                        pre.style.position = 'relative';
                        pre.appendChild(runBtn);
                    }
                });
            } else {
                contentEl.innerHTML = `<pre>${md}</pre>`;
            }
        } catch(e) {
            contentEl.innerHTML = '<p class="text-danger">Failed to load slide content.</p>';
        }

        // Update module list highlight
        this.renderModuleList(sections);
        this.updateProgressDisplay();

        // Save progress to backend
        this.saveProgress();
    }

    navigateSection(delta) {
        const sections = this.currentCourse ? this.currentCourse.sections : [];
        const newIndex = this.currentSectionIndex + delta;
        if (newIndex >= 0 && newIndex < sections.length) {
            this.loadSection(newIndex);
        }
    }

    markSectionComplete() {
        if (!this.completedSections.includes(this.currentSectionIndex)) {
            this.completedSections.push(this.currentSectionIndex);
        }
        this.renderModuleList(this.currentCourse.sections);
        this.updateProgressDisplay();
        this.saveProgress();

        // Update button
        const markBtn = document.getElementById('mark-complete-btn');
        if (markBtn) {
            markBtn.innerHTML = '<i class="fas fa-check-circle me-1"></i> Completed';
            markBtn.className = 'btn btn-sm btn-success';
        }

        // Auto-advance to next section
        const sections = this.currentCourse.sections || [];
        if (this.currentSectionIndex < sections.length - 1) {
            setTimeout(() => this.navigateSection(1), 800);
        }
    }

    updateProgressDisplay() {
        const sections = this.currentCourse ? this.currentCourse.sections : [];
        const total = sections.length;
        const completed = this.completedSections.length;
        const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

        const pctEl = document.getElementById('course-progress-pct');
        const fillEl = document.getElementById('course-progress-fill');
        const completedEl = document.getElementById('course-completed-count');
        const totalEl = document.getElementById('course-total-count');

        if (pctEl) pctEl.textContent = `${pct}%`;
        if (fillEl) fillEl.style.width = `${pct}%`;
        if (completedEl) completedEl.textContent = completed;
        if (totalEl) totalEl.textContent = total;
    }

    async saveProgress() {
        try {
            await fetch('/api/v1/progress', {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    course_id: this.currentCourseId,
                    lang: this.currentCourseLang || 'en',
                    section_index: this.currentSectionIndex,
                    completed_sections: this.completedSections
                })
            });
        } catch(e) { /* guest user, ignore */ }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // COURSE TERMINAL
    // ─────────────────────────────────────────────────────────────────────────

    async runCourseCode() {
        const code = document.getElementById('course-code-input').value.trim();
        if (!code) return;
        const outputEl = document.getElementById('course-terminal-output');
        outputEl.innerHTML = '<span class="text-muted"><div class="spinner small d-inline-block"></div> Running...</span>';

        try {
            const resp = await fetch('/api/v1/execute-code', {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code, language: 'python' })
            });
            const data = await resp.json();
            if (data.error) {
                outputEl.innerHTML = `<span class="text-danger"><strong>Error:</strong><br><pre>${data.error}</pre></span>`;
            } else {
                outputEl.innerHTML = `<span class="text-success"><strong>Output:</strong><br><pre>${data.output || '(No output)'}</pre></span>`;
            }
        } catch(e) {
            outputEl.innerHTML = `<span class="text-danger">Execution failed: ${e.message}</span>`;
        }
    }

    clearCourseTerminal() {
        document.getElementById('course-code-input').value = '';
        document.getElementById('course-terminal-output').innerHTML = '<span class="text-muted">Output will appear here...</span>';
    }

    openCourseTerminal(code) {
        const terminalSection = document.getElementById('course-terminal-section');
        const toggleBar = document.getElementById('course-terminal-toggle-bar');
        const chevron = document.getElementById('terminal-chevron');
        const body = document.getElementById('course-terminal-body');
        if (terminalSection) terminalSection.style.display = 'block';
        if (toggleBar) toggleBar.style.display = 'none';
        if (body) body.style.display = 'block';
        if (chevron) { chevron.className = 'fas fa-chevron-up'; }
        if (code !== undefined && code !== null) {
            const input = document.getElementById('course-code-input');
            if (input) input.value = code;
        }
        // Scroll to terminal
        if (terminalSection) terminalSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    toggleCourseTerminal() {
        const terminalSection = document.getElementById('course-terminal-section');
        const toggleBar = document.getElementById('course-terminal-toggle-bar');
        const chevron = document.getElementById('terminal-chevron');
        const body = document.getElementById('course-terminal-body');
        if (!body) return;
        const isOpen = body.style.display !== 'none';
        if (isOpen) {
            body.style.display = 'none';
            if (chevron) chevron.className = 'fas fa-chevron-down';
        } else {
            body.style.display = 'block';
            if (chevron) chevron.className = 'fas fa-chevron-up';
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // COURSE AI TUTOR
    // ─────────────────────────────────────────────────────────────────────────

    openCourseAIAssist() {
        const panel = document.getElementById('course-ai-panel');
        if (panel) panel.style.display = 'flex';
    }

    closeCourseAIPanel() {
        const panel = document.getElementById('course-ai-panel');
        if (panel) panel.style.display = 'none';
    }

    async sendCourseAIMessage() {
        const input = document.getElementById('course-ai-input');
        const message = input ? input.value.trim() : '';
        if (!message) return;

        const messagesEl = document.getElementById('course-ai-messages');
        // Add user message
        messagesEl.innerHTML += `<div class="course-ai-msg user-msg"><strong>You:</strong> ${message}</div>`;
        input.value = '';
        messagesEl.innerHTML += `<div class="course-ai-msg agent-msg" id="ai-typing"><i class="fas fa-robot me-1"></i><em>Thinking...</em></div>`;
        messagesEl.scrollTop = messagesEl.scrollHeight;

        const code = document.getElementById('course-code-input') ? document.getElementById('course-code-input').value : '';

        try {
            const resp = await fetch('/api/v1/chat/course', {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message,
                    course_id: this.currentCourseId || null,
                    lang: this.currentCourseLang || 'en',
                    section_index: this.currentSectionIndex || 0,
                    code: code || null
                })
            });
            const data = await resp.json();
            const typingEl = document.getElementById('ai-typing');
            if (typingEl) typingEl.remove();

            const content = data.agent_response ? data.agent_response.content : 'Sorry, I could not get a response.';
            const parsedContent = typeof marked !== 'undefined' ? marked.parse(content) : content;
            messagesEl.innerHTML += `<div class="course-ai-msg agent-msg markdown-body"><i class="fas fa-robot me-1 text-info"></i>${parsedContent}</div>`;
            messagesEl.scrollTop = messagesEl.scrollHeight;
        } catch(e) {
            const typingEl = document.getElementById('ai-typing');
            if (typingEl) typingEl.remove();
            messagesEl.innerHTML += `<div class="course-ai-msg agent-msg text-danger">Error: ${e.message}</div>`;
        }
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
        alert('Error: ' + message);
    }

    startPeriodicUpdates() {
        // setInterval(() => { this.loadAgents(); }, 30000);
    }

    // Load a past chat into the current session
    async loadChatIntoCurrentSession(chatId) {
        try {
            const userStr = localStorage.getItem('custodian_user');
            if (!userStr) {
                throw new Error('User not authenticated');
            }
            const user = JSON.parse(userStr);
            
            const response = await fetch(`/api/v1/chats?email=${encodeURIComponent(user.email)}`, {
                credentials: 'include'
            });
            const data = await response.json();
            
            const chat = data.chats.find(c => c.id === chatId);
            if (!chat) {
                throw new Error('Chat not found');
            }
            
            this.currentChatId = chat.id;
            this.currentMessages = chat.messages;
            
            const firstAgentMessage = chat.messages.find(m => m.sender !== 'You');
            if (firstAgentMessage) {
                const agent = this.agents.find(a => a.name === firstAgentMessage.sender);
                if (agent) {
                    this.selectChatAgent(agent);
                }
            }
            
            const messagesContainer = document.getElementById('chat-messages');
            messagesContainer.innerHTML = '';
            chat.messages.forEach(msg => {
                const type = msg.sender === 'You' ? 'user' : 'agent';
                this.addMessageToChat(type, msg.sender, msg.content);
            });
            
            const chatHistoryModal = bootstrap.Modal.getInstance(document.getElementById('chatHistoryModal'));
            if (chatHistoryModal) {
                chatHistoryModal.hide();
            }
        } catch (err) {
            console.error("Failed to load chat", err);
            alert('Failed to load chat: ' + err.message);
        }
    }

    // Delete a chat session
    async deleteChat(chatId) {
        if (!confirm('Are you sure you want to delete this chat session?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/v1/auth/user/chats/${chatId}`, {
                method: 'DELETE',
                credentials: 'include'
            });
            
            if (!response.ok) {
                throw new Error('Failed to delete chat');
            }
            
            // Reload chat history
            await loadChatHistory();
        } catch (err) {
            console.error("Failed to delete chat", err);
            alert('Failed to delete chat: ' + err.message);
        }
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
    // Update the profile button name (icon-only approach, no avatar image)
    const profileName = document.getElementById('user-profile-name');
    const editNameInput = document.getElementById('profileNameInput');
    const editEmailInput = document.getElementById('profileEmailInput');
    const guestLoginItem = document.getElementById('guest-login-item');

    if (profileName && user && user.name) {
        profileName.textContent = user.name.split(' ')[0];
    }

    if (editNameInput) editNameInput.value = (user && user.name) || '';
    if (editEmailInput) editEmailInput.value = (user && user.email) || '';

    // Show/hide guest login item
    if (guestLoginItem) {
        guestLoginItem.style.display = user ? 'none' : '';
    }

    if (user) {
        localStorage.setItem('custodian_user', JSON.stringify(user));
    }

    // Hide auth modal if it's showing
    const authModalElement = document.getElementById('authModal');
    if (authModalElement) {
        const authModal = bootstrap.Modal.getInstance(authModalElement);
        if (authModal) authModal.hide();
    }
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
        await fetch('/api/v1/auth/logout', { 
            method: 'POST',
            credentials: 'include'
        });
    } catch (err) {
        console.error("Logout error", err);
    } finally {
        localStorage.removeItem('custodian_user');
        location.reload();
    }
};

// Load chat history from backend
window.loadChatHistory = async function() {
    try {
        console.log('[loadChatHistory] Loading chat history...');
        const response = await fetch('/api/v1/auth/user/chats', {
            credentials: 'include'
        });
        if (!response.ok) {
            if (response.status === 401) {
                localStorage.removeItem('custodian_user');
                const authModal = new bootstrap.Modal(document.getElementById('authModal'));
                authModal.show();
            }
            throw new Error('Failed to load chat history');
        }
        
        const data = await response.json();
        console.log('[loadChatHistory] Received data:', data);
        
        const list = document.getElementById('chat-history-list');
        const currentItem = document.getElementById('current-chat-item');
        list.innerHTML = '';
        
        if (data.chats && data.chats.length > 0) {
            let currentChatHtml = '<p class="text-muted">No messages in current session yet.</p>';
            let hasPastChats = false;
            
            data.chats.forEach(chat => {
                const date = new Date(chat.last_updated).toLocaleString();
                const messageCount = chat.messages ? chat.messages.length : 0;
                
                const chatHtml = `
                    <div class="chat-history-card p-3 border border-secondary rounded d-flex justify-content-between align-items-center" style="background: rgba(26, 26, 46, 0.6);">
                        <div class="flex-grow-1">
                            <strong class="text-info">${chat.title || 'Chat Session'}</strong>
                            <div class="text-secondary small">${messageCount} messages • ${date}</div>
                        </div>
                        <div class="d-flex gap-2">
                            <button class="btn btn-sm btn-outline-info" onclick="window.app.loadChatIntoCurrentSession('${chat.id}')">
                                <i class="fas fa-folder-open"></i> Open
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="window.app.deleteChat('${chat.id}')">
                                <i class="fas fa-trash"></i> Delete
                            </button>
                        </div>
                    </div>
                `;
                
                if (window.app && window.app.currentChatId === chat.id) {
                    currentChatHtml = `
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <strong class="text-info">${chat.title || 'Current Chat'}</strong>
                                <div class="text-secondary small">${messageCount} messages</div>
                            </div>
                            <span class="badge bg-info text-dark">Active</span>
                        </div>
                    `;
                } else {
                    hasPastChats = true;
                    list.innerHTML += chatHtml;
                }
            });
            
            currentItem.innerHTML = currentChatHtml;
            if (!hasPastChats) {
                list.innerHTML = '<p class="text-center text-muted my-4">No past chat history found.</p>';
            }
        } else {
            currentItem.innerHTML = '<p class="text-muted">No messages in current session yet.</p>';
            list.innerHTML = '<p class="text-center text-muted my-4">No past chat history found.</p>';
        }
    } catch (err) {
        console.error("Failed to load chat history", err);
        const list = document.getElementById('chat-history-list');
        if (list) {
            list.innerHTML = '<p class="text-center text-danger my-4">Failed to load chat history. Please try again.</p>';
        }
    }
};

// Check authentication status on page load
document.addEventListener('DOMContentLoaded', async () => {
    console.log('[Auth] DOMContentLoaded fired');
    window.app = new CustodianAIApp();
    
    // First check if we have a cached user in localStorage
    const cachedUser = localStorage.getItem('custodian_user');
    console.log('[Auth] Cached user from localStorage:', cachedUser);
    
    if (cachedUser) {
        try {
            const user = JSON.parse(cachedUser);
            console.log('[Auth] Found cached user, calling updateUserProfile:', user);
            updateUserProfile(user);
            // User has cached profile - load chat history in background
            console.log('[Auth] Using cached user from localStorage, loading chat history...');
            // Load chat history silently in background after a short delay
            setTimeout(() => {
                if (typeof window.loadChatHistory === 'function') {
                    window.loadChatHistory().catch(e => console.log('[Auth] Background chat history load failed:', e));
                }
            }, 1500);
            return;
        } catch (e) {
            // Invalid cached data, clear it
            console.error('[Auth] Error parsing cached user:', e);
            localStorage.removeItem('custodian_user');
        }
    }
    
    // If no cached user, try backend auth status
    try {
        console.log('[Auth] No cached user, checking backend auth status...');
        const response = await fetch('/api/v1/auth/status', {
            credentials: 'include'  // This is crucial - sends cookies with the request
        });
        const data = await response.json();
        console.log('[Auth] Auth status response:', data);
        
        if (data.authenticated && data.user) {
            console.log('[Auth] Backend says authenticated, updating profile with:', data.user);
            updateUserProfile(data.user);
            console.log('[Auth] updateUserProfile called successfully');
            // Load chat history in background after authentication
            setTimeout(() => {
                if (typeof window.loadChatHistory === 'function') {
                    window.loadChatHistory().catch(e => console.log('[Auth] Background chat history load failed:', e));
                }
            }, 1500);
        } else {
            // Not authenticated - show guest login item in dropdown and show login modal
            console.log('[Auth] Not authenticated, showing login modal');
            const guestLoginItem = document.getElementById('guest-login-item');
            if (guestLoginItem) guestLoginItem.style.display = '';
            setTimeout(() => {
                const authModal = new bootstrap.Modal(document.getElementById('authModal'));
                authModal.show();
            }, 1000);
        }
    } catch (err) {
        console.error('[Auth] Failed to check auth status', err);
        // Only show modal if we truly have no cached user
        setTimeout(() => {
            const authModal = new bootstrap.Modal(document.getElementById('authModal'));
            authModal.show();
        }, 1000);
    }
});

// Add some futuristic visual effects
document.addEventListener('DOMContentLoaded', () => {
    createParticleEffect();
    addTypingEffect();
});

function createParticleEffect() {
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

// =============================================================================
// API KEYS MANAGEMENT
// =============================================================================

/**
 * Load API keys from backend and update status badges + input placeholders.
 * Called when the API Keys modal is opened (onclick="loadApiKeys()").
 */
window.loadApiKeys = async function() {
    var msgEl = document.getElementById('api-keys-message');
    if (msgEl) { msgEl.className = 'alert d-none mt-3'; msgEl.textContent = ''; }

    // Always refresh the active agent/provider display when the modal opens
    if (window.app && window.app.currentAgent) {
        window.app._updateApiKeysAgentDisplay(window.app.currentAgent);
    }

    try {
        var resp = await fetch('/api/v1/user/api-keys', { credentials: 'include' });
        if (!resp.ok) {
            if (resp.status === 401) {
                _showApiKeyMessage('You must be logged in to manage API keys.', 'warning');
            }
            return;
        }
        var data = await resp.json();
        var keys = data.keys || {};

        var providers = [
            { field: 'groq_api_key',      statusEl: 'groq-key-status',      inputEl: 'groq-key-input',      placeholder: 'gsk_...' },
            { field: 'gemini_api_key',    statusEl: 'gemini-key-status',    inputEl: 'gemini-key-input',    placeholder: 'AIza...' },
            { field: 'anthropic_api_key', statusEl: 'anthropic-key-status', inputEl: 'anthropic-key-input', placeholder: 'sk-ant-...' },
            { field: 'nim_api_key',       statusEl: 'nim-key-status',       inputEl: 'nim-key-input',       placeholder: 'nvapi-...' }
        ];

        providers.forEach(function(p) {
            var statusBadge = document.getElementById(p.statusEl);
            var input = document.getElementById(p.inputEl);
            var keyInfo = keys[p.field];

            if (keyInfo && keyInfo.set) {
                if (statusBadge) {
                    statusBadge.className = 'ms-auto badge bg-success';
                    statusBadge.textContent = keyInfo.masked ? 'Set (' + keyInfo.masked + ')' : 'Set ✓';
                }
                if (input) input.placeholder = keyInfo.masked || '••••••••';
            } else {
                if (statusBadge) {
                    statusBadge.className = 'ms-auto badge bg-secondary';
                    statusBadge.textContent = 'Using server default';
                }
                if (input) input.placeholder = p.placeholder;
            }
            if (input) input.value = '';
        });

    } catch (err) {
        console.error('Failed to load API keys:', err);
        _showApiKeyMessage('Failed to load API keys. Please try again.', 'danger');
    }
};

/**
 * Save a single provider API key to the backend.
 * @param {string} provider - 'gemini' | 'anthropic' | 'nim'
 */
window.saveApiKey = async function(provider) {
    var inputMap = { groq: 'groq-key-input', gemini: 'gemini-key-input', anthropic: 'anthropic-key-input', nim: 'nim-key-input' };
    var fieldMap = { groq: 'groq_api_key', gemini: 'gemini_api_key', anthropic: 'anthropic_api_key', nim: 'nim_api_key' };

    var inputEl = document.getElementById(inputMap[provider]);
    var keyValue = inputEl ? inputEl.value.trim() : '';

    if (!keyValue) {
        _showApiKeyMessage('Please enter a ' + provider + ' API key before saving.', 'warning');
        return;
    }

    try {
        var body = {};
        body[fieldMap[provider]] = keyValue;

        var resp = await fetch('/api/v1/user/api-keys', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (!resp.ok) {
            var errData = await resp.json().catch(function() { return {}; });
            throw new Error(errData.detail || 'Failed to save key');
        }

        _showApiKeyMessage(_capitalize(provider) + ' API key saved successfully!', 'success');
        await loadApiKeys();

    } catch (err) {
        console.error('Error saving ' + provider + ' key:', err);
        _showApiKeyMessage('Error: ' + err.message, 'danger');
    }
};

/**
 * Delete a provider API key from the backend.
 * @param {string} provider - 'gemini' | 'anthropic' | 'nim'
 */
window.deleteApiKey = async function(provider) {
    if (!confirm('Remove your ' + _capitalize(provider) + ' API key? The server default will be used instead.')) return;

    try {
        var resp = await fetch('/api/v1/user/api-keys/' + provider, {
            method: 'DELETE',
            credentials: 'include'
        });

        if (!resp.ok) {
            var errData = await resp.json().catch(function() { return {}; });
            throw new Error(errData.detail || 'Failed to delete key');
        }

        _showApiKeyMessage(_capitalize(provider) + ' API key removed.', 'info');
        await loadApiKeys();

    } catch (err) {
        console.error('Error deleting ' + provider + ' key:', err);
        _showApiKeyMessage('Error: ' + err.message, 'danger');
    }
};

function _showApiKeyMessage(text, type) {
    var el = document.getElementById('api-keys-message');
    if (!el) return;
    el.className = 'alert alert-' + type + ' mt-3';
    el.textContent = text;
    setTimeout(function() { el.className = 'alert d-none mt-3'; el.textContent = ''; }, 4000);
}

function _capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

// =============================================================================
// MY PLAN MODAL
// =============================================================================

window.loadMyPlan = async function() {
    const body = document.getElementById('my-plan-body');
    if (!body) return;
    body.innerHTML = '<div class="text-center text-muted py-4"><i class="fas fa-spinner fa-spin fa-2x"></i><p class="mt-2">Loading...</p></div>';
    try {
        const resp = await fetch('/api/v1/user/plan', { credentials: 'include' });
        const data = await resp.json();
        const plan = data.plan || 'guest';
        const isGuest = plan === 'guest';
        const isFree = plan === 'free';
        const isPro = plan === 'pro';
        const pct = Math.min(100, Math.round((data.requests_today / data.daily_limit) * 100));
        const barColor = pct >= 100 ? 'bg-danger' : pct >= 80 ? 'bg-warning' : 'bg-info';

        const planBadgeClass = isGuest ? 'bg-secondary' : isFree ? 'bg-info text-dark' : 'bg-warning text-dark';
        const planIcon = isGuest ? 'user-secret' : isFree ? 'user' : 'crown';
        const planLabel = isGuest ? 'Guest' : isFree ? 'Free' : 'Pro';

        body.innerHTML = `
            <div class="text-center mb-4">
                <span class="badge ${planBadgeClass} fs-6 px-3 py-2">
                    <i class="fas fa-${planIcon} me-2"></i>${planLabel}
                </span>
            </div>
            <div class="mb-4">
                <div class="d-flex justify-content-between small mb-1">
                    <span class="text-muted">Daily requests used</span>
                    <span class="fw-bold">${data.requests_today} / ${data.daily_limit}</span>
                </div>
                <div class="progress" style="height: 10px;">
                    <div class="progress-bar ${barColor}" role="progressbar" style="width:${pct}%"></div>
                </div>
                <div class="small text-muted mt-1">${data.remaining} request${data.remaining !== 1 ? 's' : ''} remaining today</div>
            </div>
            <div class="mb-4">
                <h6 class="text-info mb-2"><i class="fas fa-plug me-2"></i>Provider Access</h6>
                <div class="d-flex gap-2 flex-wrap">
                    ${['gemini','anthropic','nim'].map(p => {
                        const allowed = data.allowed_providers && data.allowed_providers.includes(p);
                        const labels = {gemini:'Google Gemini', anthropic:'Anthropic Claude', nim:'NVIDIA NIM'};
                        return `<span class="badge ${allowed ? 'bg-success' : 'bg-secondary'}">${allowed ? '✓' : '✗'} ${labels[p]}</span>`;
                    }).join('')}
                </div>
            </div>
            ${isGuest ? `
            <div class="border border-warning rounded p-3 mt-3">
                <h6 class="text-warning mb-2"><i class="fas fa-star me-2"></i>Sign In for More</h6>
                <ul class="text-muted small mb-3">
                    <li>20 requests/day on Free plan</li>
                    <li>50 requests/day on Pro plan</li>
                    <li>Access to Gemini, Claude &amp; NIM</li>
                    <li>Chat history &amp; course progress saved</li>
                </ul>
                <a href="/api/v1/auth/google" class="btn btn-success w-100">
                    <i class="fab fa-google me-2"></i>Sign in with Google — It's Free
                </a>
            </div>` : isFree ? `
            <div class="border border-info rounded p-3 mt-3">
                <h6 class="text-info mb-2"><i class="fas fa-crown me-2"></i>Upgrade to Pro</h6>
                <ul class="text-muted small mb-3">
                    <li>50 requests/day (vs 20 on Free)</li>
                    <li>Priority access to all providers</li>
                </ul>
                <button class="btn btn-warning text-dark w-100 fw-bold" onclick="bootstrap.Modal.getInstance(document.getElementById('myPlanModal'))?.hide(); setTimeout(() => window.app && window.app.openPaymentPage(), 300);">
                    <i class="fas fa-crown me-2"></i>Upgrade to Pro — $9.99/mo
                </button>
            </div>` : `
            <div class="text-center text-muted small mt-3">
                <i class="fas fa-check-circle text-success me-1"></i>You have full Pro access to all providers and features.
            </div>`}
        `;

        // Show/hide guest login item in dropdown
        const guestItem = document.getElementById('guest-login-item');
        if (guestItem) guestItem.style.display = isGuest ? 'block' : 'none';

    } catch(e) {
        console.error('Failed to load plan:', e);
        if (body) body.innerHTML = '<p class="text-danger text-center">Failed to load plan info. Please try again.</p>';
    }
};

// =============================================================================
// PROVIDER DETECTION HELPERS
// =============================================================================

/**
 * Derive the provider key ('gemini' | 'anthropic' | 'nim') from an agent object.
 * Uses agent name prefix conventions set in agent_manager.py.
 */
function _getAgentProvider(agent) {
    if (!agent) return null;
    const name = agent.name || '';
    if (name.startsWith('NIM-')) return 'nim';
    if (name.startsWith('Claude-') || name === 'ClaudeCode-AI') return 'anthropic';
    // All agents are now Groq by default (primary provider)
    // Groq agents have no special prefix — they use the same names as before
    return 'groq';
}

const _providerMeta = {
    groq:      { label: 'Groq (Llama)',     badgeClass: 'bg-success text-dark', icon: 'fas fa-bolt',      cardId: 'groq-provider-card' },
    gemini:    { label: 'Google Gemini',    badgeClass: 'bg-info text-dark',    icon: 'fab fa-google',    cardId: 'gemini-provider-card' },
    anthropic: { label: 'Anthropic Claude', badgeClass: 'bg-warning text-dark', icon: 'fas fa-brain',     cardId: 'anthropic-provider-card' },
    nim:       { label: 'NVIDIA NIM',       badgeClass: 'bg-secondary',         icon: 'fas fa-microchip', cardId: 'nim-provider-card' }
};

/**
 * Update the active agent/provider display inside the API Keys modal.
 * Called from selectChatAgent() whenever an agent is selected.
 */
CustodianAIApp.prototype._updateApiKeysAgentDisplay = function(agent) {
    const bar = document.getElementById('api-keys-active-agent');
    const nameEl = document.getElementById('api-keys-agent-name');
    const specEl = document.getElementById('api-keys-agent-spec');
    const badgeEl = document.getElementById('api-keys-provider-badge');

    if (!bar) return;

    if (!agent) {
        bar.classList.add('d-none');
        return;
    }

    const provider = _getAgentProvider(agent);
    const meta = _providerMeta[provider] || { label: 'Unknown', badgeClass: 'bg-secondary', icon: 'fas fa-robot' };

    bar.classList.remove('d-none');
    if (nameEl) nameEl.textContent = agent.name;
    if (specEl) specEl.textContent = agent.specialization ? '· ' + agent.specialization : '';
    if (badgeEl) {
        badgeEl.className = 'badge ' + meta.badgeClass;
        badgeEl.innerHTML = `<i class="${meta.icon} me-1"></i>${meta.label}`;
    }

    // Highlight the matching provider card in the modal
    _highlightActiveProviderCard(provider);
};

// =============================================================================
// MODEL SELECTOR
// =============================================================================

const _providerModels = {
    gemini: [
        { id: 'gemini-2.5-flash',   label: 'Gemini 2.5 Flash (default)' },
        { id: 'gemini-2.5-pro',     label: 'Gemini 2.5 Pro' },
        { id: 'gemini-2.0-flash',   label: 'Gemini 2.0 Flash' },
        { id: 'gemini-1.5-pro',     label: 'Gemini 1.5 Pro' },
        { id: 'gemini-1.5-flash',   label: 'Gemini 1.5 Flash' }
    ],
    anthropic: [
        { id: 'claude-sonnet-4-5',  label: 'Claude Sonnet 4.5 (default)' },
        { id: 'claude-opus-4-5',    label: 'Claude Opus 4.5' },
        { id: 'claude-haiku-3-5',   label: 'Claude Haiku 3.5' },
        { id: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet' },
        { id: 'claude-3-opus-20240229',     label: 'Claude 3 Opus' }
    ],
    nim: [
        { id: 'meta/llama-3.3-70b-instruct',  label: 'Llama 3.3 70B (default)' },
        { id: 'deepseek-ai/deepseek-r1',       label: 'DeepSeek R1' },
        { id: 'meta/llama-3.1-405b-instruct',  label: 'Llama 3.1 405B' },
        { id: 'mistralai/mixtral-8x22b-instruct-v0.1', label: 'Mixtral 8x22B' },
        { id: 'nvidia/llama-3.1-nemotron-70b-instruct', label: 'Nemotron 70B' }
    ]
};

/**
 * Open a model selector dropdown/popover for the current provider.
 */
CustodianAIApp.prototype.openModelSelector = function() {
    if (!this.currentAgent) return;

    // ── Guest restriction: NIM only, no model switching ──────────────────────
    const isGuestUser = !localStorage.getItem('custodian_user');
    if (isGuestUser) {
        // Show a brief tooltip-style notice but keep existing messages intact
        const existing = document.getElementById('model-selector-popup');
        if (existing) { existing.remove(); return; }
        const popup = document.createElement('div');
        popup.id = 'model-selector-popup';
        popup.className = 'model-selector-popup';
        popup.innerHTML = `
            <div class="model-selector-header">
                <span class="text-warning small fw-bold"><i class="fas fa-lock me-1"></i>Guest Mode</span>
                <button class="btn btn-sm btn-icon-only text-secondary" onclick="document.getElementById('model-selector-popup').remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="p-3 text-muted small">
                Guests use <strong class="text-success">NVIDIA NIM</strong> by default.<br>
                <a href="/api/v1/auth/google" class="text-info">Sign in with Google</a> to switch models.
            </div>
        `;
        const anchor = document.getElementById('active-model-display');
        if (anchor) {
            const rect = anchor.getBoundingClientRect();
            popup.style.position = 'fixed';
            popup.style.top = (rect.bottom + 6) + 'px';
            popup.style.left = rect.left + 'px';
        }
        document.body.appendChild(popup);
        setTimeout(() => {
            document.addEventListener('click', function closePopup(e) {
                if (!popup.contains(e.target) && e.target !== anchor) {
                    popup.remove();
                    document.removeEventListener('click', closePopup);
                }
            });
        }, 100);
        return;
    }

    const provider = _getAgentProvider(this.currentAgent);
    const models = _providerModels[provider] || [];
    const currentModel = this.currentModelOverride || null;

    // Build a simple Bootstrap dropdown list as a floating div
    const existing = document.getElementById('model-selector-popup');
    if (existing) { existing.remove(); return; } // toggle off

    const popup = document.createElement('div');
    popup.id = 'model-selector-popup';
    popup.className = 'model-selector-popup';
    popup.innerHTML = `
        <div class="model-selector-header">
            <span class="text-info small fw-bold">Select Model</span>
            <button class="btn btn-sm btn-icon-only text-secondary" onclick="document.getElementById('model-selector-popup').remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <ul class="model-selector-list list-unstyled mb-0">
            ${models.map(m => `
                <li class="model-selector-item ${currentModel === m.id ? 'active' : ''}" onclick="window.app.selectModel('${m.id}', '${m.label}')">
                    ${m.label}
                    ${currentModel === m.id ? '<i class="fas fa-check ms-auto text-info"></i>' : ''}
                </li>
            `).join('')}
        </ul>
    `;

    // Position near the model display span
    const anchor = document.getElementById('active-model-display');
    if (anchor) {
        const rect = anchor.getBoundingClientRect();
        popup.style.position = 'fixed';
        popup.style.top = (rect.bottom + 6) + 'px';
        popup.style.left = rect.left + 'px';
    }

    document.body.appendChild(popup);

    // Close on outside click
    setTimeout(() => {
        document.addEventListener('click', function closePopup(e) {
            if (!popup.contains(e.target) && e.target !== anchor) {
                popup.remove();
                document.removeEventListener('click', closePopup);
            }
        });
    }, 100);
};

/**
 * Apply a model selection for the current provider.
 */
CustodianAIApp.prototype.selectModel = function(modelId, modelLabel) {
    this.currentModelOverride = modelId;
    // Update the display
    const nameEl = document.getElementById('active-model-name');
    if (nameEl) nameEl.textContent = modelLabel.replace(' (default)', '');
    // Close popup
    const popup = document.getElementById('model-selector-popup');
    if (popup) popup.remove();
    // Store in localStorage for persistence
    localStorage.setItem('custodian_model_override_' + _getAgentProvider(this.currentAgent), modelId);
};

/**
 * Switch the active chat agent to the first available agent for the given provider.
 * Called by the Gemini / Claude / NIM quick-switch buttons in the API Keys modal.
 */
CustodianAIApp.prototype.switchToProvider = async function(provider) {
    const validProviders = ['groq', 'gemini', 'anthropic', 'nim'];
    if (!validProviders.includes(provider)) return;

    // Show a brief loading indicator on the button
    const btnMap = { gemini: 'fab fa-google', anthropic: 'fas fa-brain', nim: 'fas fa-microchip' };
    const providerLabels = { groq: 'Groq', gemini: 'Gemini', anthropic: 'Claude', nim: 'NIM' };

    try {
        // Call backend to switch provider server-side
        const resp = await fetch('/api/v1/provider/switch', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ provider })
        });

        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || 'Failed to switch provider');
        }

        // Reload agents from backend (agent IDs change after provider switch)
        const agentsResp = await fetch('/api/v1/agents', { credentials: 'include' });
        const agentsData = await agentsResp.json();
        this.agents = agentsData.agents;
        this.updateDashboardAgentList(agentsData.agents);
        this.updateModalAgentList(agentsData.agents);
        this.updatePreferredAgentSelect(agentsData.agents);

        // Close the API Keys modal
        const apiKeysModalEl = document.getElementById('apiKeysModal');
        if (apiKeysModalEl) {
            const modal = bootstrap.Modal.getInstance(apiKeysModalEl);
            if (modal) modal.hide();
        }

        // Select the first available agent (CustodianAI preferred)
        const preferred = ['CustodianAI'];
        let target = this.agents.find(a => preferred.includes(a.name));
        if (!target) target = this.agents[0];

        if (target) {
            setTimeout(() => {
                this.selectChatAgent(target);
            }, 300);
        }

    } catch (err) {
        console.error('Error switching provider:', err);
        alert('Failed to switch to ' + (providerLabels[provider] || provider) + ': ' + err.message);
    }
};

/**
 * Open the payment page in a popup window and watch for it to close,
 * then refresh the plan info.
 */
CustodianAIApp.prototype.openPaymentPage = function() {
    const popup = window.open(
        '/payment.html',
        'custodian_payment',
        'width=520,height=760,scrollbars=yes,resizable=no,toolbar=no,menubar=no,location=no,status=no'
    );

    if (!popup) {
        alert('Please allow popups for this site to open the payment page.');
        return;
    }

    // Poll until popup closes, then refresh plan info
    const pollTimer = setInterval(() => {
        if (popup.closed) {
            clearInterval(pollTimer);
            // Refresh plan info in My Plan modal if it's open
            loadMyPlan();
            // Also show a brief toast/notification
            const toastEl = document.createElement('div');
            toastEl.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;background:rgba(26,26,46,0.97);border:1px solid rgba(0,229,255,0.4);border-radius:10px;padding:14px 20px;color:#e8e8e8;font-size:0.9rem;box-shadow:0 4px 20px rgba(0,0,0,0.5);';
            toastEl.innerHTML = '<i class="fas fa-sync-alt me-2 text-info"></i>Checking your plan status...';
            document.body.appendChild(toastEl);
            setTimeout(() => toastEl.remove(), 3000);
        }
    }, 500);
};

/**
 * Show rate limit exceeded modal/popup for logged-in free users.
 */
CustodianAIApp.prototype._showRateLimitModal = function(planInfo) {
    const modalEl = document.getElementById('rateLimitModal');
    if (modalEl) {
        // Update modal content with plan info
        const remaining = planInfo ? planInfo.remaining : 0;
        const daily = planInfo ? planInfo.daily_limit : 0;
        const plan = planInfo ? planInfo.plan : 'free';
        const infoEl = document.getElementById('rate-limit-plan-info');
        if (infoEl) {
            infoEl.innerHTML = `You are on the <strong>${plan}</strong> plan (${daily} requests/day). Your limit resets at midnight UTC.`;
        }
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    } else {
        // Fallback: show a simple alert
        alert('⚠️ Daily request limit reached.\n\nSwitching to a different model as you have run out of free requests for this model today.\n\nYour limit resets at midnight UTC.');
    }
};

/**
 * Add/remove a highlight ring on the provider card that matches the active agent.
 */
function _highlightActiveProviderCard(activeProvider) {
    // Map provider key → the card's border-secondary class parent
    const providerCardMap = {
        gemini:    'gemini-key-input',
        anthropic: 'anthropic-key-input',
        nim:       'nim-key-input'
    };

    Object.keys(providerCardMap).forEach(function(p) {
        const inputEl = document.getElementById(providerCardMap[p]);
        if (!inputEl) return;
        const card = inputEl.closest('.card');
        if (!card) return;
        if (p === activeProvider) {
            card.classList.add('provider-card-active');
        } else {
            card.classList.remove('provider-card-active');
        }
    });
}
