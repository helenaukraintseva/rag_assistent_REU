let chatHistory = JSON.parse(localStorage.getItem('nexus_chat_history') || '[]');
let currentDocuments = [];
let totalQueries = 0;
let llmGenerations = 0;

// DOM элементы
const DOM = {
    thresholdSlider: document.getElementById('similarityThreshold'),
    thresholdSpan: document.getElementById('thresholdValue'),
    questionForm: document.getElementById('questionForm'),
    questionInput: document.getElementById('questionInput'),
    answerSection: document.getElementById('answerSection'),
    answerText: document.getElementById('answerText'),
    responseTimeSpan: document.getElementById('responseTime'),
    llmIndicator: document.getElementById('llmIndicator'),
    sourcesList: document.getElementById('sourcesList'),
    sourcesSection: document.getElementById('sourcesSection'),
    documentsList: document.getElementById('documentsList'),
    documentsCountBadge: document.getElementById('documentsCountBadge'),
    historySection: document.getElementById('historySection'),
    chatHistoryDiv: document.getElementById('chatHistory'),
    loadingOverlay: document.getElementById('loadingOverlay'),
    statVectors: document.getElementById('statVectors'),
    statDocs: document.getElementById('statDocs'),
    statSearches: document.getElementById('statSearches'),
    healthStatus: document.getElementById('healthStatus'),
    totalQueriesEl: document.getElementById('totalQueries'),
    avgResponseTimeEl: document.getElementById('avgResponseTime'),
    llmUsageEl: document.getElementById('llmUsage')
};

let responseTimes = [];

// Навигация по меню
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const section = item.dataset.section;

        document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');

        document.querySelectorAll('.content-section').forEach(sec => sec.classList.remove('active'));
        document.getElementById(`${section}Section`).classList.add('active');

        const titles = { chat: 'Нейро-диалог', documents: 'Корпус знаний', analytics: 'Аналитика', settings: 'Настройки' };
        document.getElementById('pageTitle').innerHTML = `<i class="fas ${item.querySelector('i').className}"></i> ${titles[section]}`;
    });
});

function updateThresholdUI() {
    let val = parseFloat(DOM.thresholdSlider.value);
    DOM.thresholdSpan.innerText = val.toFixed(2);
}
DOM.thresholdSlider.addEventListener('input', updateThresholdUI);
updateThresholdUI();

function setExample(q) {
    DOM.questionInput.value = q;
    DOM.questionInput.focus();
}
window.setExample = setExample;

async function handleSubmit(e) {
    e.preventDefault();
    const question = DOM.questionInput.value.trim();
    if (!question) {
        showFloatingAlert("⛔ введите запрос", "warning");
        return;
    }

    const k = parseInt(document.getElementById('documentsCount').value);
    const threshold = parseFloat(DOM.thresholdSlider.value);
    const use_llm = document.getElementById('useLLM').checked;

    showLoading(true);
    const startTime = performance.now();

    try {
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, k, threshold, use_llm })
        });
        const result = await response.json();

        const endTime = performance.now();
        const elapsed = (endTime - startTime) / 1000;
        responseTimes.push(elapsed);
        if (responseTimes.length > 10) responseTimes.shift();

        totalQueries++;
        if (use_llm) llmGenerations++;

        updateAnalytics();

        showLoading(false);

        if (result.success) {
            currentDocuments = result.documents || [];
            displayAnswer(result, elapsed);
            addToHistory(question, result);
            displayDocuments(currentDocuments);
            loadSystemStats();
        } else {
            showFloatingAlert(`❌ Ошибка: ${result.error}`, "danger");
        }
    } catch (err) {
        showLoading(false);
        showFloatingAlert(`🌐 Ошибка: ${err.message}`, "danger");
    }
}

function displayAnswer(result, elapsedTime) {
    DOM.answerSection.style.display = 'block';
    DOM.responseTimeSpan.innerHTML = `<i class="far fa-clock"></i> ${elapsedTime.toFixed(2)}с`;

    if (result.used_llm) {
        DOM.llmIndicator.innerHTML = `<span class="badge-llm"><i class="fas fa-microchip"></i> LLM ACTIVE</span>`;
    } else {
        DOM.llmIndicator.innerHTML = `<span class="badge-retrieval">RETRIEVAL ONLY</span>`;
    }

    let answerHtml = result.answer;
    try { answerHtml = marked.parse(result.answer); } catch(e) {}
    DOM.answerText.innerHTML = answerHtml;

    if (result.sources && result.sources.length) {
        DOM.sourcesList.innerHTML = result.sources.map(src => `<span class="source-badge-tech">📁 ${escapeHtml(src)}</span>`).join('');
        DOM.sourcesSection.style.display = 'block';
    } else {
        DOM.sourcesSection.style.display = 'none';
    }
}

