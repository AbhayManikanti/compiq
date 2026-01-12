/**
 * CompIQ Frontend Application
 * Single Page Application for Competitor Intelligence
 */

// API Configuration - Set this to your Render.com backend URL after deployment
const API_BASE_URL = window.location.hostname === 'localhost' 
    ? '' // Use proxy in development
    : 'https://YOUR-RENDER-APP.onrender.com'; // Replace with your Render URL

// State Management
const state = {
    currentPage: 'dashboard',
    stats: null,
    alerts: [],
    competitors: [],
    battleCards: [],
    insights: [],
    winLoss: []
};

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    loadPage('dashboard');
    updateAlertsBadge();
});

// Navigation
function initNavigation() {
    document.querySelectorAll('[data-page]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const page = e.currentTarget.dataset.page;
            loadPage(page);
            
            // Update active state
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            e.currentTarget.classList.add('active');
        });
    });
}

// Load Page
async function loadPage(page) {
    state.currentPage = page;
    const content = document.getElementById('page-content');
    
    content.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';
    
    try {
        switch(page) {
            case 'dashboard':
                await renderDashboard(content);
                break;
            case 'alerts':
                await renderAlerts(content);
                break;
            case 'competitors':
                await renderCompetitors(content);
                break;
            case 'battle-cards':
                await renderBattleCards(content);
                break;
            case 'win-loss':
                await renderWinLoss(content);
                break;
            case 'insights':
                await renderInsights(content);
                break;
            case 'news':
                await renderNews(content);
                break;
            default:
                content.innerHTML = '<div class="empty-state"><i class="bi bi-question-circle"></i><p>Page not found</p></div>';
        }
    } catch (error) {
        console.error('Error loading page:', error);
        content.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-exclamation-triangle"></i>
                <p>Error loading content</p>
                <small class="text-muted">${error.message}</small>
                <button class="btn btn-outline-primary mt-3" onclick="loadPage('${page}')">
                    <i class="bi bi-arrow-clockwise"></i> Retry
                </button>
            </div>
        `;
    }
}

// API Calls
async function api(endpoint, options = {}) {
    const url = `${API_BASE_URL}/api${endpoint}`;
    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        }
    });
    
    if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
    }
    
    return response.json();
}

// Update Alerts Badge
async function updateAlertsBadge() {
    try {
        const stats = await api('/stats');
        const badge = document.getElementById('alerts-badge');
        badge.textContent = stats.active_alerts || 0;
        badge.style.display = stats.active_alerts > 0 ? 'inline' : 'none';
    } catch (e) {
        console.error('Failed to update badge:', e);
    }
}

// ============ PAGE RENDERERS ============

// Dashboard
async function renderDashboard(container) {
    const stats = await api('/stats');
    const recentAlerts = await api('/alerts?limit=5');
    
    container.innerHTML = `
        <div class="page-header">
            <h1><i class="bi bi-speedometer2"></i> Dashboard</h1>
            <button class="btn btn-primary" onclick="refreshDashboard()">
                <i class="bi bi-arrow-clockwise"></i> Refresh
            </button>
        </div>
        
        <div class="row g-4 mb-4">
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <div class="stat-value">${stats.total_competitors || 0}</div>
                            <div class="stat-label">Competitors</div>
                        </div>
                        <div class="stat-icon bg-primary bg-opacity-25">
                            <i class="bi bi-people text-primary"></i>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <div class="stat-value">${stats.active_alerts || 0}</div>
                            <div class="stat-label">Active Alerts</div>
                        </div>
                        <div class="stat-icon" style="background: rgba(243, 139, 168, 0.25)">
                            <i class="bi bi-bell-fill" style="color: var(--danger)"></i>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <div class="stat-value">${stats.total_insights || 0}</div>
                            <div class="stat-label">AI Insights</div>
                        </div>
                        <div class="stat-icon" style="background: rgba(168, 85, 247, 0.25)">
                            <i class="bi bi-lightbulb-fill" style="color: #a855f7"></i>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <div class="stat-value">${stats.news_items_today || 0}</div>
                            <div class="stat-label">News Today</div>
                        </div>
                        <div class="stat-icon" style="background: rgba(137, 180, 250, 0.25)">
                            <i class="bi bi-newspaper" style="color: var(--info)"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row g-4">
            <div class="col-lg-8">
                <div class="chart-container">
                    <h5 class="mb-4"><i class="bi bi-graph-up"></i> Alert Trend (Last 7 Days)</h5>
                    <canvas id="alertTrendChart" height="200"></canvas>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="chart-container">
                    <h5 class="mb-4"><i class="bi bi-pie-chart"></i> Alerts by Risk</h5>
                    <canvas id="riskDistChart" height="200"></canvas>
                </div>
            </div>
        </div>
        
        <div class="mt-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h5><i class="bi bi-bell"></i> Recent Alerts</h5>
                <a href="#" data-page="alerts" class="btn btn-sm btn-outline-primary">View All</a>
            </div>
            <div id="recent-alerts">
                ${renderAlertsList(recentAlerts.alerts || [])}
            </div>
        </div>
    `;
    
    // Initialize charts
    initDashboardCharts(stats);
}

function initDashboardCharts(stats) {
    // Alert Trend Chart
    const trendCtx = document.getElementById('alertTrendChart');
    if (trendCtx) {
        new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: ['6d ago', '5d ago', '4d ago', '3d ago', '2d ago', 'Yesterday', 'Today'],
                datasets: [{
                    label: 'Alerts',
                    data: stats.alert_trend || [0, 0, 0, 0, 0, 0, 0],
                    borderColor: '#4f46e5',
                    backgroundColor: 'rgba(79, 70, 229, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: '#313244' } },
                    x: { grid: { color: '#313244' } }
                }
            }
        });
    }
    
    // Risk Distribution Chart
    const riskCtx = document.getElementById('riskDistChart');
    if (riskCtx) {
        new Chart(riskCtx, {
            type: 'doughnut',
            data: {
                labels: ['Critical', 'High', 'Medium', 'Low'],
                datasets: [{
                    data: [
                        stats.risk_distribution?.critical || 0,
                        stats.risk_distribution?.high || 0,
                        stats.risk_distribution?.medium || 0,
                        stats.risk_distribution?.low || 0
                    ],
                    backgroundColor: ['#f38ba8', '#fab387', '#f9e2af', '#a6e3a1']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom', labels: { color: '#cdd6f4' } }
                }
            }
        });
    }
}

// Alerts Page
async function renderAlerts(container) {
    const data = await api('/alerts');
    
    container.innerHTML = `
        <div class="page-header">
            <h1><i class="bi bi-bell"></i> Alerts</h1>
            <div class="btn-group">
                <button class="btn btn-outline-secondary dropdown-toggle" data-bs-toggle="dropdown">
                    <i class="bi bi-download"></i> Export
                </button>
                <ul class="dropdown-menu dropdown-menu-dark">
                    <li><a class="dropdown-item" href="${API_BASE_URL}/api/export/alerts/pdf" target="_blank">PDF</a></li>
                    <li><a class="dropdown-item" href="${API_BASE_URL}/api/export/alerts/csv" target="_blank">CSV</a></li>
                </ul>
            </div>
        </div>
        
        <div class="row mb-4">
            <div class="col-md-4">
                <input type="text" class="form-control" placeholder="Search alerts..." id="alert-search">
            </div>
            <div class="col-md-3">
                <select class="form-select" id="risk-filter">
                    <option value="">All Risk Levels</option>
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                </select>
            </div>
        </div>
        
        <div id="alerts-list">
            ${renderAlertsList(data.alerts || [])}
        </div>
    `;
    
    // Add event listeners
    document.getElementById('alert-search')?.addEventListener('input', filterAlerts);
    document.getElementById('risk-filter')?.addEventListener('change', filterAlerts);
}

function renderAlertsList(alerts) {
    if (!alerts.length) {
        return `
            <div class="empty-state">
                <i class="bi bi-check-circle"></i>
                <p>No alerts found</p>
            </div>
        `;
    }
    
    return alerts.map(alert => `
        <div class="alert-card" onclick="showAlertDetail(${alert.id})">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <span class="risk-badge risk-${alert.risk_level}">${alert.risk_level}</span>
                    <span class="badge bg-secondary ms-2">${alert.signal_type}</span>
                </div>
                <small class="text-muted">${formatDate(alert.created_at)}</small>
            </div>
            <h6 class="mt-2 mb-1">${alert.title}</h6>
            <p class="text-muted mb-0 small">${alert.summary || 'No summary available'}</p>
            ${alert.competitor_name ? `<small class="text-info"><i class="bi bi-building"></i> ${alert.competitor_name}</small>` : ''}
        </div>
    `).join('');
}

async function filterAlerts() {
    const search = document.getElementById('alert-search')?.value || '';
    const risk = document.getElementById('risk-filter')?.value || '';
    
    const data = await api(`/alerts?search=${search}&risk=${risk}`);
    document.getElementById('alerts-list').innerHTML = renderAlertsList(data.alerts || []);
}

async function showAlertDetail(id) {
    try {
        const alert = await api(`/alerts/${id}`);
        const modal = new bootstrap.Modal(getOrCreateModal());
        
        document.getElementById('modal-title').textContent = alert.title;
        document.getElementById('modal-body').innerHTML = `
            <div class="mb-3">
                <span class="risk-badge risk-${alert.risk_level}">${alert.risk_level}</span>
                <span class="badge bg-secondary ms-2">${alert.signal_type}</span>
            </div>
            <p>${alert.summary || 'No summary available'}</p>
            <hr>
            <h6>Details</h6>
            <pre class="bg-dark p-3 rounded" style="max-height: 300px; overflow: auto;">${JSON.stringify(alert.details || {}, null, 2)}</pre>
            ${alert.source_url ? `<a href="${alert.source_url}" target="_blank" class="btn btn-outline-primary btn-sm"><i class="bi bi-link"></i> View Source</a>` : ''}
        `;
        
        modal.show();
    } catch (e) {
        showToast('Failed to load alert details', 'error');
    }
}

// Competitors Page
async function renderCompetitors(container) {
    const data = await api('/competitors');
    
    container.innerHTML = `
        <div class="page-header">
            <h1><i class="bi bi-people"></i> Competitors</h1>
            <button class="btn btn-primary" onclick="showAddCompetitorModal()">
                <i class="bi bi-plus"></i> Add Competitor
            </button>
        </div>
        
        <div class="row g-4">
            ${(data.competitors || []).map(comp => `
                <div class="col-md-4 col-lg-3">
                    <div class="competitor-card">
                        <div class="logo">
                            ${comp.logo_url ? `<img src="${comp.logo_url}" alt="${comp.name}" style="width:100%;height:100%;object-fit:cover;border-radius:50%">` : comp.name.charAt(0)}
                        </div>
                        <h6>${comp.name}</h6>
                        <small class="text-muted">${comp.description || 'No description'}</small>
                        <div class="mt-3">
                            <span class="badge bg-danger">${comp.alert_count || 0} alerts</span>
                            <span class="badge bg-secondary">${comp.url_count || 0} URLs</span>
                        </div>
                        <a href="${comp.website || '#'}" target="_blank" class="btn btn-sm btn-outline-primary mt-3">
                            <i class="bi bi-globe"></i> Website
                        </a>
                    </div>
                </div>
            `).join('') || '<div class="col-12"><div class="empty-state"><i class="bi bi-people"></i><p>No competitors added yet</p></div></div>'}
        </div>
    `;
}

// Battle Cards Page
async function renderBattleCards(container) {
    const data = await api('/battle-cards');
    
    container.innerHTML = `
        <div class="page-header">
            <h1><i class="bi bi-card-checklist"></i> Battle Cards</h1>
            <button class="btn btn-primary" onclick="showAddBattleCardModal()">
                <i class="bi bi-plus"></i> Create Battle Card
            </button>
        </div>
        
        <div class="row g-4">
            ${(data.battle_cards || []).map(card => `
                <div class="col-lg-6">
                    <div class="battle-card">
                        <div class="d-flex justify-content-between align-items-start">
                            <h5>${card.competitor_name || 'Unknown'}</h5>
                            <small class="text-muted">Updated: ${formatDate(card.updated_at)}</small>
                        </div>
                        <p class="text-muted">${card.overview || 'No overview'}</p>
                        <div class="row mt-3">
                            <div class="col-md-6">
                                <h6 class="text-success"><i class="bi bi-check-circle"></i> Strengths</h6>
                                <ul class="small">
                                    ${(card.strengths || []).slice(0,3).map(s => `<li>${s}</li>`).join('') || '<li>None listed</li>'}
                                </ul>
                            </div>
                            <div class="col-md-6">
                                <h6 class="text-danger"><i class="bi bi-x-circle"></i> Weaknesses</h6>
                                <ul class="small">
                                    ${(card.weaknesses || []).slice(0,3).map(w => `<li>${w}</li>`).join('') || '<li>None listed</li>'}
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            `).join('') || '<div class="col-12"><div class="empty-state"><i class="bi bi-card-checklist"></i><p>No battle cards created yet</p></div></div>'}
        </div>
    `;
}

// Win/Loss Page
async function renderWinLoss(container) {
    const data = await api('/win-loss');
    
    const records = data.records || [];
    const wins = records.filter(r => r.outcome === 'won').length;
    const losses = records.filter(r => r.outcome === 'lost').length;
    const winRate = records.length ? Math.round((wins / records.length) * 100) : 0;
    
    container.innerHTML = `
        <div class="page-header">
            <h1><i class="bi bi-trophy"></i> Win/Loss Analysis</h1>
            <button class="btn btn-primary" onclick="showAddWinLossModal()">
                <i class="bi bi-plus"></i> Add Record
            </button>
        </div>
        
        <div class="row g-4 mb-4">
            <div class="col-md-4">
                <div class="stat-card text-center">
                    <div class="stat-value text-success">${wins}</div>
                    <div class="stat-label">Wins</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="stat-card text-center">
                    <div class="stat-value text-danger">${losses}</div>
                    <div class="stat-label">Losses</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="stat-card text-center">
                    <div class="stat-value" style="color: var(--primary-color)">${winRate}%</div>
                    <div class="stat-label">Win Rate</div>
                </div>
            </div>
        </div>
        
        <div class="table-dark-custom">
            <table class="table table-hover mb-0">
                <thead>
                    <tr>
                        <th>Deal</th>
                        <th>Competitor</th>
                        <th>Outcome</th>
                        <th>Value</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
                    ${records.map(r => `
                        <tr>
                            <td>${r.deal_name || 'N/A'}</td>
                            <td>${r.competitor_name || 'N/A'}</td>
                            <td>
                                <span class="badge ${r.outcome === 'won' ? 'bg-success' : 'bg-danger'}">
                                    ${r.outcome}
                                </span>
                            </td>
                            <td>${r.deal_value ? '$' + r.deal_value.toLocaleString() : 'N/A'}</td>
                            <td>${formatDate(r.close_date)}</td>
                        </tr>
                    `).join('') || '<tr><td colspan="5" class="text-center text-muted">No records yet</td></tr>'}
                </tbody>
            </table>
        </div>
    `;
}

// Insights Page
async function renderInsights(container) {
    const data = await api('/insights');
    
    container.innerHTML = `
        <div class="page-header">
            <h1><i class="bi bi-lightbulb"></i> AI Insights</h1>
            <button class="btn btn-primary" onclick="generateInsight()">
                <i class="bi bi-magic"></i> Generate Insight
            </button>
        </div>
        
        <div class="row g-4">
            ${(data.insights || []).map(insight => `
                <div class="col-lg-6">
                    <div class="insight-card">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <span class="ai-badge"><i class="bi bi-robot"></i> AI Generated</span>
                            <small class="text-muted">${formatDate(insight.created_at)}</small>
                        </div>
                        <h6>${insight.title || 'Insight'}</h6>
                        <p class="text-muted small">${(insight.content || '').substring(0, 200)}...</p>
                        <button class="btn btn-sm btn-outline-primary" onclick="showInsightDetail(${insight.id})">
                            Read More
                        </button>
                    </div>
                </div>
            `).join('') || '<div class="col-12"><div class="empty-state"><i class="bi bi-lightbulb"></i><p>No insights generated yet</p></div></div>'}
        </div>
    `;
}

async function generateInsight() {
    showToast('Generating insight...', 'info');
    try {
        await api('/insights/generate', { method: 'POST' });
        showToast('Insight generated!', 'success');
        loadPage('insights');
    } catch (e) {
        showToast('Failed to generate insight', 'error');
    }
}

// News Page
async function renderNews(container) {
    const data = await api('/news');
    
    container.innerHTML = `
        <div class="page-header">
            <h1><i class="bi bi-newspaper"></i> News Feed</h1>
            <button class="btn btn-primary" onclick="refreshNews()">
                <i class="bi bi-arrow-clockwise"></i> Refresh
            </button>
        </div>
        
        <div class="row g-3">
            ${(data.news || []).map(item => `
                <div class="col-12">
                    <div class="alert-card">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <span class="badge bg-secondary">${item.competitor_name || 'General'}</span>
                                <span class="badge bg-info">${item.source || 'News'}</span>
                            </div>
                            <small class="text-muted">${formatDate(item.published_at)}</small>
                        </div>
                        <h6 class="mt-2">${item.title}</h6>
                        <p class="text-muted small mb-2">${item.summary || ''}</p>
                        <a href="${item.url}" target="_blank" class="btn btn-sm btn-outline-primary">
                            <i class="bi bi-link"></i> Read Article
                        </a>
                    </div>
                </div>
            `).join('') || '<div class="col-12"><div class="empty-state"><i class="bi bi-newspaper"></i><p>No news items yet</p></div></div>'}
        </div>
    `;
}

async function refreshNews() {
    showToast('Fetching latest news...', 'info');
    try {
        await api('/news/fetch', { method: 'POST' });
        showToast('News updated!', 'success');
        loadPage('news');
    } catch (e) {
        showToast('Failed to fetch news', 'error');
    }
}

// ============ UTILITIES ============

function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function getOrCreateModal() {
    let modal = document.getElementById('global-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'global-modal';
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="modal-title"></h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body" id="modal-body"></div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    return modal;
}

function showToast(message, type = 'info') {
    const container = document.querySelector('.toast-container');
    const toast = document.createElement('div');
    toast.className = `toast show bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'}`;
    toast.innerHTML = `
        <div class="toast-body text-white">
            ${message}
        </div>
    `;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function refreshDashboard() {
    loadPage('dashboard');
}

// Modal handlers for adding entities
function showAddCompetitorModal() {
    const modal = new bootstrap.Modal(getOrCreateModal());
    document.getElementById('modal-title').textContent = 'Add Competitor';
    document.getElementById('modal-body').innerHTML = `
        <form id="add-competitor-form">
            <div class="mb-3">
                <label class="form-label">Name</label>
                <input type="text" class="form-control" name="name" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Website</label>
                <input type="url" class="form-control" name="website" placeholder="https://...">
            </div>
            <div class="mb-3">
                <label class="form-label">Description</label>
                <textarea class="form-control" name="description" rows="3"></textarea>
            </div>
            <button type="submit" class="btn btn-primary">Add Competitor</button>
        </form>
    `;
    
    document.getElementById('add-competitor-form').onsubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        try {
            await api('/competitors', {
                method: 'POST',
                body: JSON.stringify(Object.fromEntries(formData))
            });
            modal.hide();
            showToast('Competitor added!', 'success');
            loadPage('competitors');
        } catch (err) {
            showToast('Failed to add competitor', 'error');
        }
    };
    
    modal.show();
}

async function showInsightDetail(id) {
    try {
        const insight = await api(`/insights/${id}`);
        const modal = new bootstrap.Modal(getOrCreateModal());
        
        document.getElementById('modal-title').textContent = insight.title || 'Insight';
        document.getElementById('modal-body').innerHTML = `
            <div class="mb-3">
                <span class="ai-badge"><i class="bi bi-robot"></i> AI Generated</span>
                <small class="text-muted ms-2">${formatDate(insight.created_at)}</small>
            </div>
            <div class="insight-content">
                ${insight.content || 'No content available'}
            </div>
        `;
        
        modal.show();
    } catch (e) {
        showToast('Failed to load insight', 'error');
    }
}
