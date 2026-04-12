/**
 * shared.js — Auth, Theme, Nav, API Helpers
 * Loaded by every app page (dashboard, learn, portfolio, build)
 */

// ── API Base ──────────────────────────────────────────────────
const API_BASE = '/api/v1';

async function apiFetch(path, options = {}) {
    const res = await fetch(API_BASE + path, {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
        ...options
    });
    if (!res.ok) throw new Error(`API ${path} failed: ${res.status}`);
    return res.json();
}

// ── Theme ─────────────────────────────────────────────────────
function initTheme() {
    const saved = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
    const toggle = document.getElementById('darkModeToggle');
    if (toggle) {
        toggle.checked = saved === 'dark';
        toggle.addEventListener('change', () => {
            const theme = toggle.checked ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
        });
    }
}

// ── Auth ──────────────────────────────────────────────────────
let currentUser = null;

async function loadCurrentUser() {
    try {
        const data = await apiFetch('/user/plan');
        // Try to get user profile from cookies via plan endpoint
        const sessionRes = await fetch('/api/v1/user/plan', { credentials: 'include' });
        const planData = await sessionRes.json();

        // Try to get actual user info
        const profileRes = await fetch('/api/v1/auth/me', { credentials: 'include' });
        if (profileRes.ok) {
            currentUser = await profileRes.json();
        }
        return { user: currentUser, plan: planData };
    } catch (e) {
        return { user: null, plan: null };
    }
}

function updateUserProfileUI(user) {
    const nameEl = document.getElementById('user-display-name');
    const emailEl = document.getElementById('user-display-email');
    const avatarEl = document.getElementById('user-avatar');
    const loginItem = document.getElementById('guest-login-item');
    const logoutItem = document.getElementById('logout-item');

    if (user) {
        if (nameEl) nameEl.textContent = user.name || user.email;
        if (emailEl) emailEl.textContent = user.email;
        if (avatarEl && user.picture) {
            avatarEl.innerHTML = `<img src="${user.picture}" alt="avatar" style="width:32px;height:32px;border-radius:50%;object-fit:cover;">`;
        }
        if (loginItem) loginItem.style.display = 'none';
        if (logoutItem) logoutItem.style.display = '';
    } else {
        if (nameEl) nameEl.textContent = 'Guest';
        if (emailEl) emailEl.textContent = '';
        if (loginItem) loginItem.style.display = '';
        if (logoutItem) logoutItem.style.display = 'none';
    }
}

async function logout() {
    try {
        await fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'include' });
    } catch (e) {}
    window.location.href = '/';
}

// ── Plan / Rate Limit UI ──────────────────────────────────────
function updatePlanUI(planData) {
    if (!planData) return;
    const planBadge = document.getElementById('plan-badge');
    const requestsLeft = document.getElementById('requests-left');
    if (planBadge) planBadge.textContent = (planData.plan || 'free').toUpperCase();
    if (requestsLeft) {
        const used = planData.requests_today || 0;
        const limit = planData.daily_limit || 20;
        requestsLeft.textContent = `${limit - used} / ${limit}`;
    }
}

// ── Active Page Nav Highlight ─────────────────────────────────
function highlightActiveNav() {
    const path = window.location.pathname;
    document.querySelectorAll('.page-nav a, .nav-item').forEach(link => {
        const href = link.getAttribute('href');
        if (href && path.startsWith(href) && href !== '/') {
            link.classList.add('active');
        } else if (href === '/' && path === '/') {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

// ── Mobile Sidebar Toggle ─────────────────────────────────────
function initMobileSidebar() {
    const burger = document.getElementById('hamburger-btn');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    if (burger && sidebar) {
        burger.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            if (overlay) overlay.style.display = sidebar.classList.contains('open') ? 'block' : 'none';
        });
    }
    if (overlay) {
        overlay.addEventListener('click', () => {
            if (sidebar) sidebar.classList.remove('open');
            overlay.style.display = 'none';
        });
    }
}

// ── Language Toggle ───────────────────────────────────────────
let currentLang = localStorage.getItem('lang') || 'en';

function setLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('lang', lang);
    document.querySelectorAll('[data-lang]').forEach(el => {
        el.style.display = el.dataset.lang === lang ? '' : 'none';
    });
    // Update button states
    document.querySelectorAll('[id$="-en-btn"]').forEach(b => b.classList.toggle('active', lang === 'en'));
    document.querySelectorAll('[id$="-de-btn"]').forEach(b => b.classList.toggle('active', lang === 'de'));
    // Dispatch event for page-specific handlers
    document.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang } }));
}
window.setLanguage = setLanguage;

// ── Toast Notifications ───────────────────────────────────────
function showToast(message, type = 'info', duration = 3000) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position:fixed;bottom:1.5rem;left:50%;transform:translateX(-50%);z-index:9999;display:flex;flex-direction:column;gap:0.5rem;align-items:center;';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    const colors = { info: '#007bff', success: '#28a745', warning: '#ffc107', error: '#dc3545' };
    toast.style.cssText = `background:${colors[type]||colors.info};color:white;padding:0.75rem 1.5rem;border-radius:4px;font-size:0.9rem;box-shadow:0 2px 8px rgba(0,0,0,0.2);animation:fadeIn 0.2s ease;`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => { toast.remove(); }, duration);
}
window.showToast = showToast;

// ── Init (called on every page) ───────────────────────────────
async function initShared() {
    initTheme();
    initMobileSidebar();
    highlightActiveNav();
    setLanguage(currentLang);

    const { user, plan } = await loadCurrentUser();
    currentUser = user;
    updateUserProfileUI(user);
    updatePlanUI(plan);

    // Expose globally
    window.currentUser = currentUser;
    window.logout = logout;
    window.apiFetch = apiFetch;
    window.showToast = showToast;
}

document.addEventListener('DOMContentLoaded', initShared);
