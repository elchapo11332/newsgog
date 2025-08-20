// Global variables
let socket;
let tokensData = [];
let statsData = {};

// Initialize the application
function initializeDashboard() {
    console.log('Initializing Crypto Token Monitor Dashboard');
    
    // Initialize WebSocket connection
    initializeSocket();
    
    // Load initial data
    loadStats();
    loadTokens();
    
    // Set up periodic updates
    setInterval(updateTimeDisplays, 1000);
}

// Initialize Socket.IO connection
function initializeSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('Connected to server');
        updateConnectionStatus(true);
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        updateConnectionStatus(false);
    });
    
    socket.on('new_token', function(data) {
        console.log('New token received:', data);
        handleNewToken(data);
    });
    
    socket.on('stats_update', function(data) {
        console.log('Stats update received:', data);
        statsData = data;
        updateStatsDisplay();
    });
    
    socket.on('monitor_error', function(data) {
        console.log('Monitor error received:', data);
        showError(data.error);
    });
}

// Update connection status indicator
function updateConnectionStatus(connected) {
    const statusIndicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    
    if (connected) {
        statusIndicator.className = 'fas fa-circle text-success me-1';
        statusText.textContent = 'Connected';
    } else {
        statusIndicator.className = 'fas fa-circle text-danger me-1';
        statusText.textContent = 'Disconnected';
    }
}

// Load monitoring statistics
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        if (data.success) {
            statsData = data.stats;
            updateStatsDisplay();
        } else {
            throw new Error(data.error || 'Failed to load stats');
        }
    } catch (error) {
        console.error('Error loading stats:', error);
        showError('Failed to load monitoring statistics');
    }
}

// Load posted tokens
async function loadTokens() {
    try {
        showLoadingTokens();
        
        const response = await fetch('/api/tokens');
        const data = await response.json();
        
        if (data.success) {
            tokensData = data.tokens;
            displayTokens();
        } else {
            throw new Error(data.error || 'Failed to load tokens');
        }
    } catch (error) {
        console.error('Error loading tokens:', error);
        showError('Failed to load posted tokens');
        hideLoadingTokens();
    }
}

// Update statistics display
function updateStatsDisplay() {
    document.getElementById('tokens-found').textContent = statsData.total_tokens_found || 0;
    document.getElementById('tokens-posted').textContent = statsData.total_tokens_posted || 0;
    
    // Update monitor status
    const statusBadge = document.getElementById('monitor-status');
    if (statsData.is_running) {
        statusBadge.className = 'badge bg-success';
        statusBadge.textContent = 'Running';
    } else {
        statusBadge.className = 'badge bg-danger';
        statusBadge.textContent = 'Stopped';
    }
    
    updateTimeDisplays();
}

// Update time-based displays
function updateTimeDisplays() {
    if (statsData.last_check) {
        const lastCheck = new Date(statsData.last_check);
        const now = new Date();
        const diffSeconds = Math.floor((now - lastCheck) / 1000);
        
        let timeText;
        if (diffSeconds < 60) {
            timeText = `${diffSeconds}s ago`;
        } else if (diffSeconds < 3600) {
            timeText = `${Math.floor(diffSeconds / 60)}m ago`;
        } else {
            timeText = lastCheck.toLocaleTimeString();
        }
        
        document.getElementById('last-check').textContent = timeText;
    }
}

// Handle new token notification
function handleNewToken(tokenData) {
    // Add to tokens list
    tokensData.unshift(tokenData);
    displayTokens();
    
    // Show success notification
    showSuccess(`New token posted: ${tokenData.name}`);
}

// Display tokens list
function displayTokens() {
    const tokensList = document.getElementById('tokens-list');
    const emptyState = document.getElementById('empty-tokens');
    
    hideLoadingTokens();
    
    if (tokensData.length === 0) {
        tokensList.classList.add('d-none');
        emptyState.classList.remove('d-none');
        return;
    }
    
    emptyState.classList.add('d-none');
    tokensList.classList.remove('d-none');
    
    tokensList.innerHTML = tokensData.map(token => `
        <div class="border-bottom py-3">
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1">
                    <h6 class="mb-1">${escapeHtml(token.name)}</h6>
                    <p class="mb-1">
                        <small class="text-muted">Contract:</small>
                        <code class="ms-1">${escapeHtml(token.contract_address)}</code>
                    </p>
                    <small class="text-muted">
                        <i class="fas fa-clock me-1"></i>
                        ${formatDate(token.posted_at)}
                    </small>
                </div>
                <div class="text-end">
                    <span class="badge bg-success">
                        <i class="fas fa-check"></i>
                        Posted
                    </span>
                </div>
            </div>
        </div>
    `).join('');
}

// Show/hide loading states
function showLoadingTokens() {
    document.getElementById('loading-tokens').classList.remove('d-none');
    document.getElementById('tokens-list').classList.add('d-none');
    document.getElementById('empty-tokens').classList.add('d-none');
}

function hideLoadingTokens() {
    document.getElementById('loading-tokens').classList.add('d-none');
}

// Show error message
function showError(message) {
    const errorAlert = document.getElementById('error-alert');
    const errorMessage = document.getElementById('error-message');
    
    errorMessage.textContent = message;
    errorAlert.classList.remove('d-none');
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        errorAlert.classList.add('d-none');
    }, 5000);
}

// Show success message
function showSuccess(message) {
    const successAlert = document.getElementById('success-alert');
    const successMessage = document.getElementById('success-message');
    
    successMessage.textContent = message;
    successAlert.classList.remove('d-none');
    
    // Auto-hide after 3 seconds
    setTimeout(() => {
        successAlert.classList.add('d-none');
    }, 3000);
}

// Refresh tokens manually
function refreshTokens() {
    loadTokens();
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}
