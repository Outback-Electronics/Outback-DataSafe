const API_BASE = '/api';

// State
let currentUser = null;
let currentPath = [];
let currentParentId = null;
let authToken = localStorage.getItem('authToken');
let selectedTier = 'free';
let registrationData = {};

// DOM Elements
const loginPage = document.getElementById('login-page');
const mainApp = document.getElementById('main-app');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const fileGrid = document.getElementById('file-grid');
const photoGrid = document.getElementById('photo-grid');
const breadcrumb = document.getElementById('breadcrumb');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    if (authToken) {
        checkAuth();
    }
});

function setupEventListeners() {
    // Auth tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            if (btn.dataset.tab === 'login') {
                loginForm.classList.remove('hidden');
                registerForm.classList.add('hidden');
            } else {
                loginForm.classList.add('hidden');
                registerForm.classList.remove('hidden');
            }
        });
    });

    // Login form
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        
        try {
            const response = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            if (response.ok) {
                const data = await response.json();
                authToken = data.access_token;
                localStorage.setItem('authToken', authToken);
                await checkAuth();
            } else {
                alert('Login failed');
            }
        } catch (error) {
            alert('Login error: ' + error.message);
        }
    });

    // Register form - continue to plans
    document.getElementById('continue-to-plans').addEventListener('click', async (e) => {
        e.preventDefault();
        const username = document.getElementById('register-username').value;
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;
        const confirmPassword = document.getElementById('register-confirm-password').value;
        
        if (password !== confirmPassword) {
            alert('Passwords do not match');
            return;
        }
        
        // Store registration data
        registrationData = { username, email, password };
        
        // Load and display plans
        await loadPlans();
        
        // Show plans form
        registerForm.classList.add('hidden');
        document.getElementById('plans-form').classList.remove('hidden');
    });

    // Back to register
    document.getElementById('back-to-register').addEventListener('click', () => {
        document.getElementById('plans-form').classList.add('hidden');
        registerForm.classList.remove('hidden');
    });

    // Complete registration
    document.getElementById('complete-registration').addEventListener('click', async (e) => {
        e.preventDefault();
        
        try {
            const response = await fetch(`${API_BASE}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    ...registrationData,
                    tier: selectedTier
                })
            });
            
            if (response.ok) {
                alert('Registration successful! Please login.');
                document.querySelector('[data-tab="login"]').click();
                document.getElementById('plans-form').classList.add('hidden');
                registerForm.classList.remove('hidden');
            } else {
                alert('Registration failed');
            }
        } catch (error) {
            alert('Registration error: ' + error.message);
        }
    });

    // Logout
    document.getElementById('logout-btn').addEventListener('click', () => {
        localStorage.removeItem('authToken');
        authToken = null;
        currentUser = null;
        loginPage.classList.remove('hidden');
        mainApp.classList.add('hidden');
    });

    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.getElementById(`${item.dataset.view}-view`).classList.add('active');
            
            if (item.dataset.view === 'files') {
                loadFiles();
            } else if (item.dataset.view === 'photos') {
                loadPhotos();
            } else if (item.dataset.view === 'settings') {
                loadSettings();
            }
        });
    });

    // File upload
    document.getElementById('upload-btn').addEventListener('click', () => {
        document.getElementById('file-input').click();
    });

    document.getElementById('file-input').addEventListener('change', async (e) => {
        const files = Array.from(e.target.files);
        for (const file of files) {
            await uploadFile(file);
        }
        loadFiles();
    });

    // New folder
    document.getElementById('new-folder-btn').addEventListener('click', () => {
        const folderName = prompt('Enter folder name:');
        if (folderName) {
            createFolder(folderName);
        }
    });

    // Photo upload
    document.getElementById('upload-photo-btn').addEventListener('click', () => {
        document.getElementById('photo-input').click();
    });

    document.getElementById('photo-input').addEventListener('change', async (e) => {
        const files = Array.from(e.target.files);
        for (const file of files) {
            await uploadPhoto(file);
        }
        loadPhotos();
    });

    // Photo modal
    document.querySelector('.close-btn').addEventListener('click', () => {
        document.getElementById('photo-modal').classList.add('hidden');
    });
}

async function checkAuth() {
    try {
        const response = await fetch(`${API_BASE}/auth/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            currentUser = await response.json();
            loginPage.classList.add('hidden');
            mainApp.classList.remove('hidden');
            updateQuotaDisplay();
            loadFiles();
        } else {
            localStorage.removeItem('authToken');
            authToken = null;
        }
    } catch (error) {
        console.error('Auth check failed:', error);
    }
}

function updateQuotaDisplay() {
    if (!currentUser) return;
    
    const usedGB = (currentUser.used_space / (1024 ** 3)).toFixed(2);
    const quotaGB = (currentUser.quota / (1024 ** 3)).toFixed(2);
    const percentage = (currentUser.used_space / currentUser.quota) * 100;
    
    document.getElementById('quota-used').style.width = `${percentage}%`;
    document.getElementById('quota-text').textContent = `${usedGB} GB / ${quotaGB} GB`;
}

async function loadFiles() {
    try {
        const response = await fetch(`${API_BASE}/files?parent_id=${currentParentId || ''}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const files = await response.json();
            renderFiles(files);
            updateBreadcrumb();
        }
    } catch (error) {
        console.error('Failed to load files:', error);
    }
}

function renderFiles(files) {
    fileGrid.innerHTML = '';
    
    files.forEach(file => {
        const item = document.createElement('div');
        item.className = 'file-item';
        
        const icon = file.is_directory ? '📁' : getFileIcon(file.mime_type);
        
        item.innerHTML = `
            <div class="file-icon">${icon}</div>
            <div class="file-name">${file.original_filename}</div>
            <div class="file-size">${file.is_directory ? '' : formatFileSize(file.file_size)}</div>
        `;
        
        item.addEventListener('click', () => {
            if (file.is_directory) {
                currentPath.push(file);
                currentParentId = file.id;
                loadFiles();
            } else {
                downloadFile(file.id);
            }
        });
        
        fileGrid.appendChild(item);
    });
}

function getFileIcon(mimeType) {
    if (!mimeType) return '📄';
    if (mimeType.startsWith('image/')) return '🖼️';
    if (mimeType.startsWith('video/')) return '🎬';
    if (mimeType.startsWith('audio/')) return '🎵';
    if (mimeType.includes('pdf')) return '📕';
    if (mimeType.includes('word')) return '📘';
    if (mimeType.includes('excel')) return '📗';
    if (mimeType.includes('powerpoint')) return '📙';
    return '📄';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function updateBreadcrumb() {
    breadcrumb.innerHTML = '';
    
    const rootSpan = document.createElement('span');
    rootSpan.textContent = 'Home';
    rootSpan.addEventListener('click', () => {
        currentPath = [];
        currentParentId = null;
        loadFiles();
    });
    breadcrumb.appendChild(rootSpan);
    
    currentPath.forEach((folder, index) => {
        breadcrumb.appendChild(document.createTextNode(' / '));
        const span = document.createElement('span');
        span.textContent = folder.original_filename;
        span.addEventListener('click', () => {
            currentPath = currentPath.slice(0, index + 1);
            currentParentId = folder.id;
            loadFiles();
        });
        breadcrumb.appendChild(span);
    });
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    if (currentParentId) {
        formData.append('parent_id', currentParentId);
    }
    
    try {
        const response = await fetch(`${API_BASE}/files`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` },
            body: formData
        });
        
        if (response.ok) {
            await checkAuth(); // Update quota
        } else {
            alert('Upload failed');
        }
    } catch (error) {
        console.error('Upload error:', error);
    }
}

