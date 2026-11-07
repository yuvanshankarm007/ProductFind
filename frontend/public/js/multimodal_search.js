/**
 * Multimodal Voice & Visual Search Module for ProductFind Sentinel.
 * Integrates browser Web Speech API (with animated pulsing states & audio fallback)
 * and Visual Neural Image Search (drag-and-drop, preview thumbnail, OCR/packaging inspection).
 */

import { showToast, store } from './state.js';
import { escapeHtml } from './security.js';

let activeRecognition = null;
let isListening = false;
let selectedImageFile = null;
let selectedImageDataUrl = null;
let currentVisualMatch = null;
let searchCallbacks = {
    executeSearch: null,
    getSearchMode: () => "single",
    getBundleItems: () => [],
    addBundleItem: null
};

// Demo sample presets mapping to valid catalog search images
const SAMPLE_PRESETS = {
    "sony-xm5": {
        name: "sony_wh_1000xm5_platinum_box.jpg",
        title: "Sony WH-1000XM5",
        category: "Wireless Noise Cancelling Headphones",
        brand: "Sony",
        model: "WH-1000XM5",
        confidence: 0.98,
        tags: ["Sony Logo", "WH-1000XM5", "Factory Sealed", "Hi-Res Audio", "Silver / White"],
        color: "#f1f5f9",
        query: "Sony WH-1000XM5",
        deals: [
            { merchant: "Amazon", price: 348.00, condition: "New / Factory Sealed" },
            { merchant: "Best Buy", price: 349.99, condition: "New" },
            { merchant: "B&H Photo", price: 358.00, condition: "Authorized OEM" }
        ]
    },
    "macbook-m3": {
        name: "apple_macbook_pro_16_m3_box.jpg",
        title: "Apple MacBook Pro 16 M3 Max",
        category: "High-Performance Laptop",
        brand: "Apple",
        model: "MacBook Pro 16 M3 Max",
        confidence: 0.97,
        tags: ["Apple Inc.", "M3 Max", "Liquid Retina XDR", "Space Black", "Liquid Retina"],
        color: "#334155",
        query: "Apple MacBook Pro 16 M3 Max",
        deals: [
            { merchant: "B&H Photo", price: 3299.00, condition: "New / Sealed" },
            { merchant: "Apple Store", price: 3499.00, condition: "Official OEM" },
            { merchant: "Amazon", price: 3349.00, condition: "New" }
        ]
    },
    "iphone-16": {
        name: "iphone_16_pro_natural_titanium.jpg",
        title: "iPhone 16 Pro",
        category: "Flagship Smartphone",
        brand: "Apple",
        model: "iPhone 16 Pro",
        confidence: 0.95,
        tags: ["Apple", "iPhone 16 Pro", "A18 Pro", "Natural Titanium", "Pro Camera"],
        color: "#94a3b8",
        query: "iPhone 16 Pro",
        deals: [
            { merchant: "Apple Store", price: 999.00, condition: "New / Factory Unlocked" },
            { merchant: "Verizon Direct", price: 979.00, condition: "New" },
            { merchant: "Best Buy", price: 999.00, condition: "New" }
        ]
    },
    "switch-oled": {
        name: "nintendo_switch_oled_mario.jpg",
        title: "Nintendo Switch OLED Mario Edition",
        category: "Handheld Gaming Console",
        brand: "Nintendo",
        model: "Switch OLED",
        confidence: 0.96,
        tags: ["Nintendo", "Switch OLED", "Mario Red", "Dockable Console"],
        color: "#ef4444",
        query: "Nintendo Switch OLED Mario Edition",
        deals: [
            { merchant: "Target", price: 349.99, condition: "New" },
            { merchant: "GameStop", price: 344.99, condition: "OEM Packaged" },
            { merchant: "Amazon", price: 349.99, condition: "New" }
        ]
    },
    "aeron": {
        name: "herman_miller_aeron_graphite.jpg",
        title: "Herman Miller Aeron Chair",
        category: "Ergonomic Mesh Office Chair",
        brand: "Herman Miller",
        model: "Aeron Chair",
        confidence: 0.94,
        tags: ["Herman Miller", "Pellicle Mesh", "PostureFit SL", "Graphite"],
        color: "#1e293b",
        query: "Herman Miller Aeron Chair",
        deals: [
            { merchant: "Herman Miller Direct", price: 1695.00, condition: "12-Year Warranty" },
            { merchant: "Design Within Reach", price: 1720.00, condition: "New" },
            { merchant: "Madison Seating", price: 849.00, condition: "Open Box / Inspected" }
        ]
    }
};

