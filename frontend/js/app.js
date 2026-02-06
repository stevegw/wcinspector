/**
 * WCInspector - Windchill Knowledge Base
 * Main JavaScript Application
 */

// API Base URL
const API_BASE = '/api';

// State
let currentQuestionId = null;
let categories = {};
let importJustStarted = false;  // Flag to prevent premature progress hiding
let importWaitCount = 0;        // Counter for waiting for import to start
let currentBrowserPath = null;  // Current folder browser path
let currentBrowserFiles = [];   // Files in current folder
let selectedBrowserFiles = new Set();  // Selected files for import
let settings = {
    theme: 'light',
    ai_tone: 'technical',
    response_length: 'detailed',
    ollama_model: 'llama2',
    llm_provider: 'groq',
    groq_model: 'llama-3.1-8b-instant'
};

// Course state
let courses = [];
let currentCourse = null;
let currentLessonId = null;
let editingCourseId = null;  // Course ID being edited (null for new)
let notesTimeout = null;  // Debounce timer for auto-save notes

// Text-to-speech state
let speechSynthesis = window.speechSynthesis;
let currentUtterance = null;
let isSpeaking = false;
let availableVoices = [];
let voiceSettings = {
    voiceName: '',
    rate: 1.0,
    pitch: 1.0
};

// DOM Elements
const elements = {
    // App Loading
    appLoading: document.getElementById('app-loading'),

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
    mainTopicSuggestions: document.getElementById('main-topic-suggestions'),
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
    listenBtn: document.getElementById('listen-btn'),
    voiceSettingsBtn: document.getElementById('voice-settings-btn'),
    voiceSettingsPopup: document.getElementById('voice-settings-popup'),
    voiceSelect: document.getElementById('voice-select'),
    speechRate: document.getElementById('speech-rate'),
    speechRateValue: document.getElementById('speech-rate-value'),
    speechPitch: document.getElementById('speech-pitch'),
    speechPitchValue: document.getElementById('speech-pitch-value'),
    copyBtn: document.getElementById('copy-btn'),
    rerunBtn: document.getElementById('rerun-btn'),
    moreBtn: document.getElementById('more-btn'),
    retryBtn: document.getElementById('retry-btn'),

    // History & Sidebar
    historySidebar: document.getElementById('history-sidebar'),
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
    groqModelGroup: document.getElementById('groq-model-group'),
    groqModelSelect: document.getElementById('groq-model-select'),
    ollamaModelGroup: document.getElementById('ollama-model-group'),
    modelSelect: document.getElementById('model-select'),
    resetSettingsBtn: document.getElementById('reset-settings-btn'),
    saveSettingsBtn: document.getElementById('save-settings-btn'),

    // Sources Modal
    sourcesModal: document.getElementById('sources-modal'),
    sourcesList: document.getElementById('sources-list'),

    // Documents Modal
    documentsBtn: document.getElementById('documents-btn'),
    documentsModal: document.getElementById('documents-modal'),
    documentsList: document.getElementById('documents-list'),
    docsSearch: document.getElementById('docs-search'),
    docsTypeFilter: document.getElementById('docs-type-filter'),
    docsCategoryFilter: document.getElementById('docs-category-filter'),
    docsCount: document.getElementById('docs-count'),

    // Admin Button (header)
    adminBtn: document.getElementById('admin-btn'),

    // Scraper Modal
    scraperModal: document.getElementById('scraper-modal'),
    pagesCount: document.getElementById('pages-count'),
    chunksCount: document.getElementById('chunks-count'),
    lastUpdated: document.getElementById('last-updated'),
    categoryStats: document.getElementById('category-stats'),
    scraperProgress: document.getElementById('scraper-progress'),
    progressFill: document.getElementById('progress-fill'),
    progressText: document.getElementById('progress-text'),
    cancelScrapeBtn: document.getElementById('cancel-scrape-btn'),
    scrapeCategorySelect: document.getElementById('scrape-category-select'),
    scrapeMaxPages: document.getElementById('scrape-max-pages'),
    startScrapeBtn: document.getElementById('start-scrape-btn'),
    clearCategoryBtn: document.getElementById('clear-category-btn'),
    importDocsBtn: document.getElementById('import-docs-btn'),
    exportBtn: document.getElementById('export-btn'),

    // Import Modal
    importModal: document.getElementById('import-modal'),
    importCategorySelect: document.getElementById('import-category-select'),
    importCategoryNew: document.getElementById('import-category-new'),
    importCancelBtn: document.getElementById('import-cancel-btn'),
    importStartBtn: document.getElementById('import-start-btn'),
    resetKbBtn: document.getElementById('reset-kb-btn'),
    browserUpBtn: document.getElementById('browser-up-btn'),
    browserPath: document.getElementById('browser-path'),
    browserDrives: document.getElementById('browser-drives'),
    browserContent: document.getElementById('browser-content'),
    browserFileCount: document.getElementById('browser-file-count'),
    browserSelectedCount: document.getElementById('browser-selected-count'),
    browserSelectAll: document.getElementById('browser-select-all'),
    selectAllFiles: document.getElementById('select-all-files'),

    // Confirm Modal
    confirmModal: document.getElementById('confirm-modal'),
    confirmTitle: document.getElementById('confirm-title'),
    confirmMessage: document.getElementById('confirm-message'),
    confirmCancel: document.getElementById('confirm-cancel'),
    confirmOk: document.getElementById('confirm-ok'),

    // Internal Login Modal
    internalLoginModal: document.getElementById('internal-login-modal'),
    internalUsername: document.getElementById('internal-username'),
    internalPassword: document.getElementById('internal-password'),
    testLoginBtn: document.getElementById('test-login-btn'),
    saveCredentialsBtn: document.getElementById('save-credentials-btn'),
    loginError: document.getElementById('login-error'),
    loginSuccess: document.getElementById('login-success'),

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
    lightboxNext: document.getElementById('lightbox-next'),

    // Courses
    courseList: document.getElementById('course-list'),
    newCourseBtn: document.getElementById('new-course-btn'),
    courseModal: document.getElementById('course-modal'),
    courseModalTitle: document.getElementById('course-modal-title'),
    courseTopic: document.getElementById('course-topic'),
    courseCategory: document.getElementById('course-category'),
    courseTypeQuestions: document.getElementById('course-type-questions'),
    courseTypeLessons: document.getElementById('course-type-lessons'),
    courseNumItems: document.getElementById('course-num-items'),
    numItemsLabel: document.getElementById('num-items-label'),
    cancelCourseBtn: document.getElementById('cancel-course-btn'),
    generateCourseBtn: document.getElementById('generate-course-btn'),
    aiCourseForm: document.getElementById('ai-course-form'),
    aiGenerating: document.getElementById('ai-generating'),
    topicSuggestionsList: document.getElementById('topic-suggestions-list'),

    // Course Viewer
    courseViewer: document.getElementById('course-viewer'),
    backToMainBtn: document.getElementById('back-to-main-btn'),
    courseViewerTitle: document.getElementById('course-viewer-title'),
    courseViewerDescription: document.getElementById('course-viewer-description'),
    deleteCourseBtn: document.getElementById('delete-course-btn'),
    courseProgressText: document.getElementById('course-progress-text'),
    courseProgressFill: document.getElementById('course-progress-fill'),
    lessonList: document.getElementById('lesson-list'),
    lessonContent: document.getElementById('lesson-content'),
    lessonNumber: document.getElementById('lesson-number'),
    lessonTitle: document.getElementById('lesson-title'),
    lessonSourceLink: document.getElementById('lesson-source-link'),
    lessonPageContent: document.getElementById('lesson-page-content'),
    learnerNotes: document.getElementById('learner-notes'),
    notesSaveStatus: document.getElementById('notes-save-status'),
    prevLessonBtn: document.getElementById('prev-lesson-btn'),
    markCompleteBtn: document.getElementById('mark-complete-btn'),
    nextLessonBtn: document.getElementById('next-lesson-btn'),
    mainPanel: document.querySelector('.main-panel')
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
    // Determine user state first (before any async operations)
    // Set appropriate body class immediately (hidden behind loading overlay)
    const isReturningUser = localStorage.getItem('hasUsedApp') === 'true';
    if (!isReturningUser) {
        document.body.classList.add('clean-slate');
    }

    // Load settings
    await loadSettings();

    // Apply theme
    applyTheme(settings.theme);

    // Load categories first (needed for other components)
    await loadCategories();

    // Load history
    await loadHistory();

    // Load courses
    await loadCourses();

    // Load scraper stats
    await loadScraperStats();

    // Check if scrape/import is in progress and resume polling
    await checkScraperStatus();

    // Load available models
    await loadModels();

    // Load AI-suggested topics for main screen
    loadMainTopicSuggestions();

    // Setup event listeners
    setupEventListeners();

    // Hide loading overlay after all initialization
    if (elements.appLoading) {
        elements.appLoading.classList.add('hidden');
        // Remove from DOM after fade transition
        setTimeout(() => elements.appLoading.remove(), 300);
    }
}

function setupEventListeners() {
    // Question Form
    elements.questionForm.addEventListener('submit', handleQuestionSubmit);
    elements.clearInputBtn.addEventListener('click', () => {
        elements.questionInput.value = '';
        elements.questionInput.focus();
    });

    // Exit clean slate on input focus
    elements.questionInput.addEventListener('focus', exitCleanSlate);

    // Sidebar toggle - always starts expanded, user can collapse during session
    const sidebarToggle = document.getElementById('sidebar-toggle');
    if (sidebarToggle) {
        // Ensure sidebar starts expanded
        elements.historySidebar.classList.remove('collapsed');

        sidebarToggle.addEventListener('click', () => {
            elements.historySidebar.classList.toggle('collapsed');
        });
    }

    // Category selector
    elements.categorySelect.addEventListener('change', handleCategoryChange);

    // Sample Questions
    document.querySelectorAll('.sample-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            exitCleanSlate();
            const category = btn.dataset.category;
            if (category) {
                elements.categorySelect.value = category;
            }
            elements.questionInput.value = btn.textContent;
            elements.questionInput.focus();
        });
    });

    // Answer Actions
    elements.listenBtn.addEventListener('click', toggleSpeech);
    elements.voiceSettingsBtn.addEventListener('click', toggleVoiceSettings);
    elements.voiceSelect.addEventListener('change', handleVoiceChange);
    elements.speechRate.addEventListener('input', handleRateChange);
    elements.speechPitch.addEventListener('input', handlePitchChange);

    // Close voice settings when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.listen-controls')) {
            elements.voiceSettingsPopup.classList.add('hidden');
        }
    });

    // Initialize voices
    initVoices();

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
    elements.providerSelect.addEventListener('change', updateModelGroupVisibility);
    elements.resetSettingsBtn.addEventListener('click', resetSettings);
    elements.saveSettingsBtn.addEventListener('click', saveSettings);

    // Documents Modal
    elements.documentsBtn.addEventListener('click', openDocumentsModal);
    elements.docsSearch.addEventListener('input', filterDocuments);
    elements.docsTypeFilter.addEventListener('change', loadDocuments);
    elements.docsCategoryFilter.addEventListener('change', filterDocuments);

    // Admin (opens Scraper/KB Management modal)
    elements.adminBtn.addEventListener('click', () => showModal(elements.scraperModal));
    elements.startScrapeBtn.addEventListener('click', startScrape);
    elements.cancelScrapeBtn.addEventListener('click', cancelScrape);
    elements.clearCategoryBtn.addEventListener('click', clearSelectedCategory);
    elements.importDocsBtn.addEventListener('click', showImportModal);
    elements.exportBtn.addEventListener('click', exportHistory);

    // Import Modal
    elements.importCancelBtn.addEventListener('click', () => elements.importModal.classList.add('hidden'));
    elements.importStartBtn.addEventListener('click', startDocumentImport);
    elements.selectAllFiles.addEventListener('change', (e) => toggleSelectAllFiles(e.target.checked));
    elements.importCategorySelect.addEventListener('change', () => {
        // Clear new category input when selecting existing
        if (elements.importCategorySelect.value) {
            elements.importCategoryNew.value = '';
        }
    });
    elements.importCategoryNew.addEventListener('input', () => {
        // Clear dropdown when typing new category
        if (elements.importCategoryNew.value) {
            elements.importCategorySelect.value = '';
        }
    });
    elements.resetKbBtn.addEventListener('click', () => {
        showConfirm(
            'Reset Knowledge Base',
            'Are you sure you want to reset the knowledge base? All scraped data will be deleted.',
            resetKnowledgeBase
        );
    });

    // Folder Browser
    elements.browserUpBtn.addEventListener('click', browserGoUp);

    // Internal Login Modal
    if (elements.testLoginBtn) {
        elements.testLoginBtn.addEventListener('click', testInternalLogin);
    }
    if (elements.saveCredentialsBtn) {
        elements.saveCredentialsBtn.addEventListener('click', saveInternalCredentials);
    }
    // Allow Enter key to submit login
    if (elements.internalPassword) {
        elements.internalPassword.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                saveInternalCredentials();
            }
        });
    }

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

    // Course event listeners
    if (elements.newCourseBtn) {
        console.log('Adding click listener to newCourseBtn');
        elements.newCourseBtn.addEventListener('click', () => {
            console.log('New Course button clicked');
            showCourseModal();
        });
    } else {
        console.error('newCourseBtn not found!');
    }
    if (elements.cancelCourseBtn) {
        elements.cancelCourseBtn.addEventListener('click', () => {
            elements.courseModal.classList.add('hidden');
        });
    }
    if (elements.generateCourseBtn) {
        elements.generateCourseBtn.addEventListener('click', generateAICourse);
    }
    if (elements.courseTypeQuestions) {
        elements.courseTypeQuestions.addEventListener('change', updateCourseTypeUI);
    }
    if (elements.courseTypeLessons) {
        elements.courseTypeLessons.addEventListener('change', updateCourseTypeUI);
    }
    // Refresh topic suggestions when category changes
    if (elements.courseCategory) {
        elements.courseCategory.addEventListener('change', fetchTopicSuggestions);
    }

    // Course Viewer event listeners
    if (elements.backToMainBtn) {
        elements.backToMainBtn.addEventListener('click', closeCourseViewer);
    }
    if (elements.deleteCourseBtn) {
        elements.deleteCourseBtn.addEventListener('click', () => {
            if (currentCourse) {
                showConfirm(
                    'Delete Course',
                    `Are you sure you want to delete "${currentCourse.title}"? This cannot be undone.`,
                    async () => {
                        await deleteCourse(currentCourse.id);
                        closeCourseViewer();
                    }
                );
            }
        });
    }
    if (elements.prevLessonBtn) {
        elements.prevLessonBtn.addEventListener('click', () => navigateLesson(-1));
    }
    if (elements.nextLessonBtn) {
        elements.nextLessonBtn.addEventListener('click', () => navigateLesson(1));
    }
    if (elements.markCompleteBtn) {
        elements.markCompleteBtn.addEventListener('click', toggleLessonComplete);
    }
    if (elements.learnerNotes) {
        elements.learnerNotes.addEventListener('input', handleNotesChange);
    }
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
        // Handle FastAPI validation errors (detail can be an array)
        let message = 'An error occurred';
        if (error.detail) {
            if (Array.isArray(error.detail)) {
                message = error.detail.map(e => e.msg || e).join(', ');
            } else {
                message = error.detail;
            }
        } else if (error.error) {
            message = error.error;
        }
        throw new Error(message);
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
    if (settings.groq_model) {
        elements.groqModelSelect.value = settings.groq_model;
    }
    if (settings.ollama_model) {
        elements.modelSelect.value = settings.ollama_model;
    }
    // Show/hide model groups based on provider
    updateModelGroupVisibility();
}

