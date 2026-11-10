// Jules Agent Dashboard Client
const API_BASE = window.location.origin;

let activeTaskId = null;
let currentTasks = [];

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

async function loadTasks() {
    try {
        const res = await fetch(`${API_BASE}/api/tasks`);
        if (!res.ok) return;
        const data = await res.json();
        currentTasks = data.tasks || [];

        // If no activeTaskId set yet, pick server active_task_id or first task
        if (!activeTaskId && data.active_task_id) {
            activeTaskId = data.active_task_id;
        } else if (!activeTaskId && currentTasks.length > 0) {
            activeTaskId = currentTasks[0].id;
        }

        renderTaskList(currentTasks);
        if (activeTaskId) {
            await loadTaskDetails(activeTaskId);
        }
    } catch (e) {
        console.error("Failed to load tasks:", e);
    }
}

function renderTaskList(tasks) {
    const container = document.getElementById('task-list');
    if (!tasks || tasks.length === 0) {
        container.innerHTML = '<div class="empty-state">No previous tasks. Click "+ New Task" to begin.</div>';
        return;
    }

    container.innerHTML = '';
    tasks.forEach(task => {
        const card = document.createElement('div');
        const isActive = task.id === activeTaskId;
        card.className = `task-card ${isActive ? 'active' : ''}`;
        card.onclick = (e) => {
            if (e.target.classList.contains('task-delete-btn')) return;
            selectTask(task.id);
        };

        const date = new Date(task.created_at);
        const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        card.innerHTML = `
            <div class="task-card-header">
                <span class="task-card-title" title="${escapeHtml(task.title)}">${escapeHtml(task.title)}</span>
                <span class="task-status-chip ${task.status}">${formatStatus(task.status)}</span>
            </div>
            <div class="task-card-footer">
                <span>${timeStr}</span>
                <button class="task-delete-btn" title="Delete Task" onclick="deleteTask(event, '${task.id}')">✕</button>
            </div>
        `;
        container.appendChild(card);
    });
}

function formatStatus(status) {
    if (status === 'waiting_for_user') return 'Needs Input';
    if (status === 'completed') return 'Completed';
    return 'In Progress';
}

function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function selectTask(taskId) {
    if (activeTaskId === taskId) return;
    activeTaskId = taskId;
    try {
        await fetch(`${API_BASE}/api/tasks/${taskId}/activate`, { method: 'POST' });
    } catch (e) {
        console.error("Failed to activate task:", e);
    }
    await loadTasks();
}

async function loadTaskDetails(taskId) {
    try {
        const res = await fetch(`${API_BASE}/api/tasks/${taskId}`);
        if (!res.ok) return;
        const data = await res.json();
        const task = data.task;
        const messages = data.messages || [];

        // Update header & title
        document.getElementById('active-task-badge').textContent = `Task: ${task.title}`;
        document.getElementById('current-task-title').textContent = task.title;

        // Render plan
        renderPlan(task.plan_state);

        // Render feed
        renderMessages(messages);
    } catch (e) {
        console.error("Failed to load task details:", e);
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
                <span>${step.id}. ${escapeHtml(step.title)}</span>
            </div>
            ${step.details ? `<div class="plan-item-desc">${escapeHtml(step.details)}</div>` : ''}
            ${step.completion_message ? `<div class="plan-item-desc" style="color: var(--accent-green);">${escapeHtml(step.completion_message)}</div>` : ''}
        `;
        container.appendChild(item);
    });
}

function renderMessages(messages) {
    const feed = document.getElementById('feed-container');
    feed.innerHTML = '';

    if (!messages || messages.length === 0) {
        appendFeedItem('agent', 'agent-badge', 'Jules', 'Task initialized. Awaiting commands or input.');
        return;
    }

    messages.forEach(msg => {
        if (msg.role === 'user') {
            appendFeedItem('user', 'agent-badge', 'You', msg.content || '');
        } else if (msg.role === 'tool') {
            appendFeedItem('agent', 'tool-badge', `Tool: ${msg.name || 'Output'}`, msg.content || '');
        } else {
            appendFeedItem('agent', 'agent-badge', 'Jules', msg.content || '');
        }
    });
}

function appendFeedItem(role, badgeClass, title, text) {
    const feed = document.getElementById('feed-container');
    const item = document.createElement('div');
    item.className = `feed-item ${role === 'user' ? 'user-message' : 'agent-message'}`;

    item.innerHTML = `
        <div class="feed-header">
            <span class="badge ${badgeClass}">${escapeHtml(title)}</span>
            <span class="feed-time">${new Date().toLocaleTimeString()}</span>
        </div>
        <div class="feed-content">${escapeHtml(text)}</div>
    `;

    feed.appendChild(item);
    feed.scrollTop = feed.scrollHeight;
}

async function startNewTask() {
    const prompt = window.prompt("Enter a task prompt for Jules:");
    if (!prompt || !prompt.trim()) return;

    try {
        const res = await fetch(`${API_BASE}/api/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: prompt.trim() })
        });
        if (res.ok) {
            const data = await res.json();
            activeTaskId = data.task.id;
            await loadTasks();
        }
    } catch (e) {
        console.error("Failed to create new task:", e);
    }
}