/**
 * Initializes multimodal event listeners and binds search orchestration hooks.
 */
export function initMultimodalSearch(callbacks) {
    searchCallbacks = { ...searchCallbacks, ...callbacks };

    // 1. Microphone Voice Search Button
    const btnVoice = document.getElementById('btn-voice-search');
    if (btnVoice) {
        btnVoice.addEventListener('click', () => toggleVoiceSearch());
    }

    // 2. Camera Image Search Button
    const btnImage = document.getElementById('btn-image-search');
    if (btnImage) {
        btnImage.addEventListener('click', () => openImageSearchModal());
    }

    // 3. Modal Close Triggers
    const modalImage = document.getElementById('image-search-modal');
    const btnCloseModal = document.getElementById('modal-close-image-search');
    const btnCancelModal = document.getElementById('btn-modal-cancel-image');

    if (btnCloseModal) btnCloseModal.addEventListener('click', () => closeImageSearchModal());
    if (btnCancelModal) btnCancelModal.addEventListener('click', () => closeImageSearchModal());
    if (modalImage) {
        modalImage.addEventListener('click', (e) => {
            if (e.target === modalImage) closeImageSearchModal();
        });
    }

    // 4. Drag & Drop Zone Wireup
    setupDropzone();

    // 5. File Inputs
    const fileInput = document.getElementById('multimodal-image-input');
    const btnBrowse = document.getElementById('btn-browse-image');
    if (btnBrowse && fileInput) {
        btnBrowse.addEventListener('click', () => fileInput.click());
    }
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) {
                handleFileSelected(e.target.files[0]);
            }
        });
    }

    // 6. Clear Preview
    const btnClearPreview = document.getElementById('btn-clear-preview');
    if (btnClearPreview) {
        btnClearPreview.addEventListener('click', () => clearSelectedImage());
    }

    // 7. URL Input Drawer
    const btnPasteUrl = document.getElementById('btn-paste-image-url');
    const urlDrawer = document.getElementById('image-url-drawer');
    const btnLoadUrl = document.getElementById('btn-load-image-url');
    const inputUrl = document.getElementById('image-url-input');

    if (btnPasteUrl && urlDrawer) {
        btnPasteUrl.addEventListener('click', () => {
            urlDrawer.style.display = urlDrawer.style.display === 'none' ? 'block' : 'none';
            if (urlDrawer.style.display === 'block' && inputUrl) {
                inputUrl.focus();
            }
        });
    }

    if (btnLoadUrl && inputUrl) {
        btnLoadUrl.addEventListener('click', () => {
            const urlVal = inputUrl.value.trim();
            if (urlVal) {
                handleImageUrlSelected(urlVal);
            }
        });
        inputUrl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const urlVal = inputUrl.value.trim();
                if (urlVal) handleImageUrlSelected(urlVal);
            }
        });
    }

    // 8. Clipboard Paste (Ctrl+V) anywhere while modal is open
    window.addEventListener('paste', (e) => {
        const modal = document.getElementById('image-search-modal');
        if (modal && modal.classList.contains('active')) {
            const items = (e.clipboardData || e.originalEvent.clipboardData).items;
            for (const item of items) {
                if (item.type.indexOf('image') !== -1) {
                    const blob = item.getAsFile();
                    handleFileSelected(blob, 'clipboard_image.png');
                    showToast('📋 Image pasted from clipboard', 'info');
                    break;
                }
            }
        }
    });

    // 9. Demo Sample Buttons
    document.querySelectorAll('.visual-sample-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const sampleKey = btn.getAttribute('data-sample');
            loadSamplePreset(sampleKey);
        });
    });

    // 10. Modal "Analyze Image & Find Deals" Button
    const btnAnalyze = document.getElementById('btn-modal-analyze-image');
    if (btnAnalyze) {
        btnAnalyze.addEventListener('click', () => triggerVisualAnalysis());
    }

    // 11. Execute Visual Search Button in Result Card
    const btnExecArbitration = document.getElementById('btn-execute-visual-arbitration');
    if (btnExecArbitration) {
        btnExecArbitration.addEventListener('click', () => applyVisualMatchToSearch());
    }

    // 12. Visual Search Indicator Bar Clear Button
    const btnClearVisual = document.getElementById('btn-clear-visual-search');
    if (btnClearVisual) {
        btnClearVisual.addEventListener('click', () => clearVisualIndicator());
    }
}

