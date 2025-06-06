// Function to display notifications
    function displayNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);

        // Trigger reflow to ensure transition plays
        void notification.offsetWidth;
        notification.classList.add('show');

        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(()=> notification.remove(), 300);
        }, 3000);
    }

    document.addEventListener('DOMContentLoaded', function() {
        const orgId = document.getElementById('organizationId').value;
        const themeColorInput = document.getElementById('themeColorInput');
        const themeColorPicker = document.getElementById('themeColorPicker');
        const saveThemeButton = document.getElementById('saveThemeColorButton');
        const themeColorError = document.getElementById('themeColorError');

        const logoFileInput = document.getElementById('logoFileInput');
        const uploadLogoButton = document.getElementById('uploadLogoButton');
        const logoUploadError = document.getElementById('logoUploadError');
        const currentLogoPreview = document.getElementById('currentLogoPreview');

        // --- Theme Color Logic ---
        themeColorInput.addEventListener('input', function() {
            const hexRegex = /^#([0-9A-F]{3}){1,2}$/i;
            if (hexRegex.test(this.value)) {
                themeColorPicker.value = this.value;
                themeColorError.textContent = '';
            } else {
                themeColorError.textContent = 'Invalid hex color format (e.g., #RRGGBB or #RGB).';
            }
        });

        themeColorPicker.addEventListener('input', function() {
            themeColorInput.value = this.value;
            themeColorError.textContent = '';
        });

        saveThemeButton.addEventListener('click', async function() {
            const newThemeColor = themeColorInput.value;
            const hexRegex = /^#([0-9A-F]{3}){1,2}$/i;
            if (!newThemeColor || !hexRegex.test(newThemeColor)) {
                themeColorError.textContent = 'Please enter a valid hex color (e.g., #RRGGBB).';
                return;
            } else {
                themeColorError.textContent = '';
            }

            if (!orgId) {
                displayNotification('Organization ID not found. Cannot update theme.', 'error');
                return;
            }

            try {
                const response = await fetch(`/admin/organizations/${orgId}/theme`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ new_theme_color: newThemeColor })
                });
                const data = await response.json();

                if (response.ok) {
                    displayNotification(data.message, 'success');
                    document.documentElement.style.setProperty('--organization-theme-color', newThemeColor);
                } else {
                    displayNotification('Error updating theme: ' + (data.detail || 'Unknown error'), 'error');
                }
            } catch (error) {
                console.error('Fetch error:', error);
                displayNotification('An error occurred while saving the theme.', 'error');
            }
        });

        // --- Logo Upload Logic ---
        logoFileInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const file = this.files[0];
                const allowedTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/svg+xml'];
                if (!allowedTypes.includes(file.type)) {
                    logoUploadError.textContent = 'Invalid file type. Only PNG, JPG, JPEG, GIF, SVG are allowed.';
                    uploadLogoButton.disabled = true;
                    currentLogoPreview.style.display = 'none'; 
                } else {
                    logoUploadError.textContent = '';
                    uploadLogoButton.disabled = false;
                    
                    // Show client-side preview of the newly selected file
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        currentLogoPreview.src = e.target.result;
                        currentLogoPreview.style.display = 'block'; 
                    };
                    reader.readAsDataURL(file);
                }
            } else {
                uploadLogoButton.disabled = true;                
                if (currentLogoPreview.getAttribute('data-initial-src')) {
                    currentLogoPreview.src = currentLogoPreview.getAttribute('data-initial-src');
                    currentLogoPreview.style.display = 'block';
                } else {
                    currentLogoPreview.style.display = 'none';
                }
            }
        });

        uploadLogoButton.addEventListener('click', async function() {
            if (!orgId) {
                displayNotification('Organization ID not found. Cannot upload logo.', 'error');
                return;
            }

            const file = logoFileInput.files[0];
            if (!file) {
                logoUploadError.textContent = 'Please select a logo file to upload.';
                return;
            }

            const allowedTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/svg+xml'];
            if (!allowedTypes.includes(file.type)) {
                logoUploadError.textContent = 'Invalid file type. Only PNG, JPG, JPEG, GIF, SVG are allowed.';
                return;
            } else {
                logoUploadError.textContent = '';
            }

            const formData = new FormData();
            formData.append('logo_file', file);

            try {
                const response = await fetch(`/admin/organizations/${orgId}/logo`, {
                    method: 'PUT',
                    body: formData,
                });

                const data = await response.json();

                if (response.ok) {
                    displayNotification(data.message, 'success');                    
                } else {
                    displayNotification('Error uploading logo: ' + (data.detail || 'Unknown error'), 'error');
                }
            } catch (error) {
                console.error('Fetch error:', error);
                displayNotification('An error occurred while uploading the logo.', 'error');
            }
        });
        
        if (currentLogoPreview.src) {
            currentLogoPreview.setAttribute('data-initial-src', currentLogoPreview.src);
        }
    });