async function deleteTask(event, taskId) {
    event.stopPropagation();
    if (!confirm("Are you sure you want to delete this task?")) return;

    try {
        const res = await fetch(`${API_BASE}/api/tasks/${taskId}`, { method: 'DELETE' });
        if (res.ok) {
            const data = await res.json();
            activeTaskId = data.active_task_id;
            await loadTasks();
        }
    } catch (e) {
        console.error("Failed to delete task:", e);
    }
}

async function submitPrompt() {
    const input = document.getElementById('prompt-input');
    const val = input.value.trim();
    if (!val) return;

    input.value = '';

    // If no active task, create one
    if (!activeTaskId) {
        try {
            const res = await fetch(`${API_BASE}/api/tasks`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: val })
            });
            const data = await res.json();
            activeTaskId = data.task.id;
            await loadTasks();
            return;
        } catch (e) {
            appendFeedItem('agent', 'agent-badge', 'Error', `Failed: ${e.message}`);
            return;
        }
    }

    // Submit reply or follow-up
    appendFeedItem('user', 'agent-badge', 'You', val);

    try {
        // Try user reply first if task is waiting
        const activeTask = currentTasks.find(t => t.id === activeTaskId);
        if (activeTask && activeTask.waiting_for_user) {
            await fetch(`${API_BASE}/api/tasks/${activeTaskId}/user/reply`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ response: val })
            });
        } else {
            // Otherwise init/continue task
            await fetch(`${API_BASE}/api/tasks`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: val })
            });
        }
        await loadTasks();
    } catch (e) {
        appendFeedItem('agent', 'agent-badge', 'Error', `Failed: ${e.message}`);
    }
}

async function triggerListFiles() {
    if (!activeTaskId) {
        appendFeedItem('agent', 'tool-badge', 'Notice', 'Please create or select a task first.');
        return;
    }
    appendFeedItem('agent', 'tool-badge', 'Tool: list_files', 'Executing list_files on workspace root...');
    try {
        const res = await fetch(`${API_BASE}/api/tasks/${activeTaskId}/tool/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: 'list_files', arguments: { path: '' } })
        });
        const data = await res.json();
        const files = data.result.result || [];
        document.getElementById('inspector-code').textContent = JSON.stringify(files, null, 2);
        document.getElementById('inspector-file-badge').textContent = 'list_files';
        appendFeedItem('agent', 'agent-badge', 'Jules', `Found ${files.length} items in workspace.`);
        await loadTasks();
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

function toggleTaskSidebar() {
    const layout = document.querySelector('.main-layout');
    layout.classList.toggle('sidebar-collapsed');
}

function clearFeed() {
    document.getElementById('feed-container').innerHTML = '';
}

// Polling and init
checkHealth();
loadTasks();
setInterval(loadTasks, 4000);
