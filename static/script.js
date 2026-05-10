// ---------- ХРАНИЛИЩЕ ДАННЫХ ----------
let chats = {};
let currentChatId = "1";
let nextChatId = 2;
let availableSources = [];
let selectedSource = "all"; // "all" или конкретный документ
let isWaitingForResponse = false;

// API endpoints
const API_BASE = '';
const API_ASK = `${API_BASE}/api/ask`;
const API_KEYS = `${API_BASE}/api/available_keys`;
const API_HEALTH = `${API_BASE}/health`;

// Функции времени
function getTime() {
    const now = new Date();
    return `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}`;
}

// Загрузка доступных источников из API
async function loadAvailableSources() {
    try {
        const response = await fetch(API_KEYS);
        const data = await response.json();

        if (data.success) {
            availableSources = data.keys_info || [];
            renderSourcesList();
        } else {
            console.error('Ошибка загрузки источников');
        }
    } catch (error) {
        console.error('Ошибка при загрузке источников:', error);
    }
}

// Отображение списка источников
function renderSourcesList() {
    const sourcesBlock = document.getElementById('sourcesBlock');
    sourcesBlock.innerHTML = `<span class="sources-label">📄 Доступные документы:</span>`;

    // Кнопка "Все документы"
    const allBtn = document.createElement('span');
    allBtn.className = `source-tag ${selectedSource === 'all' ? 'active-source' : ''}`;
    allBtn.textContent = '📚 Все документы';
    allBtn.style.cursor = 'pointer';
    allBtn.style.backgroundColor = selectedSource === 'all' ? '#fef3c7' : 'white';
    allBtn.onclick = () => selectSource('all');
    sourcesBlock.appendChild(allBtn);

    // Кнопки для каждого документа
    availableSources.forEach(source => {
        const tag = document.createElement('span');
        tag.className = `source-tag ${selectedSource === source.name ? 'active-source' : ''}`;
        tag.textContent = source.name.length > 30 ? source.name.substring(0, 27) + '...' : source.name;
        tag.title = source.name;
        tag.style.cursor = 'pointer';
        tag.style.backgroundColor = selectedSource === source.name ? '#fef3c7' : 'white';
        tag.onclick = () => selectSource(source.name);
        sourcesBlock.appendChild(tag);
    });
}

// Выбор источника
function selectSource(sourceName) {
    selectedSource = sourceName;
    renderSourcesList();

    // Добавляем системное сообщение о смене источника
    const sourceText = sourceName === 'all' ? 'все документы' : `документ "${sourceName}"`;
    addMessageToUI(`🔍 Вопросы будут искаться в ${sourceText}`, 'bot', getTime(), null, true);
}

