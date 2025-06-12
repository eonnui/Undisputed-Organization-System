// Function to display notifications
function displayNotification(message, type = 'info') {
    const notification = document.createElement('div');
    // Applying minimal inline styles for visibility, no external CSS classes
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.padding = '15px';
    notification.style.borderRadius = '8px';
    notification.style.zIndex = '1000';
    notification.style.backgroundColor = type === 'success' ? '#28a745' : (type === 'error' ? '#dc3545' : '#3498db');
    notification.style.color = 'white';
    notification.style.fontWeight = 'bold';
    notification.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
    notification.style.opacity = '0';
    notification.style.transition = 'opacity 0.3s ease-in-out';
    notification.textContent = message;
    document.body.appendChild(notification);

    void notification.offsetWidth; // Trigger reflow for transition
    notification.style.opacity = '1';

    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(()=> notification.remove(), 300);
    }, 3000);
}

document.addEventListener('DOMContentLoaded', function() {
    // --- Admin Settings Logic (Theme Color and Logo Upload) ---
    const orgId = document.getElementById('organizationId').value;
    const themeColorInput = document.getElementById('themeColorInput');
    const themeColorPicker = document.getElementById('themeColorPicker');
    const saveThemeButton = document.getElementById('saveThemeColorButton');
    const themeColorError = document.getElementById('themeColorError'); // Corrected assignment here

    const logoFileInput = document.getElementById('logoFileInput');
    const uploadLogoButton = document.getElementById('uploadLogoButton');
    const logoUploadError = document.getElementById('logoUploadError');
    const currentLogoPreview = document.getElementById('currentLogoPreview');

    // Theme Color Logic
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

    // Logo Upload Logic
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

    // --- Admin Activity Log Logic ---
    let currentPage = 1;
    const limit = 20;

    async function fetchAdminLogs() {
        let url = `/admin-logs?skip=${(currentPage - 1) * limit}&limit=${limit}`;

        try {
            const response = await fetch(url);
            if (!response.ok) {
                if (response.status === 403) {
                    displayNotification("You are not authorized to view admin logs.", 'error');
                } else {
                    displayNotification("Failed to fetch admin logs.", 'error');
                }
                console.error("Failed to fetch admin logs:", response.statusText);
                renderLogs([]);
                return;
            }
            const logs = await response.json();
            renderLogs(logs);
            updatePaginationControls(logs.length);
        } catch (error) {
            console.error("Error fetching admin logs:", error);
            displayNotification("An error occurred while fetching admin logs.", 'error');
            renderLogs([]);
        }
    }

    function renderLogs(logs) {
        const tableBody = document.getElementById('logTableBody');
        tableBody.innerHTML = '';

        if (logs.length === 0) {
            // Updated colspan to match the new number of columns (5)
            tableBody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 10px; color: #555;">No logs found.</td></tr>';
            return;
        }

        logs.forEach(log => {
            const row = document.createElement('tr');

            const timestamp = new Date(log.timestamp).toLocaleString();
            const adminName = log.admin_name || 'N/A';
            // Removed organizationName as per request and to fix the ReferenceError
            const actionType = log.action_type || 'N/A';
            const description = log.description || 'No description provided.';
            // Removed targetEntity as per request and to fix the ReferenceError
            const ipAddress = log.ip_address || 'N/A';

            row.innerHTML = `
                <td>${timestamp}</td>
                <td>${adminName}</td>
                <td>${actionType}</td>
                <td>${description}</td>
                <td>${ipAddress}</td>
            `; // Removed the <td> for organizationName and targetEntity
            tableBody.appendChild(row);
        });
    }

    function updatePaginationControls(currentResultsCount) {
        document.getElementById('pageInfo').textContent = `Page ${currentPage}`;
        document.getElementById('prevPageBtn').disabled = currentPage === 1;
        document.getElementById('nextPageBtn').disabled = currentResultsCount < limit;
    }

    fetchAdminLogs();

    document.getElementById('prevPageBtn').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            fetchAdminLogs();
        }
    });

    document.getElementById('nextPageBtn').addEventListener('click', () => {
        currentPage++;
        fetchAdminLogs();
    });
});