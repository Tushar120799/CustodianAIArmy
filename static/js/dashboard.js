/**
 * dashboard.js — Chat, Agents, Provider Switching
 * Used by: /dashboard
 */

class DashboardApp {
    constructor() {
        this.agents = [];
        this.selectedAgent = null;
        this.chatHistory = [];
        this.isLoading = false;
        this.savedModel = localStorage.getItem('selectedModel');
    }

    async init() {
        await this.loadAgents();
        this.initChatInput();
        // Show auth modal for guests after short delay
        setTimeout(() => {
            if (!window.currentUser) {
                const modal = document.getElementById('authModal');
                if (modal && typeof bootstrap !== 'undefined') {
                    const bsModal = new bootstrap.Modal(modal);
                    bsModal.show();
                }
            }
        }, 1500);
    }

    async loadAgents() {
        try {
            const data = await apiFetch('/agents/main');
            this.agents = data.main_agents || [];
            this.renderAgentList();
            this.renderModalAgentList();
            this.renderMobileSelect();
            document.getElementById('active-agents').textContent = this.agents.length;
            // Auto-select first agent
            if (this.agents.length > 0 && !this.selectedAgent) {
                this.selectAgent(this.agents[0]);
            }
        } catch (e) {
            console.error('Failed to load agents:', e);
        }
    }

    renderAgentList() {
        const container = document.getElementById('dashboard-agent-list');
        if (!container) return;
        container.innerHTML = this.agents.map(agent => `
            <div class="agent-list-item d-flex align-items-center gap-2 p-2 rounded mb-1"
                style="cursor:pointer;border:1px solid transparent;transition:0.2s;"
                data-agent-id="${agent.agent_id}"
                onclick="window.dashApp.selectAgentById('${agent.agent_id}')">
                <i class="fas fa-robot text-info"></i>
                <div>
                    <div style="font-size:0.85rem;font-weight:600;color:var(--text-primary);">${agent.name}</div>
                    <div style="font-size:0.7rem;color:var(--text-muted);">${agent.specialization || 'general'}</div>
                </div>
            </div>
        `).join('');
    }

    renderModalAgentList() {
        const container = document.getElementById('modal-agent-list');
        if (!container) return;
        container.innerHTML = this.agents.map(agent => `
            <div class="agent-card" onclick="window.dashApp.selectAgentById('${agent.agent_id}'); bootstrap.Modal.getInstance(document.getElementById('agentSelectModal'))?.hide();">
                <div class="agent-header">
                    <span class="agent-title"><i class="fas fa-robot me-1"></i>${agent.name}</span>
                    <span class="agent-type">${agent.specialization || 'general'}</span>
                </div>
                <div style="font-size:0.8rem;color:var(--text-secondary);">${(agent.capabilities||[]).slice(0,3).map(c=>c.name||c).join(', ')}</div>
            </div>
        `).join('');
    }

    renderMobileSelect() {
        const sel = document.getElementById('mobile-agent-select');
        if (!sel) return;
        sel.innerHTML = '<option value="">Select Agent...</option>' +
            this.agents.map(a => `<option value="${a.agent_id}">${a.name}</option>`).join('');
    }

    selectAgentById(agentId) {
        const agent = this.agents.find(a => a.agent_id === agentId);
        if (agent) this.selectAgent(agent);
    }

    selectAgent(agent) {
        this.selectedAgent = agent;
        // Update UI
        document.querySelectorAll('.agent-list-item').forEach(el => {
            el.style.borderColor = el.dataset.agentId === agent.agent_id ? 'var(--primary-color)' : 'transparent';
            el.style.background = el.dataset.agentId === agent.agent_id ? 'rgba(0,123,255,0.08)' : '';
        });
        // Banner
        const banner = document.getElementById('active-agent-banner');
        const nameEl = document.getElementById('active-agent-name');
        const specEl = document.getElementById('active-agent-spec');
        if (banner) banner.style.display = 'flex';
        if (nameEl) nameEl.textContent = agent.name;
        if (specEl) specEl.textContent = agent.specialization ? `· ${agent.specialization}` : '';
        // Info panel
        const infoPanel = document.getElementById('agent-info-panel');
        if (infoPanel) {
            infoPanel.style.display = 'block';
            document.getElementById('info-agent-name').textContent = agent.name;
            document.getElementById('info-agent-spec').textContent = agent.specialization || '';
            document.getElementById('info-agent-desc').textContent = agent.description || '';
        }
        // Enable input
        const input = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-btn');
        if (input) { input.disabled = false; input.placeholder = `Message ${agent.name}...`; }
        if (sendBtn) sendBtn.disabled = false;
        // Mobile select sync
        const mSel = document.getElementById('mobile-agent-select');
        if (mSel) mSel.value = agent.agent_id;
    }

