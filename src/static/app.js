// Global state
let currentOfficers = [];
let currentEvents = [];

// API base URL
const API_BASE = '/api';

// Page navigation
function showPage(pageId) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    
    // Show selected page
    document.getElementById(pageId).classList.add('active');
    
    // Update navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
}

function showHome() {
    showPage('home-page');
    document.querySelector('.nav-link[onclick="showHome()"]').classList.add('active');
    loadEvents(); // Load events for filter dropdown
}

function showEvents() {
    showPage('events-page');
    document.querySelector('.nav-link[onclick="showEvents()"]').classList.add('active');
    loadEventsPage();
}

function showAddOfficer() {
    showPage('add-officer-page');
    document.querySelector('.nav-link[onclick="showAddOfficer()"]').classList.add('active');
}

function showAddEvent() {
    showPage('add-event-page');
    document.querySelector('.nav-link[onclick="showAddEvent()"]').classList.add('active');
}

function showOfficerProfile(officerId) {
    showPage('officer-page');
    loadOfficerProfile(officerId);
}

function showEventDetail(eventId) {
    showPage('event-detail-page');
    loadEventDetail(eventId);
}

// API functions
async function apiRequest(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || `HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Search functions
async function searchByCollar() {
    const collarNumber = document.getElementById('collar-search').value.trim();
    if (!collarNumber) {
        showError('Please enter a collar number');
        return;
    }
    
    try {
        showLoading();
        const officer = await apiRequest(`/search/collar/${encodeURIComponent(collarNumber)}`);
        displaySearchResults([officer]);
    } catch (error) {
        showError(error.message);
    }
}

async function searchByBreed() {
    const breed = document.getElementById('breed-search').value.trim();
    if (!breed) {
        showError('Please enter a breed/force name');
        return;
    }
    
    try {
        showLoading();
        const officers = await apiRequest(`/search/breed/${encodeURIComponent(breed)}`);
        displaySearchResults(officers);
    } catch (error) {
        showError(error.message);
    }
}

async function filterByEvent() {
    const eventId = document.getElementById('event-filter').value;
    if (!eventId) {
        clearResults();
        return;
    }
    
    try {
        showLoading();
        const event = await apiRequest(`/events/${eventId}`);
        const officers = event.officers_present || [];
        displaySearchResults(officers);
    } catch (error) {
        showError(error.message);
    }
}

// Display functions
function displaySearchResults(officers) {
    const resultsGrid = document.getElementById('results-grid');
    
    if (!officers || officers.length === 0) {
        resultsGrid.innerHTML = `
            <div class="empty-state">
                <h3>No cats found</h3>
                <p>No officers match your search criteria.</p>
            </div>
        `;
        return;
    }
    
    resultsGrid.innerHTML = officers.map(officer => `
        <div class="result-item" onclick="showOfficerProfile(${officer.id})">
            <div class="result-photo">
                ${officer.photo_url ? 
                    `<img src="${officer.photo_url}" alt="Officer ${officer.collar_number}" class="result-photo">` :
                    'No Photo'
                }
            </div>
            <div class="result-info">
                <h3>Collar #${officer.collar_number}</h3>
                <p><strong>Breed:</strong> ${officer.breed}</p>
                ${officer.role ? `<p><strong>Role:</strong> ${officer.role}</p>` : ''}
            </div>
            <div class="result-meta">
                <p>Added: ${formatDate(officer.created_at)}</p>
            </div>
        </div>
    `).join('');
}

async function loadOfficerProfile(officerId) {
    try {
        const officer = await apiRequest(`/officers/${officerId}`);
        const profileContainer = document.getElementById('officer-profile');
        
        profileContainer.innerHTML = `
            <a href="#" onclick="showHome()" class="back-btn">← Back to Search</a>
            
            <div class="profile-header">
                <div class="profile-photo ${!officer.photo_url ? 'placeholder' : ''}">
                    ${officer.photo_url ? 
                        `<img src="${officer.photo_url}" alt="Officer ${officer.collar_number}" class="profile-photo">` :
                        'No Photo'
                    }
                </div>
                <h1>Collar #${officer.collar_number}</h1>
                <p>${officer.breed}</p>
            </div>
            
            <div class="profile-content">
                <div class="profile-grid">
                    <div class="profile-section">
                        <h3>Basic Information</h3>
                        <div class="profile-field">
                            <label>Collar Number</label>
                            <p>${officer.collar_number}</p>
                        </div>
                        <div class="profile-field">
                            <label>Breed/Pride</label>
                            <p>${officer.breed}</p>
                        </div>
                        ${officer.role ? `
                            <div class="profile-field">
                                <label>Role</label>
                                <p>${officer.role}</p>
                            </div>
                        ` : ''}
                    </div>
                    
                    <div class="profile-section">
                        <h3>Description</h3>
                        <div class="profile-field">
                            <p>${officer.description || 'No description available'}</p>
                        </div>
                        ${officer.equipment ? `
                            <div class="profile-field">
                                <label>Equipment</label>
                                <p>${officer.equipment}</p>
                            </div>
                        ` : ''}
                    </div>
                </div>
                
                <div class="event-history">
                    <h3>Where This Cat Has Been Spotted</h3>
                    ${officer.event_history && officer.event_history.length > 0 ? 
                        officer.event_history.map(event => `
                            <div class="event-item">
                                <h4>${event.name}</h4>
                                <div class="event-meta">
                                    <strong>Date:</strong> ${formatDate(event.date)} | 
                                    <strong>Location:</strong> ${event.location}
                                </div>
                                ${event.activity_log ? `
                                    <div class="event-activity">
                                        <strong>Documented Activity:</strong> ${event.activity_log}
                                    </div>
                                ` : ''}
                                ${event.source_links ? `
                                    <div class="event-activity">
                                        <strong>Source Links:</strong> ${event.source_links}
                                    </div>
                                ` : ''}
                            </div>
                        `).join('') :
                        '<div class="empty-state"><p>No events documented for this officer yet.</p></div>'
                    }
                </div>
            </div>
        `;
    } catch (error) {
        document.getElementById('officer-profile').innerHTML = `
            <div class="error">Error loading officer profile: ${error.message}</div>
        `;
    }
}

async function loadEventsPage() {
    try {
        const events = await apiRequest('/events');
        const eventsGrid = document.getElementById('events-grid');
        
        if (!events || events.length === 0) {
            eventsGrid.innerHTML = `
                <div class="empty-state">
                    <h3>No events found</h3>
                    <p>No events have been documented yet.</p>
                </div>
            `;
            return;
        }
        
        eventsGrid.innerHTML = events.map(event => `
            <div class="event-card" onclick="showEventDetail(${event.id})">
                <h3>${event.name}</h3>
                <div class="date">${formatDate(event.date)}</div>
                <div class="location">${event.location}</div>
                <div class="description">${event.description || ''}</div>
                <div class="officer-count">Click to view cats present</div>
            </div>
        `).join('');
    } catch (error) {
        document.getElementById('events-grid').innerHTML = `
            <div class="error">Error loading events: ${error.message}</div>
        `;
    }
}

async function loadEventDetail(eventId) {
    try {
        const event = await apiRequest(`/events/${eventId}`);
        const eventDetailContainer = document.getElementById('event-detail');
        
        eventDetailContainer.innerHTML = `
            <a href="#" onclick="showEvents()" class="back-btn">← Back to Events</a>
            
            <div class="profile-header">
                <h1>${event.name}</h1>
                <p>${formatDate(event.date)} | ${event.location}</p>
            </div>
            
            <div class="profile-content">
                ${event.description ? `
                    <div class="profile-section">
                        <h3>Event Description</h3>
                        <p>${event.description}</p>
                    </div>
                ` : ''}
                
                <div class="profile-section">
                    <h3>Cats Spotted at This Event</h3>
                    ${event.officers_present && event.officers_present.length > 0 ? 
                        `<div class="results-grid">
                            ${event.officers_present.map(officer => `
                                <div class="result-item" onclick="showOfficerProfile(${officer.id})">
                                    <div class="result-photo">
                                        ${officer.photo_url ? 
                                            `<img src="${officer.photo_url}" alt="Officer ${officer.collar_number}" class="result-photo">` :
                                            'No Photo'
                                        }
                                    </div>
                                    <div class="result-info">
                                        <h3>Collar #${officer.collar_number}</h3>
                                        <p><strong>Breed:</strong> ${officer.breed}</p>
                                        ${officer.activity_log ? `<p><strong>Activity:</strong> ${officer.activity_log}</p>` : ''}
                                    </div>
                                </div>
                            `).join('')}
                        </div>` :
                        '<div class="empty-state"><p>No officers documented at this event yet.</p></div>'
                    }
                </div>
            </div>
        `;
    } catch (error) {
        document.getElementById('event-detail').innerHTML = `
            <div class="error">Error loading event details: ${error.message}</div>
        `;
    }
}

async function loadEvents() {
    try {
        const events = await apiRequest('/events');
        const eventFilter = document.getElementById('event-filter');
        
        eventFilter.innerHTML = '<option value="">All Events</option>' +
            events.map(event => `
                <option value="${event.id}">${event.name} (${formatDate(event.date)})</option>
            `).join('');
    } catch (error) {
        console.error('Error loading events for filter:', error);
    }
}

// Form handlers
document.getElementById('add-officer-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Get selected events
    const selectedEvents = Array.from(document.querySelectorAll('#events-checkboxes input[type="checkbox"]:checked'))
        .map(checkbox => parseInt(checkbox.value));
    
    const formData = {
        collar_number: document.getElementById('collar-number').value,
        breed: document.getElementById('breed').value,
        photo_url: document.getElementById('photo-url').value || null,
        role: document.getElementById('role').value || null,
        description: document.getElementById('description').value || null,
        equipment: document.getElementById('equipment').value || null,
        event_ids: selectedEvents
    };
    
    try {
        await apiRequest('/officers', {
            method: 'POST',
            body: JSON.stringify(formData)
        });
        
        showSuccess('Officer added successfully!');
        document.getElementById('add-officer-form').reset();
        // Reload events checkboxes to clear selections
        loadEventsForForm();
    } catch (error) {
        showError(error.message);
    }
});

document.getElementById('add-event-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
        name: document.getElementById('event-name').value,
        date: document.getElementById('event-date').value,
        location: document.getElementById('event-location').value,
        description: document.getElementById('event-description').value || null
    };
    
    try {
        await apiRequest('/events', {
            method: 'POST',
            body: JSON.stringify(formData)
        });
        
        showSuccess('Event added successfully!');
        document.getElementById('add-event-form').reset();
        loadEvents(); // Refresh events dropdown
    } catch (error) {
        showError(error.message);
    }
});

// Utility functions
function formatDate(dateString) {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function showLoading() {
    document.getElementById('results-grid').innerHTML = `
        <div class="loading">
            <p>Searching...</p>
        </div>
    `;
}

function clearResults() {
    document.getElementById('results-grid').innerHTML = '';
}

function showError(message) {
    document.getElementById('results-grid').innerHTML = `
        <div class="error">
            <strong>Error:</strong> ${message}
        </div>
    `;
}

function showSuccess(message) {
    // Create success message element
    const successDiv = document.createElement('div');
    successDiv.className = 'success';
    successDiv.innerHTML = message;
    
    // Insert at top of current page
    const activePage = document.querySelector('.page.active');
    activePage.insertBefore(successDiv, activePage.firstChild);
    
    // Remove after 5 seconds
    setTimeout(() => {
        successDiv.remove();
    }, 5000);
}

async function loadEventsForForm() {
    try {
        const events = await apiRequest('/events');
        const eventsContainer = document.getElementById('events-checkboxes');
        
        if (events.length === 0) {
            eventsContainer.innerHTML = '<p class="form-help">No events available. Add events first to associate officers with them.</p>';
            return;
        }
        
        eventsContainer.innerHTML = events.map(event => `
            <div class="checkbox-item">
                <input type="checkbox" id="event-${event.id}" value="${event.id}">
                <label for="event-${event.id}">${event.name} (${formatDate(event.date)}) - ${event.location}</label>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading events for form:', error);
        document.getElementById('events-checkboxes').innerHTML = '<p class="form-help">Error loading events.</p>';
    }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    showHome();
    loadEventsForForm(); // Load events for the Add Cat form
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        const activeElement = document.activeElement;
        if (activeElement.id === 'collar-search') {
            searchByCollar();
        } else if (activeElement.id === 'breed-search') {
            searchByBreed();
        }
    }
});


