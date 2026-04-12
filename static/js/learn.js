/**
 * learn.js — Courses, Slides, Progress, AI Tutor
 * Used by: /learn
 */

class LearnApp {
    constructor() {
        this.courses = [];
        this.currentCourse = null;
        this.currentLang = localStorage.getItem('lang') || 'en';
        this.currentSectionIndex = 0;
        this.completedSections = [];
        this.categoryFilter = null;
        this.aiPanelOpen = false;
    }

    async init() {
        await this.loadCourses();
        document.addEventListener('languageChanged', (e) => {
            this.currentLang = e.detail.lang;
            this.loadCourses();
        });
    }

    async loadCourses() {
        try {
            const data = await apiFetch(`/courses?lang=${this.currentLang}`);
            this.courses = data.courses || [];
            this.renderCategoryFilters();
            this.renderCourseGrid();
        } catch (e) {
            document.getElementById('learning-paths-grid').innerHTML =
                '<p class="text-danger">Failed to load courses. Please try again.</p>';
        }
    }

    renderCategoryFilters() {
        const bar = document.getElementById('category-filter-bar');
        if (!bar) return;
        const categories = [...new Set(this.courses.map(c => c.category).filter(Boolean))];
        bar.innerHTML = `<button class="btn btn-sm ${!this.categoryFilter ? 'btn-info' : 'btn-outline-info'}" onclick="window.learnApp.filterCourses(null, this)">All</button>` +
            categories.map(cat => `<button class="btn btn-sm ${this.categoryFilter === cat ? 'btn-info' : 'btn-outline-secondary'}" onclick="window.learnApp.filterCourses('${cat}', this)">${cat}</button>`).join('');
    }

    filterCourses(category, btn) {
        this.categoryFilter = category;
        document.querySelectorAll('#category-filter-bar button').forEach(b => {
            b.className = b === btn ? 'btn btn-sm btn-info' : 'btn btn-sm btn-outline-secondary';
        });
        this.renderCourseGrid();
    }