function updateModelGroupVisibility() {
    const provider = elements.providerSelect.value;
    if (provider === 'groq') {
        elements.groqModelGroup.classList.remove('hidden');
        elements.ollamaModelGroup.classList.add('hidden');
    } else {
        elements.groqModelGroup.classList.add('hidden');
        elements.ollamaModelGroup.classList.remove('hidden');
    }
}

async function saveSettings() {
    settings.ai_tone = elements.toneSelect.value;
    settings.response_length = elements.lengthSelect.value;
    settings.llm_provider = elements.providerSelect.value;
    settings.groq_model = elements.groqModelSelect.value;
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

    // Exit clean slate mode on first question
    exitCleanSlate();

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

        // Track questions for badges
        const questionsAsked = parseInt(localStorage.getItem('questionsAsked') || '0') + 1;
        localStorage.setItem('questionsAsked', questionsAsked.toString());
        checkBadgeEligibility();
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
        // Get topic filter and category if selected
        const topicFilter = getSelectedTopicFilter();
        const category = getSelectedCategory();

        const data = await apiRequest(`/questions/${currentQuestionId}/rerun`, {
            method: 'POST',
            body: JSON.stringify({ topic_filter: topicFilter, category })
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

// Procedure Tracker - detect and parse procedural steps
function detectProceduralSteps(text) {
    const lines = text.split('\n');
    const steps = [];
    let currentStep = null;

    for (const line of lines) {
        const trimmed = line.trim();
        // Match numbered steps like "1." or "1)" or "Step 1:"
        const stepMatch = trimmed.match(/^(?:Step\s+)?(\d+)[.):]\s*(.+)$/i);

        if (stepMatch) {
            if (currentStep) {
                steps.push(currentStep);
            }
            currentStep = {
                number: parseInt(stepMatch[1]),
                text: stepMatch[2].replace(/\*\*/g, ''), // Remove bold markers
                details: ''
            };
        } else if (currentStep && trimmed && !trimmed.match(/^[-•]/)) {
            // Add as detail to current step
            currentStep.details += (currentStep.details ? ' ' : '') + trimmed;
        }
    }

    if (currentStep) {
        steps.push(currentStep);
    }

    // Only return if we have 3+ ordered steps
    return steps.length >= 3 ? steps : null;
}

function createProcedureTracker(steps, questionId) {
    const trackerId = `procedure-${questionId}`;
    const savedProgress = JSON.parse(localStorage.getItem(trackerId) || '{}');

    const completedCount = Object.values(savedProgress).filter(Boolean).length;
    const progressPercent = Math.round((completedCount / steps.length) * 100);

    const stepsHtml = steps.map((step, index) => {
        const isCompleted = savedProgress[index] === true;
        return `
            <div class="procedure-step ${isCompleted ? 'completed' : ''}" data-index="${index}">
                <div class="step-checkbox" title="Mark as complete">
                    ${isCompleted ? '✓' : ''}
                </div>
                <div class="step-number">${step.number}</div>
                <div class="step-content">
                    <div class="step-text">${escapeHtml(step.text)}</div>
                    ${step.details ? `<button class="step-expand">Show details</button><div class="step-details">${escapeHtml(step.details)}</div>` : ''}
                </div>
            </div>
        `;
    }).join('');

    return `
        <div class="procedure-tracker" id="${trackerId}" data-question-id="${questionId}">
            <div class="procedure-header">
                <h4>📋 Procedure Tracker</h4>
                <div class="procedure-progress">
                    <span class="progress-text">${completedCount} of ${steps.length}</span>
                    <div class="procedure-progress-bar">
                        <div class="procedure-progress-fill" style="width: ${progressPercent}%"></div>
                    </div>
                </div>
            </div>
            <div class="procedure-steps">
                ${stepsHtml}
            </div>
            ${completedCount === steps.length ? `
                <div class="procedure-complete">
                    <h4>🎉 All steps completed!</h4>
                    <p>Great job finishing this procedure.</p>
                </div>
            ` : ''}
        </div>
    `;
}

function initProcedureTracker(container) {
    const tracker = container.querySelector('.procedure-tracker');
    if (!tracker) return;

    const questionId = tracker.dataset.questionId;
    const trackerId = tracker.id;

    // Handle step checkbox clicks
    tracker.querySelectorAll('.step-checkbox').forEach(checkbox => {
        checkbox.addEventListener('click', () => {
            const step = checkbox.closest('.procedure-step');
            const index = parseInt(step.dataset.index);

            // Toggle completion
            step.classList.toggle('completed');
            const isCompleted = step.classList.contains('completed');
            checkbox.innerHTML = isCompleted ? '✓' : '';

            // Save progress
            const savedProgress = JSON.parse(localStorage.getItem(trackerId) || '{}');
            savedProgress[index] = isCompleted;
            localStorage.setItem(trackerId, JSON.stringify(savedProgress));

            // Update progress display
            const steps = tracker.querySelectorAll('.procedure-step');
            const completedCount = tracker.querySelectorAll('.procedure-step.completed').length;
            const progressPercent = Math.round((completedCount / steps.length) * 100);

            tracker.querySelector('.progress-text').textContent = `${completedCount} of ${steps.length}`;
            tracker.querySelector('.procedure-progress-fill').style.width = `${progressPercent}%`;

            // Show/hide completion message
            let completeMsg = tracker.querySelector('.procedure-complete');
            if (completedCount === steps.length && !completeMsg) {
                const stepsContainer = tracker.querySelector('.procedure-steps');
                stepsContainer.insertAdjacentHTML('afterend', `
                    <div class="procedure-complete">
                        <h4>🎉 All steps completed!</h4>
                        <p>Great job finishing this procedure.</p>
                    </div>
                `);
            } else if (completedCount < steps.length && completeMsg) {
                completeMsg.remove();
            }
        });
    });

    // Handle expand details
    tracker.querySelectorAll('.step-expand').forEach(btn => {
        btn.addEventListener('click', () => {
            const details = btn.nextElementSibling;
            details.classList.toggle('expanded');
            btn.textContent = details.classList.contains('expanded') ? 'Hide details' : 'Show details';
        });
    });
}

function displayAnswer(data, questionText = null) {
    // Stop any ongoing speech when showing new answer
    stopSpeech();

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

    // Check for procedural content
    const steps = detectProceduralSteps(data.answer_text);
    let answerHtml = formatAnswer(data.answer_text);

    if (steps && currentQuestionId) {
        // Add procedure tracker before the formatted answer
        const trackerHtml = createProcedureTracker(steps, currentQuestionId);
        answerHtml = trackerHtml + '<div class="answer-text-content">' + answerHtml + '</div>';
    }

    elements.answerText.innerHTML = answerHtml;

    // Initialize procedure tracker if present
    if (steps) {
        initProcedureTracker(elements.answerText);
    }

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
    // Enhanced markdown formatting for better readability
    let html = text;

    // Escape HTML first (except for our markdown)
    html = html.replace(/</g, '&lt;').replace(/>/g, '&gt;');

    // Headers: **Header:** at start of line becomes section header
    html = html.replace(/^\*\*([^*]+):\*\*/gm, '<h4 class="answer-section-title">$1</h4>');

    // Bold text: **text**
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Inline code: `code`
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Process lines for lists and paragraphs
    const lines = html.split('\n');
    let result = [];
    let inList = false;
    let listType = null; // 'ul' or 'ol'

    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();

        // Numbered list item: 1. or 1)
        const numberedMatch = line.match(/^(\d+)[.)]\s+(.+)$/);
        if (numberedMatch) {
            if (!inList || listType !== 'ol') {
                if (inList) result.push(listType === 'ul' ? '</ul>' : '</ol>');
                result.push('<ol class="answer-list">');
                inList = true;
                listType = 'ol';
            }
            result.push(`<li>${numberedMatch[2]}</li>`);
            continue;
        }

        // Bullet list item: - or •
        const bulletMatch = line.match(/^[-•]\s+(.+)$/);
        if (bulletMatch) {
            if (!inList || listType !== 'ul') {
                if (inList) result.push(listType === 'ul' ? '</ul>' : '</ol>');
                result.push('<ul class="answer-list">');
                inList = true;
                listType = 'ul';
            }
            result.push(`<li>${bulletMatch[1]}</li>`);
            continue;
        }

        // End list if we hit a non-list line
        if (inList && line !== '') {
            result.push(listType === 'ul' ? '</ul>' : '</ol>');
            inList = false;
            listType = null;
        }

        // Empty line = paragraph break
        if (line === '') {
            if (result.length > 0 && !result[result.length - 1].match(/<\/(ul|ol|h4)>$/)) {
                result.push('<br><br>');
            }
            continue;
        }

        // Regular text
        result.push(`<span class="answer-paragraph">${line}</span><br>`);
    }

    // Close any open list
    if (inList) {
        result.push(listType === 'ul' ? '</ul>' : '</ol>');
    }

    return result.join('\n');
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

// Text-to-Speech Functions
function initVoices() {
    // Load saved voice settings
    const saved = localStorage.getItem('voiceSettings');
    if (saved) {
        try {
            voiceSettings = JSON.parse(saved);
            elements.speechRate.value = voiceSettings.rate;
            elements.speechRateValue.textContent = voiceSettings.rate + 'x';
            elements.speechPitch.value = voiceSettings.pitch;
            elements.speechPitchValue.textContent = voiceSettings.pitch;
        } catch (e) {
            console.error('Failed to load voice settings:', e);
        }
    }

    // Voices may load asynchronously
    if (speechSynthesis) {
        populateVoices();
        speechSynthesis.onvoiceschanged = populateVoices;
    }
}

function populateVoices() {
    availableVoices = speechSynthesis.getVoices();

    // Sort voices: English first, then by name
    availableVoices.sort((a, b) => {
        const aEn = a.lang.startsWith('en');
        const bEn = b.lang.startsWith('en');
        if (aEn && !bEn) return -1;
        if (!aEn && bEn) return 1;
        return a.name.localeCompare(b.name);
    });

    // Populate dropdown
    elements.voiceSelect.innerHTML = '<option value="">Default</option>';
    availableVoices.forEach((voice, index) => {
        const option = document.createElement('option');
        option.value = voice.name;
        option.textContent = `${voice.name} (${voice.lang})`;
        if (voice.name === voiceSettings.voiceName) {
            option.selected = true;
        }
        elements.voiceSelect.appendChild(option);
    });
}

function toggleVoiceSettings(e) {
    e.stopPropagation();
    elements.voiceSettingsPopup.classList.toggle('hidden');
}

function handleVoiceChange() {
    voiceSettings.voiceName = elements.voiceSelect.value;
    saveVoiceSettings();
}

function handleRateChange() {
    voiceSettings.rate = parseFloat(elements.speechRate.value);
    elements.speechRateValue.textContent = voiceSettings.rate.toFixed(1) + 'x';
    saveVoiceSettings();
}

function handlePitchChange() {
    voiceSettings.pitch = parseFloat(elements.speechPitch.value);
    elements.speechPitchValue.textContent = voiceSettings.pitch.toFixed(1);
    saveVoiceSettings();
}

function saveVoiceSettings() {
    localStorage.setItem('voiceSettings', JSON.stringify(voiceSettings));
}

function toggleSpeech() {
    if (!speechSynthesis) {
        showToast('Text-to-speech not supported in this browser', 'error');
        return;
    }

    if (isSpeaking) {
        stopSpeech();
    } else {
        startSpeech();
    }
}

function startSpeech() {
    const text = elements.answerText.textContent;
    if (!text || text.trim() === '') {
        showToast('No answer to read', 'warning');
        return;
    }

    // Cancel any ongoing speech
    speechSynthesis.cancel();

    currentUtterance = new SpeechSynthesisUtterance(text);

    // Apply voice settings
    currentUtterance.rate = voiceSettings.rate;
    currentUtterance.pitch = voiceSettings.pitch;
    currentUtterance.volume = 1.0;

    // Use selected voice or find a good default
    if (voiceSettings.voiceName) {
        const selectedVoice = availableVoices.find(v => v.name === voiceSettings.voiceName);
        if (selectedVoice) {
            currentUtterance.voice = selectedVoice;
        }
    } else {
        // Default: prefer English voice
        const englishVoice = availableVoices.find(v => v.lang.startsWith('en') && v.localService) ||
                             availableVoices.find(v => v.lang.startsWith('en')) ||
                             availableVoices[0];
        if (englishVoice) {
            currentUtterance.voice = englishVoice;
        }
    }

    // Event handlers
    currentUtterance.onstart = () => {
        isSpeaking = true;
        updateListenButton();
    };

    currentUtterance.onend = () => {
        isSpeaking = false;
        updateListenButton();
    };

    currentUtterance.onerror = (event) => {
        console.error('Speech error:', event.error);
        isSpeaking = false;
        updateListenButton();
        if (event.error !== 'canceled' && event.error !== 'interrupted') {
            showToast('Speech error: ' + event.error, 'error');
        }
    };

    speechSynthesis.speak(currentUtterance);
}

function stopSpeech() {
    if (speechSynthesis) {
        speechSynthesis.cancel();
    }
    isSpeaking = false;
    updateListenButton();
}

function updateListenButton() {
    if (!elements.listenBtn) return;

    const icon = elements.listenBtn.querySelector('.icon');
    if (isSpeaking) {
        icon.textContent = '⏹️';
        elements.listenBtn.title = 'Stop listening';
        elements.listenBtn.classList.add('speaking');
    } else {
        icon.textContent = '🔊';
        elements.listenBtn.title = 'Listen to answer';
        elements.listenBtn.classList.remove('speaking');
    }
}

// Generic speech function for any element
function speakText(text, button = null) {
    if (!speechSynthesis) {
        showToast('Text-to-speech not supported in this browser', 'error');
        return;
    }

    if (!text || text.trim() === '') {
        showToast('No text to read', 'warning');
        return;
    }

    // Cancel any ongoing speech
    speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);

    // Apply voice settings
    utterance.rate = voiceSettings.rate;
    utterance.pitch = voiceSettings.pitch;
    utterance.volume = 1.0;

    // Use selected voice or find a good default
    if (voiceSettings.voiceName) {
        const selectedVoice = availableVoices.find(v => v.name === voiceSettings.voiceName);
        if (selectedVoice) {
            utterance.voice = selectedVoice;
        }
    } else {
        const englishVoice = availableVoices.find(v => v.lang.startsWith('en') && v.localService) ||
                             availableVoices.find(v => v.lang.startsWith('en')) ||
                             availableVoices[0];
        if (englishVoice) {
            utterance.voice = englishVoice;
        }
    }

    // Event handlers
    utterance.onstart = () => {
        isSpeaking = true;
        updateListenButton();
        if (button) {
            button.textContent = '⏹️ Stop';
            button.classList.add('speaking');
        }
    };

    utterance.onend = () => {
        isSpeaking = false;
        updateListenButton();
        if (button) {
            button.textContent = '🔊 Listen';
            button.classList.remove('speaking');
        }
    };

    utterance.onerror = (event) => {
        console.error('Speech error:', event.error);
        isSpeaking = false;
        updateListenButton();
        if (button) {
            button.textContent = '🔊 Listen';
            button.classList.remove('speaking');
        }
        if (event.error !== 'canceled' && event.error !== 'interrupted') {
            showToast('Speech error: ' + event.error, 'error');
        }
    };

    currentUtterance = utterance;
    speechSynthesis.speak(utterance);
}

