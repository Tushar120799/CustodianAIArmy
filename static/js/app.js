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
            await Promise.all([
                this.loadAgents(),
                this.loadChatAgents()
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

            // Update the active agents count in the header
            document.getElementById('active-agents').textContent = data.agents.length;
        } catch (error) {
            console.error('Error loading agents:', error);
        }
    }

    async loadChatAgents() {
        try {
            // Use the /agents endpoint and filter for main agents on frontend
            const response = await fetch('/api/v1/agents');
            const data = await response.json();
            
            // Filter for main agents
            const mainAgents = data.agents.filter(agent => agent.type.toLowerCase() === 'main');
            
            this.updateChatAgentList(mainAgents);
            this.updateModalAgentList(mainAgents);
        } catch (error) {
            console.error('Error loading chat agents:', error);
        }
    }

    updateAgentsGrid(agents) {
        const grid = document.getElementById('agents-grid');
        if (!grid) return;

        grid.innerHTML = '';
        
        agents.forEach(agent => {
            const agentCard = document.createElement('div');
            agentCard.className = 'agent-card';
            
            const capabilities = agent.capabilities.map(cap => 
                `<span class="capability-tag">${cap.name}</span>`
            ).join('');

            // Direct-to-chat button
            const chatUrl = `/?section=chat&agent_id=${agent.agent_id}`;
            
            agentCard.innerHTML = `
                <div class="agent-header">
                    <div class="agent-title">${agent.name}</div>
                    <div class="agent-type">${agent.type}</div>
                </div>
                <div class="agent-info">
                    <p><strong>Specialization:</strong> ${agent.specialization || 'General'}</p>
                    <p><strong>Status:</strong> <span class="agent-status status-${agent.status}">${agent.status}</span></p>
                    <p><strong>Sub-agents:</strong> ${agent.sub_agents_count}</p>
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

    updateChatAgentList(agents) {
        const list = document.getElementById('chat-agent-list');
        if (!list) return;

        list.innerHTML = '';
        
        agents.forEach(agent => {
            const agentItem = document.createElement('div');
            agentItem.className = 'agent-list-item';
            agentItem.dataset.agentId = agent.agent_id;
            agentItem.dataset.agentName = agent.name;
            
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
        // Update UI
        document.querySelectorAll('.agent-list-item').forEach(item => {
            item.classList.remove('active');
        });
        
        const selectedItem = document.querySelector(`[data-agent-id="${agent.agent_id}"]`);
        if (selectedItem) {
            selectedItem.classList.add('active');
        }
        
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
        
        // Clear welcome message and show chat history
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.innerHTML = `
            <div class="message agent">
                <div class="message-header">${agent.name}</div>
                <div class="message-content">Hello! I'm ${agent.name}, your ${agent.specialization || 'general'} AI assistant. How can I help you today?</div>
            </div>
        `;
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
                    
                    const code = codeBlock.textContent;
                    
                    const runBtn = document.createElement('button');
                    runBtn.className = 'run-code-btn';
                    runBtn.innerHTML = '<i class="fas fa-play"></i> Run';
                    runBtn.onclick = () => this.runCode(code, lang, pre);
                    
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
        if (sectionName === 'agents') {
            // This section is removed, dashboard shows agents now.
            // Redirect or just show dashboard.
            window.location.href = '/?section=dashboard';
        } else if (sectionName === 'chat') {
            await this.loadChatAgents();
            // Always enable the change agent button on the chat page
            // so the user can make an initial selection.
            const changeAgentBtn = document.getElementById('change-agent-btn');
            if (changeAgentBtn) changeAgentBtn.disabled = false;
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

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new CustodianAIApp();
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