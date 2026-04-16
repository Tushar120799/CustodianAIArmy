/**
 * agents.js — Custom Agents Studio
 * Used by: /agents
 * Features: Create, edit, publish custom agents with skills and MCP tools
 */

class CustomAgentsApp {
    constructor() {
        this.customAgents = [];
        this.skills = [];
        this.mcpTools = [];
        this.selectedAgent = null;
        this.creationMode = 'single'; // 'single' or 'army'
        this.currentChatHistory = [];
        this.suggestedAgents = [];
        this.librarySkills = [];
        this.libraryMCPs = [];
    }

    async init() {
        await this.loadCustomAgents();
        await this.loadSkills();
        await this.loadLibraryData();
        this.initChatInput();
        this.renderLibrary();
    }

    async loadCustomAgents() {
        try {
            const data = await apiFetch('/agents/custom');
            this.customAgents = data.agents || [];
            this.renderCustomAgentsGrid();
            this.updateStats();
        } catch (e) {
            console.error('Failed to load custom agents:', e);
            this.customAgents = [];
            this.renderCustomAgentsGrid();
        }
    }

    async loadSkills() {
        try {
            const data = await apiFetch('/agents/skills');
            this.skills = data.skills || [];
            document.getElementById('skills-count').textContent = this.skills.length;
        } catch (e) {
            console.error('Failed to load skills:', e);
            this.skills = [];
        }
    }

    async loadLibraryData() {
        // Using placeholder data as requested
        this.librarySkills = Array.from({ length: 22 }, (_, i) => ({
            id: `lib_skill_${i}`,
            name: `Library Skill ${i + 1}`,
            description: `This is a short description for library skill #${i + 1}. It enables a specific capability.`
        }));
        this.libraryMCPs = Array.from({ length: 25 }, (_, i) => ({
            id: `lib_mcp_${i}`,
            name: `MCP Server ${i + 1}`,
            description: `Description for MCP server tool #${i + 1}. It connects to an external service.`
        }));
    }

    renderLibrary(skillFilter = '', mcpFilter = '') {
        const skillsContainer = document.getElementById('library-skills-list');
        const mcpContainer = document.getElementById('library-mcp-list');

        const renderItem = (item) => `
            <div class="library-item">
                <div class="library-item-info">
                    <div class="library-item-name">${this.escapeHtml(item.name)}</div>
                    <div class="library-item-desc">${this.escapeHtml(item.description)}</div>
                </div>
                <button class="btn btn-sm btn-outline-info" onclick="window.agentsApp.addLibraryItem('${item.id.startsWith('lib_skill') ? 'skill' : 'mcp'}', '${item.id}')">
                    <i class="fas fa-plus"></i> Add
                </button>
            </div>
        `;

        if (skillsContainer) {
            const filteredSkills = this.librarySkills.filter(s => s.name.toLowerCase().includes(skillFilter.toLowerCase()));
            skillsContainer.innerHTML = filteredSkills.map(renderItem).join('');
        }
        if (mcpContainer) {
            const filteredMCPs = this.libraryMCPs.filter(m => m.name.toLowerCase().includes(mcpFilter.toLowerCase()));
            mcpContainer.innerHTML = filteredMCPs.map(renderItem).join('');
        }
    }

    filterLibrary(type, query) {
        if (type === 'skills') {
            this.renderLibrary(query, '');
        } else if (type === 'mcp') {
            this.renderLibrary('', query);
        }
    }

    updateStats() {
        const myCount = this.customAgents.length;
        const publishedCount = this.customAgents.filter(a => a.is_public).length;
        document.getElementById('my-agents-count').textContent = myCount;
        document.getElementById('published-agents-count').textContent = publishedCount;
        document.getElementById('skills-count').textContent = this.skills.length;
    }