// Toggle speech for document viewer content
function toggleViewerSpeech() {
    const btn = document.getElementById('viewer-listen-btn');

    if (isSpeaking) {
        stopSpeech();
        if (btn) {
            btn.textContent = '🔊 Listen';
            btn.classList.remove('speaking');
        }
    } else {
        const contentEl = document.getElementById('viewer-content');
        if (contentEl) {
            speakText(contentEl.textContent, btn);
        }
    }
}

// Toggle speech for summary content
function toggleSummarySpeech() {
    const btn = event.target;

    if (isSpeaking) {
        stopSpeech();
        if (btn) {
            btn.textContent = '🔊 Listen';
            btn.classList.remove('speaking');
        }
    } else {
        const summaryContent = document.querySelector('#viewer-summary .summary-content');
        if (summaryContent) {
            speakText(summaryContent.textContent, btn);
        }
    }
}

// Reset viewer listen button state
function resetViewerListenButton() {
    const btn = document.getElementById('viewer-listen-btn');
    if (btn) {
        btn.textContent = '🔊 Listen';
        btn.classList.remove('speaking');
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

        // Hide course viewer if open and show main panel
        if (elements.courseViewer) {
            elements.courseViewer.classList.add('hidden');
        }
        if (elements.mainPanel) {
            elements.mainPanel.classList.remove('hidden');
        }

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
        elements.sourcesList.innerHTML = currentSources.map(url => {
            if (url.startsWith('file://')) {
                // Local file - show view and summarize buttons
                const filename = url.split('/').pop();
                return `<li class="local-source">
                    <span class="source-label">📄 ${escapeHtml(filename)}</span>
                    <div class="source-actions">
                        <button class="btn btn-small view-local-btn" data-url="${escapeHtml(url)}">View</button>
                        <button class="btn btn-small btn-secondary summarize-btn" data-url="${escapeHtml(url)}">Summarize</button>
                    </div>
                </li>`;
            } else {
                // Remote URL - show as link
                return `<li><a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(url)}</a></li>`;
            }
        }).join('');

        // Add click handlers for local file view buttons
        elements.sourcesList.querySelectorAll('.view-local-btn').forEach(btn => {
            btn.addEventListener('click', () => viewLocalDocument(btn.dataset.url));
        });

        // Add click handlers for summarize buttons
        elements.sourcesList.querySelectorAll('.summarize-btn').forEach(btn => {
            btn.addEventListener('click', () => quickSummarize(btn.dataset.url, btn));
        });
    }
    showModal(elements.sourcesModal);
}

// View local document content
async function viewLocalDocument(url) {
    try {
        const data = await apiRequest(`/pages/by-url?url=${encodeURIComponent(url)}`);

        // Create a content viewer modal or use existing one
        const content = data.content || 'No content available';
        const title = data.title || 'Document';

        showDocumentViewer(title, content, url);
    } catch (error) {
        console.error('Failed to load document:', error);
        showToast('Failed to load document content', 'error');
    }
}

// Document viewer modal
let documentViewerContent = ''; // Store original content for search
let documentViewerUrl = null;   // Store URL for summarization

function showDocumentViewer(title, content, url = null) {
    // Check if viewer modal exists, if not create it
    let viewerModal = document.getElementById('document-viewer-modal');
    if (!viewerModal) {
        viewerModal = document.createElement('div');
        viewerModal.id = 'document-viewer-modal';
        viewerModal.className = 'modal hidden';
        viewerModal.innerHTML = `
            <div class="modal-content modal-wide">
                <div class="modal-header">
                    <h2 id="viewer-title">Document</h2>
                    <button class="modal-close" aria-label="Close">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="viewer-toolbar">
                        <div class="viewer-search-bar">
                            <input type="text" id="viewer-search-input" placeholder="Search in document..." />
                            <span id="viewer-search-count"></span>
                            <button class="btn btn-small" onclick="viewerSearchPrev()">↑</button>
                            <button class="btn btn-small" onclick="viewerSearchNext()">↓</button>
                            <button class="btn btn-small" onclick="viewerSearchClear()">Clear</button>
                        </div>
                        <div class="viewer-actions">
                            <button id="viewer-listen-btn" class="btn btn-small btn-secondary" onclick="toggleViewerSpeech()">🔊 Listen</button>
                            <button id="viewer-summarize-btn" class="btn btn-small btn-primary" onclick="summarizeDocument()">Summarize</button>
                        </div>
                    </div>
                    <div id="viewer-summary" class="viewer-summary hidden"></div>
                    <div id="viewer-content" class="document-viewer-content"></div>
                </div>
            </div>
        `;
        document.body.appendChild(viewerModal);

        // Add close handler
        viewerModal.querySelector('.modal-close').addEventListener('click', () => {
            stopSpeech();
            resetViewerListenButton();
            viewerModal.classList.add('hidden');
        });
        viewerModal.addEventListener('click', (e) => {
            if (e.target === viewerModal) {
                stopSpeech();
                resetViewerListenButton();
                viewerModal.classList.add('hidden');
            }
        });

        // Add search handler
        document.getElementById('viewer-search-input').addEventListener('input', (e) => {
            viewerSearch(e.target.value);
        });
        document.getElementById('viewer-search-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (e.shiftKey) viewerSearchPrev();
                else viewerSearchNext();
            }
        });
    }

    // Store content and URL, populate
    documentViewerContent = content;
    documentViewerUrl = url;
    document.getElementById('viewer-title').textContent = title;
    document.getElementById('viewer-content').innerHTML = formatLessonContent(content);
    document.getElementById('viewer-search-input').value = '';
    document.getElementById('viewer-search-count').textContent = '';

    // Reset summary section
    const summaryEl = document.getElementById('viewer-summary');
    if (summaryEl) {
        summaryEl.classList.add('hidden');
        summaryEl.innerHTML = '';
    }

    // Show/hide summarize button based on whether we have a URL
    const summarizeBtn = document.getElementById('viewer-summarize-btn');
    if (summarizeBtn) {
        summarizeBtn.style.display = url ? 'inline-block' : 'none';
        summarizeBtn.disabled = false;
        summarizeBtn.textContent = 'Summarize';
    }

    viewerModal.classList.remove('hidden');
}

// Summarize document using AI
async function summarizeDocument() {
    if (!documentViewerUrl) {
        showToast('Cannot summarize: no document URL', 'error');
        return;
    }

    const summarizeBtn = document.getElementById('viewer-summarize-btn');
    const summaryEl = document.getElementById('viewer-summary');

    // Show loading state
    summarizeBtn.disabled = true;
    summarizeBtn.textContent = 'Summarizing...';
    summaryEl.classList.remove('hidden');
    summaryEl.innerHTML = '<div class="summary-loading">Generating AI summary...</div>';

    try {
        const response = await apiRequest(`/pages/summarize-by-url?url=${encodeURIComponent(documentViewerUrl)}`, {
            method: 'POST'
        });

        if (response.error) {
            throw new Error(response.error);
        }

        // Display summary
        summaryEl.innerHTML = `
            <div class="summary-header">
                <strong>AI Summary</strong>
                <div class="summary-actions">
                    <button class="btn btn-small btn-secondary" onclick="toggleSummarySpeech()">🔊 Listen</button>
                    <button class="btn btn-small" onclick="document.getElementById('viewer-summary').classList.add('hidden')">Hide</button>
                </div>
            </div>
            <div class="summary-content">${formatLessonContent(response.summary)}</div>
        `;
        summarizeBtn.textContent = 'Summarize';
        summarizeBtn.disabled = false;
    } catch (error) {
        console.error('Failed to summarize:', error);
        summaryEl.innerHTML = `<div class="summary-error">Failed to generate summary: ${escapeHtml(error.message)}</div>`;
        summarizeBtn.textContent = 'Retry';
        summarizeBtn.disabled = false;
    }
}

// Quick summarize - shows summary in a modal without loading full document
async function quickSummarize(url, btn = null) {
    // Show loading state on button if provided
    const originalText = btn ? btn.textContent : '';
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Loading...';
    }

    try {
        const response = await apiRequest(`/pages/summarize-by-url?url=${encodeURIComponent(url)}`, {
            method: 'POST'
        });

        if (response.error) {
            throw new Error(response.error);
        }

        // Show summary in the document viewer
        showDocumentViewer(
            `Summary: ${response.title || 'Document'}`,
            response.summary,
            url
        );

        // Hide the original summary section since we're showing the summary as content
        const summaryEl = document.getElementById('viewer-summary');
        if (summaryEl) summaryEl.classList.add('hidden');

    } catch (error) {
        console.error('Failed to summarize:', error);
        showToast('Failed to generate summary: ' + error.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }
}

// Quick summarize by page ID
async function quickSummarizeById(pageId, btn = null) {
    const originalText = btn ? btn.textContent : '';
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Loading...';
    }

    try {
        const response = await apiRequest(`/pages/${pageId}/summarize`, {
            method: 'POST'
        });

        if (response.error) {
            throw new Error(response.error);
        }

        // Show summary in the document viewer
        showDocumentViewer(
            `Summary: ${response.title || 'Document'}`,
            response.summary,
            null
        );

    } catch (error) {
        console.error('Failed to summarize:', error);
        showToast('Failed to generate summary: ' + error.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }
}

// Search within document viewer
let viewerSearchMatches = [];
let viewerSearchIndex = -1;

function viewerSearch(query) {
    const contentEl = document.getElementById('viewer-content');
    const countEl = document.getElementById('viewer-search-count');

    if (!query || query.length < 2) {
        contentEl.innerHTML = formatLessonContent(documentViewerContent);
        countEl.textContent = '';
        viewerSearchMatches = [];
        viewerSearchIndex = -1;
        return;
    }

    // Format content then highlight matches
    let html = formatLessonContent(documentViewerContent);
    const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
    let matchCount = 0;

    html = html.replace(regex, (match) => {
        matchCount++;
        return `<mark class="search-highlight" data-match="${matchCount}">${match}</mark>`;
    });

    contentEl.innerHTML = html;
    viewerSearchMatches = contentEl.querySelectorAll('.search-highlight');
    viewerSearchIndex = viewerSearchMatches.length > 0 ? 0 : -1;

    countEl.textContent = matchCount > 0 ? `${matchCount} found` : 'No matches';

    if (viewerSearchIndex >= 0) {
        highlightCurrentMatch();
    }
}

function viewerSearchNext() {
    if (viewerSearchMatches.length === 0) return;
    viewerSearchIndex = (viewerSearchIndex + 1) % viewerSearchMatches.length;
    highlightCurrentMatch();
}

function viewerSearchPrev() {
    if (viewerSearchMatches.length === 0) return;
    viewerSearchIndex = (viewerSearchIndex - 1 + viewerSearchMatches.length) % viewerSearchMatches.length;
    highlightCurrentMatch();
}

function viewerSearchClear() {
    document.getElementById('viewer-search-input').value = '';
    document.getElementById('viewer-content').innerHTML = formatLessonContent(documentViewerContent);
    document.getElementById('viewer-search-count').textContent = '';
    viewerSearchMatches = [];
    viewerSearchIndex = -1;
}

