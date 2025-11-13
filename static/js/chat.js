/**
 * Silkroad RAG Chatbot - Frontend JavaScript
 */

// DOM Elements
const chatContainer = document.getElementById('chatContainer');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const loadingOverlay = document.getElementById('loadingOverlay');

// State
let isWaitingForResponse = false;

/**
 * Initialize the chatbot
 */
function init() {
    // Load chat history if exists
    loadChatHistory();

    // Focus on input
    messageInput.focus();
}

/**
 * Send a message
 */
async function sendMessage(event) {
    event.preventDefault();

    const message = messageInput.value.trim();
    if (!message || isWaitingForResponse) return;

    // Clear input
    messageInput.value = '';

    // Remove welcome message if exists
    const welcomeMsg = document.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }

    // Add user message to chat
    addMessage('user', message);

    // Show typing indicator
    const typingId = addTypingIndicator();

    // Disable send button
    isWaitingForResponse = true;
    sendBtn.disabled = true;

    try {
        // Send request to backend
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message }),
        });

        const data = await response.json();

        // Remove typing indicator
        removeTypingIndicator(typingId);

        if (data.success) {
            // Add bot response
            addMessage('bot', data.answer, data.citations);
        } else {
            // Show error
            addErrorMessage(data.error || 'An error occurred');
        }
    } catch (error) {
        removeTypingIndicator(typingId);
        addErrorMessage('Failed to connect to server. Please try again.');
        console.error('Error:', error);
    } finally {
        // Re-enable send button
        isWaitingForResponse = false;
        sendBtn.disabled = false;
        messageInput.focus();
    }
}

/**
 * Add a message to the chat
 */
function addMessage(role, content, citations = []) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';

    const messageText = document.createElement('p');
    messageText.className = 'message-text';
    messageText.textContent = content;
    messageContent.appendChild(messageText);

    // Add citations if available
    if (citations && citations.length > 0) {
        const citationsDiv = document.createElement('div');
        citationsDiv.className = 'citations';

        const citationsTitle = document.createElement('div');
        citationsTitle.className = 'citations-title';
        citationsTitle.textContent = 'Sources / Nguồn:';
        citationsDiv.appendChild(citationsTitle);

        citations.forEach((citation, index) => {
            const citationLink = document.createElement('a');
            citationLink.className = 'citation';
            citationLink.href = citation.uri;
            citationLink.target = '_blank';
            citationLink.textContent = `${index + 1}. ${citation.title}`;
            citationsDiv.appendChild(citationLink);
        });

        messageContent.appendChild(citationsDiv);
    }

    // Add timestamp
    const timestamp = document.createElement('div');
    timestamp.className = 'message-time';
    timestamp.textContent = new Date().toLocaleTimeString('vi-VN', {
        hour: '2-digit',
        minute: '2-digit'
    });
    messageContent.appendChild(timestamp);

    messageDiv.appendChild(messageContent);
    chatContainer.appendChild(messageDiv);

    // Scroll to bottom
    scrollToBottom();
}

/**
 * Add typing indicator
 */
function addTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot';
    typingDiv.id = 'typing-indicator';

    const typingContent = document.createElement('div');
    typingContent.className = 'message-content';

    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'typing-indicator';
    typingIndicator.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;

    typingContent.appendChild(typingIndicator);
    typingDiv.appendChild(typingContent);
    chatContainer.appendChild(typingDiv);

    scrollToBottom();

    return 'typing-indicator';
}

/**
 * Remove typing indicator
 */
function removeTypingIndicator(id) {
    const typingDiv = document.getElementById(id);
    if (typingDiv) {
        typingDiv.remove();
    }
}

/**
 * Add error message
 */
function addErrorMessage(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = `Error: ${message}`;
    chatContainer.appendChild(errorDiv);
    scrollToBottom();
}

/**
 * Clear chat history
 */
async function clearChat() {
    if (!confirm('Bạn có chắc muốn xóa lịch sử chat? / Are you sure you want to clear chat history?')) {
        return;
    }

    try {
        const response = await fetch('/api/clear', {
            method: 'POST',
        });

        const data = await response.json();

        if (data.success) {
            // Clear UI
            chatContainer.innerHTML = `
                <div class="welcome-message">
                    <h2>Xin chào! 👋</h2>
                    <p>Tôi có thể giúp bạn tìm hiểu thông tin từ tài liệu.</p>
                    <p>I can help you find information from the documents.</p>
                    <div class="example-questions">
                        <p class="example-title">Ví dụ / Examples:</p>
                        <button class="example-btn" onclick="askQuestion('Silkroad là gì?')">Silkroad là gì?</button>
                        <button class="example-btn" onclick="askQuestion('What is Silkroad?')">What is Silkroad?</button>
                    </div>
                </div>
            `;
        }
    } catch (error) {
        addErrorMessage('Failed to clear chat history');
        console.error('Error:', error);
    }
}

/**
 * Ask a predefined question
 */
function askQuestion(question) {
    messageInput.value = question;
    sendMessage(new Event('submit'));
}

/**
 * Load chat history from server
 */
async function loadChatHistory() {
    try {
        const response = await fetch('/api/history');
        const data = await response.json();

        if (data.success && data.history && data.history.length > 0) {
            // Remove welcome message
            const welcomeMsg = document.querySelector('.welcome-message');
            if (welcomeMsg) {
                welcomeMsg.remove();
            }

            // Display history
            data.history.forEach(msg => {
                addMessage(msg.role, msg.content);
            });
        }
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

/**
 * Scroll to bottom of chat
 */
function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * Handle Enter key in input
 */
messageInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage(event);
    }
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', init);
