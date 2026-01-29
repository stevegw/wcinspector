/**
 * WCInspector - Windchill Knowledge Base
 * Main JavaScript Application
 */

// API Base URL
const API_BASE = '/api';

// State
let currentQuestionId = null;
let categories = {};
let settings = {
    theme: 'light',
    ai_tone: 'technical',
    response_length: 'detailed',
    ollama_model: 'llama2',
    llm_provider: 'groq'
};

// DOM Elements
const elements = {
    // Question Form
    questionForm: document.getElementById('question-form'),
    questionInput: document.getElementById('question-input'),
    submitBtn: document.getElementById('submit-btn'),
    clearInputBtn: document.getElementById('clear-input-btn'),
    categorySelect: document.getElementById('category-select'),
    sampleList: document.getElementById('sample-list'),

    // Results
    sampleQuestions: document.getElementById('sample-questions'),
    resultsCard: document.getElementById('results-card'),
    topicSelect: document.getElementById('topic-select'),
    loadingState: document.getElementById('loading-state'),
    answerDisplay: document.getElementById('answer-display'),
    answerText: document.getElementById('answer-text'),
    proTips: document.getElementById('pro-tips'),
    tipsList: document.getElementById('tips-list'),
    errorState: document.getElementById('error-state'),
    errorMessage: document.getElementById('error-message'),

    // Question Display
    questionTextDisplay: document.getElementById('question-text-display'),

    // Answer Actions
    copyBtn: document.getElementById('copy-btn'),
    rerunBtn: document.getElementById('rerun-btn'),
    moreBtn: document.getElementById('more-btn'),
    retryBtn: document.getElementById('retry-btn'),

    // History
    historyList: document.getElementById('history-list'),
    clearHistoryBtn: document.getElementById('clear-history-btn'),

    // Header Controls
    themeToggle: document.getElementById('theme-toggle'),
    settingsBtn: document.getElementById('settings-btn'),

    // Settings Modal
    settingsModal: document.getElementById('settings-modal'),
    toneSelect: document.getElementById('tone-select'),
    lengthSelect: document.getElementById('length-select'),
    providerSelect: document.getElementById('provider-select'),
    modelSelect: document.getElementById('model-select'),
    resetSettingsBtn: document.getElementById('reset-settings-btn'),
    saveSettingsBtn: document.getElementById('save-settings-btn'),

    // Sources Modal
    sourcesModal: document.getElementById('sources-modal'),
    sourcesList: document.getElementById('sources-list'),

    // Scraper Modal
    scraperBtn: document.getElementById('scraper-btn'),
    scraperModal: document.getElementById('scraper-modal'),
    scraperStatusText: document.getElementById('scraper-status-text'),
    pagesCount: document.getElementById('pages-count'),
    chunksCount: document.getElementById('chunks-count'),
    lastUpdated: document.getElementById('last-updated'),
    categoryStats: document.getElementById('category-stats'),
    scraperProgress: document.getElementById('scraper-progress'),
    progressFill: document.getElementById('progress-fill'),
    progressText: document.getElementById('progress-text'),
    scrapeCategorySelect: document.getElementById('scrape-category-select'),
    scrapeMaxPages: document.getElementById('scrape-max-pages'),
    startScrapeBtn: document.getElementById('start-scrape-btn'),
    exportBtn: document.getElementById('export-btn'),
    resetKbBtn: document.getElementById('reset-kb-btn'),

    // Confirm Modal
    confirmModal: document.getElementById('confirm-modal'),
    confirmTitle: document.getElementById('confirm-title'),
    confirmMessage: document.getElementById('confirm-message'),
    confirmCancel: document.getElementById('confirm-cancel'),
    confirmOk: document.getElementById('confirm-ok'),

    // Toast Container
    toastContainer: document.getElementById('toast-container'),

    // Related Images
    relatedImages: document.getElementById('related-images'),
    imagesList: document.getElementById('images-list'),

    // Lightbox
    lightboxModal: document.getElementById('lightbox-modal'),
    lightboxImage: document.getElementById('lightbox-image'),
    lightboxCaption: document.getElementById('lightbox-caption'),
    lightboxClose: document.getElementById('lightbox-close'),
    lightboxPrev: document.getElementById('lightbox-prev'),
    lightboxNext: document.getElementById('lightbox-next')
};