function highlightCurrentMatch() {
    viewerSearchMatches.forEach((el, i) => {
        el.classList.toggle('current', i === viewerSearchIndex);
    });
    if (viewerSearchMatches[viewerSearchIndex]) {
        viewerSearchMatches[viewerSearchIndex].scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
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

async function checkScraperStatus() {
    // Check if a scrape/import is already in progress (e.g., after page refresh)
    try {
        const data = await apiRequest('/scraper/status');
        if (data.in_progress) {
            // Open the scraper modal and show progress UI
            showModal(elements.scraperModal);
            elements.scraperProgress.classList.remove('hidden');
            elements.progressFill.style.width = `${data.progress || 0}%`;
            elements.progressText.textContent = data.status_text || 'Processing...';
            elements.startScrapeBtn.disabled = true;
            elements.importDocsBtn.disabled = true;
            elements.cancelScrapeBtn.classList.remove('hidden');
            // Resume polling
            pollScrapeStatus();
        }
    } catch (error) {
        console.error('Failed to check scraper status:', error);
    }
}

// Check if a category requires authentication
function categoryRequiresAuth(category) {
    // "internal" type categories require authentication
    const catInfo = categories[category];
    // Check if the category info indicates it's internal type
    // The backend marks internal categories with type: "internal"
    return category === 'internal' || (catInfo && catInfo.type === 'internal');
}

// Check if credentials are configured
async function checkCredentialsStatus() {
    try {
        const response = await apiRequest('/scraper/credentials-status');
        return response.configured;
    } catch (error) {
        console.error('Failed to check credentials status:', error);
        return false;
    }
}

// Store pending scrape action to resume after login
let pendingScrapeAction = null;

// Show the internal login modal
function showInternalLoginModal() {
    // Clear previous values and messages
    elements.internalUsername.value = '';
    elements.internalPassword.value = '';
    elements.loginError.classList.add('hidden');
    elements.loginSuccess.classList.add('hidden');
    elements.loginError.textContent = '';
    elements.loginSuccess.textContent = '';

    // Show modal
    showModal(elements.internalLoginModal);

    // Focus username field
    setTimeout(() => elements.internalUsername.focus(), 100);
}

// Test internal login credentials
async function testInternalLogin() {
    const username = elements.internalUsername.value.trim();
    const password = elements.internalPassword.value;

    if (!username || !password) {
        elements.loginError.textContent = 'Please enter both username and password.';
        elements.loginError.classList.remove('hidden');
        elements.loginSuccess.classList.add('hidden');
        return;
    }

    // Show loading state
    elements.testLoginBtn.disabled = true;
    elements.testLoginBtn.textContent = 'Testing...';
    elements.loginError.classList.add('hidden');
    elements.loginSuccess.classList.add('hidden');

    try {
        const result = await apiRequest('/scraper/test-login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });

        if (result.authenticated) {
            elements.loginSuccess.textContent = 'Login successful! Credentials are valid.';
            elements.loginSuccess.classList.remove('hidden');
        } else {
            elements.loginError.textContent = result.message || 'Login failed. Please check your credentials.';
            elements.loginError.classList.remove('hidden');
        }
    } catch (error) {
        elements.loginError.textContent = 'Failed to test login. Please try again.';
        elements.loginError.classList.remove('hidden');
    } finally {
        elements.testLoginBtn.disabled = false;
        elements.testLoginBtn.textContent = 'Test Login';
    }
}

// Save internal credentials and continue with scrape
async function saveInternalCredentials() {
    const username = elements.internalUsername.value.trim();
    const password = elements.internalPassword.value;

    if (!username || !password) {
        elements.loginError.textContent = 'Please enter both username and password.';
        elements.loginError.classList.remove('hidden');
        elements.loginSuccess.classList.add('hidden');
        return;
    }

    // Show loading state
    elements.saveCredentialsBtn.disabled = true;
    elements.saveCredentialsBtn.textContent = 'Saving...';
    elements.loginError.classList.add('hidden');
    elements.loginSuccess.classList.add('hidden');

    try {
        const result = await apiRequest('/scraper/set-credentials', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });

        if (result.saved) {
            // Close modal
            elements.internalLoginModal.classList.add('hidden');
            showToast('Credentials saved successfully', 'success');

            // Continue with pending scrape if any
            if (pendingScrapeAction) {
                const action = pendingScrapeAction;
                pendingScrapeAction = null;
                action();
            }
        } else {
            elements.loginError.textContent = result.message || 'Failed to save credentials.';
            elements.loginError.classList.remove('hidden');
        }
    } catch (error) {
        elements.loginError.textContent = 'Failed to save credentials. Please try again.';
        elements.loginError.classList.remove('hidden');
    } finally {
        elements.saveCredentialsBtn.disabled = false;
        elements.saveCredentialsBtn.textContent = 'Save & Continue';
    }
}

async function startScrape() {
    const category = elements.scrapeCategorySelect.value;
    const maxPages = parseInt(elements.scrapeMaxPages.value) || 1500;
    const catName = categories[category]?.name || category;

    // Check if this category requires authentication
    if (categoryRequiresAuth(category)) {
        const isConfigured = await checkCredentialsStatus();
        if (!isConfigured) {
            // Store the scrape action to resume after login
            pendingScrapeAction = () => performScrape(category, maxPages, catName);
            showInternalLoginModal();
            return;
        }
    }

    // Proceed with scrape confirmation
    performScrape(category, maxPages, catName);
}

function performScrape(category, maxPages, catName) {
    showConfirm(
        'Start Scrape',
        `Start scraping "${catName}" (up to ${maxPages} pages)? This may take a while.`,
        async () => {
            // Show progress UI immediately
            elements.scraperProgress.classList.remove('hidden');
            elements.progressText.textContent = `Starting scrape for "${catName}"...`;
            elements.progressFill.style.width = '0%';
            elements.startScrapeBtn.disabled = true;
            elements.importDocsBtn.disabled = true;
            elements.cancelScrapeBtn.classList.remove('hidden');

            // Give browser a frame to repaint
            await new Promise(resolve => requestAnimationFrame(resolve));

            try {
                await apiRequest('/scraper/start', {
                    method: 'POST',
                    body: JSON.stringify({ category, max_pages: maxPages })
                });
                showToast(`Starting scrape for ${catName}...`, 'success');
                pollScrapeStatus();
            } catch (error) {
                // Reset UI on failure
                elements.scraperProgress.classList.add('hidden');
                elements.startScrapeBtn.disabled = false;
                elements.importDocsBtn.disabled = false;
                elements.cancelScrapeBtn.classList.add('hidden');
                showToast('Failed to start scrape', 'error');
            }
        }
    );
}

function clearSelectedCategory() {
    const category = elements.scrapeCategorySelect.value;
    const catName = categories[category]?.name || category;

    showConfirm(
        'Clear Category',
        `Are you sure you want to delete all documents from "${catName}"? This cannot be undone.`,
        async () => {
            try {
                const result = await apiRequest(`/category/${category}`, {
                    method: 'DELETE'
                });
                showToast(result.message, 'success');
                await loadScraperStats();
            } catch (error) {
                showToast('Failed to clear category', 'error');
            }
        }
    );
}

async function showImportModal() {
    // Populate category dropdown with existing categories
    const categoryOptions = Object.entries(categories).map(([key, cat]) =>
        `<option value="${escapeHtml(key)}">${escapeHtml(cat.name)}</option>`
    ).join('');

    elements.importCategorySelect.innerHTML =
        '<option value="">-- Select or enter new below --</option>' + categoryOptions;

    // Clear new category input
    elements.importCategoryNew.value = '';

    // Reset browser state
    currentBrowserPath = null;
    currentBrowserFiles = [];
    selectedBrowserFiles = new Set();

    // Show the modal
    showModal(elements.importModal);

    // Load initial folder view - default to documents folder
    await browseFolder('default');
}

async function browseFolder(path) {
    elements.browserContent.innerHTML = '<div class="browser-loading">Loading...</div>';

    try {
        const url = path ? `/browse-folders?path=${encodeURIComponent(path)}` : '/browse-folders';
        const data = await apiRequest(url);

        if (data.error) {
            elements.browserContent.innerHTML = `<div class="browser-loading">${escapeHtml(data.error)}</div>`;
            return;
        }

        currentBrowserPath = data.current_path;
        currentBrowserFiles = data.files || [];

        // Update path display
        elements.browserPath.value = data.current_path || 'Select a drive';

        // Show drives if available
        if (data.drives && data.drives.length > 0) {
            elements.browserDrives.innerHTML = data.drives.map(drive =>
                `<button class="drive-btn" data-path="${escapeHtml(drive.path)}">${escapeHtml(drive.name)}</button>`
            ).join('');
            // Add click handlers
            elements.browserDrives.querySelectorAll('.drive-btn').forEach(btn => {
                btn.addEventListener('click', () => browseFolder(btn.dataset.path));
            });
        } else {
            elements.browserDrives.innerHTML = '';
        }

        // Build folder/file list
        let html = '';

        // Folders
        if (data.folders && data.folders.length > 0) {
            html += data.folders.map(folder =>
                `<div class="browser-item folder" data-path="${escapeHtml(folder.path)}">${escapeHtml(folder.name)}</div>`
            ).join('');
        }

        // Files with checkboxes
        if (data.files && data.files.length > 0) {
            html += data.files.map(file => {
                const isImported = file.imported;
                const isSelected = selectedBrowserFiles.has(file.path);
                const importedClass = isImported ? ' imported' : '';
                const importedLabel = isImported ? ' <span class="imported-label">(imported)</span>' : '';
                return `<div class="browser-item file${importedClass}" data-path="${escapeHtml(file.path)}">
                    <label class="file-checkbox-label">
                        <input type="checkbox" class="file-checkbox" data-path="${escapeHtml(file.path)}" ${isSelected ? 'checked' : ''}>
                        <span class="file-name">${escapeHtml(file.name)}${importedLabel}</span>
                    </label>
                </div>`;
            }).join('');
        }

        if (!html) {
            html = '<div class="browser-loading">No folders or documents found</div>';
        }

        elements.browserContent.innerHTML = html;

        // Add click handlers to folders
        elements.browserContent.querySelectorAll('.browser-item.folder').forEach(item => {
            item.addEventListener('click', () => browseFolder(item.dataset.path));
        });

        // Add change handlers to file checkboxes
        elements.browserContent.querySelectorAll('.file-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const filePath = e.target.dataset.path;
                if (e.target.checked) {
                    selectedBrowserFiles.add(filePath);
                } else {
                    selectedBrowserFiles.delete(filePath);
                }
                updateSelectedCount();
            });
        });

        // Show/hide select all checkbox
        const fileCount = data.files ? data.files.length : 0;
        if (fileCount > 0) {
            elements.browserSelectAll.style.display = 'block';
            // Update select all checkbox state
            const notImportedFiles = data.files.filter(f => !f.imported);
            const allSelected = notImportedFiles.length > 0 && notImportedFiles.every(f => selectedBrowserFiles.has(f.path));
            elements.selectAllFiles.checked = allSelected;
        } else {
            elements.browserSelectAll.style.display = 'none';
        }

        // Update file count
        elements.browserFileCount.textContent = fileCount === 1
            ? '1 document found'
            : `${fileCount} documents found`;

        updateSelectedCount();

        // Auto-suggest category from folder name
        if (data.current_path && !elements.importCategoryNew.value && !elements.importCategorySelect.value) {
            const folderName = data.current_path.split(/[/\\]/).pop();
            if (folderName && folderName !== 'documents') {
                elements.importCategoryNew.value = folderName;
            }
        }

    } catch (error) {
        elements.browserContent.innerHTML = `<div class="browser-loading">Error loading folder</div>`;
    }
}


function updateSelectedCount() {
    const count = selectedBrowserFiles.size;
    if (count > 0) {
        elements.browserSelectedCount.textContent = `(${count} selected)`;
    } else {
        elements.browserSelectedCount.textContent = '';
    }
}

function toggleSelectAllFiles(checked) {
    // Only select files that aren't already imported
    currentBrowserFiles.forEach(file => {
        if (!file.imported) {
            if (checked) {
                selectedBrowserFiles.add(file.path);
            } else {
                selectedBrowserFiles.delete(file.path);
            }
        }
    });
    // Update checkboxes in UI
    elements.browserContent.querySelectorAll('.file-checkbox').forEach(checkbox => {
        const file = currentBrowserFiles.find(f => f.path === checkbox.dataset.path);
        if (file && !file.imported) {
            checkbox.checked = checked;
        }
    });
    updateSelectedCount();
}

function browserGoUp() {
    if (currentBrowserPath) {
        const parts = currentBrowserPath.split(/[/\\]/);
        if (parts.length > 1) {
            parts.pop();
            const parentPath = parts.join('\\') || parts.join('/');
            if (parentPath) {
                browseFolder(parentPath);
            } else {
                // Go back to drive selection
                browseFolder(null);
            }
        } else {
            // At root, show drives
            browseFolder(null);
        }
    }
}