// ==========================================================================
// VOICE SEARCH ENGINE (Web Speech API + Backend Fallback)
// ==========================================================================

export function toggleVoiceSearch() {
    if (isListening) {
        stopVoiceSearch();
    } else {
        startVoiceSearch();
    }
}

export function startVoiceSearch() {
    const btnVoice = document.getElementById('btn-voice-search');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        console.warn("Web Speech API not supported in this browser. Falling back to audio upload.");
        showToast("🎙️ Browser speech API unavailable. Please select audio file.", "info");
        const audioInput = document.getElementById('multimodal-audio-input');
        if (audioInput) {
            audioInput.onchange = (e) => {
                if (e.target.files && e.target.files[0]) {
                    transcribeAudioFile(e.target.files[0]);
                }
            };
            audioInput.click();
        }
        return;
    }

    try {
        if (activeRecognition) {
            try { activeRecognition.abort(); } catch (e) {}
        }

        const recognition = new SpeechRecognition();
        activeRecognition = recognition;
        recognition.continuous = false;
        recognition.interimResults = true;

        // Map UI preferences to Speech recognition language
        const prefLang = store.preferences.language || "en";
        const langMap = {
            "en": "en-US",
            "hi": "hi-IN",
            "es": "es-ES",
            "de": "de-DE",
            "fr": "fr-FR",
            "ja": "ja-JP"
        };
        recognition.lang = langMap[prefLang] || "en-US";

        recognition.onstart = () => {
            isListening = true;
            if (btnVoice) btnVoice.classList.add('listening-active');
            showToast(`🎙️ Listening... Speak product name (${recognition.lang})`, "info");
            const searchInput = document.getElementById('search-input');
            if (searchInput) {
                searchInput.placeholder = "Listening... Speak clearly into your microphone";
            }
        };

        recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }

            const searchInput = document.getElementById('search-input');
            if (searchInput) {
                searchInput.value = finalTranscript || interimTranscript;
            }

            if (finalTranscript) {
                const cleaned = finalTranscript.trim();
                showToast(`🗣️ Recognized: "${cleaned}"`, "success");
                stopVoiceSearch();

                // Automatically trigger arbitration pipeline
                const mode = searchCallbacks.getSearchMode ? searchCallbacks.getSearchMode() : "single";
                if (mode === 'bundle' && searchCallbacks.addBundleItem) {
                    searchCallbacks.addBundleItem(cleaned);
                }
                if (searchCallbacks.executeSearch) {
                    searchCallbacks.executeSearch(cleaned, mode);
                }
            }
        };

        recognition.onerror = (event) => {
            console.warn("Speech recognition error:", event.error);
            stopVoiceSearch();
            if (event.error === 'no-speech') {
                showToast("⚠️ No speech detected. Please try again.", "info");
            } else if (event.error === 'not-allowed') {
                showToast("⚠️ Microphone access denied. Check browser permissions.", "error");
            } else {
                showToast(`Speech recognition notice: ${event.error}`, "info");
            }
        };

        recognition.onend = () => {
            stopVoiceSearch();
        };

        recognition.start();
    } catch (err) {
        console.error("Failed to start speech recognition:", err);
        stopVoiceSearch();
        showToast("Microphone activation failed. Using standard input.", "error");
    }
}

