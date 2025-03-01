/**
 * Settings panel for the LLMResearch WebUI.
 */
class SettingsPanel {
    /**
     * Initialize the settings panel.
     * 
     * @param {HTMLElement} panelElement - The settings panel element
     * @param {HTMLElement} toggleButton - The button to toggle the panel
     * @param {HTMLElement} themeToggleButton - The button to toggle the theme
     * @param {HTMLElement} providerSelect - The provider select element
     * @param {HTMLElement} webSearchToggle - The web search toggle element
     * @param {HTMLElement} extractUrlToggle - The extract URL toggle element
     * @param {HTMLElement} reasoningSteps - The reasoning steps input element
     * @param {HTMLElement} temperatureInput - The temperature input element
     * @param {HTMLElement} temperatureValue - The temperature value display element
     * @param {HTMLElement} clearHistoryButton - The clear history button
     */
    constructor(
        panelElement,
        toggleButton,
        themeToggleButton,
        providerSelect,
        webSearchToggle,
        extractUrlToggle,
        reasoningSteps,
        temperatureInput,
        temperatureValue,
        clearHistoryButton
    ) {
        this.panelElement = panelElement;
        this.toggleButton = toggleButton;
        this.themeToggleButton = themeToggleButton;
        this.providerSelect = providerSelect;
        this.webSearchToggle = webSearchToggle;
        this.extractUrlToggle = extractUrlToggle;
        this.reasoningSteps = reasoningSteps;
        this.temperatureInput = temperatureInput;
        this.temperatureValue = temperatureValue;
        this.clearHistoryButton = clearHistoryButton;
        
        this.isOpen = false;
        this.currentTheme = 'light';
        this.availableThemes = ['light', 'dark', 'sepia', 'high-contrast'];
        this.themeIndex = 0;
        
        this.onClearHistoryCallback = null;
        
        // Set up event listeners
        this.setupEventListeners();
    }
    
    /**
     * Set up event listeners for the settings panel.
     */
    setupEventListeners() {
        // Toggle panel
        this.toggleButton.addEventListener('click', () => {
            this.togglePanel();
        });
        
        // Toggle theme
        this.themeToggleButton.addEventListener('click', () => {
            this.cycleTheme();
        });
        
        // Temperature input
        this.temperatureInput.addEventListener('input', () => {
            const value = this.temperatureInput.value;
            this.temperatureValue.textContent = value;
            this.saveSettings();
        });
        
        // Provider select
        this.providerSelect.addEventListener('change', () => {
            this.saveSettings();
        });
        
        // Web search toggle
        this.webSearchToggle.addEventListener('change', () => {
            this.saveSettings();
        });
        
        // Extract URL toggle
        this.extractUrlToggle.addEventListener('change', () => {
            this.saveSettings();
        });
        
        // Reasoning steps
        this.reasoningSteps.addEventListener('change', () => {
            this.saveSettings();
        });
        
        // Clear history button
        this.clearHistoryButton.addEventListener('click', () => {
            if (this.onClearHistoryCallback) {
                this.onClearHistoryCallback();
            }
        });
    }
    
    /**
     * Toggle the settings panel.
     */
    togglePanel() {
        this.isOpen = !this.isOpen;
        
        if (this.isOpen) {
            this.panelElement.classList.add('active');
        } else {
            this.panelElement.classList.remove('active');
        }
    }
    
    /**
     * Cycle through available themes.
     */
    cycleTheme() {
        this.themeIndex = (this.themeIndex + 1) % this.availableThemes.length;
        this.currentTheme = this.availableThemes[this.themeIndex];
        
        // Remove all theme classes
        document.body.classList.remove(...this.availableThemes.map(theme => `theme-${theme}`));
        
        // Add the current theme class
        document.body.classList.add(`theme-${this.currentTheme}`);
        
        // Save the theme preference
        localStorage.setItem('theme', this.currentTheme);
        
        // Save settings
        this.saveSettings();
    }
    
