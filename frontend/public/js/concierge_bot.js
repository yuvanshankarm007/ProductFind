/**
 * Sentinel AI Concierge: Chatbot & Voice Integrated Assistant for Doubts & Queries.
 * Provides real-time doubt clearing, voice speech-to-text, voice text-to-speech narration,
 * and contextual assistance referencing active search results.
 */

import { showToast } from './state.js';

let voiceNarrationEnabled = false;
let isListening = false;
let speechRecognizer = null;
let currentUtterance = null;

export function initConciergeBot() {
    // Silence any speech synthesis immediately
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
    }
    const launcherBtn = document.getElementById('sentinel-concierge-launcher');
    const drawer = document.getElementById('sentinel-concierge-drawer');
    const closeBtn = document.getElementById('concierge-close-btn');
    const chatForm = document.getElementById('concierge-chat-form');
    const inputEl = document.getElementById('concierge-chat-input');
    const messagesEl = document.getElementById('concierge-messages');
    const micBtn = document.getElementById('concierge-mic-btn');
    const soundToggleBtn = document.getElementById('concierge-sound-toggle');
    const suggestionPills = document.querySelectorAll('.concierge-suggestion-pill');

    if (!launcherBtn || !drawer) return;

    // 1. Toggle Drawer open/close
    launcherBtn.addEventListener('click', () => {
        const isOpen = drawer.classList.contains('open');
        if (isOpen) {
            closeDrawer();
        } else {
            openDrawer();
        }
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', closeDrawer);
    }

    function openDrawer() {
        drawer.classList.add('open');
        launcherBtn.classList.add('active');
        if (inputEl) inputEl.focus();
        // Hide badge if any
        const badge = launcherBtn.querySelector('.concierge-badge');
        if (badge) badge.style.display = 'none';
    }

    function closeDrawer() {
        drawer.classList.remove('open');
        launcherBtn.classList.remove('active');
        stopListening();
        stopSpeaking();
    }

    // 2. Sound Toggle (TTS Voice Narration)
    if (soundToggleBtn) {
        soundToggleBtn.addEventListener('click', () => {
            voiceNarrationEnabled = !voiceNarrationEnabled;
            updateSoundIcon();
            if (!voiceNarrationEnabled) {
                stopSpeaking();
                showToast("Voice narration muted.", "info");
            } else {
                showToast("Voice narration enabled.", "success");
            }
        });
    }

    function updateSoundIcon() {
        if (!soundToggleBtn) return;
        soundToggleBtn.innerHTML = voiceNarrationEnabled ? `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
            </svg>
        ` : `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                <line x1="23" y1="9" x2="17" y2="15"></line>
                <line x1="17" y1="9" x2="23" y2="15"></line>
            </svg>
        `;
        soundToggleBtn.title = voiceNarrationEnabled ? "Mute Voice Narration" : "Unmute Voice Narration";
    }

    // 3. Form Submit (Text message)
    if (chatForm && inputEl) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const text = inputEl.value.trim();
            if (!text) return;
            inputEl.value = '';
            handleUserDoubt(text);
        });
    }

    // 4. Suggestion Pills
    suggestionPills.forEach(pill => {
        pill.addEventListener('click', () => {
            const query = pill.getAttribute('data-query') || pill.textContent.trim();
            if (query) {
                handleUserDoubt(query);
            }
        });
    });

    // 5. Speech-to-Text Microphone
    if (micBtn) {
        micBtn.addEventListener('click', () => {
            if (isListening) {
                stopListening();
            } else {
                startListening();
            }
        });
    }

    function startListening() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            showToast("Speech Recognition not supported in this browser. Please type your query.", "warning");
            return;
        }

        try {
            speechRecognizer = new SpeechRecognition();
            speechRecognizer.continuous = false;
            speechRecognizer.interimResults = true;
            speechRecognizer.lang = 'en-US';

            speechRecognizer.onstart = () => {
                isListening = true;
                if (micBtn) micBtn.classList.add('listening-active');
                if (inputEl) inputEl.placeholder = "Listening... Speak your doubt now";
            };

            speechRecognizer.onresult = (event) => {
                let interim = '';
                let final = '';
                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        final += event.results[i][0].transcript;
                    } else {
                        interim += event.results[i][0].transcript;
                    }
                }
                if (inputEl) {
                    inputEl.value = final || interim;
                }
                if (final) {
                    stopListening();
                    handleUserDoubt(final);
                }
            };

            speechRecognizer.onerror = (e) => {
                console.warn("[Concierge Voice] Speech error:", e.error);
                stopListening();
                if (e.error !== 'no-speech') {
                    showToast(`Voice error: ${e.error}`, "warning");
                }
            };

            speechRecognizer.onend = () => {
                stopListening();
            };

            stopSpeaking();
            speechRecognizer.start();
        } catch (err) {
            console.error("SpeechRecognition start error:", err);
            stopListening();
        }
    }

    function stopListening() {
        isListening = false;
        if (speechRecognizer) {
            try { speechRecognizer.stop(); } catch (_) {}
            speechRecognizer = null;
        }
        if (micBtn) micBtn.classList.remove('listening-active');
        if (inputEl) inputEl.placeholder = "Ask any doubt (e.g. Is Open Box delivery safe?)...";
    }

    function stopSpeaking() {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
        }
    }

    function speakText(text) {
        // Disabled: Support bot will not speak aloud via SpeechSynthesis
        stopSpeaking();
        return;
    }

    async function handleUserDoubt(userQuery) {
        appendMessage('user', userQuery);

        // Typing indicator
        const typingId = appendTypingIndicator();

        // Get active search query for context
        const searchInput = document.getElementById('search-input');
        const activeProd = searchInput ? searchInput.value.trim() : null;

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: userQuery,
                    active_query: activeProd,
                    voice_enabled: voiceNarrationEnabled
                })
            });

            removeTypingIndicator(typingId);

            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }

            const data = await res.json();
            appendMessage('assistant', data.reply, data.suggestions);

            // Voice narration permanently silenced per user policy
        } catch (err) {
            removeTypingIndicator(typingId);
            appendMessage('assistant', `I experienced a temporary communication glitch (${err.message}). You can ask about Open Box delivery, TCO calculations, or PayPal protection.`);
        }
    }

    function appendMessage(role, text, suggestions = []) {
        if (!messagesEl) return;

        const msgDiv = document.createElement('div');
        msgDiv.className = `concierge-message ${role}`;

        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';
        
        // Clean KaTeX/LaTeX math artifacts into readable Unicode
        let cleanText = (text || '')
            .replace(/\$\$\\le\s*([0-9.]+)\\\%\$\$/g, '≤ $1%')
            .replace(/\$\\le\s*([0-9.]+)\\\%\$/g, '≤ $1%')
            .replace(/\\le/g, '≤')
            .replace(/\\ge/g, '≥')
            .replace(/\\%/g, '%')
            .replace(/\$\$/g, '');

        // Parse simple markdown (bold, lists)
        let formatted = escapeHtml(cleanText)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/•\s*(.*?)(?=\n|$)/g, '<li>$1</li>')
            .replace(/\n\n/g, '<br><br>')
            .replace(/\n/g, '<br>');

        bubbleDiv.innerHTML = formatted;
        msgDiv.appendChild(bubbleDiv);

        // If suggestions available, render clickable suggestion pills below the assistant message
        if (role === 'assistant' && suggestions && suggestions.length > 0) {
            const sugContainer = document.createElement('div');
            sugContainer.className = 'message-suggestions';
            suggestions.forEach(sug => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'concierge-suggestion-pill mini';
                btn.textContent = sug;
                btn.addEventListener('click', () => {
                    if (sug.toLowerCase().startsWith('search ')) {
                        const targetTerm = sug.replace(/^search\s+/i, '').trim();
                        const searchInput = document.getElementById('search-input');
                        if (searchInput) searchInput.value = targetTerm;
                        closeDrawer();
                        const searchForm = document.getElementById('search-form');
                        if (searchForm) {
                            const submitEvent = new Event('submit', { cancelable: true });
                            searchForm.dispatchEvent(submitEvent);
                        }
                    } else {
                        handleUserDoubt(sug);
                    }
                });
                sugContainer.appendChild(btn);
            });
            msgDiv.appendChild(sugContainer);
        }

        const timeSpan = document.createElement('span');
        timeSpan.className = 'message-time';
        timeSpan.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        msgDiv.appendChild(timeSpan);

        messagesEl.appendChild(msgDiv);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function appendTypingIndicator() {
        if (!messagesEl) return null;
        const id = 'typing-' + Date.now();
        const typingDiv = document.createElement('div');
        typingDiv.id = id;
        typingDiv.className = 'concierge-message assistant typing';
        typingDiv.innerHTML = `
            <div class="message-bubble typing-bubble">
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="dot"></span>
            </div>
        `;
        messagesEl.appendChild(typingDiv);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return id;
    }

    function removeTypingIndicator(id) {
        if (!id) return;
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function escapeHtml(str) {
        return (str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}