    renderCourseGrid() {
        const grid = document.getElementById('learning-paths-grid');
        if (!grid) return;
        let filtered = this.courses;
        if (this.categoryFilter) filtered = filtered.filter(c => c.category === this.categoryFilter);
        if (filtered.length === 0) {
            grid.innerHTML = '<p class="text-muted">No courses found.</p>';
            return;
        }
        grid.innerHTML = filtered.map(course => `
            <div class="learning-path-card" onclick="window.learnApp.openCourse('${course.id}', '${course.lang}')">
                <div class="path-icon"><i class="${course.icon || 'fas fa-book'}"></i></div>
                <div class="path-title">${course.title}</div>
                <div class="path-description">${course.description || ''}</div>
                <div class="path-footer">
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="badge bg-secondary">${course.category || 'General'}</span>
                        <span class="text-muted small">${course.section_count || 0} modules</span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    async openCourse(courseId, lang) {
        try {
            const data = await apiFetch(`/courses/${courseId}?lang=${lang || this.currentLang}`);
            this.currentCourse = data;
            this.currentSectionIndex = 0;
            this.completedSections = [];

            // Load progress if logged in
            if (window.currentUser) {
                try {
                    const prog = await apiFetch('/progress/me');
                    const p = (prog.progress || []).find(p => p.course_id === courseId && p.lang === lang);
                    if (p) {
                        this.currentSectionIndex = p.section_index || 0;
                        this.completedSections = p.completed_sections || [];
                    }
                } catch (e) {}
            }

            this.showCourseDetail();
            this.renderModuleList();
            this.loadSection(this.currentSectionIndex);
        } catch (e) {
            showToast('Failed to load course', 'error');
        }
    }

    showCourseDetail() {
        document.getElementById('view-course-list').style.display = 'none';
        document.getElementById('view-course-detail').style.display = 'block';
        document.getElementById('course-sidebar-title').textContent = this.currentCourse.title;
        document.getElementById('course-breadcrumb').textContent = this.currentCourse.title;
        document.getElementById('course-lang-badge').textContent = (this.currentCourse.lang || 'EN').toUpperCase();
        document.getElementById('course-total-count').textContent = (this.currentCourse.sections || []).length;
        // Show terminal for Python courses
        const isPython = (this.currentCourse.id || '').includes('python');
        document.getElementById('course-terminal-section').style.display = isPython ? 'block' : 'none';
        this.updateProgress();
    }

    showCourseList() {
        document.getElementById('view-course-list').style.display = 'block';
        document.getElementById('view-course-detail').style.display = 'none';
        this.currentCourse = null;
    }

    renderModuleList() {
        const nav = document.getElementById('course-module-list');
        if (!nav || !this.currentCourse) return;
        const sections = this.currentCourse.sections || [];
        nav.innerHTML = sections.map((s, i) => {
            const done = this.completedSections.includes(i);
            const active = i === this.currentSectionIndex;
            return `<div class="course-module-item ${active ? 'active' : ''} ${done ? 'completed' : ''}"
                onclick="window.learnApp.loadSection(${i})">
                <span class="module-icon"><i class="fas ${done ? 'fa-check-circle' : active ? 'fa-play-circle' : 'fa-circle'}"></i></span>
                <span>${s.title}</span>
            </div>`;
        }).join('');
    }

    async loadSection(index) {
        if (!this.currentCourse) return;
        const sections = this.currentCourse.sections || [];
        if (index < 0 || index >= sections.length) return;
        this.currentSectionIndex = index;

        const contentEl = document.getElementById('course-slide-content');
        contentEl.innerHTML = '<div class="text-center py-4"><div class="spinner"></div></div>';

        try {
            const data = await apiFetch(`/courses/${this.currentCourse.id}/slides/${this.currentCourse.lang}/${index}`);
            const html = typeof marked !== 'undefined' ? marked.parse(data.content || '') : data.content;
            contentEl.innerHTML = html;
            if (typeof hljs !== 'undefined') {
                contentEl.querySelectorAll('pre code').forEach(b => hljs.highlightElement(b));
            }
            document.getElementById('course-section-title').textContent = data.title;
            document.getElementById('course-section-badge').textContent = `${index + 1} / ${sections.length}`;
            document.getElementById('prev-section-btn').disabled = index === 0;
            document.getElementById('next-section-btn').disabled = index === sections.length - 1;
            this.renderModuleList();
            contentEl.scrollTop = 0;
        } catch (e) {
            contentEl.innerHTML = '<p class="text-danger">Failed to load section.</p>';
        }
    }

    navigateSection(delta) {
        this.loadSection(this.currentSectionIndex + delta);
    }

    markSectionComplete() {
        if (!this.completedSections.includes(this.currentSectionIndex)) {
            this.completedSections.push(this.currentSectionIndex);
        }
        this.updateProgress();
        this.renderModuleList();
        showToast('Section marked complete!', 'success');
        // Save progress
        if (window.currentUser) {
            apiFetch('/progress', {
                method: 'POST',
                body: JSON.stringify({
                    course_id: this.currentCourse.id,
                    lang: this.currentCourse.lang,
                    section_index: this.currentSectionIndex,
                    completed_sections: this.completedSections
                })
            }).catch(() => {});
        }
        // Auto-advance
        const sections = this.currentCourse.sections || [];
        if (this.currentSectionIndex < sections.length - 1) {
            setTimeout(() => this.navigateSection(1), 600);
        }
    }

    updateProgress() {
        const total = (this.currentCourse?.sections || []).length;
        const done = this.completedSections.length;
        const pct = total > 0 ? Math.round((done / total) * 100) : 0;
        document.getElementById('course-progress-pct').textContent = pct + '%';
        document.getElementById('course-progress-fill').style.width = pct + '%';
        document.getElementById('course-completed-count').textContent = done;
    }

    toggleTerminal() {
        const body = document.getElementById('course-terminal-body');
        const chevron = document.getElementById('terminal-chevron');
        if (body) {
            const hidden = body.style.display === 'none';
            body.style.display = hidden ? 'block' : 'none';
            if (chevron) chevron.className = `fas fa-chevron-${hidden ? 'up' : 'down'}`;
        }
    }

    async runCode() {
        const code = document.getElementById('course-code-input')?.value;
        const output = document.getElementById('course-terminal-output');
        if (!code || !output) return;
        output.textContent = 'Running...';
        try {
            const data = await apiFetch('/execute-code', {
                method: 'POST',
                body: JSON.stringify({ code, language: 'python' })
            });
            output.textContent = data.output || data.error || '(no output)';
        } catch (e) {
            output.textContent = 'Error: ' + e.message;
        }
    }

    clearTerminal() {
        const output = document.getElementById('course-terminal-output');
        if (output) output.textContent = 'Ready.';
    }

    toggleAIPanel() {
        this.aiPanelOpen = !this.aiPanelOpen;
        const panel = document.getElementById('course-ai-panel');
        if (panel) panel.style.display = this.aiPanelOpen ? 'flex' : 'none';
    }

    async sendAIMessage() {
        const input = document.getElementById('course-ai-input');
        const msg = input?.value?.trim();
        if (!msg) return;
        input.value = '';

        const messages = document.getElementById('course-ai-messages');
        messages.innerHTML += `<div class="message user"><div class="message-content">${msg}</div></div>`;
        messages.innerHTML += `<div id="ai-typing" class="message agent"><div class="typing-indicator"><span></span><span></span><span></span></div></div>`;
        messages.scrollTop = messages.scrollHeight;

        try {
            const data = await apiFetch('/chat/course', {
                method: 'POST',
                body: JSON.stringify({
                    message: msg,
                    course_id: this.currentCourse?.id,
                    lang: this.currentCourse?.lang || 'en',
                    section_index: this.currentSectionIndex
                })
            });
            document.getElementById('ai-typing')?.remove();
            const resp = data.agent_response?.content || 'No response';
            const html = typeof marked !== 'undefined' ? marked.parse(resp) : resp;
            messages.innerHTML += `<div class="message agent"><div class="message-content markdown-body">${html}</div></div>`;
            messages.scrollTop = messages.scrollHeight;
        } catch (e) {
            document.getElementById('ai-typing')?.remove();
            messages.innerHTML += `<div class="message agent"><div class="message-content text-danger">Error: ${e.message}</div></div>`;
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.learnApp = new LearnApp();
    setTimeout(() => window.learnApp.init(), 100);
});