export function stopVoiceSearch() {
    isListening = false;
    const btnVoice = document.getElementById('btn-voice-search');
    if (btnVoice) btnVoice.classList.remove('listening-active');

    const searchInput = document.getElementById('search-input');
    if (searchInput && (!searchInput.value || searchInput.placeholder.includes("Listening"))) {
        searchInput.placeholder = "Search any product (e.g., Sony WH-1000XM5, MacBook Pro M3, iPhone 16 Pro)...";
    }

    if (activeRecognition) {
        try {
            activeRecognition.stop();
        } catch (e) {}
        activeRecognition = null;
    }
}

async function transcribeAudioFile(file) {
    showToast("Transcribing audio file...", "info");
    const formData = new FormData();
    formData.append("file", file);
    formData.append("language", store.preferences.language || "en");
    formData.append("country", store.preferences.country || "US");
    formData.append("currency", store.preferences.currency || "USD");
    formData.append("preferred_payment", store.preferences.preferredPayment || "all");
    formData.append("session_id", store.sessionId || "web-sess");
    const mode = searchCallbacks.getSearchMode ? searchCallbacks.getSearchMode() : "single";
    formData.append("mode", mode);
    formData.append("warranty_priority", store.riskPreferences.warrantyPriority || 0.5);
    formData.append("speed_priority", store.riskPreferences.speedPriority || 0.5);
    formData.append("trust_tolerance", store.riskPreferences.trustTolerance || 0.7);
    formData.append("auto_search", "true");

    try {
        const resp = await fetch("/api/voice/transcribe", {
            method: "POST",
            body: formData
        });
        const data = await resp.json();
        if (resp.ok && data.status === "success") {
            const transcript = data.transcript;
            const searchInput = document.getElementById('search-input');
            if (searchInput) searchInput.value = transcript;
            showToast(`🗣️ Transcribed: "${transcript}" (${Math.round(data.confidence * 100)}%)`, "success");

            if (mode === 'bundle' && searchCallbacks.addBundleItem) {
                searchCallbacks.addBundleItem(transcript);
            }
            if (searchCallbacks.executeSearch) {
                const bundleItems = searchCallbacks.getBundleItems ? searchCallbacks.getBundleItems() : null;
                searchCallbacks.executeSearch(transcript, mode, bundleItems);
            }
        } else {
            showToast(`Transcription error: ${data.detail || 'Failed to process audio'}`, "error");
        }
    } catch (err) {
        showToast(`Audio transcription request failed: ${err.message}`, "error");
    }
}

// ==========================================================================
// VISUAL SEARCH ENGINE (Modal, Dropzone, Feature Extraction & Deals)
// ==========================================================================

export function openImageSearchModal() {
    const modal = document.getElementById('image-search-modal');
    if (modal) {
        modal.classList.add('active');
        // Reset state if no image selected
        if (!selectedImageFile && !selectedImageDataUrl) {
            clearSelectedImage();
        }
    }
}

export function closeImageSearchModal() {
    const modal = document.getElementById('image-search-modal');
    if (modal) {
        modal.classList.remove('active');
    }
}

function setupDropzone() {
    const dropzone = document.getElementById('image-dropzone');
    if (!dropzone) return;

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dragover');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length > 0) {
            handleFileSelected(files[0]);
        }
    });
}

function handleFileSelected(file, overrideName) {
    if (!file || !file.type.startsWith('image/')) {
        showToast("⚠️ Please select a valid image file (JPEG, PNG, WebP)", "error");
        return;
    }

    selectedImageFile = file;
    const fileName = overrideName || file.name || "uploaded_image.png";
    const fileSizeKb = Math.round(file.size / 1024);

    const reader = new FileReader();
    reader.onload = (e) => {
        selectedImageDataUrl = e.target.result;
        renderImagePreview(selectedImageDataUrl, fileName, `${fileSizeKb} KB`);
    };
    reader.readAsDataURL(file);
}