    initChatInput() {
        const input = document.getElementById('chat-input');
        if (!input) return;
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.sendMessage(); }
        });
        input.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 150) + 'px';
        });
    }

    async sendMessage() {
        const input = document.getElementById('chat-input');
        const message = input?.value?.trim();
        if (!message || this.isLoading || !this.selectedAgent) return;

        this.isLoading = true;
        input.value = '';
        input.style.height = 'auto';
        document.getElementById('send-btn').disabled = true;

        // Add user message
        this.addMessage('user', 'You', message);
        this.chatHistory.push({ role: 'user', content: message });

        // Typing indicator
        const typingId = this.addTypingIndicator();

        try {
            const isGuest = !window.currentUser;
            const endpoint = isGuest ? '/chat/guest' : '/chat';
            const body = {
                message,
                agent_id: this.selectedAgent.agent_id,
                agent_name: this.selectedAgent.name,
                history: this.chatHistory.slice(-20)
            };

            const data = await apiFetch(endpoint, {
                method: 'POST',
                body: JSON.stringify(body)
            });

            this.removeTypingIndicator(typingId);

            const resp = data.agent_response;
            if (resp?.metadata?.rate_limited) {
                this.addMessage('agent', 'System', resp.content, true);
            } else {
                this.addMessage('agent', resp.agent_name || this.selectedAgent.name, resp.content, true);
                this.chatHistory.push({ role: 'assistant', content: resp.content });
            }

            // Update plan UI
            if (data.plan_info) updatePlanUI(data.plan_info);

        } catch (e) {
            this.removeTypingIndicator(typingId);
            this.addMessage('agent', 'System', `⚠️ Error: ${e.message}`, false);
        }

        this.isLoading = false;
        document.getElementById('send-btn').disabled = false;
        input.focus();
    }

    addMessage(role, sender, content, isMarkdown = false) {
        const container = document.getElementById('chat-messages');
        if (!container) return;
        // Remove welcome message
        const welcome = container.querySelector('.welcome-message');
        if (welcome) welcome.remove();

        const msgId = 'msg-' + Date.now();
        const div = document.createElement('div');
        div.className = `message ${role}`;
        div.id = msgId;

        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        let contentHtml = isMarkdown && typeof marked !== 'undefined'
            ? marked.parse(content)
            : content.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');

        div.innerHTML = `
            <div class="message-header">${sender} · ${time}</div>
            <div class="message-content markdown-body">${contentHtml}</div>
        `;
        container.appendChild(div);

        // Syntax highlight
        if (isMarkdown && typeof hljs !== 'undefined') {
            div.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
        }

        container.scrollTop = container.scrollHeight;
        return msgId;
    }

    addTypingIndicator() {
        const container = document.getElementById('chat-messages');
        const id = 'typing-' + Date.now();
        const div = document.createElement('div');
        div.className = 'message agent';
        div.id = id;
        div.innerHTML = `<div class="typing-indicator"><span></span><span></span><span></span></div>`;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        return id;
    }

    removeTypingIndicator(id) {
        document.getElementById(id)?.remove();
    }
}

// Init on DOM ready — wait for apiFetch to be available from shared.js
document.addEventListener('DOMContentLoaded', () => {
    window.dashApp = new DashboardApp();

    function tryInit(attempts) {
        if (typeof apiFetch === 'function') {
            window.dashApp.init();
        } else if (attempts > 0) {
            setTimeout(() => tryInit(attempts - 1), 150);
        } else {
            console.error('[Dashboard] apiFetch not available after retries');
        }
    }
    tryInit(10);
});