function displayDocuments(docs) {
    DOM.documentsCountBadge.innerText = docs.length;
    if (!docs.length) {
        DOM.documentsList.innerHTML = `<div class="empty-state"><i class="fas fa-dizzy"></i><p>нет результатов</p></div>`;
        return;
    }

    docs.sort((a,b) => b.score - a.score);
    let html = '';
    docs.slice(0, 5).forEach((doc, idx) => {
        const scorePercent = Math.round(doc.score * 100);
        const preview = doc.preview || doc.text?.substring(0, 100) + '…';
        html += `
            <div class="document-card-tech" onclick="showDocumentModal(${idx})">
                <div class="d-flex justify-content-between">
                    <span class="score-badge">🎯 ${scorePercent}%</span>
                    <span class="small">#${idx+1}</span>
                </div>
                <div class="mt-2 small">${escapeHtml(preview)}</div>
            </div>
        `;
    });
    DOM.documentsList.innerHTML = html;
}

window.showDocumentModal = function(index) {
    const doc = currentDocuments[index];
    if (!doc) return;
    const modalBody = document.getElementById('modalDocumentContent');
    modalBody.innerHTML = `
        <div class="mb-3"><span class="badge bg-info">релевантность ${Math.round(doc.score*100)}%</span></div>
        <div class="doc-full-text">${escapeHtml(doc.text)}</div>
        <hr><details><summary>метаданные</summary><pre>${JSON.stringify(doc.metadata || {}, null, 2)}</pre></details>
    `;
    new bootstrap.Modal(document.getElementById('documentsModal')).show();
};

function addToHistory(question, result) {
    chatHistory.unshift({
        id: Date.now(),
        timestamp: new Date().toISOString(),
        question,
        answer: result.answer,
        documentsCount: result.documents_count || 0,
        time: result.total_time || 0
    });
    if (chatHistory.length > 10) chatHistory = chatHistory.slice(0, 10);
    localStorage.setItem('nexus_chat_history', JSON.stringify(chatHistory));
    updateChatHistoryUI();
}

function updateChatHistoryUI() {
    if (!chatHistory.length) {
        DOM.historySection.style.display = 'none';
        return;
    }
    DOM.historySection.style.display = 'block';
    let html = '';
    chatHistory.slice(0, 5).forEach(h => {
        const time = new Date(h.timestamp).toLocaleTimeString();
        html += `
            <div class="history-item">
                <div class="history-time">${time}</div>
                <div class="history-question">${escapeHtml(h.question.substring(0, 80))}</div>
            </div>
        `;
    });
    DOM.chatHistoryDiv.innerHTML = html;
}

async function loadSystemStats() {
    try {
        const resp = await fetch('/stats');
        const data = await resp.json();
        DOM.statVectors.innerText = data.total_vectors || 0;
        DOM.statDocs.innerText = data.metadata_count || 0;
        DOM.statSearches.innerText = data.search_count || 0;
    } catch(e) {}
}

async function checkHealth() {
    try {
        const res = await fetch('/health');
        const json = await res.json();
        if (json.status === 'ok') {
            DOM.healthStatus.innerText = 'онлайн';
            DOM.healthStatus.className = 'text-success';
        } else {
            DOM.healthStatus.innerText = 'ошибка';
            DOM.healthStatus.className = 'text-danger';
        }
    } catch(e) {
        DOM.healthStatus.innerText = 'offline';
        DOM.healthStatus.className = 'text-danger';
    }
}

function updateAnalytics() {
    if (DOM.totalQueriesEl) DOM.totalQueriesEl.innerText = totalQueries;
    const avgTime = responseTimes.length ? (responseTimes.reduce((a,b) => a+b,0) / responseTimes.length).toFixed(2) : 0;
    if (DOM.avgResponseTimeEl) DOM.avgResponseTimeEl.innerText = avgTime;
    const llmPct = totalQueries ? Math.round((llmGenerations / totalQueries) * 100) : 0;
    if (DOM.llmUsageEl) DOM.llmUsageEl.innerText = `${llmPct}%`;
}

function showFloatingAlert(msg, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `floating-alert ${type}`;
    alertDiv.innerHTML = `<i class="fas fa-bell"></i> ${msg}`;
    document.body.appendChild(alertDiv);
    setTimeout(() => alertDiv.remove(), 3000);
}

function showLoading(show) {
    DOM.loadingOverlay.style.display = show ? 'flex' : 'none';
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[m]));
}

function clearHistory() {
    chatHistory = [];
    localStorage.removeItem('nexus_chat_history');
    updateChatHistoryUI();
    showFloatingAlert("История очищена", "info");
}
window.clearHistory = clearHistory;

DOM.questionForm.addEventListener('submit', handleSubmit);
loadSystemStats();
checkHealth();
updateChatHistoryUI();
updateAnalytics();
setInterval(checkHealth, 30000);
setInterval(loadSystemStats, 45000);