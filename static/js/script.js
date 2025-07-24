class eyeMEI {
    constructor() {
        this.init();
    }

    init() {
        this.imeiForm = document.getElementById('imei-form');
        this.imeiInput = document.getElementById('imei-input');
        this.lookupBtn = document.getElementById('lookup-btn');
        this.loadingSection = document.getElementById('loading-section');
        this.resultsSection = document.getElementById('results-section');
        this.errorModal = document.getElementById('error-modal');
        this.dropdownSelected = document.getElementById('dropdown-selected');
        this.dropdownOptions = document.getElementById('dropdown-options');
        this.currentDatabaseValue = 'isthisphoneblocked';
        
        this.bindEvents();
        this.formatIMEIInput();
        this.initCustomDropdown();
        this.loadDatabaseStats();
        console.log('Welcome to eyeMEI, an eye for IMEI. Created with <3 by JoshAtticus')
        console.log('Report issues, contribute or see the source code on GitHub: https://github.com/JoshAtticus/eyeMEI')
    }

    bindEvents() {
        this.imeiForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.performLookup();
        });

        document.querySelector('.close').addEventListener('click', () => {
            this.closeModal();
        });

        this.errorModal.addEventListener('click', (e) => {
            if (e.target === this.errorModal) {
                this.closeModal();
            }
        });
    }

    formatIMEIInput() {
        this.imeiInput.addEventListener('input', (e) => {
            let value = e.target.value.replace(/\D/g, '');
            
            if (value.length > 15) {
                value = value.substring(0, 15);
            }
            
            e.target.value = value;
            
            this.updateLookupButton();
        });

        this.imeiInput.addEventListener('keypress', (e) => {
            if (!/\d/.test(e.key) && !['Backspace', 'Delete', 'Tab', 'Enter'].includes(e.key)) {
                e.preventDefault();
            }
        });
    }

    updateLookupButton() {
        const imei = this.imeiInput.value.trim();
        const isValid = imei.length === 15 && /^\d{15}$/.test(imei);
        
        this.lookupBtn.disabled = !isValid;
        
        if (isValid) {
            this.lookupBtn.innerHTML = '<i class="fas fa-search"></i> Lookup IMEI';
        } else {
            this.lookupBtn.innerHTML = '<i class="fas fa-search"></i> Enter 15 digits';
        }
    }

    async performLookup() {
        const imei = this.imeiInput.value.trim();
        
        if (!this.validateIMEI(imei)) {
            console.log('IMEI validation failed');
            this.showError('Please enter a valid 15-digit IMEI number.');
            return;
        }
        this.showLoading();

        try {
            const databaseType = this.currentDatabaseValue;
            const response = await fetch('/api/lookup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    imei: imei,
                    database_type: databaseType
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to perform lookup');
            }

            const data = await response.json();
            this.displayResults(data);

        } catch (error) {
            console.error('Lookup error:', error);
            this.showError(`Lookup failed: ${error.message}`);
            this.hideLoading();
        }
    }

    validateIMEI(imei) {
        return imei && /^\d{15}$/.test(imei);
    }

    showLoading() {
        this.resultsSection.classList.add('hidden');
        this.loadingSection.classList.remove('hidden');
        this.lookupBtn.disabled = true;
        this.lookupBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking...';
    }

    hideLoading() {
        this.loadingSection.classList.add('hidden');
        this.lookupBtn.disabled = false;
        this.updateLookupButton();
    }

    displayResults(data) {
        this.hideLoading();
        this.displayDatabaseInfo(data.eyemei_device_info, data.tac, 'eyeMEI');
        this.displaySecondaryDatabaseInfo(data.secondary_device_info, data.tac, data.secondary_db_name);
        this.displayProviderResults(data.provider_checks);
        this.resultsSection.classList.remove('hidden');
        this.resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

    displayDatabaseInfo(deviceInfo, tac, dbName) {
        const databaseDetails = document.getElementById('database-details');
        
        if (deviceInfo) {
            let imageHtml = '';
            if (deviceInfo.image) {
                imageHtml = `
                    <div class="device-image">
                        <img src="/${deviceInfo.image}" alt="${this.escapeHtml(deviceInfo.brand)} ${this.escapeHtml(deviceInfo.model)}" onerror="this.style.display='none'">
                    </div>
                `;
            }
            
            databaseDetails.innerHTML = `
                ${imageHtml}
                <div class="info-item">
                    <span class="info-label">Brand:</span>
                    <span class="info-value">${this.escapeHtml(deviceInfo.brand)}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Model:</span>
                    <span class="info-value">${this.escapeHtml(deviceInfo.model)}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">TAC:</span>
                    <span class="info-value">${this.escapeHtml(tac)}</span>
                </div>
            `;
        } else {
            databaseDetails.innerHTML = `
                <div class="device-image">
                    <img src="/public/images/devices/unknown-device.svg" alt="Unknown Device" onerror="this.style.display='none'">
                </div>
                <div class="info-item">
                    <span class="info-label">Status:</span>
                    <span class="info-value">Not Found (contribute?)</span>
                </div>
            `;
        }
    }

    displaySecondaryDatabaseInfo(deviceInfo, tac, dbName) {
        const secondaryDbDetails = document.getElementById('secondary-db-details');
        
        if (deviceInfo) {
            let imageHtml = '';
            if (deviceInfo.image && deviceInfo.image !== 'public/images/devices/unknown-device.svg') {
                imageHtml = `
                    <div class="device-image">
                        <img src="/${deviceInfo.image}" alt="${this.escapeHtml(deviceInfo.brand)} ${this.escapeHtml(deviceInfo.model)}" onerror="this.style.display='none'">
                    </div>
                `;
            }
            
            secondaryDbDetails.innerHTML = `
                ${imageHtml}
                <div class="info-item">
                    <span class="info-label">Brand:</span>
                    <span class="info-value">${this.escapeHtml(deviceInfo.brand)}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Model:</span>
                    <span class="info-value">${this.escapeHtml(deviceInfo.model)}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">TAC:</span>
                    <span class="info-value">${this.escapeHtml(tac)}</span>
                </div>
            `;
        } else {
            secondaryDbDetails.innerHTML = `
                <div class="info-item">
                    <span class="info-label">TAC:</span>
                    <span class="info-value">${this.escapeHtml(tac)}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Status:</span>
                    <span class="info-value">Not found in ${dbName}</span>
                </div>
            `;
        }
    }

    displayProviderResults(providerChecks) {
        const providerResults = document.getElementById('provider-results');
        
        providerResults.innerHTML = providerChecks.map(result => {
            const statusClass = this.getStatusClass(result);
            const statusText = this.getStatusText(result);
            
            return `
                <div class="provider-result ${statusClass}">
                    <div class="provider-header">
                        <span class="provider-name">${this.escapeHtml(result.provider)}</span>
                        <span class="provider-status ${this.getStatusBadgeClass(result)}">${statusText}</span>
                    </div>
                    <div class="provider-details">
                        ${this.getProviderDetails(result)}
                    </div>
                </div>
            `;
        }).join('');
    }

    getStatusClass(result) {
        if (!result.success) return 'error';
        
        const status = result.status?.toLowerCase();
        if (status === 'not blocked' || status === 'compatible') return 'success';
        if (status === 'blocked' || status === 'not compatible') return 'warning';
        if (status === 'not phone') return 'neutral';
        return 'error';
    }

    getStatusText(result) {
        if (!result.success) return 'Error';
        return result.status || 'Unknown';
    }

    getStatusBadgeClass(result) {
        if (!result.success) return 'status-error';
        
        const status = result.status?.toLowerCase();
        if (status === 'not blocked' || status === 'compatible') return 'status-ok';
        if (status === 'blocked' || status === 'not compatible') return 'status-blocked';
        if (status === 'not phone') return 'status-unknown';
        return 'status-unknown';
    }

    getProviderDetails(result) {
        if (!result.success) {
            return `<small>Unable to check: ${this.escapeHtml(result.error || 'Service unavailable')}</small>`;
        }

        let details = [];
        
        if (result.market_name && result.market_name !== 'Unknown') {
            details.push(`Device: ${this.escapeHtml(result.market_name)}`);
        }
        
        if (result.device_name && result.device_name !== 'Unknown') {
            details.push(`Device: ${this.escapeHtml(result.device_name)}`);
        }
        
        if (result.result_html) {
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = result.result_html;
            const text = tempDiv.textContent || tempDiv.innerText || '';
            if (text.trim()) {
                details.push(text.trim());
            }
        }
        
        if (details.length === 0) {
            details.push('Check completed successfully');
        }
        
        return `<small>${details.join(' • ')}</small>`;
    }

    resetForm() {
        this.imeiInput.value = '';
        this.imeiInput.focus();
        this.resultsSection.classList.add('hidden');
        this.loadingSection.classList.add('hidden');
        this.updateLookupButton();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    showError(message) {
        const errorMessage = document.getElementById('error-message');
        errorMessage.textContent = message;
        this.errorModal.classList.remove('hidden');
    }

    closeModal() {
        this.errorModal.classList.add('hidden');
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async loadDatabaseStats() {
        try {
            const response = await fetch('/api/database-stats');
            if (response.ok) {
                const stats = await response.json();
                this.updateDropdownWithStats(stats);
            }
        } catch (error) {
            console.log('Could not load database stats:', error);
        }
    }

    updateDropdownWithStats(stats) {
        const options = this.dropdownOptions.querySelectorAll('.dropdown-option');
        options.forEach(option => {
            const value = option.dataset.value;
            const subElement = option.querySelector('.option-sub');
        });
        
        // Update the selected option display as well
        const selectedOption = this.dropdownOptions.querySelector('.dropdown-option.active');
        if (selectedOption) {
            const optionContent = selectedOption.querySelector('.option-content').cloneNode(true);
            const currentContent = this.dropdownSelected.querySelector('.option-content');
            currentContent.replaceWith(optionContent);
        }
    }

    initCustomDropdown() {
        this.dropdownSelected.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleDropdown();
        });

        this.dropdownOptions.addEventListener('click', (e) => {
            const option = e.target.closest('.dropdown-option');
            if (option) {
                this.selectOption(option);
            }
        });

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.custom-dropdown')) {
                this.closeDropdown();
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeDropdown();
            }
        });
    }

    toggleDropdown() {
        const isOpen = this.dropdownOptions.classList.contains('open');
        if (isOpen) {
            this.closeDropdown();
        } else {
            this.openDropdown();
        }
    }

    openDropdown() {
        this.dropdownSelected.classList.add('open');
        this.dropdownOptions.classList.add('open');
    }

    closeDropdown() {
        this.dropdownSelected.classList.remove('open');
        this.dropdownOptions.classList.remove('open');
    }

    selectOption(optionElement) {
        this.dropdownOptions.querySelectorAll('.dropdown-option').forEach(opt => {
            opt.classList.remove('active');
        });

        optionElement.classList.add('active');

        const optionContent = optionElement.querySelector('.option-content').cloneNode(true);
        const currentContent = this.dropdownSelected.querySelector('.option-content');
        currentContent.replaceWith(optionContent);

        this.currentDatabaseValue = optionElement.dataset.value;

        this.closeDropdown();

        // Reload database stats when switching
        this.loadDatabaseStats();

        if (!this.resultsSection.classList.contains('hidden')) {
            this.performLookup();
        }
    }
}

function closeModal() {
    document.getElementById('error-modal').classList.add('hidden');
}

document.addEventListener('DOMContentLoaded', () => {
    new eyeMEI();
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeModal();
    }
    
    if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
        e.preventDefault();
        document.getElementById('imei-input').focus();
    }
});

document.getElementById('imei-input')?.addEventListener('paste', (e) => {
    setTimeout(() => {
        const input = e.target;
        let value = input.value.replace(/\D/g, '');
        if (value.length > 15) {
            value = value.substring(0, 15);
        }
        input.value = value;
        
        input.dispatchEvent(new Event('input'));
    }, 0);
});