function startDocumentImport() {
    // Get category from either dropdown or new input
    let category = elements.importCategoryNew.value.trim();
    if (!category) {
        category = elements.importCategorySelect.value;
    }

    if (!category) {
        showToast('Please select or enter a category', 'error');
        return;
    }

    // Check if a folder with documents is selected
    if (!currentBrowserPath) {
        showToast('Please select a folder first', 'error');
        return;
    }

    if (currentBrowserFiles.length === 0) {
        showToast('No documents in selected folder', 'error');
        return;
    }

    // Determine which files to import
    const filesToImport = selectedBrowserFiles.size > 0
        ? Array.from(selectedBrowserFiles)
        : null; // null means import all from folder

    // If no files selected, warn user
    if (selectedBrowserFiles.size === 0) {
        // Check if all files are already imported
        const notImportedFiles = currentBrowserFiles.filter(f => !f.imported);
        if (notImportedFiles.length === 0) {
            showToast('All documents in this folder are already imported', 'warning');
            return;
        }
    }

    const importCount = filesToImport ? filesToImport.length : currentBrowserFiles.filter(f => !f.imported).length;

    // Close import modal, show scraper modal with progress FIRST
    elements.importModal.classList.add('hidden');
    showModal(elements.scraperModal);

    // Show progress UI with indeterminate animation
    elements.scraperProgress.classList.remove('hidden');
    elements.progressText.textContent = `Importing ${importCount} document(s) as "${category}"...`;
    elements.progressFill.style.width = '';
    elements.progressFill.classList.add('indeterminate');
    elements.startScrapeBtn.disabled = true;
    elements.importDocsBtn.disabled = true;
    elements.cancelScrapeBtn.classList.remove('hidden');

    // Set flag to prevent pollScrapeStatus from hiding progress too early
    importJustStarted = true;
    importWaitCount = 0;

    const folderPath = currentBrowserPath;

    // Double RAF to ensure paint happens before fetch
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            // Use raw fetch - fire and forget
            fetch(`${API_BASE}/scraper/import-docs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    category,
                    folder_path: folderPath,
                    selected_files: filesToImport
                })
            }).then(response => {
                if (response.ok) {
                    showToast(`Importing documents as "${category}"...`, 'success');
                } else {
                    importJustStarted = false;
                    showToast('Failed to start document import', 'error');
                }
            }).catch(() => {
                importJustStarted = false;
                showToast('Failed to start document import', 'error');
            });

            // Start polling after a delay to let the backend start
            setTimeout(() => {
                pollImportStatus();
            }, 500);
        });
    });
}

async function pollImportStatus() {
    try {
        const data = await apiRequest('/scraper/status');

        if (data.in_progress) {
            // Reset wait counter since import has started
            importJustStarted = false;
            importWaitCount = 0;
            // Update text but keep indeterminate animation
            elements.progressText.textContent = data.status_text || 'Working...';
            setTimeout(pollImportStatus, 1000);
        } else if (importJustStarted && importWaitCount < 10) {
            // Import might not have started yet, keep waiting (max 5 seconds)
            importWaitCount++;
            elements.progressText.textContent = 'Starting import...';
            setTimeout(pollImportStatus, 500);
        } else {
            // Reset flags
            importJustStarted = false;
            importWaitCount = 0;
            // Import complete - remove indeterminate animation
            elements.progressFill.classList.remove('indeterminate');
            elements.progressFill.style.width = '100%';
            elements.progressText.textContent = data.status_text || 'Complete!';

            // Log debug info if available
            if (data.debug_log && data.debug_log.length > 0) {
                console.log('Import debug log:', data.debug_log);
            }
            if (data.errors && data.errors.length > 0) {
                console.log('Import errors:', data.errors);
            }

            // Show completion for a moment before hiding
            setTimeout(async () => {
                elements.scraperProgress.classList.add('hidden');
                elements.cancelScrapeBtn.classList.add('hidden');
                elements.startScrapeBtn.disabled = false;
                elements.importDocsBtn.disabled = false;
                elements.progressFill.style.width = '0%';
                await loadScraperStats();
                await loadCategories();
                showToast('Import complete!', 'success');
            }, 1500);
        }
    } catch (error) {
        elements.progressFill.classList.remove('indeterminate');
        elements.scraperProgress.classList.add('hidden');
        elements.cancelScrapeBtn.classList.add('hidden');
        elements.startScrapeBtn.disabled = false;
        elements.importDocsBtn.disabled = false;
        showToast('Status check failed', 'error');
    }
}

async function pollScrapeStatus() {
    try {
        const data = await apiRequest('/scraper/status');

        if (data.in_progress) {
            elements.progressFill.style.width = `${data.progress || 0}%`;
            elements.progressText.textContent = data.status_text || 'Processing...';
            elements.cancelScrapeBtn.classList.remove('hidden');
            setTimeout(pollScrapeStatus, 2000);
        } else {
            elements.scraperProgress.classList.add('hidden');
            elements.cancelScrapeBtn.classList.add('hidden');
            elements.startScrapeBtn.disabled = false;
            elements.importDocsBtn.disabled = false;
            await loadScraperStats();
            await loadCategories();  // Reload categories in case new ones were created
            if (data.status_text && data.status_text.includes('Cancelled')) {
                showToast('Cancelled', 'error');
            } else {
                showToast('Complete!', 'success');
            }
        }
    } catch (error) {
        elements.scraperProgress.classList.add('hidden');
        elements.cancelScrapeBtn.classList.add('hidden');
        elements.startScrapeBtn.disabled = false;
        elements.importDocsBtn.disabled = false;
        showToast('Status check failed', 'error');
    }
}

async function cancelScrape() {
    try {
        await apiRequest('/scraper/cancel', { method: 'POST' });
        showToast('Cancelling...', 'success');
    } catch (error) {
        showToast('Failed to cancel', 'error');
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

// Action card type detection based on topic content
function getActionCardType(topic) {
    const lowerTopic = topic.toLowerCase();

    // Challenge: quizzes, validation, verification
    if (/validat|verif|check|test|quiz|exercise/.test(lowerTopic)) {
        return { type: 'challenge', icon: '⚡', verb: 'Challenge' };
    }

    // Practice: procedures, how-to, steps
    if (/how to|create|configur|setup|set up|implement|build|steps/.test(lowerTopic)) {
        return { type: 'practice', icon: '🛠️', verb: 'Practice' };
    }

    // Explore: structures, architecture, deep-dive
    if (/structur|architect|overview|explor|analyz|investigat/.test(lowerTopic)) {
        return { type: 'explore', icon: '🔍', verb: 'Explore' };
    }

    // Default to Learn
    return { type: 'learn', icon: '📖', verb: 'Learn' };
}

// Format topic text for action cards
function formatActionCardTitle(topic, actionType) {
    // Remove common prefixes
    let title = topic
        .replace(/^(understanding|what is|how to|overview of|introduction to)\s*/i, '')
        .trim();

    // Capitalize first letter
    title = title.charAt(0).toUpperCase() + title.slice(1);

    return title;
}

// Default fallback suggestions (shown immediately, replaced by AI if available)
const defaultSuggestions = [
    { topic: 'BOM management in Windchill', description: 'Learn how to create and manage Bills of Materials' },
    { topic: 'How to create workflows', description: 'Set up automated processes and approvals' },
    { topic: 'Part versioning and revisions', description: 'Understand version control for parts' },
    { topic: 'Change management process', description: 'Handle engineering changes effectively' },
    { topic: 'Document management basics', description: 'Organize and control documents' },
    { topic: 'Search and navigation tips', description: 'Find information quickly in Windchill' }
];

// Render action cards from suggestions array
function renderActionCards(container, suggestions) {
    container.innerHTML = suggestions.map(s => {
        const action = getActionCardType(s.topic);
        const title = formatActionCardTitle(s.topic, action);
        return `
            <button type="button" class="action-card"
                    data-type="${action.type}"
                    data-topic="${escapeHtml(s.topic)}"
                    title="${escapeHtml(s.description || '')}">
                <span class="action-card-type">
                    ${action.icon} ${action.verb}
                </span>
                <span class="action-card-title">${escapeHtml(title)}</span>
            </button>
        `;
    }).join('');

    // Add click handlers
    container.querySelectorAll('.action-card').forEach(card => {
        card.addEventListener('click', () => {
            exitCleanSlate();
            const topic = card.dataset.topic;
            elements.questionInput.value = `Tell me about ${topic}`;
            elements.questionInput.focus();
        });
    });
}

// Load AI-suggested topics for the main ask screen
async function loadMainTopicSuggestions(category = null) {
    const container = elements.mainTopicSuggestions;
    if (!container) return;

    // Show fallback suggestions immediately (don't make user wait)
    renderActionCards(container, defaultSuggestions);

    // Try to load AI suggestions in background (with timeout)
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000); // 8 second timeout

        const url = category
            ? `/topics/suggest?category=${encodeURIComponent(category)}&limit=6`
            : '/topics/suggest?limit=6';

        const response = await fetch(`/api${url}`, {
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (response.ok) {
            const data = await response.json();
            if (data.suggestions?.length > 0) {
                // Replace fallback with AI suggestions
                renderActionCards(container, data.suggestions);
            }
        }
    } catch (error) {
        // Silently fail - fallback suggestions are already shown
        console.log('AI suggestions unavailable, using defaults');
    }
}

function getSelectedTopicFilter() {
    // Topic dropdown removed - always use all topics (AI suggestions handle discovery)
    return null;
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

        // Populate category select dropdown with stats
        const categoryOptions = Object.entries(categories).map(([key, cat]) => {
            console.log('Processing category:', key, cat);
            const pages = cat.pages_scraped || 0;
            const chunks = cat.chunks_indexed || 0;
            const stats = pages > 0 || chunks > 0 ? ` (${pages}p, ${chunks}c)` : '';
            const fullTitle = `${cat.name} - ${pages} pages, ${chunks} chunks`;
            return `<option value="${escapeHtml(key)}" title="${escapeHtml(fullTitle)}">${escapeHtml(cat.name)}${stats}</option>`;
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

    // Reload AI-suggested topics for the selected category
    loadMainTopicSuggestions(category);
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

// Clean Slate Mode - Progressive Disclosure
function exitCleanSlate() {
    if (document.body.classList.contains('clean-slate')) {
        document.body.classList.remove('clean-slate');
        localStorage.setItem('hasUsedApp', 'true');
    }
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

// ============== Course Functions ==============

// Load all courses
async function loadCourses() {
    try {
        const data = await apiRequest('/courses');
        courses = data.courses || [];
        renderCourseList();
    } catch (error) {
        console.error('Failed to load courses:', error);
    }
}

// Badge system
function getBadges() {
    const badges = JSON.parse(localStorage.getItem('userBadges') || '{}');
    return badges;
}

function awardBadge(badgeId, badgeName, badgeIcon) {
    const badges = getBadges();
    if (!badges[badgeId]) {
        badges[badgeId] = {
            name: badgeName,
            icon: badgeIcon,
            earned: new Date().toISOString()
        };
        localStorage.setItem('userBadges', JSON.stringify(badges));
        showToast(`🏆 Badge earned: ${badgeName}!`, 'success');
        renderBadges();
    }
}

function checkBadgeEligibility() {
    const badges = getBadges();
    const questionsAsked = parseInt(localStorage.getItem('questionsAsked') || '0');
    const coursesCompleted = courses.filter(c => c.progress === 100).length;
    const totalCourses = courses.length;

    // First Steps - Complete any course section
    if (!badges['first-steps'] && courses.some(c => c.completed_items > 0)) {
        awardBadge('first-steps', 'First Steps', '🌱');
    }

    // Knowledge Seeker - Ask 10 questions
    if (!badges['knowledge-seeker'] && questionsAsked >= 10) {
        awardBadge('knowledge-seeker', 'Knowledge Seeker', '🔍');
    }

    // Course Master - Complete any course
    if (!badges['course-master'] && coursesCompleted >= 1) {
        awardBadge('course-master', 'Course Master', '🎓');
    }

    // Scholar - Complete 3 courses
    if (!badges['scholar'] && coursesCompleted >= 3) {
        awardBadge('scholar', 'Scholar', '📚');
    }

    // Dedicated Learner - Create 5+ courses
    if (!badges['dedicated-learner'] && totalCourses >= 5) {
        awardBadge('dedicated-learner', 'Dedicated Learner', '⭐');
    }
}

function renderBadges() {
    const badgesContainer = document.getElementById('achievement-badges');
    if (!badgesContainer) return;

    const badges = getBadges();
    const badgesList = Object.values(badges);

    if (badgesList.length === 0) {
        badgesContainer.innerHTML = '';
        badgesContainer.style.display = 'none';
        return;
    }

    badgesContainer.style.display = 'flex';
    badgesContainer.innerHTML = badgesList.map(badge => `
        <span class="badge earned" title="Earned: ${new Date(badge.earned).toLocaleDateString()}">
            <span class="badge-icon">${badge.icon}</span>
            ${badge.name}
        </span>
    `).join('');
}

// Render course list in sidebar as roadmap
function renderCourseList() {
    if (!elements.courseList) return;

    // Render badges first
    renderBadges();
    checkBadgeEligibility();

    if (courses.length === 0) {
        elements.courseList.innerHTML = '<p class="empty-state">No learning journeys yet.<br><small>Create a course to start!</small></p>';
        return;
    }

    // Render as roadmap
    elements.courseList.innerHTML = `
        <div class="course-roadmap">
            ${courses.map((course, index) => {
                const isActive = currentCourse && currentCourse.id === course.id;
                const isCompleted = course.progress === 100;
                const isCurrent = !isCompleted && course.progress > 0;

                // For now, no locking - all courses accessible
                const nodeClass = [
                    'roadmap-node',
                    isActive ? 'active' : '',
                    isCompleted ? 'completed' : '',
                    isCurrent ? 'current' : ''
                ].filter(Boolean).join(' ');

                const statusText = isCompleted
                    ? 'Completed'
                    : course.progress > 0
                        ? `${course.completed_items}/${course.total_items} done`
                        : 'Not started';

                return `
                    <div class="${nodeClass}" data-id="${course.id}" title="${escapeHtml(course.title)}">
                        <div class="node-connector"></div>
                        <div class="node-circle">
                            ${isCompleted ? '✓' : (index + 1)}
                        </div>
                        <div class="node-content">
                            <div class="node-title">${escapeHtml(course.title)}</div>
                            <div class="node-status">${statusText}</div>
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
    `;

    // Add click handlers for roadmap nodes
    elements.courseList.querySelectorAll('.roadmap-node:not(.locked)').forEach(node => {
        node.addEventListener('click', () => {
            const courseId = parseInt(node.dataset.id);
            openCourse(courseId);
        });
    });
}

// Show AI course generation modal
function showCourseModal() {
    console.log('showCourseModal called');
    editingCourseId = null;

    // Reset form
    if (elements.courseTopic) {
        elements.courseTopic.value = '';
    }

    // Default to questions type
    if (elements.courseTypeQuestions) {
        elements.courseTypeQuestions.checked = true;
        updateCourseTypeUI();
    }

    // Populate category dropdown with all available categories
    if (elements.courseCategory) {
        const cats = categories || {};
        const categoryOptions = Object.entries(cats).map(([key, cat]) =>
            `<option value="${escapeHtml(key)}">${escapeHtml(cat.name)} (${cat.pages_scraped || 0} pages)</option>`
        ).join('');
        elements.courseCategory.innerHTML = '<option value="">All Sources</option>' + categoryOptions;
        elements.courseCategory.value = '';
    }

    // Show form, hide generating state
    if (elements.aiCourseForm) {
        elements.aiCourseForm.classList.remove('hidden');
    }
    if (elements.aiGenerating) {
        elements.aiGenerating.classList.add('hidden');
    }
    if (elements.generateCourseBtn) {
        elements.generateCourseBtn.disabled = false;
    }

    if (elements.courseModal) {
        showModal(elements.courseModal);
        console.log('Modal shown');
        // Fetch topic suggestions when modal opens
        fetchTopicSuggestions();
    } else {
        console.error('courseModal element not found!');
        alert('Error: Course modal not found. Please refresh the page.');
    }
}

// Fetch AI-generated topic suggestions
async function fetchTopicSuggestions() {
    const container = elements.topicSuggestionsList;
    if (!container) return;

    container.innerHTML = '<span class="loading-text">Loading suggestions...</span>';

    try {
        const category = elements.courseCategory?.value || '';
        const response = await apiRequest(`/topics/suggest?category=${encodeURIComponent(category)}&limit=8`);

        if (response.suggestions?.length > 0) {
            container.innerHTML = response.suggestions.map(s => `
                <button type="button" class="topic-chip"
                        data-topic="${escapeHtml(s.topic)}"
                        title="${escapeHtml(s.description || '')}">
                    ${escapeHtml(s.topic)}
                </button>
            `).join('');

            // Add click handlers to chips
            container.querySelectorAll('.topic-chip').forEach(chip => {
                chip.addEventListener('click', () => {
                    if (elements.courseTopic) {
                        elements.courseTopic.value = chip.dataset.topic;
                        elements.courseTopic.focus();
                    }
                });
            });
        } else {
            container.innerHTML = '<span class="loading-text">No suggestions available</span>';
        }
    } catch (error) {
        console.error('Failed to fetch topic suggestions:', error);
        container.innerHTML = '<span class="loading-text">Could not load suggestions</span>';
    }
}

// Update UI based on course type selection
function updateCourseTypeUI() {
    const isQuestions = elements.courseTypeQuestions && elements.courseTypeQuestions.checked;

    if (elements.numItemsLabel) {
        elements.numItemsLabel.textContent = isQuestions ? 'Number of Questions' : 'Number of Lessons';
    }

    if (elements.courseNumItems) {
        if (isQuestions) {
            elements.courseNumItems.innerHTML = `
                <option value="5" selected>5 questions</option>
                <option value="10">10 questions</option>
                <option value="15">15 questions</option>
            `;
        } else {
            elements.courseNumItems.innerHTML = `
                <option value="3">3 lessons (Quick overview)</option>
                <option value="5" selected>5 lessons (Standard)</option>
                <option value="7">7 lessons (Comprehensive)</option>
                <option value="10">10 lessons (Deep dive)</option>
            `;
        }
    }
}

// Generate AI course
async function generateAICourse() {
    const topic = elements.courseTopic ? elements.courseTopic.value.trim() : '';
    const category = elements.courseCategory ? elements.courseCategory.value : '';
    const numItems = elements.courseNumItems ? parseInt(elements.courseNumItems.value) : 5;
    const isQuestions = elements.courseTypeQuestions && elements.courseTypeQuestions.checked;

    if (!topic) {
        showToast('Please describe what you want to learn', 'error');
        return;
    }

    // Show generating state
    if (elements.aiCourseForm) {
        elements.aiCourseForm.classList.add('hidden');
    }
    if (elements.aiGenerating) {
        elements.aiGenerating.classList.remove('hidden');
    }
    if (elements.generateCourseBtn) {
        elements.generateCourseBtn.disabled = true;
    }

    try {
        let response;
        if (isQuestions) {
            // Generate question-based course
            response = await apiRequest('/courses/generate-questions', {
                method: 'POST',
                body: JSON.stringify({
                    topic: topic,
                    category: category || null,
                    num_questions: numItems
                })
            });
        } else {
            // Generate lesson-based course
            response = await apiRequest('/courses/generate', {
                method: 'POST',
                body: JSON.stringify({
                    topic: topic,
                    category: category || null,
                    num_lessons: numItems
                })
            });
        }

        if (response.error) {
            throw new Error(response.error);
        }

        if (!response.course_id) {
            console.error('No course_id in response:', response);
            throw new Error('Course was created but ID was not returned');
        }

        elements.courseModal.classList.add('hidden');
        await loadCourses();

        // Open the new course
        await openCourse(response.course_id);

        const itemType = isQuestions ? 'questions' : 'lessons';
        const itemCount = isQuestions ? response.num_questions : response.num_lessons;
        showToast(`Course created with ${itemCount} ${itemType}!`, 'success');
    } catch (error) {
        console.error('Generation failed:', error);
        showToast(error.message || 'Failed to generate course', 'error');

        // Reset form state
        if (elements.aiCourseForm) {
            elements.aiCourseForm.classList.remove('hidden');
        }
        if (elements.aiGenerating) {
            elements.aiGenerating.classList.add('hidden');
        }
        if (elements.generateCourseBtn) {
            elements.generateCourseBtn.disabled = false;
        }
    }
}

// Delete course
async function deleteCourse(courseId) {
    try {
        await apiRequest(`/courses/${courseId}`, { method: 'DELETE' });
        await loadCourses();
        showToast('Course deleted', 'success');
    } catch (error) {
        console.error('Delete failed:', error);
        showToast('Failed to delete course', 'error');
    }
}

// Open course in viewer
async function openCourse(courseId) {
    try {
        const course = await apiRequest(`/courses/${courseId}`);
        currentCourse = course;
        currentLessonId = null;

        // Update sidebar active state
        renderCourseList();

        // Show course viewer, hide main panel
        if (elements.courseViewer) {
            elements.courseViewer.classList.remove('hidden');
        }
        if (elements.mainPanel) {
            elements.mainPanel.classList.add('hidden');
        }

        // Update header
        if (elements.courseViewerTitle) {
            elements.courseViewerTitle.textContent = course.title;
        }
        if (elements.courseViewerDescription) {
            elements.courseViewerDescription.textContent = course.description || '';
        }

        // Update progress
        updateCourseProgress(course);

        // Render lesson list
        renderLessonList(course);

        // If there are lessons, open the first/resume one
        if (course.items && course.items.length > 0) {
            if (course.current_item_id) {
                openLesson(course.current_item_id);
            } else {
                openLesson(course.items[0].id);
            }
        } else {
            // Hide lesson content if no lessons
            if (elements.lessonContent) {
                elements.lessonContent.classList.add('hidden');
            }
        }
    } catch (error) {
        console.error('Failed to open course:', error);
        showToast('Failed to open course', 'error');
    }
}

// Close course viewer
function closeCourseViewer() {
    currentCourse = null;
    currentLessonId = null;

    if (elements.courseViewer) {
        elements.courseViewer.classList.add('hidden');
    }
    if (elements.mainPanel) {
        elements.mainPanel.classList.remove('hidden');
    }

    renderCourseList();
}

// Update course progress display
function updateCourseProgress(course) {
    if (elements.courseProgressText) {
        elements.courseProgressText.textContent = `${course.completed_items} of ${course.total_items} lessons complete`;
    }
    if (elements.courseProgressFill) {
        elements.courseProgressFill.style.width = `${course.progress}%`;
    }
}

// Render lesson list
function renderLessonList(course) {
    if (!elements.lessonList) return;

    if (!course.items || course.items.length === 0) {
        elements.lessonList.innerHTML = `
            <div class="empty-state" style="padding: 40px; text-align: center;">
                <p>No lessons yet. Create a new course to get started.</p>
            </div>
        `;
        return;
    }

    elements.lessonList.innerHTML = course.items.map((item, index) => {
        // Check for AI-generated title or question in instructor_notes
        let lessonTitle = item.page_title;
        let isQuestion = false;
        if (item.instructor_notes) {
            try {
                const aiContent = JSON.parse(item.instructor_notes);
                if (aiContent.type === 'question') {
                    // For questions, show a truncated version of the question
                    isQuestion = true;
                    const question = aiContent.question || '';
                    lessonTitle = question.length > 50 ? question.substring(0, 50) + '...' : question;
                } else if (aiContent.ai_generated && aiContent.title) {
                    lessonTitle = aiContent.title;
                }
            } catch (e) { /* not JSON, use page_title */ }
        }

        const itemLabel = isQuestion ? 'Q' : '';
        // Determine quiz result class
        let quizClass = '';
        let checkIcon = '';
        if (isQuestion && item.completed && item.quiz_correct !== null && item.quiz_correct !== undefined) {
            quizClass = item.quiz_correct ? 'quiz-correct' : 'quiz-incorrect';
            checkIcon = item.quiz_correct ? '✓' : '✗';
        } else if (item.completed) {
            checkIcon = '✓';
        }

        return `
            <div class="lesson-item ${item.completed ? 'completed' : ''} ${currentLessonId === item.id ? 'active' : ''} ${isQuestion ? 'question-item' : ''} ${quizClass}"
                 data-id="${item.id}">
                <span class="lesson-position">${itemLabel}${index + 1}</span>
                <div class="lesson-checkbox" data-id="${item.id}">
                    ${checkIcon ? `<span class="check-icon">${checkIcon}</span>` : ''}
                </div>
                <span class="lesson-title-text">${escapeHtml(lessonTitle)}</span>
            </div>
        `;
    }).join('');

    // Add click handlers for lessons
    elements.lessonList.querySelectorAll('.lesson-item').forEach(item => {
        item.addEventListener('click', (e) => {
            if (!e.target.closest('.lesson-checkbox')) {
                openLesson(parseInt(item.dataset.id));
            }
        });
    });

    // Add click handlers for checkboxes
    elements.lessonList.querySelectorAll('.lesson-checkbox').forEach(checkbox => {
        checkbox.addEventListener('click', (e) => {
            e.stopPropagation();
            const itemId = parseInt(checkbox.dataset.id);
            toggleLessonCompleteById(itemId);
        });
    });
}

// Fix encoding issues in content (using Unicode escapes for reliability)
function fixEncoding(text) {
    if (!text) return '';

    let result = text;

    // PRIORITY 0: Triple-encoded patterns (UTF-8 → Latin1 → UTF-8 with Windows-1252)
    // Pattern: Ã¢Â€Â + final byte (€ = U+20AC is 0x80 in Windows-1252)
    result = result.replace(/\u00c3\u00a2\u00c2\u20ac\u00c2\u00a2/g, '\u2022'); // Ã¢Â€Â¢ → • (bullet)
    result = result.replace(/\u00c3\u00a2\u00c2\u20ac\u00c2\u2122/g, "'");      // Ã¢Â€Â™ → ' (apostrophe) - ™ is U+2122 for 0x99
    result = result.replace(/\u00c3\u00a2\u00c2\u20ac\u00c2\u0099/g, "'");      // alternate apostrophe
    result = result.replace(/\u00c3\u00a2\u00c2\u20ac\u00c2\u201c/g, '"');      // left quote
    result = result.replace(/\u00c3\u00a2\u00c2\u20ac\u00c2\u009c/g, '"');      // alternate left quote
    result = result.replace(/\u00c3\u00a2\u00c2\u20ac\u00c2\u009d/g, '"');      // right quote
    result = result.replace(/\u00c3\u00a2\u00c2\u20ac\u00c2\u0094/g, '\u2014'); // em dash
    result = result.replace(/\u00c3\u00a2\u00c2\u20ac\u00c2\u201d/g, '\u2014'); // alternate em dash
    result = result.replace(/\u00c3\u00a2\u00c2\u20ac\u00c2\u0093/g, '\u2013'); // en dash

    // PRIORITY 1: Two-character patterns (middle byte stripped)
    result = result.replace(/\u00e2\u00a2/g, '\u2022');  // â¢ → • (bullet)
    result = result.replace(/\u00e2\u0099/g, "'");       // â™ → ' (apostrophe)
    result = result.replace(/\u00e2\u009c/g, '"');       // âœ → " (left quote)
    result = result.replace(/\u00e2\u009d/g, '"');       // â → " (right quote)
    result = result.replace(/\u00e2\u0094/g, '\u2014');  // â" → — (em dash)
    result = result.replace(/\u00e2\u0093/g, '\u2013');  // â" → – (en dash)
    result = result.replace(/\u00e2\u00a6/g, '\u2026');  // â¦ → … (ellipsis)

    // PRIORITY 2: Three-character patterns (full UTF-8 misread as Latin-1)
    result = result.replace(/\u00e2\u0080\u00a2/g, '\u2022'); // â€¢ → •
    result = result.replace(/\u00e2\u0080\u0099/g, "'");      // â€™ → '
    result = result.replace(/\u00e2\u0080\u009c/g, '"');      // â€œ → "
    result = result.replace(/\u00e2\u0080\u009d/g, '"');      // â€ → "
    result = result.replace(/\u00e2\u0080\u0094/g, '\u2014'); // â€" → —
    result = result.replace(/\u00e2\u0080\u0093/g, '\u2013'); // â€" → –
    result = result.replace(/\u00e2\u0080\u00a6/g, '\u2026'); // â€¦ → …
    result = result.replace(/\u00e2\u0084\u00a2/g, '\u2122'); // â„¢ → ™
    result = result.replace(/\u00e2\u0080\u0098/g, "'");      // â€˜ → '

    // PRIORITY 3: Clean up partially converted and remaining junk
    result = result.replace(/\u2014\u00a6/g, '\u2026');  // —¦ → …
    result = result.replace(/\u2014\u00a2/g, '\u2022'); // —¢ → •
    result = result.replace(/\u00c3\u00a2/g, '\u2014'); // Ã¢ → — (partial triple-encode = em dash)
    result = result.replace(/\u00a6/g, '');              // Lone broken bar ¦
    result = result.replace(/\u00a2/g, '');              // Lone cent sign ¢
    result = result.replace(/\u20ac/g, '');              // Lone euro sign €

    // PRIORITY 4: Convert dot-like chars to bullets
    result = result.replace(/(^|\n|\s)\u00b7\s/g, '$1\u2022 ');  // · middle dot → •
    result = result.replace(/(^|\n|\s)\u2219\s/g, '$1\u2022 '); // ∙ bullet operator → •

    // Handle â before contractions
    result = result.replace(/\u00e2(?=s\b)/g, "'");
    result = result.replace(/\u00e2(?=t\b)/g, "'");
    result = result.replace(/\u00e2(?=ll\b)/g, "'");
    result = result.replace(/\u00e2(?=re\b)/g, "'");
    result = result.replace(/\u00e2(?=ve\b)/g, "'");

    // Remaining â = em-dash
    result = result.replace(/(\w)\u00e2(\w)/g, '$1\u2014$2');
    result = result.replace(/\s\u00e2\s/g, ' \u2014 ');
    result = result.replace(/\u00e2/g, '\u2014');

    // Non-breaking space
    result = result.replace(/\u00c2\u00a0/g, ' ');
    result = result.replace(/\u00a0/g, ' ');

    // Cleanup stray chars
    result = result.replace(/\u00c2/g, '');
    result = result.replace(/\u00c3/g, '');
    result = result.replace(/\ufffd/g, '');

    return result;
}

// Format content for better readability
function formatLessonContent(content) {
    if (!content) return '<p class="empty-state">No content available</p>';

    // Fix encoding issues first
    let text = fixEncoding(content);

    // Additional cleanup: — at start of line likely meant to be bullet
    text = text.replace(/^—\s*/gm, '• ');
    text = text.replace(/\n—\s*/g, '\n• ');

    // Escape HTML
    text = escapeHtml(text);

    // Split into lines and process
    const lines = text.split('\n');
    const result = [];
    let inList = false;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) {
            if (inList) {
                result.push('</ul>');
                inList = false;
            }
            continue;
        }

        // Check if line starts with bullet character
        const bulletMatch = line.match(/^[\u2022\u2023\u2043\u25e6\u00b7\-\*]\s*(.+)/);
        if (bulletMatch) {
            if (!inList) {
                result.push('<ul class="content-list">');
                inList = true;
            }
            result.push(`<li>${bulletMatch[1]}</li>`);
        } else {
            if (inList) {
                result.push('</ul>');
                inList = false;
            }
            result.push(`<p>${line}</p>`);
        }
    }

    if (inList) {
        result.push('</ul>');
    }

    return result.join('');
}

// Quiz state tracking - persists answers across navigation
let quizState = {
    courseId: null,
    answers: {},  // itemId -> { selectedIndex, isCorrect }
    total: 0,
    sourceUrls: []  // Source URLs for the quiz
};

// Reset quiz state completely
function resetQuizState() {
    quizState = {
        courseId: null,
        answers: {},
        total: 0,
        sourceUrls: []
    };
}

// Initialize quiz state for a course, loading saved answers from backend
function initQuizState(courseId, totalQuestions, courseItems) {
    if (quizState.courseId !== courseId) {
        quizState = {
            courseId: courseId,
            answers: {},
            total: totalQuestions,
            sourceUrls: []
        };

        // Load saved answers and collect source URLs from course items
        if (courseItems) {
            const urlSet = new Set();
            courseItems.forEach(item => {
                if (item.quiz_answer !== null && item.quiz_answer !== undefined) {
                    quizState.answers[item.id] = {
                        selectedIndex: item.quiz_answer,
                        isCorrect: item.quiz_correct === true
                    };
                }
                // Collect source URLs from instructor_notes
                if (item.instructor_notes) {
                    try {
                        const data = JSON.parse(item.instructor_notes);
                        if (data.source_urls) {
                            data.source_urls.forEach(url => urlSet.add(url));
                        }
                    } catch (e) { /* ignore */ }
                }
            });
            quizState.sourceUrls = Array.from(urlSet);
        }
    }
    updateQuizScoreBar();
}

// Get quiz score
function getQuizScore() {
    let correct = 0;
    let answered = 0;
    for (const key in quizState.answers) {
        answered++;
        if (quizState.answers[key].isCorrect) {
            correct++;
        }
    }
    return { correct, answered, total: quizState.total };
}

// Update quiz score bar display
function updateQuizScoreBar() {
    const scoreBar = document.getElementById('quiz-score-bar');
    if (!scoreBar) return;

    const { correct, answered, total } = getQuizScore();
    const percentage = answered > 0 ? Math.round((correct / answered) * 100) : 0;

    // Build source link if URLs available
    let sourceLink = '';
    if (quizState.sourceUrls && quizState.sourceUrls.length > 0) {
        const firstUrl = quizState.sourceUrls[0];
        if (firstUrl.startsWith('file://')) {
            // Local file - use viewLocalDocument
            sourceLink = `<button class="btn btn-small btn-secondary" onclick="viewLocalDocument('${escapeHtml(firstUrl)}')">View Original</button>`;
        } else {
            sourceLink = `<a href="${escapeHtml(firstUrl)}" target="_blank" class="btn btn-small btn-secondary">View Original</a>`;
        }
    }

    scoreBar.innerHTML = `
        <div id="quiz-score-display">
            Score: <strong>${correct}/${answered}</strong> (${percentage}%)
        </div>
        <div class="quiz-score-actions">
            <button class="btn btn-small btn-secondary" onclick="restartQuiz()">Restart Quiz</button>
            ${sourceLink}
        </div>
    `;
    scoreBar.style.display = 'flex';
}

// Restart quiz with new random questions
function restartQuiz() {
    if (!currentCourse) return;

    showConfirm(
        'Restart Quiz',
        'Generate new random questions? Your current progress will be lost.',
        async () => {
            // Reset quiz state immediately
            resetQuizState();

            // Get the course topic from title (remove "Quiz: " prefix if present)
            let topic = currentCourse.title;
            if (topic.startsWith('Quiz:')) {
                topic = topic.substring(5).trim();
            }

            // Save the number of questions before deleting
            const numQuestions = currentCourse.items ? currentCourse.items.length : 5;

            // Show loading state
            const scoreBar = document.getElementById('quiz-score-bar');
            if (scoreBar) {
                scoreBar.innerHTML = '<div class="quiz-score-display">Generating new questions...</div>';
            }

            try {
                // Delete the old course
                await apiRequest(`/courses/${currentCourse.id}`, { method: 'DELETE' });

                // Generate new quiz with same topic and category
                const response = await apiRequest('/courses/generate-questions', {
                    method: 'POST',
                    body: JSON.stringify({
                        topic: topic,
                        category: currentCourse.category || null,
                        num_questions: numQuestions
                    })
                });

                if (response.success && response.course_id) {
                    // Load and open the new course
                    await loadCourses();
                    await openCourse(response.course_id);
                    showToast('New quiz generated!', 'success');
                } else {
                    throw new Error(response.error || 'Failed to generate quiz');
                }
            } catch (error) {
                console.error('Failed to restart quiz:', error);
                showToast('Failed to generate new quiz: ' + error.message, 'error');
                // Reload the current course to restore state
                if (currentCourse) {
                    await openCourse(currentCourse.id);
                }
            }
        }
    );
}

// Format a single quiz question with state
function formatQuizQuestion(questionData, itemId) {
    if (!questionData) return '<p class="empty-state">No content available</p>';

    const difficulty = questionData.difficulty || 'basic';
    const questionType = questionData.question_type || 'concept';
    const options = questionData.options || [];
    const correctIndex = questionData.correct_index;

    // Fallback for old format (text answer instead of multiple choice)
    if (!options.length || options.length !== 4) {
        return formatOldQuestionContent(questionData);
    }

    // Check if already answered
    const previousAnswer = quizState.answers[itemId];
    const isAnswered = !!previousAnswer;

    let html = '<div class="question-card quiz-question" data-item-id="' + itemId + '" data-answered="' + isAnswered + '">';

    // Question header with result badge (only shown after answering)
    html += '<div class="question-header">';
    if (isAnswered) {
        html += previousAnswer.isCorrect
            ? '<span class="question-badge result-correct">Correct</span>'
            : '<span class="question-badge result-incorrect">Incorrect</span>';
    }
    html += '</div>';

    // Question
    html += '<div class="question-text">';
    html += `<h3>${escapeHtml(questionData.question)}</h3>`;
    html += '</div>';

    // Multiple choice options
    html += '<div class="quiz-options">';
    const optionLabels = ['A', 'B', 'C', 'D'];
    options.forEach((option, idx) => {
        let optionClass = 'quiz-option';
        let disabled = '';

        if (isAnswered) {
            disabled = 'disabled';
            if (idx === correctIndex) {
                optionClass += ' correct';
            } else if (idx === previousAnswer.selectedIndex) {
                optionClass += ' incorrect';
            }
        }

        html += `<button class="${optionClass}" data-index="${idx}" data-correct="${idx === correctIndex}" ${disabled} onclick="selectQuizOption(this, ${correctIndex}, '${itemId}')">`;
        html += `<span class="option-label">${optionLabels[idx]}</span>`;
        html += `<span class="option-text">${escapeHtml(option)}</span>`;
        html += '</button>';
    });
    html += '</div>';

    // Explanation (shown if answered)
    const explanationVisible = isAnswered ? '' : 'hidden';
    html += `<div class="quiz-explanation ${explanationVisible}">`;
    if (questionData.explanation) {
        html += `<p><strong>Explanation:</strong> ${escapeHtml(questionData.explanation)}</p>`;
    }
    html += '</div>';

    html += '</div>'; // question-card
    return html;
}

// Handle quiz option selection
function selectQuizOption(button, correctIndex, itemId) {
    const questionCard = button.closest('.quiz-question');

    // Check if already answered
    if (questionCard.dataset.answered === 'true') {
        return;
    }

    // Mark as answered
    questionCard.dataset.answered = 'true';

    const selectedIndex = parseInt(button.dataset.index);
    const isCorrect = selectedIndex === correctIndex;

    // Save answer to state
    quizState.answers[itemId] = {
        selectedIndex: selectedIndex,
        isCorrect: isCorrect
    };

    // Save answer to backend
    if (currentCourse && currentCourse.id) {
        apiRequest(`/courses/${currentCourse.id}/items/${itemId}/quiz-answer`, {
            method: 'POST',
            body: JSON.stringify({
                selected_index: selectedIndex,
                is_correct: isCorrect
            })
        }).catch(err => console.error('Failed to save quiz answer:', err));
    }

    if (isCorrect) {
        button.classList.add('correct');
    } else {
        button.classList.add('incorrect');
        // Highlight the correct answer
        const correctButton = questionCard.querySelector(`[data-index="${correctIndex}"]`);
        if (correctButton) {
            correctButton.classList.add('correct');
        }
    }

    // Disable all options
    questionCard.querySelectorAll('.quiz-option').forEach(opt => {
        opt.disabled = true;
    });

    // Show explanation
    const explanation = questionCard.querySelector('.quiz-explanation');
    if (explanation) {
        explanation.classList.remove('hidden');
    }

    // Update score bar
    updateQuizScoreBar();

    // Add result badge
    const header = questionCard.querySelector('.question-header');
    if (header) {
        const badge = document.createElement('span');
        badge.className = isCorrect ? 'question-badge result-correct' : 'question-badge result-incorrect';
        badge.textContent = isCorrect ? 'Correct' : 'Incorrect';
        header.appendChild(badge);
    }

    // Auto-mark question as complete and update lesson list
    if (currentCourse && currentCourse.id) {
        // Mark complete on backend
        apiRequest(`/courses/${currentCourse.id}/items/${itemId}/complete`, {
            method: 'POST'
        }).then(() => {
            // Update the lesson list item with correct/incorrect color
            const lessonItem = document.querySelector(`.lesson-item[data-id="${itemId}"]`);
            if (lessonItem) {
                lessonItem.classList.add('completed');
                lessonItem.classList.add(isCorrect ? 'quiz-correct' : 'quiz-incorrect');
                const checkbox = lessonItem.querySelector('.lesson-checkbox');
                if (checkbox) {
                    checkbox.innerHTML = isCorrect ? '<span class="check-icon">✓</span>' : '<span class="check-icon">✗</span>';
                }
            }
            // Update the item in currentCourse
            const item = currentCourse.items.find(i => i.id === parseInt(itemId));
            if (item) {
                item.completed = true;
                item.quiz_correct = isCorrect;
            }
        }).catch(err => console.error('Failed to mark complete:', err));
    }
}

// Format old-style question content (text answer, not multiple choice)
function formatOldQuestionContent(questionData) {
    const difficulty = questionData.difficulty || 'basic';
    const questionType = questionData.question_type || 'concept';

    let html = '<div class="question-card">';

    // Question header with badges
    html += '<div class="question-header">';
    html += `<span class="question-badge difficulty-${difficulty}">${difficulty}</span>`;
    html += `<span class="question-badge type-${questionType}">${questionType}</span>`;
    html += '<span class="question-badge" style="background: var(--warning); color: #000;">Old Format</span>';
    html += '</div>';

    // Question
    html += '<div class="question-text">';
    html += `<h3>${escapeHtml(questionData.question)}</h3>`;
    html += '</div>';

    // Answer section (hidden by default)
    html += '<div class="answer-section">';
    html += '<button class="btn btn-primary show-answer-btn" onclick="toggleOldAnswer(this)">Show Answer</button>';
    html += '<div class="answer-content hidden">';

    // Answer
    html += '<div class="answer-text">';
    html += `<strong>Answer:</strong>`;
    html += `<p>${escapeHtml(questionData.answer || 'No answer available')}</p>`;
    html += '</div>';

    // Source excerpt
    if (questionData.source_excerpt) {
        html += '<div class="source-excerpt">';
        html += '<strong>Source Reference:</strong>';
        html += `<blockquote>${escapeHtml(questionData.source_excerpt)}</blockquote>`;
        html += '</div>';
    }

    html += '</div>'; // answer-content
    html += '</div>'; // answer-section

    html += '</div>'; // question-card
    return html;
}

// Toggle old-style answer visibility
function toggleOldAnswer(button) {
    const answerContent = button.nextElementSibling;
    if (answerContent.classList.contains('hidden')) {
        answerContent.classList.remove('hidden');
        button.textContent = 'Hide Answer';
        button.classList.remove('btn-primary');
        button.classList.add('btn-secondary');
    } else {
        answerContent.classList.add('hidden');
        button.textContent = 'Show Answer';
        button.classList.remove('btn-secondary');
        button.classList.add('btn-primary');
    }
}

// Toggle notes section visibility
function toggleNotesSection(header) {
    const section = header.closest('.lesson-notes-section');
    if (section) {
        section.classList.toggle('collapsed');
    }
}

// Format AI-generated lesson content
function formatAILessonContent(aiContent, itemId) {
    if (!aiContent) return '<p class="empty-state">No content available</p>';

    // Check if this is question-type content
    if (aiContent.type === 'question') {
        return formatQuizQuestion(aiContent, itemId);
    }

    let html = '<div class="ai-lesson-content">';

    // Summary
    if (aiContent.summary) {
        html += `<div class="ai-lesson-summary">${escapeHtml(aiContent.summary)}</div>`;
    }

    // Main content
    if (aiContent.content) {
        const content = escapeHtml(aiContent.content);
        // Convert line breaks to paragraphs and handle bullet points
        const lines = content.split('\n');
        let inList = false;

        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) {
                if (inList) {
                    html += '</ul>';
                    inList = false;
                }
                continue;
            }

            // Check for bullet points
            const bulletMatch = trimmed.match(/^[\u2022\u2023\-\*•]\s*(.+)/);
            if (bulletMatch) {
                if (!inList) {
                    html += '<ul class="content-list">';
                    inList = true;
                }
                html += `<li>${bulletMatch[1]}</li>`;
            } else {
                if (inList) {
                    html += '</ul>';
                    inList = false;
                }
                html += `<p>${trimmed}</p>`;
            }
        }
        if (inList) html += '</ul>';
    }

    // Key points
    if (aiContent.key_points && aiContent.key_points.length > 0) {
        html += '<div class="ai-key-points">';
        html += '<h4>Key Points</h4>';
        html += '<ul>';
        for (const point of aiContent.key_points) {
            html += `<li>${escapeHtml(point)}</li>`;
        }
        html += '</ul>';
        html += '</div>';
    }

    // Source links
    if (aiContent.source_urls && aiContent.source_urls.length > 0) {
        html += '<div class="ai-sources">';
        html += '<strong>Sources:</strong> ';
        const links = aiContent.source_urls
            .filter(url => url)
            .map(url => {
                if (url.startsWith('file://')) {
                    // Local file - show view button
                    const filename = url.split('/').pop();
                    return `<button class="btn btn-small view-local-btn" data-url="${escapeHtml(url)}" onclick="viewLocalDocument('${escapeHtml(url)}')">${escapeHtml(decodeURIComponent(filename))}</button>`;
                } else {
                    return `<a href="${escapeHtml(url)}" target="_blank">View Documentation</a>`;
                }
            });
        html += links.join(' | ');
        html += '</div>';
    }

    html += '</div>';
    return html;
}

