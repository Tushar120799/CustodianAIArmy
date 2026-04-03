// app.test.js
// Jest-style test cases for burger menu, floating agent status button, and UI guardrails


const { setupAgentStatusModal, setupBurgerMenu, setupNavigation } = require('./app.js');

describe('Custodian AI Army UI', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <button id="agent-status-btn" class="agent-status-btn"><i class="fas fa-user-astronaut"></i></button>
      <div id="agent-status-modal" class="agent-status-modal">
        <div class="agent-status-modal-content">
          <span class="close-modal" id="close-agent-status-modal">&times;</span>
          <h3>Agent Status</h3>
          <div id="agent-status-list"></div>
        </div>
      </div>
      <button class="burger-btn" id="burger-btn"><i class="fas fa-bars"></i></button>
      <aside class="sidebar"><nav class="nav-menu" id="nav-menu">
        <div class="nav-item" data-section="dashboard">Dashboard</div>
        <div class="nav-item" data-section="agents">Agent Army</div>
        <div class="nav-item" data-section="chat">AI Chat</div>
      </nav></aside>
      <section id="dashboard" class="content-section"></section>
      <section id="agents" class="content-section"></section>
      <section id="chat" class="content-section"></section>
    `;
    setupAgentStatusModal();
    setupBurgerMenu();
    setupNavigation();
  });

  test('Agent Status button opens and closes modal', () => {
    const btn = document.getElementById('agent-status-btn');
    const modal = document.getElementById('agent-status-modal');
    const close = document.getElementById('close-agent-status-modal');
    btn.click();
    expect(modal.style.display).toBe('flex');
    close.click();
    expect(modal.style.display).toBe('none');
  });

  test('Burger menu toggles sidebar', () => {
    const burger = document.getElementById('burger-btn');
    const sidebar = document.querySelector('.sidebar');
    burger.click();
    expect(sidebar.classList.contains('open')).toBe(true);
    burger.click();
    expect(sidebar.classList.contains('open')).toBe(false);
  });

  test('Navigation hides and shows correct section', () => {
    const navMenu = document.getElementById('nav-menu');
    const dashboard = document.getElementById('dashboard');
    const agents = document.getElementById('agents');
    dashboard.style.display = '';
    agents.style.display = 'none';
    navMenu.querySelector('[data-section="agents"]').click();
    expect(dashboard.style.display).toBe('none');
    expect(agents.style.display).toBe('');
  });

  // Add more tests for agent selection, mobile dropdown, etc. as needed
});
