/**
 * build.js — MVP Builder Page Logic
 * Integrates with backend MVP Builder API for 5-phase pipeline
 */

document.addEventListener('DOMContentLoaded', () => {
    // State management
    let state = {
        session: null,
        currentFile: null,
        mode: 'plan', // 'plan' or 'act'
        isSending: false,
    };

    // UI Elements
    const cliOutput = document.getElementById('cli-output');
    const cliInput = document.getElementById('cli-input');
    const sendBtn = document.getElementById('send-btn');
    const agentStatus = document.getElementById('agent-status');
    const modeButtons = document.querySelectorAll('.mode-btn');
    const phaseSteps = document.querySelectorAll('.phase-step');
    const currentPhaseName = document.getElementById('current-phase-name');
    const overallProgress = document.getElementById('overall-progress').querySelector('.progress-fill');
    const progressPercent = document.getElementById('progress-percent');
    const terminalContent = document.getElementById('terminal-content');
    const projectNameEl = document.getElementById('project-name');
    const fileTreeEl = document.getElementById('file-tree');
    const editorTabsEl = document.getElementById('editor-tabs');
    const editorContentEl = document.getElementById('editor-content');
    const githubConnectorContainer = document.getElementById('github-connector-container');
    const publishBtn = document.getElementById('github-publish-btn');
    const newProjectBtn = document.getElementById('new-project-btn');
    const ideaChips = document.querySelectorAll('.idea-chip');


    // --- Core Functions ---

    const addLog = (message, level = 'info', target = terminalContent) => {
        const entry = document.createElement('div');
        entry.className = `log-entry ${level}`;
        entry.innerHTML = `<span>[${new Date().toLocaleTimeString()}]</span> ${message}`;
        target.appendChild(entry);
        target.scrollTop = target.scrollHeight;
    };

    const addCliMessage = (content, role) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `cli-message ${role}`;
        
        // Basic markdown-to-HTML conversion
        let htmlContent = content
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
            .replace(/\n/g, '<br>');

        messageDiv.innerHTML = htmlContent;
        cliOutput.appendChild(messageDiv);
        cliOutput.scrollTop = cliOutput.scrollHeight;

        // Remove welcome message if it exists
        const welcome = cliOutput.querySelector('.cli-welcome');
        if (welcome) welcome.remove();
    };

    const updateUI = () => {
        if (!state.session) return;

        // Update phase indicator
        phaseSteps.forEach((step, index) => {
            step.classList.remove('active', 'completed');
            if (index < state.session.current_phase_index) {
                step.classList.add('completed');
            } else if (index === state.session.current_phase_index) {
                step.classList.add('active');
            }
        });

        // Update progress panel
        currentPhaseName.textContent = state.session.current_phase || 'Not Started';
        overallProgress.style.width = `${state.session.overall_progress}%`;
        progressPercent.textContent = `${state.session.overall_progress}%`;
        
        // Update project name
        projectNameEl.textContent = state.session.product_idea || 'Untitled Project';

        // Update logs
        terminalContent.innerHTML = ''; // Clear and rebuild
        state.session.logs.forEach(log => addLog(log.message, log.level));

        // Update file explorer
        updateFileTree(state.session.files);

        // Update GitHub connection status
        updateGitHubConnector();
    };

    const updateFileTree = (files) => {
        if (!files || files.length === 0) {
            fileTreeEl.innerHTML = '<div class="empty-state">No files yet.</div>';
            return;
        }
        // This is a simplified tree view. A more robust implementation would handle nested directories.
        fileTreeEl.innerHTML = files.map(file => 
            `<div class="file-item" data-path="${file}"><i class="fas fa-file-code"></i> ${file}</div>`
        ).join('');
    };

    // --- GitHub Connection ---
    
    const handleGitHubAuthPopup = (sessionId) => {
        if (!sessionId) {
            addLog("Session ID is required to initiate GitHub auth.", "error");
            return;
        }

        addLog("Initiating GitHub connection...", "info");
        const authUrl = `/api/v1/auth/github/login?session_id=${sessionId}`;
        const popup = window.open(authUrl, 'github-auth', 'width=600,height=700');

        const handleMessage = async (event) => {
            // Security: Ensure message is from our origin
            if (event.origin !== window.location.origin) {
                return;
            }

            const { data } = event;
            if (data && data.provider === 'github' && data.token) {
                if (popup) popup.close();
                window.removeEventListener('message', handleMessage);

                if (data.session_id !== sessionId) {
                    addLog("GitHub auth session ID mismatch. Aborting.", "error");
                    return;
                }

                await finalizeGitHubConnection(data.token, data.username);
            } else if (data && data.error) {
                if (popup) popup.close();
                window.removeEventListener('message', handleMessage);
                addLog(`GitHub authentication failed: ${data.error}`, "error");
            }
        };

        window.addEventListener('message', handleMessage, false);
    };

    const finalizeGitHubConnection = async (token, username) => {
        addLog(`Authenticating with backend as ${username}...`, "info");
        try {
            const response = await fetch('/api/v1/mvp/connect-github', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: state.session.session_id,
                    github_token: token,
                }),
            });
            const result = await response.json();
            if (!response.ok || !result.success) {
                throw new Error(result.message || 'Backend connection failed.');
            }
            
            // Update session state and UI
            state.session.github_connected = true;
            state.session.github_username = result.github_username;
            addLog(`GitHub connected as ${result.github_username}!`, "success");
            updateGitHubConnector();

        } catch (error) {
            addLog(`Error finalizing GitHub connection: ${error.message}`, "error");
        }
    };

    const updateGitHubConnector = () => {
        if (!state.session) return;

        if (state.session.github_connected) {
            githubConnectorContainer.innerHTML = `
                <div class="github-connected-state">
                    <p><i class="fab fa-github"></i> Connected as <strong>${state.session.github_username}</strong></p>
                    <button id="github-disconnect-btn" class="btn-text-danger">Disconnect</button>
                </div>
            `;
            publishBtn.disabled = false;
            document.getElementById('github-disconnect-btn').addEventListener('click', disconnectGitHub);
        } else {
            githubConnectorContainer.innerHTML = `
                <button class="github-connect-btn" id="github-connect-btn"><i class="fab fa-github"></i> Connect GitHub</button>
            `;
            publishBtn.disabled = true;
            document.getElementById('github-connect-btn').addEventListener('click', () => {
                handleGitHubAuthPopup(state.session.session_id);
            });
        }
    };

    const disconnectGitHub = async () => {
        addLog("Disconnecting GitHub...", "info");
        try {
            const response = await fetch('/api/v1/mvp/disconnect-github', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: state.session.session_id }),
            });
            const result = await response.json();
            if (!response.ok || !result.success) {
                throw new Error(result.message || 'Failed to disconnect.');
            }
            state.session.github_connected = false;
            state.session.github_username = null;
            state.session.github_token = null;
            addLog("GitHub disconnected.", "info");
            updateGitHubConnector();
        } catch (error) {
            addLog(`Error disconnecting GitHub: ${error.message}`, "error");
        }
    };


    // --- API Calls ---

    const createNewSession = async (productIdea) => {
        addLog(`Creating new session for: "${productIdea}"`, "info");
        try {
            const response = await fetch('/api/v1/mvp/create-session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ product_idea: productIdea }),
            });
            const data = await response.json();
            if (!data.success) throw new Error(data.detail || 'Failed to create session');
            
            state.session = data.session;
            addLog(`Session ${state.session.session_id} created.`, "success");
            updateUI();
        } catch (error) {
            addLog(`Error creating session: ${error.message}`, "error");
        }
    };

    const sendMessage = async () => {
        const message = cliInput.value.trim();
        if (!message || state.isSending) return;

        if (!state.session) {
            await createNewSession(message);
        }

        addCliMessage(message, 'user');
        cliInput.value = ''; // Clear input after sending
        state.isSending = true;
        sendBtn.disabled = true;
        agentStatus.innerHTML = '<i class="fas fa-circle text-warning"></i> Thinking...';

        try {
            const response = await fetch('/api/v1/mvp/send-message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: state.session.session_id,
                    message: message,
                    mode: state.mode,
                }),
            });
            const data = await response.json();
            if (!data.success) throw new Error(data.detail || 'Agent failed to respond');

            addCliMessage(data.result.response, 'assistant');
            state.session = data.session; // Update session state from response
            updateUI();

        } catch (error) {
            addLog(`Error sending message: ${error.message}`, "error");
            addCliMessage(`Sorry, I encountered an error: ${error.message}`, 'assistant error');
        } finally {
            state.isSending = false;
            sendBtn.disabled = false;
            agentStatus.innerHTML = '<i class="fas fa-circle text-success"></i> Ready';
        }
    };

    // --- Event Listeners ---

    sendBtn.addEventListener('click', sendMessage);
    cliInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    modeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            modeButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.mode = btn.dataset.mode;
            addLog(`Switched to ${state.mode.toUpperCase()} mode.`, "system");
        });
    });

    newProjectBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to start a new project? This will clear the current session.')) {
            state.session = null;
            cliOutput.innerHTML = `
                <div class="cli-welcome">
                    <div class="welcome-text">🚀 Welcome to MVP Builder</div>
                    <div class="welcome-sub">Your AI army will guide you through 5 phases</div>
                    <div class="welcome-instructions mt-3">
                        <div>💡 <strong>Plan Mode:</strong> Discuss your idea</div>
                        <div>⚡ <strong>Act Mode:</strong> Watch agents build</div>
                    </div>
                </div>`;
            terminalContent.innerHTML = '<div class="log-entry system">[System] Ready to build...</div>';
            updateUI();
        }
    });

    ideaChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const idea = chip.dataset.idea;
            cliInput.value = idea;
            sendMessage();
        });
    });

    // Initial load
    addLog("MVP Builder UI Initialized.", "system");
    updateGitHubConnector(); // Initial render of the button
});