// Current sources for modal
let currentSources = [];

// Current question text for display
let currentQuestionText = '';

// Current images for lightbox
let currentImages = [];
let currentImageIndex = 0;

// Confirm callback
let confirmCallback = null;

// Flag to prevent double submission
let isSubmitting = false;

// Initialize Application
document.addEventListener('DOMContentLoaded', init);

async function init() {
    // Load settings
    await loadSettings();

    // Apply theme
    applyTheme(settings.theme);

    // Load categories first (needed for other components)
    await loadCategories();

    // Load history
    await loadHistory();

    // Load scraper stats
    await loadScraperStats();

    // Load available models
    await loadModels();

    // Load available topics for filtering
    await loadTopics();

    // Setup event listeners
    setupEventListeners();
}

function setupEventListeners() {
    // Question Form
    elements.questionForm.addEventListener('submit', handleQuestionSubmit);
    elements.clearInputBtn.addEventListener('click', () => {
        elements.questionInput.value = '';
        elements.questionInput.focus();
    });

    // Category selector
    elements.categorySelect.addEventListener('change', handleCategoryChange);

    // Sample Questions
    document.querySelectorAll('.sample-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const category = btn.dataset.category;
            if (category) {
                elements.categorySelect.value = category;
            }
            elements.questionInput.value = btn.textContent;
            elements.questionInput.focus();
        });
    });

    // Answer Actions
    elements.copyBtn.addEventListener('click', copyAnswer);
    elements.rerunBtn.addEventListener('click', rerunQuery);
    elements.moreBtn.addEventListener('click', showSourcesModal);
    elements.retryBtn.addEventListener('click', () => {
        elements.questionForm.dispatchEvent(new Event('submit'));
    });

    // History
    elements.clearHistoryBtn.addEventListener('click', () => {
        showConfirm(
            'Clear History',
            'Are you sure you want to clear all question history? This cannot be undone.',
            clearHistory
        );
    });

    // Theme Toggle
    elements.themeToggle.addEventListener('click', toggleTheme);

    // Settings
    elements.settingsBtn.addEventListener('click', () => showModal(elements.settingsModal));
    elements.resetSettingsBtn.addEventListener('click', resetSettings);
    elements.saveSettingsBtn.addEventListener('click', saveSettings);

    // Scraper
    elements.scraperBtn.addEventListener('click', () => showModal(elements.scraperModal));
    elements.startScrapeBtn.addEventListener('click', startScrape);
    elements.exportBtn.addEventListener('click', exportHistory);
    elements.resetKbBtn.addEventListener('click', () => {
        showConfirm(
            'Reset Knowledge Base',
            'Are you sure you want to reset the knowledge base? All scraped data will be deleted.',
            resetKnowledgeBase
        );
    });

    // Modal Close Buttons
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal').classList.add('hidden');
        });
    });

    // Click outside modal to close
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.add('hidden');
            }
        });
    });

    // Confirm Modal
    elements.confirmCancel.addEventListener('click', () => {
        elements.confirmModal.classList.add('hidden');
        confirmCallback = null;
    });
    elements.confirmOk.addEventListener('click', () => {
        elements.confirmModal.classList.add('hidden');
        if (confirmCallback) {
            confirmCallback();
            confirmCallback = null;
        }
    });

    // Keyboard shortcuts
    elements.questionInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleQuestionSubmit(e);
        }
    });

    // Lightbox controls
    if (elements.lightboxClose) {
        elements.lightboxClose.addEventListener('click', closeLightbox);
    }
    if (elements.lightboxPrev) {
        elements.lightboxPrev.addEventListener('click', () => navigateLightbox(-1));
    }
    if (elements.lightboxNext) {
        elements.lightboxNext.addEventListener('click', () => navigateLightbox(1));
    }
    if (elements.lightboxModal) {
        elements.lightboxModal.addEventListener('click', (e) => {
            if (e.target === elements.lightboxModal) {
                closeLightbox();
            }
        });
    }

    // Keyboard navigation for lightbox
    document.addEventListener('keydown', (e) => {
        if (!elements.lightboxModal || elements.lightboxModal.classList.contains('hidden')) {
            return;
        }
        if (e.key === 'Escape') {
            closeLightbox();
        } else if (e.key === 'ArrowLeft') {
            navigateLightbox(-1);
        } else if (e.key === 'ArrowRight') {
            navigateLightbox(1);
        }
    });

    // Clear error state when user starts typing
    elements.questionInput.addEventListener('input', () => {
        elements.questionInput.classList.remove('input-error');
    });

    // Topic filter change - re-run query with new filter
    elements.topicSelect.addEventListener('change', handleTopicFilterChange);
}

