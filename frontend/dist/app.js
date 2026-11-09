// Jules Agent Dashboard Client
const API_BASE = window.location.origin;

async function checkHealth() {
    try {
        const res = await fetch(`${API_BASE}/api/health`);
        if (res.ok) {
            const data = await res.json();
            document.getElementById('connection-status').textContent = 'Connected';
            document.getElementById('workspace-label').textContent = data.workspace;
        } else {
            document.getElementById('connection-status').textContent = 'Disconnected';
        }
    } catch (e) {
        document.getElementById('connection-status').textContent = 'Offline';
    }
}

async function fetchState() {
    try {
        const res = await fetch(`${API_BASE}/api/state`);
        if (res.ok) {
            const state = await res.json();
            renderPlan(state.plan_state);
        }
    } catch (e) {
        console.error("Failed to fetch state:", e);
    }
}

function renderPlan(planState) {
    const container = document.getElementById('plan-container');
    const counter = document.getElementById('step-counter');

    if (!planState || !planState.steps || planState.steps.length === 0) {
        container.innerHTML = '<div class="empty-state">No active plan initialized.</div>';
        counter.textContent = '0 / 0';
        return;
    }

    const total = planState.steps.length;
    const completed = planState.steps.filter(s => s.completed).length;
    counter.textContent = `${completed} / ${total}`;

    container.innerHTML = '';
    planState.steps.forEach(step => {
        const item = document.createElement('div');
        const isActive = step.id === planState.current_step_id;
        item.className = `plan-item ${isActive ? 'active' : ''} ${step.completed ? 'completed' : ''}`;

        const checkMark = step.completed ? '✅' : (isActive ? '⏳' : '⚪');
        item.innerHTML = `
            <div class="plan-item-title">
                <span>${checkMark}</span>
                <span>${step.id}. ${step.title}</span>
            </div>
            ${step.details ? `<div class="plan-item-desc">${step.details}</div>` : ''}
            ${step.completion_message ? `<div class="plan-item-desc" style="color: var(--accent-green);">${step.completion_message}</div>` : ''}
        `;
        container.appendChild(item);
    });
}

function appendFeedItem(role, badgeClass, title, text) {
    const feed = document.getElementById('feed-container');
    const item = document.createElement('div');
    item.className = `feed-item ${role === 'user' ? 'user-message' : 'agent-message'}`;

    item.innerHTML = `
        <div class="feed-header">
            <span class="badge ${badgeClass}">${title}</span>
            <span class="feed-time">${new Date().toLocaleTimeString()}</span>
        </div>
        <div class="feed-content">${text}</div>
    `;

    feed.appendChild(item);
    feed.scrollTop = feed.scrollHeight;
}

async function submitPrompt() {
    const input = document.getElementById('prompt-input');
    const val = input.value.trim();
    if (!val) return;

    appendFeedItem('user', 'agent-badge', 'You', val);
    input.value = '';

    try {
        const res = await fetch(`${API_BASE}/api/task/init`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: val })
        });
        const data = await res.json();
        appendFeedItem('agent', 'agent-badge', 'Jules', `Task registered: ${val}`);
        fetchState();
    } catch (e) {
        appendFeedItem('agent', 'agent-badge', 'Error', `Failed: ${e.message}`);
    }
}

async function triggerListFiles() {
    appendFeedItem('agent', 'tool-badge', 'Tool: list_files', 'Executing list_files on workspace root...');
    try {
        const res = await fetch(`${API_BASE}/api/tool/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: 'list_files', arguments: { path: '' } })
        });
        const data = await res.json();
        const files = data.result.result || [];
        document.getElementById('inspector-code').textContent = JSON.stringify(files, null, 2);
        document.getElementById('inspector-file-badge').textContent = 'list_files';
        appendFeedItem('agent', 'agent-badge', 'Jules', `Found ${files.length} items in workspace.`);
    } catch (e) {
        appendFeedItem('agent', 'tool-badge', 'Error', e.message);
    }
}

async function triggerStatus() {
    try {
        const res = await fetch(`${API_BASE}/api/state`);
        const state = await res.json();
        document.getElementById('inspector-code').textContent = JSON.stringify(state, null, 2);
        document.getElementById('inspector-file-badge').textContent = 'system_state';
    } catch (e) {
        console.error(e);
    }
}

function clearFeed() {
    document.getElementById('feed-container').innerHTML = '';
}

// Polling and init
checkHealth();
fetchState();
setInterval(fetchState, 3000);