    /**
     * Set the theme.
     * 
     * @param {string} theme - The theme to set
     */
    setTheme(theme) {
        if (this.availableThemes.includes(theme)) {
            this.themeIndex = this.availableThemes.indexOf(theme);
            this.currentTheme = theme;
            
            // Remove all theme classes
            document.body.classList.remove(...this.availableThemes.map(t => `theme-${t}`));
            
            // Add the current theme class
            document.body.classList.add(`theme-${this.currentTheme}`);
            
            // Save the theme preference
            localStorage.setItem('theme', this.currentTheme);
        }
    }
    
    /**
     * Update the settings UI with the provided settings.
     * 
     * @param {Object} settings - The settings to update
     */
    updateSettings(settings) {
        // Update theme
        if (settings.theme) {
            this.setTheme(settings.theme);
        }
        
        // Update provider
        if (settings.provider) {
            this.providerSelect.value = settings.provider;
        }
        
        // Update web search toggle
        this.webSearchToggle.checked = settings.web_search_enabled !== false;
        
        // Update extract URL toggle
        this.extractUrlToggle.checked = settings.extract_url_content !== false;
        
        // Update reasoning steps
        if (settings.reasoning_steps) {
            this.reasoningSteps.value = settings.reasoning_steps;
        }
        
        // Update temperature
        if (settings.temperature !== undefined) {
            this.temperatureInput.value = settings.temperature;
            this.temperatureValue.textContent = settings.temperature;
        }
    }
    
    /**
     * Update the provider select options.
     * 
     * @param {Object} providers - The providers data
     */
    updateProviders(providers) {
        // Clear existing options
        this.providerSelect.innerHTML = '';
        
        // Add options for each provider
        providers.providers.forEach(provider => {
            const option = document.createElement('option');
            option.value = provider;
            option.textContent = provider + (provider === providers.default_provider ? ' (默认)' : '');
            this.providerSelect.appendChild(option);
        });
        
        // Select the default provider
        if (providers.default_provider) {
            this.providerSelect.value = providers.default_provider;
        }
    }
    
    /**
     * Get the current settings.
     * 
     * @returns {Object} - The current settings
     */
    getCurrentSettings() {
        return {
            theme: this.currentTheme,
            provider: this.providerSelect.value,
            web_search_enabled: this.webSearchToggle.checked,
            extract_url_content: this.extractUrlToggle.checked,
            reasoning_steps: parseInt(this.reasoningSteps.value, 10),
            temperature: parseFloat(this.temperatureInput.value)
        };
    }
    
    /**
     * Save the current settings.
     */
    async saveSettings() {
        try {
            const settings = this.getCurrentSettings();
            
            // Save to localStorage
            localStorage.setItem('settings', JSON.stringify(settings));
            
            // Save to server
            const api = new ApiClient();
            await api.updateSettings({
                theme: settings.theme,
                web_search_enabled: settings.web_search_enabled,
                extract_url_content: settings.extract_url_content,
                reasoning_steps: settings.reasoning_steps,
                temperature: settings.temperature
            });
        } catch (error) {
            console.error('Failed to save settings:', error);
        }
    }
    
    /**
     * Load settings from localStorage.
     */
    loadLocalSettings() {
        try {
            // Load theme
            const theme = localStorage.getItem('theme');
            if (theme) {
                this.setTheme(theme);
            }
            
            // Load other settings
            const settingsJson = localStorage.getItem('settings');
            if (settingsJson) {
                const settings = JSON.parse(settingsJson);
                this.updateSettings(settings);
            }
        } catch (error) {
            console.error('Failed to load settings:', error);
        }
    }
    
    /**
     * Set the callback for when the clear history button is clicked.
     * 
     * @param {Function} callback - The callback function
     */
    onClearHistory(callback) {
        this.onClearHistoryCallback = callback;
    }
}