// API Functions
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        }
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
        throw new Error(error.detail || 'An error occurred');
    }

    return response.json();
}

// Settings Functions
async function loadSettings() {
    try {
        const data = await apiRequest('/settings');
        settings = { ...settings, ...data };
        updateSettingsUI();
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

function updateSettingsUI() {
    elements.toneSelect.value = settings.ai_tone;
    elements.lengthSelect.value = settings.response_length;
    if (settings.llm_provider) {
        elements.providerSelect.value = settings.llm_provider;
    }
    if (settings.ollama_model) {
        elements.modelSelect.value = settings.ollama_model;
    }
}

async function saveSettings() {
    settings.ai_tone = elements.toneSelect.value;
    settings.response_length = elements.lengthSelect.value;
    settings.llm_provider = elements.providerSelect.value;
    settings.ollama_model = elements.modelSelect.value;

    try {
        await apiRequest('/settings', {
            method: 'PUT',
            body: JSON.stringify(settings)
        });
        elements.settingsModal.classList.add('hidden');
        showToast('Settings saved successfully', 'success');
    } catch (error) {
        showToast('Failed to save settings', 'error');
    }
}

async function resetSettings() {
    try {
        await apiRequest('/settings/reset', { method: 'POST' });
        await loadSettings();
        applyTheme(settings.theme);
        showToast('Settings reset to defaults', 'success');
    } catch (error) {
        showToast('Failed to reset settings', 'error');
    }
}

// Theme Functions
function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    elements.themeToggle.querySelector('.icon').textContent = theme === 'dark' ? '☀️' : '🌙';
}

async function toggleTheme() {
    const newTheme = settings.theme === 'dark' ? 'light' : 'dark';
    settings.theme = newTheme;
    applyTheme(newTheme);

    try {
        await apiRequest('/settings', {
            method: 'PUT',
            body: JSON.stringify({ theme: newTheme })
        });
    } catch (error) {
        console.error('Failed to save theme:', error);
    }
}

// Question Functions
async function handleQuestionSubmit(e) {
    e.preventDefault();

    // Prevent double submission
    if (isSubmitting) {
        return;
    }

    const question = elements.questionInput.value.trim();
    if (!question) {
        showToast('Please enter a question', 'error');
        elements.questionInput.classList.add('input-error');
        elements.questionInput.focus();
        return;
    }

    // Set submission flag immediately to prevent double-clicks
    isSubmitting = true;

    // Clear error state on successful validation
    elements.questionInput.classList.remove('input-error');

    // Show loading state
    showLoading();

    try {
        // Get topic filter and category if selected
        const topicFilter = getSelectedTopicFilter();
        const category = getSelectedCategory();

        const data = await apiRequest('/ask', {
            method: 'POST',
            body: JSON.stringify({ question, topic_filter: topicFilter, category })
        });

        currentQuestionId = data.question_id;
        currentSources = data.source_links || [];
        displayAnswer(data, question);
        updateTopicFilterStatus(data.topic_filter_applied);
        await loadHistory();
        elements.questionInput.value = '';
    } catch (error) {
        showError(error.message);
    } finally {
        // Reset submission flag regardless of success or failure
        isSubmitting = false;
    }
}

async function rerunQuery() {
    if (!currentQuestionId) return;

    showLoading();

    try {
        // Get topic filter if selected
        const topicFilter = getSelectedTopicFilter();

        const data = await apiRequest(`/questions/${currentQuestionId}/rerun`, {
            method: 'POST',
            body: JSON.stringify({ topic_filter: topicFilter })
        });

        currentSources = data.source_links || [];
        displayAnswer(data);
        updateTopicFilterStatus(data.topic_filter_applied);
    } catch (error) {
        showError(error.message);
    }
}

function showLoading() {
    elements.sampleQuestions.classList.add('hidden');
    elements.resultsCard.classList.remove('hidden');
    elements.loadingState.classList.remove('hidden');
    elements.answerDisplay.classList.add('hidden');
    elements.errorState.classList.add('hidden');
    elements.submitBtn.disabled = true;
}

function displayAnswer(data, questionText = null) {
    elements.loadingState.classList.add('hidden');
    elements.answerDisplay.classList.remove('hidden');
    elements.errorState.classList.add('hidden');
    elements.submitBtn.disabled = false;

    // Display the question text above the answer
    if (questionText) {
        currentQuestionText = questionText;
    }
    if (elements.questionTextDisplay && currentQuestionText) {
        elements.questionTextDisplay.textContent = currentQuestionText;
    }

    elements.answerText.innerHTML = formatAnswer(data.answer_text);

    // Display pro tips
    if (data.pro_tips && data.pro_tips.length > 0) {
        elements.proTips.classList.remove('hidden');
        elements.tipsList.innerHTML = data.pro_tips.map(tip =>
            `<div class="tip-item">${tip}</div>`
        ).join('');
    } else {
        elements.proTips.classList.add('hidden');
    }

    // Display relevant images
    displayRelevantImages(data.relevant_images || []);
}

function showError(message) {
    elements.loadingState.classList.add('hidden');
    elements.answerDisplay.classList.add('hidden');
    elements.errorState.classList.remove('hidden');
    elements.errorMessage.textContent = message;
    elements.submitBtn.disabled = false;
}

function formatAnswer(text) {
    // Basic markdown-like formatting
    return text
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        .replace(/`([^`]+)`/g, '<code>$1</code>');
}

async function copyAnswer() {
    const text = elements.answerText.textContent;
    try {
        await navigator.clipboard.writeText(text);
        showToast('Answer copied to clipboard', 'success');
    } catch (error) {
        showToast('Failed to copy answer', 'error');
    }
}

// History Functions
async function loadHistory() {
    try {
        const data = await apiRequest('/questions');
        displayHistory(data.questions || []);
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

function displayHistory(questions) {
    if (questions.length === 0) {
        elements.historyList.innerHTML = '<p class="empty-state">No questions yet</p>';
        return;
    }

    elements.historyList.innerHTML = questions.map(q => `
        <div class="history-item ${q.id === currentQuestionId ? 'active' : ''}"
             data-id="${q.id}"
             title="${escapeHtml(q.question_text)}">
            ${escapeHtml(q.question_text)}
        </div>
    `).join('');

    // Add click handlers
    elements.historyList.querySelectorAll('.history-item').forEach(item => {
        item.addEventListener('click', () => loadQuestion(item.dataset.id));
    });
}

async function loadQuestion(id) {
    try {
        const data = await apiRequest(`/questions/${id}`);
        currentQuestionId = parseInt(id);
        currentSources = data.answer?.source_links || [];

        elements.sampleQuestions.classList.add('hidden');
        elements.resultsCard.classList.remove('hidden');

        if (data.answer) {
            displayAnswer(data.answer, data.question_text);
        }

        // Update active state in history
        elements.historyList.querySelectorAll('.history-item').forEach(item => {
            item.classList.toggle('active', item.dataset.id === id.toString());
        });
    } catch (error) {
        showToast('Failed to load question', 'error');
    }
}

async function clearHistory() {
    try {
        await apiRequest('/questions', { method: 'DELETE' });
        await loadHistory();
        currentQuestionId = null;
        elements.resultsCard.classList.add('hidden');
        elements.sampleQuestions.classList.remove('hidden');
        showToast('History cleared', 'success');
    } catch (error) {
        showToast('Failed to clear history', 'error');
    }
}

// Sources Modal
function showSourcesModal() {
    if (currentSources.length === 0) {
        elements.sourcesList.innerHTML = '<li>No source links available</li>';
    } else {
        elements.sourcesList.innerHTML = currentSources.map(url =>
            `<li><a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(url)}</a></li>`
        ).join('');
    }
    showModal(elements.sourcesModal);
}

// Scraper Functions
async function loadScraperStats() {
    try {
        const data = await apiRequest('/scraper/stats');
        elements.pagesCount.textContent = data.total_pages || 0;
        elements.chunksCount.textContent = data.total_chunks || 0;
        elements.lastUpdated.textContent = data.last_full_scrape
            ? formatDate(data.last_full_scrape)
            : 'Never';
        elements.scraperStatusText.textContent = `Knowledge base: ${data.total_pages || 0} pages, ${data.total_chunks || 0} chunks`;

        // Display per-category stats
        if (data.by_category && Object.keys(data.by_category).length > 0) {
            elements.categoryStats.innerHTML = '<h4>By Category:</h4>' +
                Object.entries(data.by_category).map(([cat, stats]) => {
                    const catName = categories[cat]?.name || cat;
                    return `<p><strong>${escapeHtml(catName)}:</strong> ${stats.pages || 0} pages, ${stats.chunks || 0} chunks</p>`;
                }).join('');
        } else {
            elements.categoryStats.innerHTML = '';
        }
    } catch (error) {
        console.error('Failed to load scraper stats:', error);
    }
}

async function startScrape() {
    try {
        const category = elements.scrapeCategorySelect.value;
        const maxPages = parseInt(elements.scrapeMaxPages.value) || 1500;
        await apiRequest('/scraper/start', {
            method: 'POST',
            body: JSON.stringify({ category, max_pages: maxPages })
        });
        elements.scraperProgress.classList.remove('hidden');
        elements.startScrapeBtn.disabled = true;
        const catName = categories[category]?.name || category;
        showToast(`Starting scrape for ${catName} (${maxPages} pages)...`, 'success');
        pollScrapeStatus();
    } catch (error) {
        showToast('Failed to start scrape', 'error');
    }
}

async function pollScrapeStatus() {
    try {
        const data = await apiRequest('/scraper/status');

        if (data.in_progress) {
            elements.progressFill.style.width = `${data.progress || 0}%`;
            elements.progressText.textContent = data.status_text || 'Scraping...';
            setTimeout(pollScrapeStatus, 2000);
        } else {
            elements.scraperProgress.classList.add('hidden');
            elements.startScrapeBtn.disabled = false;
            await loadScraperStats();
            showToast('Scraping complete', 'success');
        }
    } catch (error) {
        elements.scraperProgress.classList.add('hidden');
        elements.startScrapeBtn.disabled = false;
        showToast('Scrape status check failed', 'error');
    }
}

async function resetKnowledgeBase() {
    try {
        await apiRequest('/reset', { method: 'POST' });
        await loadScraperStats();
        showToast('Knowledge base reset', 'success');
    } catch (error) {
        showToast('Failed to reset knowledge base', 'error');
    }
}

// Export Function
async function exportHistory() {
    try {
        const response = await fetch(`${API_BASE}/export`);
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `wcinspector-export-${formatDateFilename(new Date())}.json`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        showToast('Export downloaded', 'success');
    } catch (error) {
        showToast('Failed to export history', 'error');
    }
}

// Models Function
async function loadModels() {
    try {
        const data = await apiRequest('/models');
        if (data.models && data.models.length > 0) {
            elements.modelSelect.innerHTML = data.models.map(model =>
                `<option value="${model}">${model}</option>`
            ).join('');
            if (settings.ollama_model) {
                elements.modelSelect.value = settings.ollama_model;
            }
        } else {
            elements.modelSelect.innerHTML = '<option value="">No models available</option>';
        }
    } catch (error) {
        console.error('Failed to load models:', error);
        elements.modelSelect.innerHTML = '<option value="">Unable to load models</option>';
    }
}

// Topics Functions
async function loadTopics(category = null) {
    try {
        // Build URL with optional category parameter
        const url = category ? `/topics?category=${encodeURIComponent(category)}` : '/topics';
        const data = await apiRequest(url);
        if (data.topics && data.topics.length > 0) {
            // Keep the "All Topics" option and add the rest
            elements.topicSelect.innerHTML = '<option value="">All Topics</option>' +
                data.topics.map(topic =>
                    `<option value="${escapeHtml(topic)}">${escapeHtml(topic)}</option>`
                ).join('');
        } else {
            elements.topicSelect.innerHTML = '<option value="">All Topics</option>';
        }
    } catch (error) {
        console.error('Failed to load topics:', error);
        // Keep default option if topics can't be loaded
        elements.topicSelect.innerHTML = '<option value="">All Topics</option>';
    }
}

function getSelectedTopicFilter() {
    return elements.topicSelect.value || null;
}

function updateTopicFilterStatus(topicApplied) {
    // Status is now shown via toast notification instead of inline text
    if (topicApplied) {
        console.log(`Topic filter applied: ${topicApplied}`);
    }
}

async function handleTopicFilterChange() {
    // Only re-run if we have a current question
    if (!currentQuestionId) {
        return;
    }

    const topicFilter = getSelectedTopicFilter();
    showLoading();

    try {
        const data = await apiRequest(`/questions/${currentQuestionId}/rerun`, {
            method: 'POST',
            body: JSON.stringify({ topic_filter: topicFilter })
        });

        currentSources = data.source_links || [];
        displayAnswer(data);
        updateTopicFilterStatus(data.topic_filter_applied);
        showToast(topicFilter ? `Filtered by: ${topicFilter}` : 'Showing all topics', 'success');
    } catch (error) {
        showError(error.message);
    }
}

// Categories Functions
async function loadCategories() {
    console.log('loadCategories called');
    console.log('categorySelect element:', elements.categorySelect);
    try {
        const data = await apiRequest('/categories');
        console.log('API response:', data);
        categories = data.categories || {};

        console.log('Categories object:', categories);
        console.log('Categories entries:', Object.entries(categories));

        // Populate category select dropdown
        const categoryOptions = Object.entries(categories).map(([key, cat]) => {
            console.log('Processing category:', key, cat);
            return `<option value="${escapeHtml(key)}">${escapeHtml(cat.name)}</option>`;
        }).join('');

        console.log('Category options HTML:', categoryOptions);

        if (elements.categorySelect) {
            elements.categorySelect.innerHTML = '<option value="">All Categories</option>' + categoryOptions;
            console.log('Updated categorySelect innerHTML');
        } else {
            console.error('categorySelect element is null!');
        }

        if (elements.scrapeCategorySelect) {
            elements.scrapeCategorySelect.innerHTML = categoryOptions;
        }

        // Update sample questions visibility based on category
        updateSampleQuestions();
    } catch (error) {
        console.error('Failed to load categories:', error);
        if (elements.categorySelect) {
            elements.categorySelect.innerHTML = '<option value="">All Categories</option>';
        }
    }
}

function getSelectedCategory() {
    return elements.categorySelect.value || null;
}

async function handleCategoryChange() {
    const category = getSelectedCategory();

    // Update sample questions visibility
    updateSampleQuestions();

    // Update placeholder text based on category
    if (category && categories[category]) {
        elements.questionInput.placeholder = `Ask a question about ${categories[category].name}...`;
    } else {
        elements.questionInput.placeholder = 'Ask a question...';
    }

    // Reload topics for the selected category
    await loadTopics(category);
}

function updateSampleQuestions() {
    const selectedCategory = getSelectedCategory();
    const sampleBtns = elements.sampleList.querySelectorAll('.sample-btn');

    sampleBtns.forEach(btn => {
        const btnCategory = btn.dataset.category;
        if (!selectedCategory || btnCategory === selectedCategory) {
            btn.style.display = '';
        } else {
            btn.style.display = 'none';
        }
    });
}

// Utility Functions
function showModal(modal) {
    modal.classList.remove('hidden');
}

function showConfirm(title, message, callback) {
    elements.confirmTitle.textContent = title;
    elements.confirmMessage.textContent = message;
    confirmCallback = callback;
    showModal(elements.confirmModal);
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function formatDateFilename(date) {
    return date.toISOString().split('T')[0];
}

// Image Functions
function displayRelevantImages(images) {
    if (!elements.relatedImages || !elements.imagesList) {
        return;
    }

    currentImages = images || [];

    if (currentImages.length === 0) {
        elements.relatedImages.classList.add('hidden');
        return;
    }

    elements.relatedImages.classList.remove('hidden');
    elements.imagesList.innerHTML = currentImages.map((img, index) => {
        const altText = escapeHtml(img.alt_text || img.caption || 'Documentation image');
        const caption = img.caption || img.alt_text || '';
        return `
            <div class="image-item" data-index="${index}" onclick="showImageLightbox(${index})">
                <img src="${escapeHtml(img.url)}" alt="${altText}" loading="lazy" onerror="this.parentElement.style.display='none'">
                <div class="image-overlay">
                    <div class="image-overlay-text">${escapeHtml(caption)}</div>
                </div>
            </div>
        `;
    }).join('');
}

function showImageLightbox(index) {
    if (!elements.lightboxModal || !currentImages || currentImages.length === 0) {
        return;
    }

    currentImageIndex = index;
    updateLightboxImage();
    elements.lightboxModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeLightbox() {
    if (!elements.lightboxModal) {
        return;
    }

    elements.lightboxModal.classList.add('hidden');
    document.body.style.overflow = '';
}

function navigateLightbox(direction) {
    if (!currentImages || currentImages.length === 0) {
        return;
    }

    currentImageIndex += direction;

    // Wrap around
    if (currentImageIndex < 0) {
        currentImageIndex = currentImages.length - 1;
    } else if (currentImageIndex >= currentImages.length) {
        currentImageIndex = 0;
    }

    updateLightboxImage();
}

function updateLightboxImage() {
    if (!elements.lightboxImage || !elements.lightboxCaption) {
        return;
    }

    const img = currentImages[currentImageIndex];
    if (!img) {
        return;
    }

    elements.lightboxImage.src = img.url;
    elements.lightboxImage.alt = img.alt_text || img.caption || 'Documentation image';

    // Build caption
    let captionHtml = '';
    if (img.alt_text) {
        captionHtml += `<div class="lightbox-caption-title">${escapeHtml(img.alt_text)}</div>`;
    }
    if (img.caption && img.caption !== img.alt_text) {
        captionHtml += `<div class="lightbox-caption-text">${escapeHtml(img.caption)}</div>`;
    }
    if (img.page_title) {
        captionHtml += `<div class="lightbox-caption-text">From: ${escapeHtml(img.page_title)}</div>`;
    }

    // Show image count
    captionHtml += `<div class="lightbox-caption-text">${currentImageIndex + 1} of ${currentImages.length}</div>`;

    elements.lightboxCaption.innerHTML = captionHtml;

    // Update nav button visibility
    if (elements.lightboxPrev && elements.lightboxNext) {
        const showNav = currentImages.length > 1;
        elements.lightboxPrev.style.display = showNav ? '' : 'none';
        elements.lightboxNext.style.display = showNav ? '' : 'none';
    }
}

// Make showImageLightbox globally accessible for onclick
window.showImageLightbox = showImageLightbox;