    setCreationMode(mode) {
        this.creationMode = mode;
        document.querySelectorAll('.creation-mode-toggle .mode-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });
        
        if (mode === 'army') {
            const modal = new bootstrap.Modal(document.getElementById('armyChatModal'));
            modal.show();
        }
    }

    renderCustomAgentsGrid(filter = 'all') {
        const container = document.getElementById('custom-agents-grid');
        if (!container) return;

        let filtered = this.customAgents;
        if (filter === 'private') {
            filtered = this.customAgents.filter(a => !a.is_public);
        } else if (filter === 'public') {
            filtered = this.customAgents.filter(a => a.is_public);
        }

        if (filtered.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5" style="color:var(--text-muted);">
                    <i class="fas fa-robot fa-3x mb-3" style="opacity:0.3;"></i>
                    <p>No custom agents yet. Create your first agent!</p>
                </div>
            `;
            return;
        }

        container.innerHTML = filtered.map(agent => `
            <div class="custom-agent-card ${this.selectedAgent?.agent_id === agent.agent_id ? 'selected' : ''}" 
                 onclick="window.agentsApp.selectCustomAgent('${agent.agent_id}')">
                <span class="custom-agent-badge custom">Custom</span>
                <span class="custom-agent-badge ${agent.is_public ? 'public' : 'private'}">
                    ${agent.is_public ? 'Published' : 'Private'}
                </span>
                <div class="custom-agent-header">
                    <div class="custom-agent-icon">
                        <i class="fas fa-robot"></i>
                    </div>
                    <div>
                        <h4 class="custom-agent-name">${this.escapeHtml(agent.name)}</h4>
                        <p class="custom-agent-spec">${this.escapeHtml(agent.specialization || 'General')}</p>
                    </div>
                </div>
                <p class="custom-agent-desc">${this.escapeHtml(agent.description || 'No description')}</p>
                <div class="custom-agent-meta">
                    <span><i class="fas fa-star me-1"></i>${(agent.skills || []).length} Skills</span>
                    <span><i class="fas fa-plug me-1"></i>${(agent.mcp_tools || []).length} MCPs</span>
                </div>
                ${(agent.skills || []).length > 0 ? `
                    <div class="custom-agent-skills mt-2">
                        ${(agent.skills || []).slice(0, 3).map(() => `<span class="custom-agent-skill-dot"></span>`).join('')}
                    </div>
                ` : ''}
                <div class="custom-agent-actions">
                    <button class="btn btn-outline-info" onclick="event.stopPropagation(); window.agentsApp.editAgent('${agent.agent_id}')">
                        <i class="fas fa-edit me-1"></i>Edit
                    </button>
                    <button class="btn btn-outline-success" onclick="event.stopPropagation(); window.agentsApp.chatWithAgent('${agent.agent_id}')">
                        <i class="fas fa-comments me-1"></i>Chat
                    </button>
                </div>
            </div>
        `).join('');
    }

    selectCustomAgent(agentId) {
        const agent = this.customAgents.find(a => a.agent_id === agentId);
        if (!agent) return;
        
        this.selectedAgent = agent;
        this.renderCustomAgentsGrid();
        
        // Populate form with agent data
        document.getElementById('agent-name-input').value = agent.name || '';
        document.getElementById('agent-spec-input').value = agent.specialization || '';
        document.getElementById('agent-desc-input').value = agent.description || '';
        document.getElementById('generated-prompt-output').value = agent.prompt || '';
        
        // Set publishing option
        document.getElementById(agent.is_public ? 'publish-public' : 'publish-private').checked = true;
        this.updatePublicUrlDisplay(agent);
        
        // Render skills and MCP tools
        this.renderSelectedSkills(agent.skills || []);
        this.renderSelectedMCPTools(agent.mcp_tools || []);
    }

    editAgent(agentId) {
        this.selectCustomAgent(agentId);
        // Scroll to top of creation panel
        document.querySelector('.agents-creation-panel').scrollIntoView({ behavior: 'smooth' });
    }

    chatWithAgent(agentId) {
        const agent = this.customAgents.find(a => a.agent_id === agentId);
        if (!agent) return;
        
        this.selectedAgent = agent;
        document.getElementById('chat-agent-name').textContent = agent.name;
        document.getElementById('custom-agent-chat-card').style.display = 'block';
        document.getElementById('custom-chat-messages').innerHTML = `
            <div class="message agent">
                <div class="message-header">${agent.name}</div>
                <div class="message-content">Hello! I'm ${agent.name}, your ${agent.specialization || 'custom'} assistant. How can I help you today?</div>
            </div>
        `;
        this.currentChatHistory = [];
        
        // Scroll to chat
        document.getElementById('custom-agent-chat-card').scrollIntoView({ behavior: 'smooth' });
    }

    closeChat() {
        document.getElementById('custom-agent-chat-card').style.display = 'none';
        this.selectedAgent = null;
        this.renderCustomAgentsGrid();
    }

    async sendCustomMessage() {
        const input = document.getElementById('custom-chat-input');
        const message = input?.value?.trim();
        if (!message || !this.selectedAgent) return;

        input.value = '';
        
        // Add user message
        this.addCustomMessage('user', 'You', message);
        this.currentChatHistory.push({ role: 'user', content: message });

        try {
            const data = await apiFetch('/chat/custom', {
                method: 'POST',
                body: JSON.stringify({
                    message,
                    agent_id: this.selectedAgent.agent_id,
                    history: this.currentChatHistory.slice(-20)
                })
            });
            
            const response = data.response || data.message || 'No response generated';
            this.addCustomMessage('agent', this.selectedAgent.name, response);
            this.currentChatHistory.push({ role: 'assistant', content: response });
        } catch (e) {
            this.addCustomMessage('agent', 'System', `⚠️ Error: ${e.message}`);
        }
    }

    addCustomMessage(role, sender, content) {
        const container = document.getElementById('custom-chat-messages');
        if (!container) return;

        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const div = document.createElement('div');
        div.className = `message ${role}`;
        div.innerHTML = `
            <div class="message-header">${sender} · ${time}</div>
            <div class="message-content">${this.escapeHtml(content)}</div>
        `;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    initChatInput() {
        const input = document.getElementById('custom-chat-input');
        if (!input) return;
        
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendCustomMessage();
            }
        });
        
        input.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 100) + 'px';
        });
    }

    async generatePrompt() {
        const idea = document.getElementById('prompt-idea-input').value.trim();
        if (!idea) {
            showToast('Please enter an idea for your agent', 'warning');
            return;
        }

        try {
            const data = await apiFetch('/agents/generate-prompt', {
                method: 'POST',
                body: JSON.stringify({ idea, skills: this.getSelectedSkills() })
            });
            document.getElementById('generated-prompt-output').value = data.prompt || '';
            showToast('Prompt generated successfully!', 'success');
        } catch (e) {
            showToast('Failed to generate prompt', 'error');
        }
    }

    async refinePrompt() {
        const currentPrompt = document.getElementById('generated-prompt-output').value.trim();
        if (!currentPrompt) {
            showToast('Please generate a prompt first', 'warning');
            return;
        }

        try {
            const data = await apiFetch('/agents/refine-prompt', {
                method: 'POST',
                body: JSON.stringify({ prompt: currentPrompt })
            });
            document.getElementById('generated-prompt-output').value = data.prompt || '';
            showToast('Prompt refined!', 'success');
        } catch (e) {
            showToast('Failed to refine prompt', 'error');
        }
    }

    openAddSkillModal() {
        const modal = new bootstrap.Modal(document.getElementById('skillModal'));
        modal.show();
    }

    addSkill() {
        const name = document.getElementById('skill-name-input').value.trim();
        const desc = document.getElementById('skill-desc-input').value.trim();
        const category = document.getElementById('skill-category-input').value;

        if (!name) {
            showToast('Please enter a skill name', 'warning');
            return;
        }

        const skill = {
            id: 'skill_' + Date.now(),
            name,
            description: desc,
            category
        };

        this.skills.push(skill);
        this.renderSelectedSkills([...this.getSelectedSkills(), skill.id]);
        
        // Close modal
        bootstrap.Modal.getInstance(document.getElementById('skillModal'))?.hide();
        
        // Clear inputs
        document.getElementById('skill-name-input').value = '';
        document.getElementById('skill-desc-input').value = '';
        
        showToast('Skill added!', 'success');
    }

    getSelectedSkills() {
        const tags = document.querySelectorAll('.skill-tag');
        return Array.from(tags).map(t => t.dataset.skillId);
    }

    renderSelectedSkills(skillIds) {
        const container = document.getElementById('skills-tags-container');
        if (!container) return;

        if (skillIds.length === 0) {
            container.innerHTML = '<span class="text-muted small">No skills added yet.</span>';
            return;
        }

        container.innerHTML = skillIds.map(id => {
            const skill = this.skills.find(s => s.id === id) || { name: 'Unknown', category: 'other' };
            const icons = {
                technical: 'fa-code',
                creative: 'fa-palette',
                analytical: 'fa-chart-line',
                communication: 'fa-comments',
                other: 'fa-star'
            };
            const icon = icons[skill.category] || icons.other;
            
            return `
                <span class="skill-tag" data-skill-id="${id}">
                    <i class="fas ${icon} skill-icon"></i>
                    <span>${this.escapeHtml(skill.name)}</span>
                    <i class="fas fa-times skill-remove" onclick="window.agentsApp.removeSkill('${id}')"></i>
                </span>
            `;
        }).join('');
    }

    removeSkill(skillId) {
        const current = this.getSelectedSkills();
        const filtered = current.filter(id => id !== skillId);
        this.renderSelectedSkills(filtered);
    }

    addLibraryItem(type, itemId) {
        if (type === 'skill') {
            const skill = this.librarySkills.find(s => s.id === itemId);
            if (!skill) return;
            // To reuse existing logic, we add it to the main skills list if not present
            if (!this.skills.find(s => s.id === skill.id)) {
                this.skills.push({ ...skill, category: 'technical' });
            }
            this.renderSelectedSkills([...this.getSelectedSkills(), skill.id]);
            showToast(`Skill "${skill.name}" added!`, 'success');
        } else if (type === 'mcp') {
            const mcp = this.libraryMCPs.find(m => m.id === itemId);
            if (!mcp) return;
            if (!this.mcpTools.find(t => t.id === mcp.id)) {
                this.mcpTools.push({ ...mcp, endpoint: '', config: {} });
            }
            this.renderSelectedMCPTools([...this.getSelectedMCPTools(), mcp.id]);
            showToast(`MCP "${mcp.name}" added!`, 'success');
        }
    }

    openAddMCPModal() {
        const modal = new bootstrap.Modal(document.getElementById('mcpModal'));
        modal.show();
    }

    addMCPTool() {
        const name = document.getElementById('mcp-name-input').value.trim();
        const endpoint = document.getElementById('mcp-endpoint-input').value.trim();
        const configStr = document.getElementById('mcp-config-input').value.trim();

        if (!name) {
            showToast('Please enter a tool name', 'warning');
            return;
        }

        let config = {};
        if (configStr) {
            try {
                config = JSON.parse(configStr);
            } catch (e) {
                showToast('Invalid JSON configuration', 'error');
                return;
            }
        }

        const mcpTool = {
            id: 'mcp_' + Date.now(),
            name,
            endpoint,
            config
        };

        this.mcpTools.push(mcpTool);
        this.renderSelectedMCPTools([...this.getSelectedMCPTools(), mcpTool.id]);
        
        bootstrap.Modal.getInstance(document.getElementById('mcpModal'))?.hide();
        
        document.getElementById('mcp-name-input').value = '';
        document.getElementById('mcp-endpoint-input').value = '';
        document.getElementById('mcp-config-input').value = '';
        
        showToast('MCP tool added!', 'success');
    }

    getSelectedMCPTools() {
        const items = document.querySelectorAll('.mcp-tool-item');
        return Array.from(items).map(i => i.dataset.mcpId);
    }

    renderSelectedMCPTools(mcpIds) {
        const container = document.getElementById('mcp-tools-list');
        if (!container) return;

        if (mcpIds.length === 0) {
            container.innerHTML = '<span class="text-muted small">No MCP tools attached yet.</span>';
            return;
        }

        container.innerHTML = mcpIds.map(id => {
            const mcp = this.mcpTools.find(m => m.id === id) || { name: 'Unknown', endpoint: '' };
            return `
                <div class="mcp-tool-item" data-mcp-id="${id}">
                    <div class="mcp-tool-info">
                        <i class="fas fa-plug" style="color:var(--primary-color);"></i>
                        <div>
                            <div class="mcp-tool-name">${this.escapeHtml(mcp.name)}</div>
                            ${mcp.endpoint ? `<div class="mcp-tool-endpoint">${this.escapeHtml(mcp.endpoint)}</div>` : ''}
                        </div>
                    </div>
                    <i class="fas fa-times mcp-tool-remove" onclick="window.agentsApp.removeMCPTool('${id}')"></i>
                </div>
            `;
        }).join('');
    }

    removeMCPTool(mcpId) {
        const current = this.getSelectedMCPTools();
        const filtered = current.filter(id => id !== mcpId);
        this.renderSelectedMCPTools(filtered);
    }

    updatePublicUrlDisplay(agent) {
        const infoEl = document.getElementById('public-url-info');
        const urlEl = document.getElementById('share-url-display');
        
        if (agent.is_public && agent.public_url) {
            infoEl.style.display = 'block';
            urlEl.textContent = agent.public_url;
        } else {
            infoEl.style.display = 'none';
        }
    }

    async saveAgent() {
        const name = document.getElementById('agent-name-input').value.trim();
        const specialization = document.getElementById('agent-spec-input').value.trim();
        const description = document.getElementById('agent-desc-input').value.trim();
        const prompt = document.getElementById('generated-prompt-output').value.trim();
        const isPublic = document.getElementById('publish-public').checked;

        if (!name) {
            showToast('Please enter an agent name', 'warning');
            return;
        }

        const selectedSkillIds = this.getSelectedSkills();
        const selectedMCPIds = this.getSelectedMCPTools();

        const agentData = {
            name,
            specialization,
            description,
            prompt,
            is_public: isPublic,
            skills: selectedSkillIds,
            mcp_tools: selectedMCPIds
        };

        // If editing existing agent
        if (this.selectedAgent && this.selectedAgent.agent_id) {
            agentData.agent_id = this.selectedAgent.agent_id;
        }

        try {
            const data = await apiFetch('/agents/custom/save', {
                method: 'POST',
                body: JSON.stringify(agentData)
            });
            
            showToast(data.message || 'Agent saved successfully!', 'success');
            
            // Reload agents
            await this.loadCustomAgents();
            
            // If public, show share URL
            if (isPublic && data.public_url) {
                this.updatePublicUrlDisplay({ is_public: true, public_url: data.public_url });
            }
            
        } catch (e) {
            showToast('Failed to save agent: ' + e.message, 'error');
        }
    }

    filterAgents(filter) {
        this.renderCustomAgentsGrid(filter);
    }

    // Agent Army Methods
    async sendArmyChatMessage() {
        const input = document.getElementById('army-chat-input');
        const message = input?.value?.trim();
        if (!message) return;

        input.value = '';
        
        // Add user message
        this.addArmyMessage('user', 'You', message);
        this.currentChatHistory.push({ role: 'user', content: message });

        try {
            const data = await apiFetch('/agents/army/chat', {
                method: 'POST',
                body: JSON.stringify({
                    message,
                    history: this.currentChatHistory.slice(-20)
                })
            });
            
            const response = data.response || '';
            this.addArmyMessage('agent', 'AI Assistant', response);
            this.currentChatHistory.push({ role: 'assistant', content: response });
            
            // Check if there are suggested agents
            if (data.suggested_agents && data.suggested_agents.length > 0) {
                this.suggestedAgents = data.suggested_agents;
                this.renderSuggestedAgents();
            }
        } catch (e) {
            this.addArmyMessage('agent', 'System', `⚠️ Error: ${e.message}`);
        }
    }

    addArmyMessage(role, sender, content) {
        const container = document.getElementById('army-chat-messages');
        if (!container) return;

        const div = document.createElement('div');
        div.className = `message ${role}`;
        div.innerHTML = `
            <div class="message-header">${sender}</div>
            <div class="message-content">${this.escapeHtml(content)}</div>
        `;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    renderSuggestedAgents() {
        const container = document.getElementById('suggested-agents-list');
        const section = document.getElementById('army-suggested-agents');
        
        if (!container || this.suggestedAgents.length === 0) return;

        section.style.display = 'block';
        container.innerHTML = this.suggestedAgents.map((agent, idx) => `
            <div class="suggested-agent-item">
                <input type="checkbox" id="suggested-agent-${idx}" value="${idx}" checked>
                <label for="suggested-agent-${idx}" class="small mb-0" style="cursor:pointer;flex:1;">
                    <strong>${this.escapeHtml(agent.name)}</strong>
                    <br><small style="color:var(--text-muted);">${this.escapeHtml(agent.specialization || '')}</small>
                </label>
            </div>
        `).join('');
    }

    async createArmyFromSuggestions() {
        const checkboxes = document.querySelectorAll('#suggested-agents-list input[type="checkbox"]:checked');
        const selectedIndices = Array.from(checkboxes).map(cb => parseInt(cb.value));
        
        if (selectedIndices.length === 0) {
            showToast('Please select at least one agent', 'warning');
            return;
        }

        const agentsToCreate = selectedIndices.map(idx => this.suggestedAgents[idx]);

        try {
            const data = await apiFetch('/agents/army/create', {
                method: 'POST',
                body: JSON.stringify({ agents: agentsToCreate })
            });
            
            showToast(`Created ${agentsToCreate.length} agents!`, 'success');
            
            // Close modal
            bootstrap.Modal.getInstance(document.getElementById('armyChatModal'))?.hide();
            
            // Reload agents
            await this.loadCustomAgents();
            
            // Reset army chat
            this.suggestedAgents = [];
            this.currentChatHistory = [];
            document.getElementById('army-suggested-agents').style.display = 'none';
            document.getElementById('army-chat-messages').innerHTML = `
                <div class="message agent">
                    <div class="message-header">AI Assistant</div>
                    <div class="message-content">Hello! I'm here to help you build your agent army. Tell me about the types of agents you'd like to create and what tasks they should handle.</div>
                </div>
            `;
            
        } catch (e) {
            showToast('Failed to create agents: ' + e.message, 'error');
        }
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.agentsApp = new CustomAgentsApp();

    function tryInit(attempts) {
        if (typeof apiFetch === 'function') {
            window.agentsApp.init();
        } else if (attempts > 0) {
            setTimeout(() => tryInit(attempts - 1), 150);
        } else {
            console.error('[Agents] apiFetch not available after retries');
        }
    }
    tryInit(10);
});