// Open lesson content
function openLesson(itemId) {
    if (!currentCourse) return;

    const item = currentCourse.items.find(i => i.id === itemId);
    if (!item) return;

    const index = currentCourse.items.findIndex(i => i.id === itemId);
    currentLessonId = itemId;

    // Update lesson list active state
    if (elements.lessonList) {
        elements.lessonList.querySelectorAll('.lesson-item').forEach(el => {
            el.classList.toggle('active', parseInt(el.dataset.id) === itemId);
        });
    }

    // Check if this is AI-generated content (lesson or question)
    let aiContent = null;
    if (item.instructor_notes) {
        try {
            aiContent = JSON.parse(item.instructor_notes);
            // Accept both ai_generated lessons and question type content
            if (!aiContent.ai_generated && aiContent.type !== 'question') {
                aiContent = null;
            }
        } catch (e) {
            aiContent = null;
        }
    }

    // Check if this is a quiz question
    const isQuizQuestion = aiContent && aiContent.type === 'question';

    // Hide/show lesson header based on content type
    const lessonHeader = document.querySelector('.lesson-detail-header');
    if (lessonHeader) {
        if (isQuizQuestion) {
            lessonHeader.style.display = 'none';
        } else {
            lessonHeader.style.display = '';

            // Update lesson number
            if (elements.lessonNumber) {
                elements.lessonNumber.textContent = index + 1;
            }

            // Update lesson title
            if (elements.lessonTitle) {
                elements.lessonTitle.textContent = aiContent ? aiContent.title : item.page_title;
            }

            // Update source link
            if (elements.lessonSourceLink) {
                if (item.page_url) {
                    if (item.page_url.startsWith('file://')) {
                        // Local file - change to view content button
                        elements.lessonSourceLink.href = '#';
                        elements.lessonSourceLink.textContent = 'View Source Content';
                        elements.lessonSourceLink.onclick = (e) => {
                            e.preventDefault();
                            viewLocalDocument(item.page_url);
                        };
                        elements.lessonSourceLink.style.display = '';
                    } else {
                        // Remote URL - normal link
                        elements.lessonSourceLink.href = item.page_url;
                        elements.lessonSourceLink.textContent = 'View Original';
                        elements.lessonSourceLink.onclick = null;
                        elements.lessonSourceLink.style.display = '';
                    }
                } else {
                    elements.lessonSourceLink.style.display = 'none';
                }
            }
        }
    }

    // Update lesson content
    if (elements.lessonPageContent) {
        if (aiContent) {
            // Check if this is a quiz (question-type course with multiple choice)
            if (aiContent.type === 'question') {
                // Check if it's new format (has options array)
                const isNewFormat = aiContent.options && aiContent.options.length === 4;

                if (isNewFormat) {
                    // Initialize quiz state if needed
                    const questionItems = currentCourse.items.filter(i => {
                        try {
                            const data = JSON.parse(i.instructor_notes || '{}');
                            return data.type === 'question' && data.options && data.options.length === 4;
                        } catch { return false; }
                    });
                    initQuizState(currentCourse.id, questionItems.length, questionItems);
                } else {
                    // Hide score bar for old format
                    const scoreBar = document.getElementById('quiz-score-bar');
                    if (scoreBar) scoreBar.style.display = 'none';
                }
            }
            // Display AI-generated content with nice formatting
            elements.lessonPageContent.innerHTML = formatAILessonContent(aiContent, itemId);
        } else {
            // Display scraped page content
            elements.lessonPageContent.innerHTML = formatLessonContent(item.page_content);
            // Hide quiz score bar for non-quiz content
            const scoreBar = document.getElementById('quiz-score-bar');
            if (scoreBar) scoreBar.style.display = 'none';
        }
    }

    // Update notes
    if (elements.learnerNotes) {
        elements.learnerNotes.value = item.learner_notes || '';
    }
    if (elements.notesSaveStatus) {
        elements.notesSaveStatus.textContent = '';
        elements.notesSaveStatus.className = 'notes-status';
    }

    // Hide/show navigation and mark complete based on content type
    const lessonActions = document.querySelector('.lesson-actions');
    if (lessonActions) {
        if (isQuizQuestion) {
            lessonActions.style.display = 'none';
        } else {
            lessonActions.style.display = '';
            // Update mark complete button
            updateMarkCompleteButton(item.completed);
            // Update nav button states
            updateLessonNavButtons();
        }
    }

    // Show lesson content
    if (elements.lessonContent) {
        elements.lessonContent.classList.remove('hidden');
    }

    // Update resume position
    setResumePosition(itemId);
}

