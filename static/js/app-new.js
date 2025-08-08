/**
 * Daily Inspo - Frontend Application
 * 
 * Handles UI interactions, API communication, and idea display
 * functionality for the automated app idea generator.
 */

class DailyInspoApp {
    constructor() {
        this.currentPage = 1;
        this.totalPages = 1;
        this.currentFilters = {};
        this.ideas = [];
        this.projects = [];
        this.currentProject = null;
        this.chatSession = null;
        this.chatWebSocket = null;
        
        this.init();
    }

    /**
     * Initialize application
     */
    async init() {
        try {
            this.bindEventListeners();
            await this.loadSystemStats();
            await this.loadFilterOptions();
            await this.loadIdeas();
            await this.loadProjects();
        } catch (error) {
            console.error('Failed to initialize application:', error);
            this.showError('Failed to initialize application');
        }
    }

    /**
     * Bind event listeners to DOM elements
     */
    bindEventListeners() {
        // Search functionality
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.applyFilters();
                }, 500); // Debounce search
            });
        }

        // Filter controls
        const applyFiltersBtn = document.getElementById('apply-filters');
        if (applyFiltersBtn) {
            applyFiltersBtn.addEventListener('click', () => this.applyFilters());
        }

        const clearFiltersBtn = document.getElementById('clear-filters');
        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', () => this.clearFilters());
        }

        const randomIdeaBtn = document.getElementById('random-idea');
        if (randomIdeaBtn) {
            randomIdeaBtn.addEventListener('click', () => this.showRandomIdea());
        }

        // Pagination buttons
        const prevPageBtn = document.getElementById('prev-page');
        if (prevPageBtn) {
            prevPageBtn.addEventListener('click', () => {
                if (this.currentPage > 1) {
                    this.navigateToPage(this.currentPage - 1);
                }
            });
        }

        const nextPageBtn = document.getElementById('next-page');
        if (nextPageBtn) {
            nextPageBtn.addEventListener('click', () => {
                if (this.currentPage < this.totalPages) {
                    this.navigateToPage(this.currentPage + 1);
                }
            });
        }

        // Modal controls
        const modalClose = document.getElementById('modal-close');
        if (modalClose) {
            modalClose.addEventListener('click', () => this.hideIdeaModal());
        }

        const modalBackdrop = document.querySelector('.modal__backdrop');
        if (modalBackdrop) {
            modalBackdrop.addEventListener('click', () => this.hideIdeaModal());
        }

        // ESC key to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideIdeaModal();
                this.hideProjectModal();
                this.hideChatModal();
            }
        });

        // Project management controls
        const createProjectBtn = document.getElementById('create-project-btn');
        if (createProjectBtn) {
            createProjectBtn.addEventListener('click', () => this.showProjectModal());
        }

        const projectForm = document.getElementById('project-form');
        if (projectForm) {
            projectForm.addEventListener('submit', (e) => this.handleProjectSubmit(e));
        }

        // Chat controls
        const chatInput = document.getElementById('chat-input');
        const sendMessageBtn = document.getElementById('send-message-btn');
        
        if (chatInput) {
            chatInput.addEventListener('input', () => {
                if (sendMessageBtn) {
                    sendMessageBtn.disabled = chatInput.value.trim().length === 0;
                }
            });

            chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendChatMessage();
                }
            });
        }

        if (sendMessageBtn) {
            sendMessageBtn.addEventListener('click', () => this.sendChatMessage());
        }

        // Event delegation for project card buttons
        const projectsGrid = document.getElementById('projects-grid');
        if (projectsGrid) {
            projectsGrid.addEventListener('click', (e) => {
                const projectCard = e.target.closest('.project-card');
                if (!projectCard) return;
                
                const projectId = parseInt(projectCard.dataset.projectId);
                
                if (e.target.matches('[data-action="chat"]')) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.openProjectChat(projectId);
                } else if (e.target.matches('[data-action="analyze"]')) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.analyzeProject(projectId);
                } else if (e.target.matches('[data-action="details"]')) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.showProjectDetails(projectId);
                }
            });
        }
    }

    /**
     * Load system statistics and update header
     */
    async loadSystemStats() {
        try {
            const stats = await this.apiRequest('/api/ideas/stats/');
            
            // Update header stats
            const totalElement = document.getElementById('stats-total');
            if (totalElement) {
                totalElement.textContent = stats.total_ideas || 0;
            }
            
            const lastElement = document.getElementById('stats-last');
            if (lastElement && stats.last_generation) {
                const lastDate = new Date(stats.last_generation);
                lastElement.textContent = this.formatDate(lastDate.toISOString());
            } else if (lastElement) {
                lastElement.textContent = 'Never';
            }
        } catch (error) {
            console.error('Failed to load system stats:', error);
        }
    }

    /**
     * Load available filter options from API
     */
    async loadFilterOptions() {
        try {
            // Load industries
            const industries = await this.apiRequest('/api/filters/industries/');
            this.populateSelect('industry-filter', industries);
            
            // Load technologies
            const technologies = await this.apiRequest('/api/filters/technologies/');
            this.populateSelect('technology-filter', technologies);
            
            // Load target markets
            const targetMarkets = await this.apiRequest('/api/filters/target-markets/');
            this.populateSelect('market-filter', targetMarkets);
            
            // Complexity is already populated in HTML
        } catch (error) {
            console.error('Failed to load filter options:', error);
        }
    }

    /**
     * Load ideas from API with current filters
     */
    async loadIdeas() {
        this.showLoading();
        
        try {
            const params = {
                ...this.currentFilters,
                limit: 50,
                offset: (this.currentPage - 1) * 50
            };
            
            const queryString = this.buildQueryString(params);
            const response = await this.apiRequest(`/api/ideas/search/?${queryString}`);
            
            this.ideas = response.ideas || [];
            this.renderIdeasGrid(this.ideas);
            
            // Update pagination
            this.totalPages = Math.ceil(response.total_count / 50);
            this.updatePagination(this.currentPage, this.totalPages, response.has_more);
            
        } catch (error) {
            console.error('Failed to load ideas:', error);
            this.showError('Failed to load ideas');
            this.showEmptyState();
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Render idea cards in the grid
     */
    renderIdeasGrid(ideas) {
        const grid = document.getElementById('ideas-grid');
        
        if (ideas.length === 0) {
            this.showEmptyState();
            return;
        }

        // Clear existing content
        grid.innerHTML = '';
        
        // Render each idea card
        ideas.forEach(idea => {
            const card = this.createIdeaCard(idea);
            grid.appendChild(card);
        });
        
        // Ensure grid is visible
        document.getElementById('empty-state').classList.add('hidden');
    }

    /**
     * Create HTML element for individual idea card
     */
    createIdeaCard(idea) {
        const card = document.createElement('div');
        card.className = 'idea-card';
        card.dataset.ideaId = idea.id;
        
        // Add click handler for modal
        card.addEventListener('click', () => this.showIdeaModal(idea.id));
        
        // Create tags HTML
        const tagsHtml = idea.tags.map(tag => 
            `<span class="tag tag--${tag.category}">${tag.value}</span>`
        ).join('');
        
        // Create card HTML structure
        card.innerHTML = `
            <h3 class="idea-card__title">${this.escapeHtml(idea.title)}</h3>
            <p class="idea-card__summary">${this.escapeHtml(idea.summary)}</p>
            <div class="idea-card__tags">${tagsHtml}</div>
            <div class="idea-card__meta">
                <span>${this.formatDate(idea.generated_date)}</span>
                <span>Click to view details</span>
            </div>
        `;
        
        return card;
    }

    /**
     * Create tag element with appropriate styling
     */
    createTagElement(tag) {
        const tagEl = document.createElement('span');
        tagEl.className = `tag tag--${tag.category}`;
        tagEl.textContent = tag.value;
        return tagEl;
    }

    /**
     * Show detailed idea modal
     */
    async showIdeaModal(ideaId) {
        try {
            this.showLoading();
            
            // Fetch detailed idea data
            const idea = await this.apiRequest(`/api/ideas/${ideaId}`);
            
            // Populate modal content
            document.getElementById('modal-title').textContent = idea.title;
            
            const modalContent = document.getElementById('modal-content');
            
            // Create tags HTML
            const tagsHtml = idea.tags.map(tag => 
                `<span class="tag tag--${tag.category}">${tag.value}</span>`
            ).join('');
            
            // Create competitors list
            const competitorsHtml = idea.market_data?.competitors ? 
                '<ul>' + idea.market_data.competitors.map(comp => `<li>${this.escapeHtml(comp)}</li>`).join('') + '</ul>' :
                '<p>Not specified</p>';
            
            modalContent.innerHTML = `
                <div class="modal__section">
                    <h3>Summary</h3>
                    <p>${this.escapeHtml(idea.summary)}</p>
                </div>
                
                <div class="modal__section">
                    <h3>Description</h3>
                    <p>${this.escapeHtml(idea.description)}</p>
                </div>
                
                <div class="modal__section">
                    <h3>Supporting Logic</h3>
                    <p>${this.escapeHtml(idea.supporting_logic)}</p>
                </div>
                
                <div class="modal__section">
                    <h3>Tags</h3>
                    <div class="idea-card__tags">${tagsHtml}</div>
                </div>
                
                ${idea.market_data ? `
                <div class="modal__section">
                    <h3>Market Analysis</h3>
                    <p><strong>Market Size:</strong> ${this.escapeHtml(idea.market_data.market_size || 'Not specified')}</p>
                    <p><strong>Technical Feasibility:</strong> ${this.escapeHtml(idea.market_data.technical_feasibility || 'Not assessed')}</p>
                    <p><strong>Development Timeline:</strong> ${this.escapeHtml(idea.market_data.development_timeline || 'Not estimated')}</p>
                    <div>
                        <strong>Key Competitors:</strong>
                        ${competitorsHtml}
                    </div>
                </div>
                ` : ''}
                
                <div class="modal__section">
                    <h3>Generated</h3>
                    <p>${this.formatDate(idea.generated_date)}</p>
                </div>
            `;
            
            // Show modal
            document.getElementById('idea-modal').classList.remove('hidden');
            
        } catch (error) {
            console.error('Failed to load idea details:', error);
            this.showError('Failed to load idea details');
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Hide idea modal
     */
    hideIdeaModal() {
        const modal = document.getElementById('idea-modal');
        modal.classList.add('hidden');
    }

    /**
     * Apply current filters and reload ideas
     */
    async applyFilters() {
        this.currentFilters = this.collectFilterValues();
        this.currentPage = 1;
        await this.loadIdeas();
    }

    /**
     * Collect current filter values from form elements
     */
    collectFilterValues() {
        const filters = {};
        
        // Collect search query
        const searchInput = document.getElementById('search-input');
        if (searchInput?.value?.trim()) {
            filters.q = searchInput.value.trim();
        }
        
        // Collect filter selections
        const industrySelect = document.getElementById('industry-filter');
        if (industrySelect) {
            const selectedIndustries = Array.from(industrySelect.selectedOptions).map(opt => opt.value);
            if (selectedIndustries.length > 0) {
                filters.industry = selectedIndustries;
            }
        }
        
        const complexitySelect = document.getElementById('complexity-filter');
        if (complexitySelect) {
            const selectedComplexity = Array.from(complexitySelect.selectedOptions).map(opt => opt.value);
            if (selectedComplexity.length > 0) {
                filters.complexity = selectedComplexity;
            }
        }
        
        const technologySelect = document.getElementById('technology-filter');
        if (technologySelect) {
            const selectedTech = Array.from(technologySelect.selectedOptions).map(opt => opt.value);
            if (selectedTech.length > 0) {
                filters.technology = selectedTech;
            }
        }
        
        const marketSelect = document.getElementById('market-filter');
        if (marketSelect) {
            const selectedMarkets = Array.from(marketSelect.selectedOptions).map(opt => opt.value);
            if (selectedMarkets.length > 0) {
                filters.target_market = selectedMarkets;
            }
        }
        
        return filters;
    }

    /**
     * Clear all filters and reload
     */
    async clearFilters() {
        this.currentFilters = {};
        this.currentPage = 1;
        
        // Clear form elements
        const searchInput = document.getElementById('search-input');
        if (searchInput) searchInput.value = '';
        
        const selects = [
            'industry-filter',
            'complexity-filter', 
            'technology-filter',
            'market-filter'
        ];
        
        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            if (select) {
                Array.from(select.options).forEach(option => {
                    option.selected = false;
                });
            }
        });
        
        await this.loadIdeas();
    }

    /**
     * Generate and show new random idea
     */
    async showRandomIdea() {
        try {
            // Show loading state
            const button = document.getElementById('random-idea');
            const originalText = button.textContent;
            button.textContent = 'Generating...';
            button.disabled = true;
            
            // Generate a new idea
            const newIdea = await this.apiRequest('/api/ideas/generate/', {
                method: 'POST'
            });
            
            // Show the newly generated idea
            await this.showIdeaModal(newIdea.id);
            
            // Refresh the ideas list to include the new idea
            await this.loadIdeas();
            
            // Reset button
            button.textContent = originalText;
            button.disabled = false;
            
        } catch (error) {
            console.error('Failed to generate new idea:', error);
            
            // Reset button
            const button = document.getElementById('random-idea');
            if (button) {
                button.textContent = 'Generate New Idea';
                button.disabled = false;
            }
            
            if (error.message.includes('timeout')) {
                this.showError('Idea generation timed out. Please try again.');
            } else if (error.message.includes('Generation script not found')) {
                this.showError('Generation system not configured properly');
            } else {
                this.showError('Failed to generate new idea. Please try again.');
            }
        }
    }

    /**
     * Handle pagination navigation
     */
    async navigateToPage(page) {
        if (page < 1 || page > this.totalPages) {
            return;
        }
        
        this.currentPage = page;
        await this.loadIdeas();
    }

    /**
     * Update pagination controls
     */
    updatePagination(currentPage, totalPages, hasMore) {
        this.currentPage = currentPage;
        this.totalPages = totalPages;
        
        // Update button states
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');
        const pageInfo = document.getElementById('page-info');
        
        if (prevBtn) {
            prevBtn.disabled = currentPage <= 1;
        }
        
        if (nextBtn) {
            nextBtn.disabled = currentPage >= totalPages;
        }
        
        if (pageInfo) {
            pageInfo.textContent = `Page ${currentPage} of ${totalPages || 1}`;
        }
    }

    /**
     * Show loading state
     */
    showLoading() {
        document.getElementById('loading').classList.remove('hidden');
        document.getElementById('ideas-grid').classList.add('hidden');
        document.getElementById('empty-state').classList.add('hidden');
    }

    /**
     * Hide loading state
     */
    hideLoading() {
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('ideas-grid').classList.remove('hidden');
    }

    /**
     * Show empty state when no ideas found
     */
    showEmptyState() {
        document.getElementById('ideas-grid').classList.add('hidden');
        document.getElementById('empty-state').classList.remove('hidden');
    }

    /**
     * Show error message
     */
    showError(message) {
        // TODO: Implement error display
        console.error(message);
        // Could add toast notification or error banner
    }

    /**
     * Format date for display
     */
    formatDate(dateString) {
        // TODO: Implement date formatting
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    /**
     * Truncate text to specified length
     */
    truncateText(text, maxLength = 150) {
        if (text.length <= maxLength) {
            return text;
        }
        return text.substring(0, maxLength).trim() + '...';
    }

    /**
     * Build query string from filter parameters
     */
    buildQueryString(params) {
        // TODO: Implement query string building
        const queryParams = new URLSearchParams();
        
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined && value !== '') {
                if (Array.isArray(value)) {
                    value.forEach(v => queryParams.append(key, v));
                } else {
                    queryParams.append(key, value);
                }
            }
        });
        
        return queryParams.toString();
    }

    /**
     * Make API request with error handling
     */
    async apiRequest(url, options = {}) {
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                let errorMessage = `${response.status} ${response.statusText}`;
                
                // Try to get detailed error message from response
                try {
                    const errorData = await response.json();
                    console.log('API Error Response:', errorData);
                    
                    if (errorData.detail) {
                        // Handle Pydantic validation errors (array format)
                        if (Array.isArray(errorData.detail)) {
                            const validationErrors = errorData.detail.map(err => 
                                `${err.loc?.join('.')}: ${err.msg}`
                            ).join('; ');
                            errorMessage = `Validation error: ${validationErrors}`;
                        } else {
                            errorMessage = errorData.detail;
                        }
                    }
                } catch (parseError) {
                    console.error('Could not parse error response:', parseError);
                }
                
                throw new Error(`API request failed: ${errorMessage}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    /**
     * Populate select element with options
     */
    populateSelect(selectId, options) {
        const select = document.getElementById(selectId);
        if (!select || !options) return;
        
        while (select.children.length > 0) {
            select.removeChild(select.firstChild);
        }
        
        options.forEach(option => {
            const optionEl = document.createElement('option');
            optionEl.value = option;
            optionEl.textContent = option;
            select.appendChild(optionEl);
        });
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ================================
    // PROJECT MANAGEMENT METHODS
    // ================================

    /**
     * Load and display projects
     */
    async loadProjects() {
        try {
            const projects = await this.apiRequest('/api/projects/');
            this.projects = projects;
            this.renderProjects();
        } catch (error) {
            console.error('Failed to load projects:', error);
            this.showError('Failed to load projects');
        }
    }

    /**
     * Render projects grid
     */
    renderProjects() {
        const projectsGrid = document.getElementById('projects-grid');
        const emptyState = document.getElementById('projects-empty-state');
        
        if (!projectsGrid) return;

        if (this.projects.length === 0) {
            projectsGrid.innerHTML = '';
            if (emptyState) {
                emptyState.classList.remove('hidden');
            }
            return;
        }

        if (emptyState) {
            emptyState.classList.add('hidden');
        }

        projectsGrid.innerHTML = this.projects.map(project => this.createProjectCard(project)).join('');
    }

    /**
     * Create project card HTML
     */
    createProjectCard(project) {
        const statusColors = {
            'planning': '#3498db',
            'development': '#f39c12', 
            'testing': '#9b59b6',
            'completed': '#27ae60',
            'paused': '#95a5a6',
            'archived': '#7f8c8d'
        };

        const statusColor = statusColors[project.status] || '#3498db';
        const lastAnalysis = project.last_analysis 
            ? new Date(project.last_analysis).toLocaleDateString()
            : 'Never';

        return `
            <div class="project-card" data-project-id="${project.id}">
                <div class="project-card__header">
                    <h3 class="project-card__title">${this.escapeHtml(project.name)}</h3>
                    <span class="project-status" style="background-color: ${statusColor}">
                        ${project.status.replace('_', ' ')}
                    </span>
                </div>
                <div class="project-card__body">
                    <p class="project-card__description">${this.escapeHtml(project.description)}</p>
                    <div class="project-card__meta">
                        <div class="project-meta-item">
                            <span class="project-meta-label">Ideas:</span>
                            <span class="project-meta-value">${project.idea_count}</span>
                        </div>
                        <div class="project-meta-item">
                            <span class="project-meta-label">Last Analysis:</span>
                            <span class="project-meta-value">${lastAnalysis}</span>
                        </div>
                    </div>
                </div>
                <div class="project-card__actions">
                    <button type="button" class="btn btn--small" data-action="details">
                        View Details
                    </button>
                    <button type="button" class="btn btn--small btn--primary" data-action="chat">
                        💬 Chat
                    </button>
                    <button type="button" class="btn btn--small" data-action="analyze">
                        🔍 Analyze
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Show project creation modal
     */
    showProjectModal() {
        const modal = document.getElementById('project-modal');
        const ideaList = document.getElementById('idea-connection-list');
        
        if (modal) {
            modal.classList.remove('hidden');
            
            // Populate idea connection list
            if (ideaList && this.ideas.length > 0) {
                ideaList.innerHTML = this.ideas.slice(0, 10).map(idea => `
                    <label class="checkbox-label">
                        <input type="checkbox" value="${idea.id}" name="connected-ideas">
                        <span>${this.escapeHtml(idea.title)}</span>
                    </label>
                `).join('');
            }
        }
    }

    /**
     * Hide project creation modal
     */
    hideProjectModal() {
        const modal = document.getElementById('project-modal');
        if (modal) {
            modal.classList.add('hidden');
            document.getElementById('project-form')?.reset();
        }
    }

    /**
     * Handle project form submission
     */
    async handleProjectSubmit(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const connectedIdeas = Array.from(document.querySelectorAll('input[name="connected-ideas"]:checked'))
            .map(checkbox => parseInt(checkbox.value));
        
        const projectData = {
            name: formData.get('project-name') || document.getElementById('project-name').value,
            description: formData.get('project-description') || document.getElementById('project-description').value,
            folder_path: formData.get('project-folder') || document.getElementById('project-folder').value,
            status: formData.get('project-status') || document.getElementById('project-status').value,
            repository_url: formData.get('project-repository') || document.getElementById('project-repository').value || null,
            idea_ids: connectedIdeas
        };
        
        console.log('Form data being sent:', projectData);
        
        // Validate required fields
        if (!projectData.name || !projectData.description || !projectData.folder_path) {
            this.showError('Please fill in all required fields (Name, Description, Folder Path)');
            return;
        }

        try {
            await this.apiRequest('/api/projects/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(projectData)
            });
            
            this.hideProjectModal();
            await this.loadProjects();
            this.showSuccess('Project created successfully!');
        } catch (error) {
            console.error('Failed to create project:', error);
            console.log('Project data being sent:', projectData);
            
            // Try to get more specific error message
            let errorMessage = 'Failed to create project. Please check your inputs.';
            if (error.message && error.message.includes('API request failed')) {
                // Try to fetch more details from the API response
                errorMessage = `Failed to create project: ${error.message}`;
            }
            
            this.showError(errorMessage);
        }
    }

    /**
     * Show project details (placeholder for future implementation)
     */
    showProjectDetails(projectId) {
        console.log('Project details for ID:', projectId);
        // TODO: Implement project details modal
        this.showError('Project details view not implemented yet');
    }

    /**
     * Analyze project (compare with connected ideas)
     */
    async analyzeProject(projectId) {
        try {
            this.showSuccess('Project analysis started...');
            await this.apiRequest(`/api/projects/${projectId}/analyze`, { method: 'POST' });
            
            // Reload projects after a delay to show updated analysis date
            setTimeout(() => this.loadProjects(), 2000);
        } catch (error) {
            console.error('Failed to analyze project:', error);
            this.showError('Failed to start project analysis');
        }
    }

    // ================================
    // CHAT SYSTEM METHODS
    // ================================

    /**
     * Open chat for a project
     */
    async openProjectChat(projectId) {
        console.log('Opening chat for project ID:', projectId);
        try {
            const project = this.projects.find(p => p.id === projectId);
            console.log('Found project:', project);
            if (!project) throw new Error('Project not found');

            this.currentProject = project;
            
            // Get or create chat session
            const sessions = await this.apiRequest(`/api/chat/sessions/${projectId}`);
            
            if (sessions.length > 0) {
                this.chatSession = sessions[0]; // Use most recent session
            } else {
                // Create new session
                this.chatSession = await this.apiRequest('/api/chat/sessions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        project_id: projectId,
                        title: `Chat - ${project.name}`,
                        initial_message: `I'd like to discuss my project "${project.name}" and how it aligns with my connected ideas. Can you help analyze the current state?`
                    })
                });
            }

            this.showChatModal();
            await this.loadChatMessages();
            this.connectChatWebSocket();
            
        } catch (error) {
            console.error('Failed to open chat:', error);
            console.error('Error details:', error.message);
            this.showError(`Failed to open project chat: ${error.message}`);
        }
    }

    /**
     * Show chat modal
     */
    showChatModal() {
        const modal = document.getElementById('chat-modal');
        const projectName = document.getElementById('chat-project-name');
        
        if (modal) {
            modal.classList.remove('hidden');
            
            if (projectName && this.currentProject) {
                projectName.textContent = this.currentProject.name;
            }
        }
    }

    /**
     * Hide chat modal
     */
    hideChatModal() {
        const modal = document.getElementById('chat-modal');
        if (modal) {
            modal.classList.add('hidden');
        }

        // Disconnect WebSocket
        if (this.chatWebSocket) {
            this.chatWebSocket.close();
            this.chatWebSocket = null;
        }

        // Clear chat state
        this.currentProject = null;
        this.chatSession = null;
    }

    /**
     * Load chat messages
     */
    async loadChatMessages() {
        if (!this.chatSession) return;

        try {
            const messages = await this.apiRequest(`/api/chat/sessions/${this.chatSession.id}/messages`);
            this.renderChatMessages(messages);
        } catch (error) {
            console.error('Failed to load chat messages:', error);
        }
    }

    /**
     * Render chat messages
     */
    renderChatMessages(messages) {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;

        chatMessages.innerHTML = messages.map(message => this.createChatMessage(message)).join('');
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    /**
     * Create chat message HTML
     */
    createChatMessage(message) {
        const isUser = message.role === 'user';
        const timestamp = new Date(message.timestamp).toLocaleTimeString();
        
        return `
            <div class="chat-message ${isUser ? 'chat-message--user' : 'chat-message--assistant'}">
                <div class="chat-message__content">
                    <div class="chat-message__text">${this.escapeHtml(message.content)}</div>
                    <div class="chat-message__timestamp">${timestamp}</div>
                </div>
                <div class="chat-message__avatar">
                    ${isUser ? '👤' : '🤖'}
                </div>
            </div>
        `;
    }

    /**
     * Connect to chat WebSocket
     */
    connectChatWebSocket() {
        if (!this.chatSession) return;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/chat/sessions/${this.chatSession.id}/ws`;
        
        this.chatWebSocket = new WebSocket(wsUrl);

        this.chatWebSocket.onopen = () => {
            console.log('Chat WebSocket connected');
            this.updateChatStatus('Connected');
        };

        this.chatWebSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'message') {
                this.addChatMessage(data.data);
            }
        };

        this.chatWebSocket.onclose = () => {
            console.log('Chat WebSocket disconnected');
            this.updateChatStatus('Disconnected');
        };

        this.chatWebSocket.onerror = (error) => {
            console.error('Chat WebSocket error:', error);
            this.updateChatStatus('Connection error');
        };
    }

    /**
     * Send chat message
     */
    async sendChatMessage() {
        const chatInput = document.getElementById('chat-input');
        const sendButton = document.getElementById('send-message-btn');
        
        if (!chatInput || !this.chatSession) return;

        const message = chatInput.value.trim();
        if (!message) return;

        try {
            sendButton.disabled = true;
            chatInput.disabled = true;
            
            // Send via REST API (which will also broadcast via WebSocket)
            await this.apiRequest(`/api/chat/sessions/${this.chatSession.id}/messages`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.chatSession.id,
                    role: 'user',
                    content: message
                })
            });

            chatInput.value = '';
            this.updateChatStatus('Message sent');
            
        } catch (error) {
            console.error('Failed to send message:', error);
            this.showError('Failed to send message');
        } finally {
            sendButton.disabled = false;
            chatInput.disabled = false;
            chatInput.focus();
        }
    }

    /**
     * Add new chat message to UI
     */
    addChatMessage(message) {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;

        const messageHtml = this.createChatMessage(message);
        chatMessages.insertAdjacentHTML('beforeend', messageHtml);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    /**
     * Update chat status
     */
    updateChatStatus(status) {
        const chatStatus = document.getElementById('chat-status');
        if (chatStatus) {
            chatStatus.textContent = status;
            setTimeout(() => {
                chatStatus.textContent = '';
            }, 3000);
        }
    }
}

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('=== UPDATED JAVASCRIPT LOADED V2 ===');
    console.log('Event delegation has been implemented');
    window.dailyInspoApp = new DailyInspoApp();
});


// Export for potential testing or external access
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DailyInspoApp;
}