document.addEventListener('DOMContentLoaded', function() {
    const style = document.createElement('style');
    style.textContent = `
        .btn-close {
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: #aaa;
            line-height: 1;
            padding: 5px;
            transition: color 0.2s ease;
        }

        .btn-close:hover,
        .btn-close:focus {
            color: #000;
            outline: none;
        }

        .modal-body {
            padding: 20px;
        }
        .modal-body .mb-3 {
            /* Example 1: Add a light background and padding */
            padding: 15px; /* Adds space inside the box */
            margin-bottom: 15px; /* Slightly adjust default margin if desired */
            background-color: #f8f9fa; /* Light grey background */
            border: 1px solid #e2e6ea; /* Subtle border */
            border-radius: 5px; /* Rounded corners */
        }

        .modal-footer {
            padding: 15px;
            border-top: 1px solid #e9e9e9;
            display: flex;
            justify-content: flex-end;
            gap: 10px;
        }

        @keyframes slideInBottom {
            from { transform: translateY(20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        .custom-alert {
            padding: 15px;
            margin-bottom: 1rem;
            border: 1px solid transparent;
            border-radius: 0.25rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.9rem;
            opacity: 1;
            transition: opacity 0.5s ease-out;
        }

        .custom-alert-success {
            color: #0f5132;
            background-color: #d1e7dd;
            border-color: #badbcc;
        }

        .custom-alert-danger {
            color: #842029;
            background-color: #f8d7da;
            border-color: #f5c2c7;
        }

        .custom-close-btn {
            background: none;
            border: none;
            font-size: 1.25rem;
            line-height: 1;
            color: inherit;
            cursor: pointer;
            padding: 0 5px;
            opacity: 0.5;
            transition: opacity 0.2s ease;
        }

        .custom-close-btn:hover {
            opacity: 1;
        }

        body.modal-open {
            overflow: hidden;
        }
    `;
    document.head.appendChild(style);

    const adminDataElement = document.getElementById('adminData');

    const adminId = adminDataElement ? (adminDataElement.dataset.adminId ? parseInt(adminDataElement.dataset.adminId) : null) : null;
    const organizationId = adminDataElement ? (adminDataElement.dataset.organizationId ? parseInt(adminDataElement.dataset.organizationId) : null) : null;

    // getAuthToken() is REMOVED as sessions don't use client-side tokens

    function showCustomModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            console.log(`Showing modal: ${modalId}`);
            modal.style.display = 'flex';
            modal.style.opacity = '1';
            modal.setAttribute('aria-hidden', 'false');
            modal.classList.add('show-modal');
            document.body.classList.add('modal-open');
            const handleModalClick = function(event) {
                if (event.target === modal) {
                    console.log(`Clicked outside modal content for ${modalId}. Hiding.`);
                    hideCustomModal(modalId);
                }
            };
            modal.removeEventListener('click', handleModalClick);
            modal.addEventListener('click', handleModalClick);
        }
    }
    function hideCustomModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            console.log(`Hiding modal: ${modalId}`);
            modal.style.display = 'none';
            modal.style.opacity = '0';
            modal.setAttribute('aria-hidden', 'true');
            modal.classList.remove('show-modal');
            document.body.classList.remove('modal-open');
        }
    }
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            console.log('Escape key pressed.');
            const openModals = document.querySelectorAll('.modal[aria-hidden="false"]');
            if (openModals.length > 0) {
                hideCustomModal(openModals[openModals.length - 1].id);
            }
        }
    });
    function formatDateForInput(dateString, includeTime = true) {
        const date = new Date(dateString);
        const year = date.getFullYear();
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const day = date.getDate().toString().padStart(2, '0');
        if (includeTime) {
            const hours = date.getHours().toString().padStart(2, '0');
            const minutes = date.getMinutes().toString().padStart(2, '0');
            return `${year}-${month}-${day}T${hours}:${minutes}`;
        } else {
            return `${year}-${month}-${day}`;
        }
    }
    function showAlert(message, type = 'success') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `custom-alert custom-alert-${type} custom-alert-dismissible`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="custom-close-btn" aria-label="Close">&times;</button>
        `;
        document.querySelector('.container-fluid').prepend(alertDiv);
        alertDiv.querySelector('.custom-close-btn').addEventListener('click', function() {
            console.log('Alert close button clicked.');
            alertDiv.remove();
        });
        setTimeout(() => alertDiv.remove(), 5000);
    }

    // Helper function to create a size and price input row
    function createSizePriceRow(size = '', price = '') {
        const row = document.createElement('div');
        row.classList.add('row', 'g-2', 'mb-2', 'align-items-center', 'size-price-row');
        row.innerHTML = `
            <div class="col-5">
                <input type="text" class="form-control form-control-sm campaign-size" placeholder="Size (e.g., S, M, XL)" value="${size}" required>
            </div>
            <div class="col-5">
                <input type="number" step="0.01" class="form-control form-control-sm campaign-price" placeholder="Price" value="${price}" required>
            </div>
            <div class="col-2">
                <button type="button" class="btn btn-danger btn-sm remove-size-price-row">X</button>
            </div>
        `;
        return row;
    }

    // Add event listeners for adding size/price rows
    document.getElementById('addCreateCampaignSizePrice').addEventListener('click', function() {
        document.getElementById('createCampaignSizePricesContainer').appendChild(createSizePriceRow());
    });

    document.getElementById('addEditCampaignSizePrice').addEventListener('click', function() {
        document.getElementById('editCampaignSizePricesContainer').appendChild(createSizePriceRow());
    });

    // Delegated event listener for removing size/price rows
    document.querySelectorAll('#createCampaignSizePricesContainer, #editCampaignSizePricesContainer').forEach(container => {
        container.addEventListener('click', function(event) {
            if (event.target.classList.contains('remove-size-price-row')) {
                event.target.closest('.size-price-row').remove();
            }
        });
    });

    // Helper function to collect size and price data from the form
    function collectSizePriceData(containerId) {
        const pricesBySize = {};
        const container = document.getElementById(containerId);
        container.querySelectorAll('.size-price-row').forEach(row => {
            const sizeInput = row.querySelector('.campaign-size');
            const priceInput = row.querySelector('.campaign-price');
            if (sizeInput && priceInput && sizeInput.value && priceInput.value) {
                pricesBySize[sizeInput.value.trim()] = parseFloat(priceInput.value);
            }
        });
        return pricesBySize;
    }

    async function fetchCampaigns() {
        try {
            // No Authorization header needed for session-based auth
            const response = await fetch(`/campaigns/`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const campaigns = await response.json();
            populateCampaignsTable(campaigns);
            populateCampaignFilter(campaigns);
        } catch (error) {
            console.error('Error fetching campaigns:', error);
            showAlert('Failed to load campaigns.', 'danger');
        }
    }

    function populateCampaignsTable(campaigns) {
        const tbody = document.querySelector('#campaignsTable tbody');
        tbody.innerHTML = '';
        campaigns.forEach(campaign => {
            const descriptionSnippet = campaign.description ? campaign.description.substring(0, Math.min(campaign.description.length, 50)) + '...' : 'No description';

            let priceDisplay = '';
            if (campaign.prices_by_size) {
                const sizes = Object.keys(campaign.prices_by_size);
                if (sizes.length > 0) { // Check if there's at least one size
                    const firstSize = sizes[0];
                    const firstPrice = campaign.prices_by_size[firstSize];
                    priceDisplay = `₱${firstPrice.toFixed(2)} (${firstSize})`; // Display the first price and its size
                } else {
                    priceDisplay = 'N/A'; // No sizes defined
                }
            } else if (campaign.price_per_shirt) { // Fallback for old campaigns or if prices_by_size isn't available
                priceDisplay = `₱${campaign.price_per_shirt.toFixed(2)}`;
            } else {
                priceDisplay = 'N/A';
            }

            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${campaign.title}</td>
                <td>${descriptionSnippet}</td>
                <td>${priceDisplay}</td>
                <td>${new Date(campaign.pre_order_deadline).toLocaleDateString()}</td>
                <td>${campaign.available_stock}</td>
                <td>${campaign.is_active ? 'Yes' : 'No'}</td>
                <td>
                    ${campaign.size_chart_image_path ? `<img src="${campaign.size_chart_image_path}" alt="Size Chart" style="max-width: 80px; height: auto;">` : 'No Image'}
                </td>
                <td>
                    <button class="custom-button custom-button-info edit-campaign-btn" data-campaign-id="${campaign.id}">Edit</button>
                    <button class="custom-button custom-button-danger delete-campaign-btn" data-campaign-id="${campaign.id}">Delete</button>
                </td>
            `;
        });
    }

    async function handleCreateCampaign(event) {
        event.preventDefault();
        const form = event.target;
        const formData = new FormData(form);

        formData.set('is_active', form.querySelector('#campaignIsActive').checked ? 'true' : 'false');

        // MODIFIED: Collect prices by size
        const pricesBySize = collectSizePriceData('createCampaignSizePricesContainer');
        if (Object.keys(pricesBySize).length === 0) {
            showAlert('Please add at least one size and price.', 'danger');
            return;
        }
        formData.append('prices_by_size', JSON.stringify(pricesBySize));
        // Remove the old price_per_shirt if it exists in formData (optional, depends on backend)
        formData.delete('price_per_shirt');

        try {
            // No Authorization header for session-based auth
            const response = await fetch('/campaigns/', {
                method: 'POST',
                body: formData
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const newCampaign = await response.json();
            showAlert('Campaign created successfully!');
            fetchCampaigns();
            hideCustomModal('createCampaignModal');
            form.reset();
            // Reset the dynamic size/price fields after successful creation
            document.getElementById('createCampaignSizePricesContainer').innerHTML = '';
            document.getElementById('createCampaignSizePricesContainer').appendChild(createSizePriceRow()); // Add an initial empty row
        } catch (error) {
            console.error('Error creating campaign:', error);
            showAlert(`Failed to create campaign: ${error.message}`, 'danger');
        }
    }

    async function handleEditCampaign(event) {
        event.preventDefault();
        const form = event.target;
        const campaignId = form.querySelector('#editCampaignId').value;
        const formData = new FormData(form);

        formData.set('is_active', form.querySelector('#editCampaignIsActive').checked ? 'true' : 'false');

        // MODIFIED: Collect prices by size for editing
        const pricesBySize = collectSizePriceData('editCampaignSizePricesContainer');
        if (Object.keys(pricesBySize).length === 0) {
            showAlert('Please add at least one size and price.', 'danger');
            return;
        }
        formData.append('prices_by_size', JSON.stringify(pricesBySize));
        // Remove the old price_per_shirt if it exists in formData (optional, depends on backend)
        formData.delete('price_per_shirt');

        try {
            // No Authorization header for session-based auth
            const response = await fetch(`/campaigns/${campaignId}`, {
                method: 'PUT',
                body: formData
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const updatedCampaign = await response.json();
            showAlert('Campaign updated successfully!');
            fetchCampaigns();
            hideCustomModal('editCampaignModal');
        } catch (error) {
            console.error('Error updating campaign:', error);
            showAlert(`Failed to update campaign: ${error.message}`, 'danger');
        }
    }

    async function handleDeleteCampaign(campaignId) {
        if (!confirm('Are you sure you want to delete this campaign? This action cannot be undone.')) {
            return;
        }
        try {
            // No Authorization header for session-based auth
            const response = await fetch(`/campaigns/${campaignId}`, {
                method: 'DELETE'
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            showAlert('Campaign deleted successfully!');
            fetchCampaigns();
        } catch (error) {
            console.error('Error deleting campaign:', error);
            showAlert(`Failed to delete campaign: ${error.message}`, 'danger');
        }
    }

    document.querySelector('#campaignsTable tbody').addEventListener('click', async function(event) {
        if (event.target.classList.contains('edit-campaign-btn')) {
            const campaignId = event.target.dataset.campaignId;
            try {
                // No Authorization header for session-based auth
                const response = await fetch(`/campaigns/${campaignId}`);
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
                }
                const campaign = await response.json();

                document.getElementById('editCampaignId').value = campaign.id;
                document.getElementById('editCampaignTitle').value = campaign.title;
                document.getElementById('editCampaignDescription').value = campaign.description || '';
                // document.getElementById('editCampaignPrice').value = campaign.price_per_shirt; // REMOVED: No longer a single price input
                document.getElementById('editCampaignPreOrderDeadline').value = formatDateForInput(campaign.pre_order_deadline); // Changed to include time
                document.getElementById('editCampaignStock').value = campaign.available_stock;
                document.getElementById('editCampaignIsActive').checked = campaign.is_active;

                const currentImageDiv = document.getElementById('currentSizeChartImage');
                if (campaign.size_chart_image_path) {
                    currentImageDiv.innerHTML = `<img src="${campaign.size_chart_image_path}" style="max-width: 150px; height: auto;"><p>Current Image</p>`;
                } else {
                    currentImageDiv.innerHTML = `<p>No current image.</p>`;
                }
                document.getElementById('editCampaignSizeChart').value = ''; // Clear file input

                // MODIFIED: Populate size and price inputs for editing
                const editSizePricesContainer = document.getElementById('editCampaignSizePricesContainer');
                editSizePricesContainer.innerHTML = ''; // Clear existing rows
                if (campaign.prices_by_size && Object.keys(campaign.prices_by_size).length > 0) {
                    for (const size in campaign.prices_by_size) {
                        editSizePricesContainer.appendChild(createSizePriceRow(size, campaign.prices_by_size[size]));
                    }
                } else {
                    // If no prices_by_size, add a default empty row to start
                    editSizePricesContainer.appendChild(createSizePriceRow());
                }

                showCustomModal('editCampaignModal');
            } catch (error) {
                console.error('Error fetching campaign for edit:', error);
                showAlert(`Failed to load campaign details for editing: ${error.message}`, 'danger');
            }
        } else if (event.target.classList.contains('delete-campaign-btn')) {
            const campaignId = event.target.dataset.campaignId;
            handleDeleteCampaign(campaignId);
        }
    });

    // --- The crucial function for displaying orders (NO TOKEN REQUIRED HERE) ---
    async function fetchOrders(campaignId = null) {
        let url;

        // Construct the URL based on whether a campaign ID is provided
        if (campaignId && campaignId !== '') {
            url = `/orders/campaign/${campaignId}`;
        } else {
            url = `/orders/`; // This should fetch all orders for the admin's organization
        }

        url += `?skip=0&limit=200`; // Add pagination parameters

        try {
            // No Authorization header for session-based auth; browser automatically sends session cookie
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                const errorData = await response.json();
                // This will show any error from the backend, including 401 Unauthorized if no session
                throw new Error(`HTTP error! Status: ${response.status}, Detail: ${errorData.detail || response.statusText}`);
            }
            const orders = await response.json();
            populateOrdersTable(orders);
        } catch (error) {
            console.error('Error fetching orders:', error);
            // Display the specific error message from the backend
            showAlert(`Failed to load orders: ${error.message}`, 'danger');
            document.querySelector('#ordersTable tbody').innerHTML = `<tr><td colspan="6" class="text-center">Error loading orders: ${error.message}</td></tr>`;
        }
    }

    function populateOrdersTable(orders) {
        const tbody = document.querySelector('#ordersTable tbody');
        tbody.innerHTML = '';
        if (orders.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center">No orders found for this selection.</td></tr>';
            return;
        }
        orders.forEach(order => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${order.id}</td>
                <td>${order.student_name}</td>
                <td>${order.campaign.title}</td>
                <td>${order.shirt_size}</td>
                <td>${order.quantity}</td>
                <td>₱${order.order_total_amount.toFixed(2)}</td>
            `;
        });
    }

    function populateCampaignFilter(campaigns) {
        const select = document.getElementById('orderCampaignFilter');
        select.innerHTML = '<option value="">All Campaigns</option>';
        campaigns.forEach(campaign => {
            const option = document.createElement('option');
            option.value = campaign.id;
            option.textContent = campaign.title;
            select.appendChild(option);
        });
    }

    const createCampaignButton = document.querySelector('button[data-bs-target="#createCampaignModal"]');
    if (createCampaignButton) {
        createCampaignButton.addEventListener('click', function() {
            console.log('Add New Campaign button clicked.');
            showCustomModal('createCampaignModal');
            // Ensure at least one size/price row is present when creating a new campaign
            const createCampaignSizePricesContainer = document.getElementById('createCampaignSizePricesContainer');
            if (createCampaignSizePricesContainer.children.length === 0) {
                createCampaignSizePricesContainer.appendChild(createSizePriceRow());
            }
        });
    }

    document.querySelectorAll('.modal .btn-close').forEach(button => {
        button.addEventListener('click', function() {
            console.log('Modal close button clicked.');
            const modalId = button.closest('.modal').id;
            hideCustomModal(modalId);
        });
    });

    document.getElementById('createCampaignForm').addEventListener('submit', handleCreateCampaign);
    document.getElementById('editCampaignForm').addEventListener('submit', handleEditCampaign);

    document.getElementById('applyOrderFilters').addEventListener('click', () => {
        const campaignId = document.getElementById('orderCampaignFilter').value;
        fetchOrders(campaignId);
    });

    // Initial calls when the page loads
    fetchCampaigns();
    fetchOrders(''); // This will attempt to load all orders immediately
});