// Navigate lessons
function navigateLesson(direction) {
    if (!currentCourse || !currentLessonId) return;

    const currentIndex = currentCourse.items.findIndex(i => i.id === currentLessonId);
    if (currentIndex === -1) return;

    const newIndex = currentIndex + direction;
    if (newIndex >= 0 && newIndex < currentCourse.items.length) {
        openLesson(currentCourse.items[newIndex].id);
    }
}

// Update lesson nav buttons
function updateLessonNavButtons() {
    if (!currentCourse || !currentLessonId) return;

    const currentIndex = currentCourse.items.findIndex(i => i.id === currentLessonId);

    if (elements.prevLessonBtn) {
        elements.prevLessonBtn.disabled = currentIndex <= 0;
    }
    if (elements.nextLessonBtn) {
        elements.nextLessonBtn.disabled = currentIndex >= currentCourse.items.length - 1;
    }
}

// Update mark complete button
function updateMarkCompleteButton(completed) {
    if (elements.markCompleteBtn) {
        elements.markCompleteBtn.textContent = completed ? 'Mark Incomplete' : 'Mark Complete';
        elements.markCompleteBtn.classList.toggle('btn-secondary', completed);
        elements.markCompleteBtn.classList.toggle('btn-primary', !completed);
    }
}

// Toggle lesson complete
async function toggleLessonComplete() {
    if (!currentCourse || !currentLessonId) return;
    await toggleLessonCompleteById(currentLessonId);
}