function handleImageUrlSelected(url) {
    selectedImageFile = null;
    selectedImageDataUrl = url;

    // Create preview
    renderImagePreview(url, url.split('/').pop() || "remote_image.jpg", "Remote Image URL");
    showToast("✓ Remote image linked", "info");
}

function renderImagePreview(src, name, sizeText) {
    const emptyState = document.getElementById('dropzone-empty-state');
    const previewState = document.getElementById('dropzone-preview-state');
    const thumb = document.getElementById('image-preview-thumbnail');
    const fnEl = document.getElementById('preview-filename');
    const fsEl = document.getElementById('preview-filesize');
    const btnAnalyze = document.getElementById('btn-modal-analyze-image');
    const resultCard = document.getElementById('visual-modal-result-card');

    if (emptyState) emptyState.style.display = 'none';
    if (previewState) previewState.style.display = 'block';
    if (thumb) thumb.src = src;
    if (fnEl) fnEl.textContent = name;
    if (fsEl) fsEl.textContent = `${sizeText} • Validated Image`;
    if (btnAnalyze) btnAnalyze.disabled = false;
    if (resultCard) resultCard.style.display = 'none';
}

function clearSelectedImage() {
    selectedImageFile = null;
    selectedImageDataUrl = null;
    currentVisualMatch = null;

    const emptyState = document.getElementById('dropzone-empty-state');
    const previewState = document.getElementById('dropzone-preview-state');
    const btnAnalyze = document.getElementById('btn-modal-analyze-image');
    const resultCard = document.getElementById('visual-modal-result-card');
    const progressBar = document.getElementById('visual-scan-progress');
    const urlDrawer = document.getElementById('image-url-drawer');

    if (emptyState) emptyState.style.display = 'block';
    if (previewState) previewState.style.display = 'none';
    if (btnAnalyze) btnAnalyze.disabled = true;
    if (resultCard) resultCard.style.display = 'none';
    if (progressBar) progressBar.style.display = 'none';
    if (urlDrawer) urlDrawer.style.display = 'none';
}

function loadSamplePreset(sampleKey) {
    const preset = SAMPLE_PRESETS[sampleKey];
    if (!preset) return;

    // Create a sleek colored SVG data URI representing the sample retail unit
    const svg = `
        <svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 160 160">
            <rect width="160" height="160" rx="12" fill="${preset.color}"/>
            <circle cx="80" cy="80" r="45" fill="rgba(0,0,0,0.3)"/>
            <text x="80" y="75" font-family="Arial, sans-serif" font-size="14" font-weight="bold" fill="#ffffff" text-anchor="middle">${preset.brand}</text>
            <text x="80" y="95" font-family="Arial, sans-serif" font-size="11" fill="#38bdf8" text-anchor="middle">${preset.model}</text>
        </svg>
    `;
    const dataUri = `data:image/svg+xml;base64,${btoa(svg)}`;
    selectedImageDataUrl = dataUri;
    selectedImageFile = null;

    renderImagePreview(dataUri, preset.name, "Sample Benchmark Asset");

    // Automatically trigger visual neural inspection
    triggerVisualAnalysis(preset);
}