async function createFolder(name) {
    try {
        const response = await fetch(`${API_BASE}/files/directory`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: name,
                parent_id: currentParentId,
                is_directory: true
            })
        });
        
        if (response.ok) {
            loadFiles();
        } else {
            alert('Failed to create folder');
        }
    } catch (error) {
        console.error('Create folder error:', error);
    }
}

async function downloadFile(fileId) {
    try {
        const response = await fetch(`${API_BASE}/files/${fileId}/download`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = response.headers.get('Content-Disposition')?.split('filename=')[1] || 'file';
            a.click();
            window.URL.revokeObjectURL(url);
        }
    } catch (error) {
        console.error('Download error:', error);
    }
}

async function loadPhotos() {
    try {
        const response = await fetch(`${API_BASE}/photos`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const photos = await response.json();
            renderPhotos(photos);
        }
    } catch (error) {
        console.error('Failed to load photos:', error);
    }
}

function renderPhotos(photos) {
    photoGrid.innerHTML = '';
    
    photos.forEach(photo => {
        const item = document.createElement('div');
        item.className = 'photo-item';
        
        const img = document.createElement('img');
        img.src = `${API_BASE}/photos/${photo.id}/thumbnail`;
        img.alt = photo.file_path;
        
        item.appendChild(img);
        
        item.addEventListener('click', () => {
            showPhotoModal(photo.id);
        });
        
        photoGrid.appendChild(item);
    });
}