// Toggle lesson complete by ID
async function toggleLessonCompleteById(itemId) {
    if (!currentCourse) return;

    const item = currentCourse.items.find(i => i.id === itemId);
    if (!item) return;

    try {
        const endpoint = item.completed ? 'uncomplete' : 'complete';
        const data = await apiRequest(`/courses/${currentCourse.id}/items/${itemId}/${endpoint}`, {
            method: 'POST'
        });

        // Update local state
        item.completed = data.completed;
        item.completed_at = data.completed_at;
        currentCourse.completed_items = data.completed_items;
        currentCourse.total_items = data.total_items;
        currentCourse.progress = data.progress;

        // Update UI
        updateCourseProgress(currentCourse);
        renderLessonList(currentCourse);

        if (currentLessonId === itemId) {
            updateMarkCompleteButton(item.completed);
        }

        // Refresh course list in sidebar
        await loadCourses();

        // Auto-advance to next lesson if marking complete
        if (data.completed && currentLessonId === itemId) {
            const currentIndex = currentCourse.items.findIndex(i => i.id === itemId);
            if (currentIndex < currentCourse.items.length - 1) {
                setTimeout(() => navigateLesson(1), 500);
            }
        }
    } catch (error) {
        console.error('Failed to toggle complete:', error);
        showToast('Failed to update lesson', 'error');
    }
}

// Handle notes change with debounce
function handleNotesChange() {
    if (elements.notesSaveStatus) {
        elements.notesSaveStatus.textContent = 'Saving...';
        elements.notesSaveStatus.className = 'notes-status saving';
    }

    clearTimeout(notesTimeout);
    notesTimeout = setTimeout(saveNotes, 1000);
}

// Save learner notes
async function saveNotes() {
    if (!currentCourse || !currentLessonId) return;

    const notes = elements.learnerNotes ? elements.learnerNotes.value : '';

    try {
        await apiRequest(`/courses/${currentCourse.id}/items/${currentLessonId}/notes`, {
            method: 'PUT',
            body: JSON.stringify({ notes })
        });

        // Update local state
        const item = currentCourse.items.find(i => i.id === currentLessonId);
        if (item) {
            item.learner_notes = notes;
        }

        if (elements.notesSaveStatus) {
            elements.notesSaveStatus.textContent = 'Saved';
            elements.notesSaveStatus.className = 'notes-status saved';
            setTimeout(() => {
                if (elements.notesSaveStatus) {
                    elements.notesSaveStatus.textContent = '';
                }
            }, 2000);
        }
    } catch (error) {
        console.error('Failed to save notes:', error);
        if (elements.notesSaveStatus) {
            elements.notesSaveStatus.textContent = 'Failed to save';
            elements.notesSaveStatus.className = 'notes-status';
        }
    }
}

// Set resume position
async function setResumePosition(itemId) {
    if (!currentCourse) return;

    try {
        await apiRequest(`/courses/${currentCourse.id}/resume?item_id=${itemId}`, {
            method: 'PUT'
        });
        currentCourse.current_item_id = itemId;
    } catch (error) {
        console.error('Failed to set resume position:', error);
    }
}

// ==================== Documents Modal ====================

let allDocuments = [];  // Cache all documents for filtering

async function openDocumentsModal() {
    showModal(elements.documentsModal);

    // Populate category filter
    const categoryOptions = Object.entries(categories).map(([key, cat]) =>
        `<option value="${escapeHtml(key)}">${escapeHtml(cat.name)}</option>`
    ).join('');
    elements.docsCategoryFilter.innerHTML = '<option value="">All Categories</option>' + categoryOptions;

    // Reset filters
    elements.docsTypeFilter.value = 'imported';
    elements.docsSearch.value = '';
    elements.docsCategoryFilter.value = '';

    await loadDocuments();
}

async function loadDocuments() {
    elements.documentsList.innerHTML = '<p class="loading-state">Loading documents...</p>';

    const docType = elements.docsTypeFilter.value;

    try {
        let url = '/pages/search?limit=500';
        if (docType === 'imported') {
            url += '&local_only=true';
        } else if (docType === 'web') {
            url += '&web_only=true';
        }

        const data = await apiRequest(url);
        allDocuments = data.pages || [];
        filterDocuments();
    } catch (error) {
        console.error('Failed to load documents:', error);
        elements.documentsList.innerHTML = '<p class="empty-state">Failed to load documents</p>';
    }
}

function filterDocuments() {
    const searchTerm = elements.docsSearch.value.toLowerCase().trim();
    const category = elements.docsCategoryFilter.value;

    let filtered = allDocuments;

    if (category) {
        filtered = filtered.filter(doc => doc.category === category);
    }

    if (searchTerm) {
        filtered = filtered.filter(doc =>
            (doc.title && doc.title.toLowerCase().includes(searchTerm)) ||
            (doc.section && doc.section.toLowerCase().includes(searchTerm))
        );
    }

    renderDocuments(filtered);
}

function renderDocuments(documents) {
    elements.docsCount.textContent = `${documents.length} document${documents.length !== 1 ? 's' : ''}`;

    if (documents.length === 0) {
        elements.documentsList.innerHTML = '<p class="empty-state">No documents found</p>';
        return;
    }

    elements.documentsList.innerHTML = documents.map(doc => `
        <div class="document-item" data-id="${doc.id}" data-url="${escapeHtml(doc.url || '')}">
            <div class="document-info">
                <span class="document-title">${escapeHtml(doc.title || 'Untitled')}</span>
                <span class="document-meta">
                    <span class="document-category">${escapeHtml(doc.category || 'Unknown')}</span>
                    ${doc.section ? `<span class="document-section">${escapeHtml(doc.section)}</span>` : ''}
                </span>
            </div>
            <div class="document-actions">
                <button class="btn btn-small doc-view-btn">View</button>
                <button class="btn btn-small btn-primary doc-summarize-btn">Summarize</button>
            </div>
        </div>
    `).join('');

    // Add event handlers
    elements.documentsList.querySelectorAll('.doc-view-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const item = btn.closest('.document-item');
            const url = item.dataset.url;
            if (url) {
                viewLocalDocument(url);
            } else {
                showToast('Cannot view: no URL available', 'error');
            }
        });
    });

    elements.documentsList.querySelectorAll('.doc-summarize-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const item = btn.closest('.document-item');
            const pageId = parseInt(item.dataset.id);
            quickSummarizeById(pageId, btn);
        });
    });
}