// Logo Animation - Palestine Catwatch -> Copwatch -> Catwatch sequence
function initLogoAnimation() {
    const logoText = document.getElementById('logo-text');
    
    function animationCycle() {
        // Start with Catwatch (default state)
        logoText.textContent = 'Catwatch';
        logoText.className = 'logo-text catwatch';
        
        // After 2 seconds, switch to Copwatch for 0.75 seconds
        setTimeout(() => {
            logoText.textContent = 'Copwatch';
            logoText.className = 'logo-text copwatch';
            
            // After 0.75 seconds, blink back to Catwatch for 0.2 seconds
            setTimeout(() => {
                logoText.textContent = 'Catwatch';
                logoText.className = 'logo-text catwatch';
                
                // After 0.2 seconds, start the cycle again
                setTimeout(() => {
                    animationCycle();
                }, 200); // 0.2 seconds
            }, 750); // 0.75 seconds
        }, 2000); // 2 seconds initial display
    }
    
    // Start the animation cycle
    animationCycle();
}

// News Ticker Functionality
class NewsTicker {
    constructor() {
        this.newsItems = [
            "🔴 BREAKING: UN Commission finds Israel committing genocide in Gaza",
            "📍 LIVE: Over 65,000 Palestinians killed in Israel's war on Gaza",
            "⚡ UPDATE: Israeli forces intensify Gaza City ground offensive",
            "🚨 ALERT: Thousands of Palestinians flee Gaza City as troops advance",
            "📢 PROTEST: Week of Palestine Action protests begins across UK",
            "🇬🇧 UK: Mass demonstrations continue in London over Palestine solidarity",
            "🇪🇺 EUROPE: Pro-Palestine protests spread across European capitals",
            "🌍 GLOBAL: International condemnation grows over Gaza offensive",
            "🏥 CRISIS: Gaza hospitals overwhelmed as casualties mount",
            "🆘 URGENT: Humanitarian crisis deepens in Gaza Strip",
            "📊 REPORT: UN documents systematic violations in occupied territories",
            "🔥 LIVE: 'Gaza is burning' - Israeli Defense Minister on new operation",
            "🚫 BANNED: Palestine Action faces restrictions amid growing protests",
            "✊ SOLIDARITY: Global movement for Palestinian rights gains momentum",
            "📱 SOCIAL: #FreePalestine trends worldwide as awareness spreads"
        ];
        this.currentIndex = 0;
        this.tickerElement = document.getElementById('ticker-content');
        this.init();
    }
    