// Отправка вопроса к API
async function sendToAPI(question) {
    if (isWaitingForResponse) return null;

    isWaitingForResponse = true;
    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;

    try {
        const requestBody = {
            question: question,
            use_ai_selection: true  // Всегда true
        };

        const response = await fetch(API_ASK, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (data.success) {
            return {
                text: data.answer,
                source: data.sources && data.sources.length > 0 ? data.sources[0] : null,
                doc_link: data.doc_link || null,
                sources_info: data.doc_link || null  // Добавьте эту строку
            };
        } else {
            return {
                text: "Извините, произошла ошибка...",
                source: null,
                doc_link: null,
                error: data.error
            };
        }
    } catch (error) {
        console.error('Ошибка при запросе:', error);
        return {
            text: "Извините, не удалось连接到 серверу...",
            source: null,
            doc_link: null,
            error: error.message
        };
    } finally {
        isWaitingForResponse = false;
        sendBtn.disabled = false;
    }
}

// Добавление сообщения в UI и сохранение в историю
// Добавление сообщения в UI и сохранение в историю
function addMessageToUI(text, sender, timestamp, sourceDoc, saveToChat = true, docLink = null) {
const messagesContainer = document.getElementById('chatMessages');
const messageDiv = document.createElement('div');
messageDiv.className = `message ${sender}`;

const bubble = document.createElement('div');
bubble.className = 'bubble';
bubble.textContent = text;

const timeSpan = document.createElement('div');
timeSpan.className = 'timestamp';
timeSpan.textContent = timestamp;

messageDiv.appendChild(bubble);
messageDiv.appendChild(timeSpan);

// УЛУЧШЕННАЯ ПЛАШКА С ССЫЛКОЙ
if (sender === 'bot') {
// Проверяем наличие источника
const hasSource = sourceDoc && sourceDoc !== '' && sourceDoc !== null;
const hasLink = docLink && docLink !== '' && docLink !== null;

if (hasSource || hasLink) {
    const citation = document.createElement('div');
    citation.className = 'citation';
    citation.style.cssText = `
        margin-top: 0.5rem;
        margin-left: 0.75rem;
        background: #f0fdf4;
        border-left: 3px solid #22c55e;
        padding: 0.4rem 0.8rem;
        border-radius: 8px;
        font-size: 0.75rem;
        cursor: pointer;
        transition: all 0.2s ease;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        max-width: 90%;
    `;

    // Если есть ссылка - делаем кликабельной
    if (hasLink) {
        const link = document.createElement('a');
        link.href = docLink;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.style.cssText = `
            color: #166534;
            text-decoration: none;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
        `;

        // Иконка документа
        const icon = document.createElement('span');
        icon.textContent = '📄';

        // Название источника (обрезаем если длинное)
        let displayName = sourceDoc || 'Документ';
        if (displayName.length > 40) {
            displayName = displayName.substring(0, 37) + '...';
        }

        const text = document.createTextNode(` ${displayName}`);
        link.appendChild(icon);
        link.appendChild(text);

        // Добавляем эффект при наведении
        link.onmouseenter = () => {
            link.style.textDecoration = 'underline';
        };
        link.onmouseleave = () => {
            link.style.textDecoration = 'none';
        };

        citation.appendChild(link);

        // Добавляем иконку внешней ссылки
        const externalIcon = document.createElement('span');
        externalIcon.textContent = ' ↗';
        externalIcon.style.fontSize = '0.7rem';
        externalIcon.style.opacity = '0.7';
        citation.appendChild(externalIcon);

    } else {
        // Если ссылки нет, но есть название источника - некликабельная плашка
        citation.innerHTML = `📎 Источник: ${sourceDoc}`;
        citation.style.background = '#fef3c7';
        citation.style.borderLeftColor = '#f59e0b';
    }

    messageDiv.appendChild(citation);
}

// Дополнительно: если есть несколько источников (sources_info)
if (arguments[7] && arguments[7].length > 0) {
    const sourcesList = arguments[7];
    const sourcesContainer = document.createElement('div');
    sourcesContainer.style.cssText = `
        margin-top: 0.3rem;
        margin-left: 0.75rem;
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
    `;

    sourcesList.forEach(source => {
        if (source.link && source.link !== '') {
            const sourceTag = document.createElement('a');
            sourceTag.href = source.link;
            sourceTag.target = '_blank';
            sourceTag.style.cssText = `
                background: #e2e8f0;
                padding: 0.2rem 0.6rem;
                border-radius: 12px;
                font-size: 0.7rem;
                color: #1e293b;
                text-decoration: none;
                transition: background 0.2s;
            `;
            sourceTag.textContent = `📄 ${source.name || 'Документ'}`;
            sourceTag.onmouseenter = () => sourceTag.style.background = '#cbd5e1';
            sourceTag.onmouseleave = () => sourceTag.style.background = '#e2e8f0';
            sourcesContainer.appendChild(sourceTag);
        }
    });

    if (sourcesContainer.children.length > 0) {
        messageDiv.appendChild(sourcesContainer);
    }
}
}

messagesContainer.appendChild(messageDiv);
messagesContainer.scrollTop = messagesContainer.scrollHeight;

// Сохраняем в чат
if (saveToChat && chats[currentChatId]) {
chats[currentChatId].messages.push({
    text,
    sender,
    timestamp,
    sourceDoc,
    docLink
});
saveChats();
}
}

// Отправка сообщения пользователя
async function sendUserMessage(text) {
    if (!text.trim() || isWaitingForResponse) return;

    const timestamp = getTime();
    addMessageToUI(text, 'user', timestamp, null, true);

    // Показываем индикатор загрузки
    const loadingMsg = addLoadingIndicator();

    // Отправляем запрос к API
    const answer = await sendToAPI(text);

    // Удаляем индикатор загрузки
    removeLoadingIndicator(loadingMsg);

    // Добавляем ответ бота
    addMessageToUI(answer.text, 'bot', getTime(), answer.source, true, answer.doc_link);
}

// Индикатор загрузки
function addLoadingIndicator() {
    const messagesContainer = document.getElementById('chatMessages');
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message bot';
    loadingDiv.id = 'loadingIndicator';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerHTML = '<span class="loading"></span> Думаю...';

    loadingDiv.appendChild(bubble);
    messagesContainer.appendChild(loadingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    return loadingDiv;
}

function removeLoadingIndicator(loadingMsg) {
    if (loadingMsg && loadingMsg.parentNode) {
        loadingMsg.remove();
    }
    const indicator = document.getElementById('loadingIndicator');
    if (indicator) indicator.remove();
}

// Инициализация чатов
function init() {
    if (!localStorage.getItem('plekhanov_chats_api')) {
        const defaultChat = {
            messages: [
                { text: "Здравствуйте! Я AI-ассистент РЭУ им. Г.В. Плеханова. Я имею доступ к официальным документам университета и могу ответить на ваши вопросы.", sender: "bot", timestamp: getTime(), sourceDoc: null, docLink: null },
                { text: "Выберите документ для поиска или оставьте 'Все документы' - я сам найду нужную информацию.", sender: "bot", timestamp: getTime(), sourceDoc: null, docLink: null }
            ],
            sources: []
        };
        chats = { "1": defaultChat };
        nextChatId = 2;
        saveChats();
    } else {
        loadChats();
    }
    renderHistoryList();
    renderCurrentChat();

    // Загружаем доступные источники
<!--            loadAvailableSources();-->
}

function saveChats() {
    localStorage.setItem('plekhanov_chats_api', JSON.stringify(chats));
    localStorage.setItem('nextChatId_api', nextChatId);
}

function loadChats() {
    chats = JSON.parse(localStorage.getItem('plekhanov_chats_api'));
    nextChatId = parseInt(localStorage.getItem('nextChatId_api')) || 2;
}

// Рендер истории
function renderHistoryList() {
    const container = document.getElementById('historyList');
    container.innerHTML = '';
    Object.keys(chats).forEach(chatId => {
        const li = document.createElement('li');
        li.className = `history-item ${chatId == currentChatId ? 'active' : ''}`;
        const firstMsg = chats[chatId].messages[0];
        const preview = firstMsg ? firstMsg.text.substring(0, 30) + '...' : 'Новый чат';
        li.innerHTML = `<span>${preview}</span>
                       <button class="delete-chat-btn" data-id="${chatId}">🗑️</button>`;
        li.querySelector('span').addEventListener('click', (e) => {
            e.stopPropagation();
            setCurrentChat(chatId);
        });
        const delBtn = li.querySelector('.delete-chat-btn');
        delBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteSingleChat(chatId);
        });
        container.appendChild(li);
    });
}

