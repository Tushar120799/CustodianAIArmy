/**
 * shared.js — Auth, Nav, API Helpers
 * Loaded by every app page (dashboard, learn, portfolio, build)
 * Dark theme is permanent — no theme toggling
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

// ── Auth ──────────────────────────────────────────────────────
let currentUser = null;

async function loadCurrentUser() {
    try {
        const profileRes = await fetch('/api/v1/auth/me', { credentials: 'include' });
        if (profileRes.ok) {
            currentUser = await profileRes.json();
        }
        const planRes = await fetch('/api/v1/user/plan', { credentials: 'include' });
        const planData = planRes.ok ? await planRes.json() : null;
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
            avatarEl.innerHTML = `<img src="${user.picture}" alt="avatar" style="width:32px;height:32px;border-radius:50%;object-fit:cover;border:2px solid var(--primary-color);">`;
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
    document.querySelectorAll('.nav-item').forEach(link => {
        const href = link.getAttribute('href');
        if (!href) return;
        if (href === '/' && path === '/') {
            link.classList.add('active');
        } else if (href !== '/' && path.startsWith(href)) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
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
    document.querySelectorAll('[id$="-en-btn"], [id="lang-en-btn"], [id="learn-lang-en-btn"]').forEach(b => b.classList.toggle('active', lang === 'en'));
    document.querySelectorAll('[id$="-de-btn"], [id="lang-de-btn"], [id="learn-lang-de-btn"]').forEach(b => b.classList.toggle('active', lang === 'de'));
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
    const colors = {
        info: 'rgba(77,171,247,0.9)',
        success: 'rgba(16,185,129,0.9)',
        warning: 'rgba(245,158,11,0.9)',
        error: 'rgba(245,108,108,0.9)'
    };
    toast.style.cssText = `background:${colors[type]||colors.info};color:#000;padding:0.75rem 1.5rem;border-radius:6px;font-size:0.875rem;font-weight:600;box-shadow:0 4px 16px rgba(0,0,0,0.4);animation:fadeIn 0.2s ease;backdrop-filter:blur(8px);`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => { toast.remove(); }, duration);
}
window.showToast = showToast;

// ── Init (called on every page) ───────────────────────────────
async function initShared() {
    // Dark theme is always on — no toggling needed
    document.documentElement.setAttribute('data-theme', 'dark');
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