    init() {
        this.updateTicker();
        // Update ticker every 15 seconds
        setInterval(() => {
            this.updateTicker();
        }, 15000);
    }
    
    updateTicker() {
        const newsItem = this.newsItems[this.currentIndex];
        this.tickerElement.innerHTML = `<span class="ticker-item">${newsItem}</span>`;
        this.currentIndex = (this.currentIndex + 1) % this.newsItems.length;
    }
    
    // Method to add real-time news (could be connected to news API)
    addNewsItem(newsText) {
        this.newsItems.unshift(`🔴 BREAKING: ${newsText}`);
        // Keep only last 20 items to prevent memory issues
        if (this.newsItems.length > 20) {
            this.newsItems = this.newsItems.slice(0, 20);
        }
    }
}

// Initialize news ticker
let newsTicker;

// Enhanced initialization
document.addEventListener('DOMContentLoaded', () => {
    showHome();
    loadEventsForForm();
    initLogoAnimation();
    newsTicker = new NewsTicker();
});

// Optional: Function to fetch real news from API (placeholder for future enhancement)
async function fetchLatestNews() {
    try {
        // This could be connected to a news API in the future
        // For now, we use the predefined news items
        console.log('News ticker running with predefined updates');
    } catch (error) {
        console.error('Error fetching news:', error);
    }
}