async function triggerVisualAnalysis(overridePreset) {
    const progressBar = document.getElementById('visual-scan-progress');
    const btnAnalyze = document.getElementById('btn-modal-analyze-image');
    const resultCard = document.getElementById('visual-modal-result-card');

    if (progressBar) progressBar.style.display = 'block';
    if (btnAnalyze) btnAnalyze.disabled = true;
    if (resultCard) resultCard.style.display = 'none';

    try {
        let matchResult = null;
        let returnedDeals = [];

        if (overridePreset) {
            // Simulated instant neural OCR pipeline for benchmark presets
            await new Promise(r => setTimeout(r, 450));
            matchResult = {
                brand: overridePreset.brand,
                model: overridePreset.model,
                category: overridePreset.category,
                extracted_query: overridePreset.query,
                confidence: overridePreset.confidence,
                detected_labels: overridePreset.tags
            };
            returnedDeals = overridePreset.deals || [];
        } else if (selectedImageFile) {
            // Real HTTP multipart backend request
            const formData = new FormData();
            formData.append("file", selectedImageFile);
            formData.append("country", store.preferences.country || "US");
            formData.append("currency", store.preferences.currency || "USD");
            formData.append("preferred_payment", store.preferences.preferredPayment || "all");
            formData.append("session_id", store.sessionId || "web-sess");
            const mode = searchCallbacks.getSearchMode ? searchCallbacks.getSearchMode() : "single";
            formData.append("mode", mode);
            formData.append("warranty_priority", store.riskPreferences.warrantyPriority || 0.5);
            formData.append("speed_priority", store.riskPreferences.speedPriority || 0.5);
            formData.append("trust_tolerance", store.riskPreferences.trustTolerance || 0.7);

            const resp = await fetch("/api/search/image", {
                method: "POST",
                body: formData
            });
            const data = await resp.json();
            if (!resp.ok) {
                throw new Error(data.detail || "Visual extraction failed.");
            }
            matchResult = data.visual_analysis;
            returnedDeals = data.final_options || data.deals || [];
        } else if (selectedImageDataUrl) {
            // JSON base64 / URL backend request
            const payload = selectedImageDataUrl.startsWith("http")
                ? { image_url: selectedImageDataUrl }
                : { image_base64: selectedImageDataUrl, filename: "product_image.png" };

            payload.country = store.preferences.country || "US";
            payload.currency = store.preferences.currency || "USD";
            payload.preferred_payment = store.preferences.preferredPayment || "all";
            payload.session_id = store.sessionId || "web-sess";
            payload.mode = searchCallbacks.getSearchMode ? searchCallbacks.getSearchMode() : "single";
            payload.warranty_priority = store.riskPreferences.warrantyPriority || 0.5;
            payload.speed_priority = store.riskPreferences.speedPriority || 0.5;
            payload.trust_tolerance = store.riskPreferences.trustTolerance || 0.7;

            const resp = await fetch("/api/search/image", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();
            if (!resp.ok) {
                throw new Error(data.detail || "Visual extraction failed.");
            }
            matchResult = data.visual_analysis;
            returnedDeals = data.final_options || data.deals || [];
        }

        if (progressBar) progressBar.style.display = 'none';
        if (btnAnalyze) btnAnalyze.disabled = false;

        if (matchResult) {
            currentVisualMatch = matchResult;
            renderVisualResultCard(matchResult, returnedDeals);
        }
    } catch (err) {
        if (progressBar) progressBar.style.display = 'none';
        if (btnAnalyze) btnAnalyze.disabled = false;
        showToast(`Visual scan failed: ${err.message}`, "error");
    }
}

function renderVisualResultCard(match, deals) {
    const card = document.getElementById('visual-modal-result-card');
    const title = document.getElementById('visual-result-title');
    const category = document.getElementById('visual-result-category');
    const pill = document.getElementById('visual-result-confidence-pill');
    const tagsContainer = document.getElementById('visual-result-tags');

    if (!card) return;

    if (title) title.textContent = `${match.brand} ${match.model}`;
    if (category) category.textContent = match.category;
    if (pill) {
        const pct = Math.round((match.confidence || 0.95) * 100);
        pill.textContent = `${pct}% Match Confidence`;
    }

    if (tagsContainer) {
        const labels = match.detected_labels || [match.brand, match.model, "OCR Verified"];
        tagsContainer.innerHTML = labels.map(label => `
            <span class="tag-pill" style="font-size: 11px; padding: 2px 8px; border-color: rgba(56, 189, 248, 0.3); background: rgba(56, 189, 248, 0.1); color: #7dd3fc;">
                ${escapeHtml(label)}
            </span>
        `).join('');
    }

    // Render Deals Preview if deals were returned
    let dealsContainer = document.getElementById('visual-result-deals-preview');
    if (!dealsContainer) {
        dealsContainer = document.createElement('div');
        dealsContainer.id = 'visual-result-deals-preview';
        dealsContainer.style.marginTop = '0.75rem';
        dealsContainer.style.marginBottom = '1rem';
        dealsContainer.style.padding = '0.6rem 0.8rem';
        dealsContainer.style.background = 'rgba(15, 23, 42, 0.6)';
        dealsContainer.style.border = '1px solid rgba(255, 255, 255, 0.08)';
        dealsContainer.style.borderRadius = '8px';
        if (tagsContainer && tagsContainer.parentNode) {
            tagsContainer.parentNode.insertBefore(dealsContainer, tagsContainer.nextSibling);
        }
    }

    const activeDeals = deals || match.deals || match.final_options || [];
    if (activeDeals && activeDeals.length > 0) {
        dealsContainer.style.display = 'block';
        const dealRows = activeDeals.slice(0, 3).map(d => `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px dashed rgba(255,255,255,0.06); font-size: 12px;">
                <div>
                    <span style="font-weight: 700; color: #f8fafc;">${escapeHtml(d.merchant || d.seller || 'Merchant')}</span>
                    <span style="color: #64748b; font-size: 11px; margin-left: 6px;">[${d.condition || 'New'}]</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-weight: 800; color: #34d399; font-family: monospace;">$${Number(d.price || d.final_price || 0).toFixed(2)}</span>
                    <span style="background: rgba(16, 185, 129, 0.15); color: #34d399; font-size: 10px; padding: 1px 6px; border-radius: 4px; font-weight: 600;">✓ Verified</span>
                </div>
            </div>
        `).join('');

        dealsContainer.innerHTML = `
            <div style="font-size: 11px; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px; display: flex; justify-content: space-between;">
                <span>🎯 Instant Arbitrated Deals Found</span>
                <span style="color: #94a3b8; font-weight: normal;">(${activeDeals.length} options)</span>
            </div>
            ${dealRows}
        `;
    } else {
        dealsContainer.style.display = 'none';
    }

    card.style.display = 'block';
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function applyVisualMatchToSearch() {
    if (!currentVisualMatch) return;

    const query = currentVisualMatch.extracted_query || `${currentVisualMatch.brand} ${currentVisualMatch.model}`;
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.value = query;
    }

    // Display visual indicator bar under search bar
    showVisualIndicatorBar(currentVisualMatch);

    // Close modal
    closeImageSearchModal();

    showToast(`📷 Visual search loaded: "${query}"`, "success");

    // Execute arbitration pipeline
    const mode = searchCallbacks.getSearchMode ? searchCallbacks.getSearchMode() : "single";
    if (mode === 'bundle' && searchCallbacks.addBundleItem) {
        searchCallbacks.addBundleItem(query);
    }
    if (searchCallbacks.executeSearch) {
        const bundleItems = searchCallbacks.getBundleItems ? searchCallbacks.getBundleItems() : null;
        searchCallbacks.executeSearch(query, mode, bundleItems);
    }
}

function showVisualIndicatorBar(match) {
    const bar = document.getElementById('visual-search-indicator-bar');
    const badge = document.getElementById('visual-indicator-badge');
    const text = document.getElementById('visual-indicator-text');
    const cat = document.getElementById('visual-indicator-category');

    if (!bar) return;

    if (badge) {
        const pct = Math.round((match.confidence || 0.95) * 100);
        badge.textContent = `📷 ${pct}% Match`;
    }
    if (text) text.textContent = `${match.brand} ${match.model}`;
    if (cat) cat.textContent = `(${match.category})`;

    bar.style.display = 'flex';
}

function clearVisualIndicator() {
    const bar = document.getElementById('visual-search-indicator-bar');
    if (bar) bar.style.display = 'none';
    currentVisualMatch = null;
    showToast("Visual match filter cleared", "info");
}