function setCurrentChat(chatId) {
    if (!chats[chatId]) return;
    currentChatId = chatId;
    renderHistoryList();
    renderCurrentChat();
}

function deleteSingleChat(chatId) {
    if (Object.keys(chats).length === 1) {
        const newId = String(nextChatId++);
        chats[newId] = {
            messages: [{ text: "Новый диалог. Задайте свой вопрос.", sender: "bot", timestamp: getTime(), sourceDoc: null, docLink: null }],
            sources: []
        };
        delete chats[chatId];
        currentChatId = newId;
    } else {
        delete chats[chatId];
        if (currentChatId === chatId) {
            currentChatId = Object.keys(chats)[0];
        }
    }
    saveChats();
    renderHistoryList();
    renderCurrentChat();
}

function clearAllHistory() {
    const newId = String(nextChatId++);
    chats = {
        [newId]: {
            messages: [{ text: "Вся история удалена. Начнём новый диалог.", sender: "bot", timestamp: getTime(), sourceDoc: null, docLink: null }],
            sources: []
        }
    };
    currentChatId = newId;
    saveChats();
    renderHistoryList();
    renderCurrentChat();
}

// Отображение текущего чата
function renderCurrentChat() {
    const chat = chats[currentChatId];
    if (!chat) return;
    const messagesContainer = document.getElementById('chatMessages');
    messagesContainer.innerHTML = '';
    chat.messages.forEach(msg => {
        addMessageToUI(msg.text, msg.sender, msg.timestamp, msg.sourceDoc, false, msg.docLink);
    });
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Настройка быстрых вопросов
function setupQuickQuestions() {
    const btns = document.querySelectorAll('.quick-btn');
    btns.forEach(btn => {
        btn.addEventListener('click', () => {
            const qText = btn.getAttribute('data-q');
            document.getElementById('messageInput').value = qText;
            sendUserMessage(qText);
        });
    });
}

// Обработчики событий
document.getElementById('sendBtn').addEventListener('click', () => {
    const input = document.getElementById('messageInput');
    sendUserMessage(input.value);
    input.value = '';
});

document.getElementById('messageInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        const input = document.getElementById('messageInput');
        sendUserMessage(input.value);
        input.value = '';
    }
});

document.getElementById('clearHistoryBtn').addEventListener('click', clearAllHistory);

// Запуск
init();
setupQuickQuestions();