async function uploadPhoto(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_BASE}/photos`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` },
            body: formData
        });
        
        if (response.ok) {
            await checkAuth(); // Update quota
        } else {
            alert('Upload failed');
        }
    } catch (error) {
        console.error('Upload error:', error);
    }
}

async function showPhotoModal(photoId) {
    try {
        const response = await fetch(`${API_BASE}/photos/${photoId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            document.getElementById('modal-photo').src = url;
            document.getElementById('photo-modal').classList.remove('hidden');
        }
    } catch (error) {
        console.error('Failed to load photo:', error);
    }
}

async function loadPlans() {
    try {
        const response = await fetch(`${API_BASE}/storage/tiers`);
        if (response.ok) {
            const tiers = await response.json();
            const plansGrid = document.getElementById('plans-grid');
            plansGrid.innerHTML = '';
            
            const tierNames = {
                'free': 'Free',
                'basic': 'Basic',
                'standard': 'Standard',
                'premium': 'Premium',
                'ultimate': 'Ultimate'
            };
            
            Object.entries(tiers).forEach(([tier, bytes]) => {
                const card = document.createElement('div');
                card.className = 'plan-card';
                if (tier === selectedTier) {
                    card.classList.add('selected');
                }
                
                const storageGB = bytes / (1024 ** 3);
                const storageText = storageGB >= 1024 ? `${(storageGB / 1024).toFixed(0)} TB` : `${storageGB.toFixed(0)} GB`;
                
                card.innerHTML = `
                    <div class="plan-name">${tierNames[tier]}</div>
                    <div class="plan-storage">${storageText}</div>
                    <div class="plan-price">${tier === 'free' ? 'Free' : 'Coming Soon'}</div>
                `;
                
                card.addEventListener('click', () => {
                    document.querySelectorAll('.plan-card').forEach(c => c.classList.remove('selected'));
                    card.classList.add('selected');
                    selectedTier = tier;
                });
                
                plansGrid.appendChild(card);
            });
        }
    } catch (error) {
        console.error('Failed to load plans:', error);
    }
}

async function loadSettings() {
    try {
        // Load user info
        const response = await fetch(`${API_BASE}/auth/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const user = await response.json();
            
            // Update account info
            document.getElementById('settings-username').textContent = user.username;
            document.getElementById('settings-email').textContent = user.email;
            
            // Update storage info
            const tierNames = {
                'free': 'Free',
                'basic': 'Basic',
                'standard': 'Standard',
                'premium': 'Premium',
                'ultimate': 'Ultimate'
            };
            
            const currentTier = user.tier || 'free';
            document.getElementById('current-plan').textContent = tierNames[currentTier] || 'Free';
            
            const usedGB = user.used_space / (1024 ** 3);
            const totalGB = user.quota / (1024 ** 3);
            
            document.getElementById('storage-used').textContent = `${usedGB.toFixed(2)} GB`;
            document.getElementById('storage-total').textContent = totalGB >= 1024 ? `${(totalGB / 1024).toFixed(0)} TB` : `${totalGB.toFixed(0)} GB`;
            
            const percentage = (user.used_space / user.quota) * 100;
            document.getElementById('settings-quota-used').style.width = `${percentage}%`;
            
            // Load upgrade plans
            await loadUpgradePlans(currentTier);
        }
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

async function loadUpgradePlans(currentTier) {
    try {
        const response = await fetch(`${API_BASE}/storage/tiers`);
        if (response.ok) {
            const tiers = await response.json();
            const plansGrid = document.getElementById('settings-plans-grid');
            plansGrid.innerHTML = '';
            
            const tierNames = {
                'free': 'Free',
                'basic': 'Basic',
                'standard': 'Standard',
                'premium': 'Premium',
                'ultimate': 'Ultimate'
            };
            
            Object.entries(tiers).forEach(([tier, bytes]) => {
                // Only show plans that are upgrades
                if (tier !== currentTier) {
                    const card = document.createElement('div');
                    card.className = 'plan-card';
                    
                    const storageGB = bytes / (1024 ** 3);
                    const storageText = storageGB >= 1024 ? `${(storageGB / 1024).toFixed(0)} TB` : `${storageGB.toFixed(0)} GB`;
                    
                    card.innerHTML = `
                        <div class="plan-name">${tierNames[tier]}</div>
                        <div class="plan-storage">${storageText}</div>
                        <div class="plan-price">Coming Soon</div>
                    `;
                    
                    plansGrid.appendChild(card);
                }
            });
        }
    } catch (error) {
        console.error('Failed to load upgrade plans:', error);
    }
}
