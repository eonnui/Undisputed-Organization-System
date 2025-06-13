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
    const adminId = adminDataElement.dataset.adminId ? parseInt(adminDataElement.dataset.adminId) : null;
    const organizationId = adminDataElement.dataset.organizationId ? parseInt(adminDataElement.dataset.organizationId) : null;

    
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
    

    async function fetchCampaigns() {
        try {
            const orgFilter = (organizationId !== null) ? `?organization_id=${organizationId}` : '';
            const response = await fetch(`/campaigns/${orgFilter}`);
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

            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${campaign.title}</td>
                <td>${descriptionSnippet}</td>
                <td>₱${campaign.price_per_shirt.toFixed(2)}</td>
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

        try {
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

        try {
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
            const response = await fetch(`/campaigns/${campaignId}`, {
                method: 'DELETE'
            });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            showAlert('Campaign deleted successfully!');
            fetchCampaigns();
        } catch (error) {
            console.error('Error deleting campaign:', error);
            showAlert('Failed to delete campaign.', 'danger');
        }
    }

    document.querySelector('#campaignsTable tbody').addEventListener('click', async function(event) {
        if (event.target.classList.contains('edit-campaign-btn')) {
            const campaignId = event.target.dataset.campaignId;
            try {
                const response = await fetch(`/campaigns/${campaignId}`);
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                const campaign = await response.json();

                document.getElementById('editCampaignId').value = campaign.id;
                document.getElementById('editCampaignTitle').value = campaign.title;
                document.getElementById('editCampaignDescription').value = campaign.description || '';
                document.getElementById('editCampaignPrice').value = campaign.price_per_shirt;
                document.getElementById('editCampaignPreOrderDeadline').value = formatDateForInput(campaign.pre_order_deadline, false);
                document.getElementById('editCampaignStock').value = campaign.available_stock;
                document.getElementById('editCampaignIsActive').checked = campaign.is_active;

                const currentImageDiv = document.getElementById('currentSizeChartImage');
                if (campaign.size_chart_image_path) {
                    currentImageDiv.innerHTML = `<img src="${campaign.size_chart_image_path}" style="max-width: 150px; height: auto;"><p>Current Image</p>`;
                } else {
                    currentImageDiv.innerHTML = `<p>No current image.</p>`;
                }
                document.getElementById('editCampaignSizeChart').value = '';

                showCustomModal('editCampaignModal'); 

            } catch (error) {
                console.error('Error fetching campaign for edit:', error);
                showAlert('Failed to load campaign details for editing.', 'danger');
            }
        } else if (event.target.classList.contains('delete-campaign-btn')) {
            const campaignId = event.target.dataset.campaignId;
            handleDeleteCampaign(campaignId);
        }
    });

    async function fetchOrders(campaignId = null, statusFilter = null) {
        let url;
        if (campaignId) {
            url = `/orders/campaign/${campaignId}`;
        } else {
            document.querySelector('#ordersTable tbody').innerHTML = '<tr><td colspan="10" class="text-center">Select a campaign to view orders.</td></tr>';
            return;
        }

        url += `?skip=0&limit=200`;
        if (statusFilter) {
            url += `&status=${statusFilter}`;
        }

        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const orders = await response.json();
            populateOrdersTable(orders);
        } catch (error) {
            console.error('Error fetching orders:', error);
            showAlert('Failed to load orders.', 'danger');
        }
    }

    function populateOrdersTable(orders) {
        const tbody = document.querySelector('#ordersTable tbody');
        tbody.innerHTML = '';
        if (orders.length === 0) {
            tbody.innerHTML = '<tr><td colspan="10" class="text-center">No orders found for this selection.</td></tr>';
            return;
        }
        orders.forEach(order => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${order.id}</td>
                <td>${order.user.first_name} ${order.user.last_name} (${order.user.student_number})</td>
                <td>${order.campaign.name}</td>
                <td>${order.size}</td>
                <td>${order.quantity}</td>
                <td>₱${order.total_price.toFixed(2)}</td>
                <td>${order.payment_status}</td>
                <td>${order.order_status}</td>
                <td>
                    ${order.payment_screenshot_path ? `<a href="${order.payment_screenshot_path}" target="_blank">View</a>` : 'N/A'}
                </td>
                <td>
                    <button class="custom-button custom-button-warning update-order-status-btn"
                            data-order-id="${order.id}"
                            data-current-status="${order.order_status}">
                        Update Status
                    </button>
                </td>
            `;
        });
    }

    function populateCampaignFilter(campaigns) {
        const select = document.getElementById('orderCampaignFilter');
        select.innerHTML = '<option value="">All Campaigns</option>';
        campaigns.forEach(campaign => {
            const option = document.createElement('option');
            option.value = campaign.id;
            option.textContent = campaign.name;
            select.appendChild(option);
        });
    }

    async function handleUpdateOrderStatus(event) {
        event.preventDefault();
        const form = event.target;
        const orderId = document.getElementById('updateOrderId').value;
        const newStatus = document.getElementById('newOrderStatus').value;
        const formData = new FormData();
        formData.append('order_status', newStatus);

        try {
            const response = await fetch(`/orders/${orderId}`, {
                method: 'PUT',
                body: formData
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const updatedOrder = await response.json();
            showAlert('Order status updated successfully!');
            const selectedCampaignId = document.getElementById('orderCampaignFilter').value;
            const selectedStatus = document.getElementById('orderStatusFilter').value;
            fetchOrders(selectedCampaignId, selectedStatus);

            hideCustomModal('updateOrderStatusModal'); 

        } catch (error) {
            console.error('Error updating order status:', error);
            showAlert(`Failed to update order status: ${error.message}`, 'danger');
        }
    }

    document.querySelector('#ordersTable tbody').addEventListener('click', function(event) {
        if (event.target.classList.contains('update-order-status-btn')) {
            const orderId = event.target.dataset.orderId;
            const currentStatus = event.target.dataset.currentStatus;
            document.getElementById('updateOrderId').value = orderId;
            document.getElementById('orderCurrentStatus').value = currentStatus;
            document.getElementById('newOrderStatus').value = currentStatus;

            showCustomModal('updateOrderStatusModal'); 
        }
    });

    
    const createCampaignButton = document.querySelector('button[data-bs-target="#createCampaignModal"]');
    if (createCampaignButton) {
        createCampaignButton.addEventListener('click', function() {
            console.log('Add New Campaign button clicked.');
            showCustomModal('createCampaignModal');
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
    document.getElementById('updateOrderStatusForm').addEventListener('submit', handleUpdateOrderStatus);

    document.getElementById('applyOrderFilters').addEventListener('click', () => {
        const campaignId = document.getElementById('orderCampaignFilter').value;
        const status = document.getElementById('orderStatusFilter').value;
        fetchOrders(campaignId || null, status || null);
    });

    fetchCampaigns();
});