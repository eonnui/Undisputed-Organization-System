document.addEventListener('DOMContentLoaded', function() {

    const orderModal = document.getElementById('orderModal');
    const closeButtonOrderModal = document.querySelector('#orderModal .close-button');
    const orderForm = document.getElementById('orderForm');
    const modalCampaignId = document.getElementById('modalCampaignId');
    const modalCampaignTitle = document.getElementById('modalCampaignTitle');
    const quantityInput = document.getElementById('quantity');
    const displayTotalAmount = document.getElementById('displayTotalAmount');
    const modalOrderTotalAmount = document.getElementById('modalOrderTotalAmount');
    const orderMessage = document.getElementById('orderMessage');
    const orderButtons = document.querySelectorAll('.order-button');
    // MODIFIED: This will now store prices by size for the currently selected campaign
    let currentCampaignPricesBySize = {}; 
    let currentSelectedSize = ''; // To store the selected size for new orders

    const orderDetailModal = document.getElementById('orderDetailModal');
    const closeOrderDetailModalButton = document.getElementById('closeOrderDetailModal');
    const orderDetailContent = document.getElementById('orderDetailContent');
    const modalOrderDetailIdDisplay = document.getElementById('modalOrderDetailId');

    const updateOrderModal = document.getElementById('updateOrderModal');
    const closeUpdateOrderModalButton = document.querySelector('#updateOrderModal .close-button');
    const updateOrderForm = document.getElementById('updateOrderForm');
    const updateOrderId = document.getElementById('updateOrderId');
    const updateQuantityInput = document.getElementById('updateQuantity');
    const updateShirtSizeInput = document.getElementById('updateShirtSize'); // This should become a select/dropdown
    const updateDisplayTotalAmount = document.getElementById('updateDisplayTotalAmount');
    const updateOrderTotalAmount = document.getElementById('updateOrderTotalAmount');
    const updateOrderMessage = document.getElementById('updateOrderMessage');
    // MODIFIED: This will store prices by size for the campaign of the order being updated
    let currentUpdateCampaignPricesBySize = {}; 
    let currentUpdateSelectedSize = ''; // To store the selected size for updates


    const allOrderDisplayElements = document.querySelectorAll('.order-item, .order-card');
    const toggleCompletedOrdersButton = document.getElementById('toggleCompletedOrdersButton');
    let hidingCompletedOrders = true;

    // DEFINED: URL Endpoints
    const CREATE_ORDER_URL = '/orders/';
    const DELETE_ORDER_URL_BASE = '/orders/';
    const UPDATE_ORDER_URL_BASE = '/orders/';
    const GET_ORDER_DETAILS_URL_BASE = '/orders/';
    // IMPORTANT: Confirm this PayMaya URL with your backend
    const PAYMAYA_CREATE_PAYMENT_URL = '/payments/paymaya/create'; 

    // --- Modal Closing Logic ---
    closeButtonOrderModal.onclick = () => {
        orderModal.style.display = 'none';
    };
    closeOrderDetailModalButton.onclick = () => {
        orderDetailModal.style.display = 'none';
    };
    closeUpdateOrderModalButton.onclick = () => {
        updateOrderModal.style.display = 'none';
    };

    window.onclick = (event) => {
        if (event.target === orderModal) {
            orderModal.style.display = 'none';
        }
        if (event.target === orderDetailModal) {
            orderDetailModal.style.display = 'none';
        }
        if (event.target === updateOrderModal) {
            updateOrderModal.style.display = 'none';
        }
    };

    // --- New Order Functionality ---
    orderButtons.forEach(button => {
        button.addEventListener('click', async function() { // Added async here
            const campaignId = this.dataset.campaignId;
            const campaignTitle = this.dataset.campaignTitle;
            
            orderMessage.textContent = 'Loading campaign details...';
            orderMessage.style.color = 'blue';

            try {
                // Fetch full campaign details to get prices_by_size
                const response = await fetch(`/campaigns/${campaignId}`);
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
                }
                const campaign = await response.json();

                currentCampaignPricesBySize = campaign.prices_by_size || {};
                
                // Populate size selection in the modal
                const sizeSelect = document.getElementById('shirt_size'); // MODIFIED: Changed to 'shirt_size' to match HTML
                sizeSelect.innerHTML = ''; // Clear previous options

                if (Object.keys(currentCampaignPricesBySize).length > 0) {
                    for (const size in currentCampaignPricesBySize) {
                        const option = document.createElement('option');
                        option.value = size;
                        option.textContent = `${size} (₱${currentCampaignPricesBySize[size].toFixed(2)})`;
                        sizeSelect.appendChild(option);
                    }
                    currentSelectedSize = sizeSelect.value; // Set initial selected size
                } else {
                    sizeSelect.innerHTML = '<option value="">No sizes available</option>';
                    currentSelectedSize = '';
                    orderMessage.textContent = 'No sizes and prices defined for this campaign.';
                    orderMessage.style.color = 'red';
                    return; // Prevent opening modal if no sizes
                }

                modalCampaignId.value = campaignId;
                modalCampaignTitle.textContent = campaignTitle;
                quantityInput.value = 1;
                updateTotalAmount(); // Calculate initial total based on first size
                orderModal.style.display = 'block';
                orderMessage.textContent = ''; // Clear message on successful load
            } catch (error) {
                console.error('Error fetching campaign details for order:', error);
                orderMessage.textContent = `Failed to load campaign details: ${error.message}`;
                orderMessage.style.color = 'red';
            }
        });
    });

    // Event listener for size selection change
    const shirtSizeSelect = document.getElementById('shirt_size'); // MODIFIED: Changed to 'shirt_size' to match HTML
    if (shirtSizeSelect) {
        shirtSizeSelect.addEventListener('change', function() {
            currentSelectedSize = this.value;
            updateTotalAmount();
        });
    }

    quantityInput.addEventListener('input', updateTotalAmount);

    function updateTotalAmount() {
        const quantity = parseInt(quantityInput.value);
        const price = currentCampaignPricesBySize[currentSelectedSize]; // Get price for selected size

        if (isNaN(quantity) || quantity < 1 || !currentSelectedSize || isNaN(price)) {
            quantityInput.value = 1;
            displayTotalAmount.textContent = `₱0.00`;
            modalOrderTotalAmount.value = '0.00';
        } else {
            const total = price * quantity;
            displayTotalAmount.textContent = `₱${total.toFixed(2)}`;
            modalOrderTotalAmount.value = total.toFixed(2);
        }
    }

    // --- Update Order Modal Price Calculation ---
    function updateOrderDetailTotalAmount() {
        const quantity = parseInt(updateQuantityInput.value);
        const price = currentUpdateCampaignPricesBySize[currentUpdateSelectedSize]; // Get price for selected size

        if (isNaN(quantity) || quantity < 1 || !currentUpdateSelectedSize || isNaN(price)) {
            updateQuantityInput.value = 1;
            updateDisplayTotalAmount.textContent = `₱0.00`;
            updateOrderTotalAmount.value = '0.00';
        } else {
            const total = price * quantity;
            updateDisplayTotalAmount.textContent = `₱${total.toFixed(2)}`;
            updateOrderTotalAmount.value = total.toFixed(2);
        }
    }

    updateQuantityInput.addEventListener('input', updateOrderDetailTotalAmount);

    // Event listener for update size selection change
    if (updateShirtSizeInput) { // updateShirtSizeInput should now be a <select>
        updateShirtSizeInput.addEventListener('change', function() {
            currentUpdateSelectedSize = this.value;
            updateOrderDetailTotalAmount();
        });
    }

    // --- Form Submissions ---
    orderForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        orderMessage.textContent = 'Submitting order...';
        orderMessage.style.color = 'blue';
        
        // MODIFIED: Ensure selected size and current price are used
        const campaignId = modalCampaignId.value;
        const shirtSize = currentSelectedSize;
        const quantity = parseInt(quantityInput.value);
        const orderTotalAmount = parseFloat(modalOrderTotalAmount.value);

        // --- Start Debugging Logs ---
        console.log('--- Order Submission Data (Before FormData) ---');
        console.log('campaignId:', campaignId);
        console.log('shirtSize:', shirtSize);
        console.log('quantity:', quantity);
        console.log('orderTotalAmount:', orderTotalAmount);
        console.log('student_name value:', document.getElementById('student_name').value);
        console.log('student_year_section value:', document.getElementById('student_year_section').value);
        console.log('student_email value:', document.getElementById('student_email').value);
        console.log('student_phone value:', document.getElementById('student_phone').value);
        // --- End Debugging Logs ---

        if (!shirtSize || isNaN(quantity) || quantity < 1 || isNaN(orderTotalAmount) || orderTotalAmount <= 0) {
            orderMessage.textContent = 'Please select a size, enter a valid quantity, and ensure total amount is valid.';
            orderMessage.style.color = 'red';
            return;
        }

        // --- IMPORTANT CHANGE: Create FormData object ---
        const formData = new FormData();
        formData.append('campaign_id', campaignId);
        formData.append('shirt_size', shirtSize);
        formData.append('quantity', quantity);
        // order_total_amount is removed from backend form parameters. If you still need it, add it here.
        // formData.append('order_total_amount', orderTotalAmount); 
        formData.append('student_name', document.getElementById('student_name').value);
        formData.append('student_year_section', document.getElementById('student_year_section').value);
        
        // Optional fields, append only if they have values
        const studentEmail = document.getElementById('student_email').value;
        if (studentEmail) {
            formData.append('student_email', studentEmail);
        }
        const studentPhone = document.getElementById('student_phone').value;
        if (studentPhone) {
            formData.append('student_phone', studentPhone);
        }
        // --- END IMPORTANT CHANGE ---

        // Note: When sending FormData, browsers automatically set the 'Content-Type' header to 'multipart/form-data'
        // Do NOT manually set 'Content-Type': 'application/json' or it will cause issues.
        console.log('Payload sent to server (FormData):', formData); // Log the FormData object

        try {
            const response = await fetch(CREATE_ORDER_URL, {
                method: 'POST',
                // Removed headers: { 'Content-Type': 'application/json' }
                body: formData, // Send FormData directly
            });
            if (response.ok) {
                const result = await response.json();
                orderMessage.textContent = 'Order placed successfully!';
                orderMessage.style.color = 'green';
                console.log('Order successful:', result);
                setTimeout(() => {
                    orderModal.style.display = 'none';
                    location.reload(); 
                }, 1500);
            } else {
                const errorData = await response.json();
                orderMessage.textContent = `Error: ${errorData.detail || 'Failed to place order.'}`;
                orderMessage.style.color = 'red';
                console.error('Order failed:', errorData);
            }
        } catch (error) {
            orderMessage.textContent = 'An unexpected error occurred.';
            orderMessage.style.color = 'red';
            console.error('Network or other error:', error);
        }
    });

    updateOrderForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        updateOrderMessage.textContent = 'Updating order...';
        updateOrderMessage.style.color = 'blue';

        const orderId = updateOrderId.value;
        const updatedQuantity = parseInt(updateQuantityInput.value);
        const updatedShirtSize = updateShirtSizeInput.value;
        const updatedTotalAmount = parseFloat(updateOrderTotalAmount.value);

        // MODIFIED: Validate selected size and price data
        if (!updatedShirtSize || isNaN(updatedQuantity) || updatedQuantity < 1 || isNaN(updatedTotalAmount) || updatedTotalAmount <= 0) {
            updateOrderMessage.textContent = 'Please select a size, enter a valid quantity, and ensure total amount is valid.';
            updateOrderMessage.style.color = 'red';
            return;
        }

        const updateData = {
            quantity: updatedQuantity,
            shirt_size: updatedShirtSize,
            order_total_amount: updatedTotalAmount
        };

        try {
            const response = await fetch(`${UPDATE_ORDER_URL_BASE}${orderId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(updateData),
            });

            if (response.ok) {
                const result = await response.json();
                updateOrderMessage.textContent = 'Order updated successfully!';
                updateOrderMessage.style.color = 'green';
                console.log('Order update successful:', result);
                setTimeout(() => {
                    updateOrderModal.style.display = 'none';
                    location.reload();
                }, 1500);
            } else {
                const errorData = await response.json();
                updateOrderMessage.textContent = `Error: ${errorData.detail || 'Failed to update order.'}`;
                updateOrderMessage.style.color = 'red';
                console.error('Order update failed:', errorData);
            }
        } catch (error) {
            updateOrderMessage.textContent = 'An unexpected error occurred.';
            updateOrderMessage.style.color = 'red';
            console.error('Network or other error:', error);
        }
    });

    // --- PayMaya Payment Integration ---
    const paymayaPayButtons = document.querySelectorAll('.paymaya-pay-button');

    paymayaPayButtons.forEach(button => {
        button.addEventListener('click', handlePaymayaPayment);
    });

    async function handlePaymayaPayment(event) {
        const button = event.currentTarget;
        const paymentItemId = button.dataset.paymentItemId;
        const orderId = button.dataset.orderId;
        if (!paymentItemId) {
            alert('Payment item ID is missing. Cannot proceed with payment.');
            console.error('Missing paymentItemId for shirt order ID:', orderId);
            return;
        }
        button.disabled = true;
        const originalText = button.textContent;
        button.textContent = 'Processing...';
        const formData = new FormData();
        formData.append('payment_item_id', paymentItemId);
        try {
            const response = await fetch(PAYMAYA_CREATE_PAYMENT_URL, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `Failed to initiate PayMaya payment for order ${orderId}.`);
            }
            const paymentData = await response.json();
            const checkoutUrl = paymentData.redirectUrl;

            if (checkoutUrl) {
                window.location.href = checkoutUrl;
            } else {
                alert('PayMaya checkout URL not found in response. Please try again or contact support.');
                console.error('PayMaya response:', paymentData);
            }

        } catch (error) {
            console.error('Error initiating PayMaya payment:', error);
            alert(`Error initiating payment: ${error.message}. Please try again.`);
        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    }

    // --- Delete Order Functionality ---
    async function handleDeleteOrder(orderId) {
        if (!confirm('Are you sure you want to remove this order? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch(`${DELETE_ORDER_URL_BASE}${orderId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (response.ok) {
                alert('Order removed successfully!');
                location.reload(); 
            } else {
                const errorData = await response.json();
                alert(`Failed to remove order: ${errorData.detail || 'Unknown error.'}`);
                console.error('Failed to remove order:', errorData);
            }
        } catch (error) {
            console.error('Error removing order:', error);
            alert(`An unexpected error occurred while removing the order: ${error.message}`);
        }
    }

    // --- Utility Function (CSRF token, if needed for Flask) ---
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // --- View Details Button Logic (Dynamic Attachment) ---
    function attachViewDetailsButtonListeners() {
        document.querySelectorAll('.view-details-button').forEach(button => {
            button.removeEventListener('click', handleViewDetailsClick); 
            button.addEventListener('click', handleViewDetailsClick);
        });
    }

    async function handleViewDetailsClick() {
        const orderId = this.dataset.orderId;
        modalOrderDetailIdDisplay.textContent = `(ID: ${orderId})`;
        orderDetailContent.innerHTML = '<p class="loading-message">Loading order details...';
        orderDetailModal.style.display = 'flex';
        try {
            const response = await fetch(`${GET_ORDER_DETAILS_URL_BASE}${orderId}`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to fetch order details.');
            }
            const order = await response.json();
            displayOrderDetail(order);
        } catch (error) {
            console.error('Error fetching order details:', error);
            orderDetailContent.innerHTML = `<p class="error-message">Error loading details: ${error.message}</p>`;
        }
    }

    attachViewDetailsButtonListeners();

    // --- Display Order Details in Modal ---
    function displayOrderDetail(order) {
        const formatDate = (dateString) => {
            if (!dateString) return 'N/A';
            const options = { year: 'numeric', month: 'long', day: 'numeric', hour: 'numeric', minute: 'numeric', hour12: true };
            return new Date(dateString).toLocaleDateString('en-US', options);
        };

        let paymentStatusHtml = '';
        const isPaymentSuccessful = order.payment && (order.payment.status === 'paid' || order.payment.status === 'success');
        const orderCanBeRemoved = !isPaymentSuccessful; 
        const orderCanBeEdited = !isPaymentSuccessful; 

        if (order.payment) {
            const paymentStatusTagClass = `tag-${order.payment.status ? order.payment.status.toLowerCase() : 'pending'}`;
            paymentStatusHtml = `
                <p><strong>Status:</strong> <span class="order-status-tag ${paymentStatusTagClass}">${order.payment.status || 'Pending Payment'}</span></p>
                <p><strong>Payment ID:</strong> ${order.payment.paymaya_payment_id || 'N/A'}</p>
                <p><strong>Payment Amount:</strong> &#8369;${(order.payment.amount || 0).toFixed(2)}</p>
                <p><strong>Payment Created:</strong> ${formatDate(order.payment.created_at)}</p>
                <p><strong>Last Updated:</strong> ${formatDate(order.payment.updated_at)}</p>
            `;
        } else {
            paymentStatusHtml = `<p><strong>Status:</strong> <span class="order-status-tag tag-pending">Pending Payment</span></p><p>No payment record found yet.</p>`;
        }

        let campaignDetailsHtml = '';
        if (order.campaign) {
            let campaignPriceDisplay = 'N/A';
            if (order.campaign.prices_by_size && order.shirt_size && order.campaign.prices_by_size[order.shirt_size]) {
                campaignPriceDisplay = `&#8369;${order.campaign.prices_by_size[order.shirt_size].toFixed(2)} (${order.shirt_size})`;
            } else if (order.campaign.price_per_shirt) { // Fallback for old campaigns
                campaignPriceDisplay = `&#8369;${order.campaign.price_per_shirt.toFixed(2)}`;
            }

            campaignDetailsHtml = `
                <h3>Campaign Details</h3>
                <p><strong>Campaign:</strong> ${order.campaign.title || 'N/A'}</p>
                <p><strong>Description:</strong> ${order.campaign.description || 'N/A'}</p>
                <p><strong>Price per Shirt:</strong> ${campaignPriceDisplay}</p> 
                <p><strong>Pre-order Deadline:</strong> ${new Date(order.campaign.pre_order_deadline).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</p>
            `;
        } else {
            campaignDetailsHtml = `<h3>Campaign Details</h3><p>Campaign data not available.</p>`;
        }

        let modalPaymentButtonHtml = '';
        if (order.payment && !isPaymentSuccessful) {
            modalPaymentButtonHtml = `
                <button class="pay-button paymaya-pay-button-modal"
                        data-payment-item-id="${order.payment_item ? order.payment_item.id : ''}"
                        data-order-id="${order.id}">
                    Complete Payment
                </button>
            `;
        } else if (isPaymentSuccessful) {
            modalPaymentButtonHtml = `
                <button class="paid-button" disabled style="cursor: not-allowed;">
                    Payment Successful
                </button>
            `;
        }

        let removeOrderButtonHtml = '';
        if (orderCanBeRemoved) {
            removeOrderButtonHtml = `
                <button class="remove-order-button" data-order-id="${order.id}">
                    Remove Order
                </button>
            `;
        }

        let editOrderButtonHtml = '';
        if (orderCanBeEdited) {
            editOrderButtonHtml = `
                <button class="edit-order-button" data-order-id="${order.id}">
                    Edit Order
                </button>
            `;
        }

        orderDetailContent.innerHTML = `
            <div class="detail-section">
                ${campaignDetailsHtml}
            </div>
            <div class="detail-section">
                <h3>Your Order Information</h3>
                <p><strong>Ordered By:</strong> ${order.student_name || 'N/A'}</p>
                <p><strong>Student ID:</strong> ${order.student_id || 'N/A'}</p>
                <p><strong>Year & Section:</strong> ${order.student_year_section || 'N/A'}</p>
                <p><strong>Email:</strong> ${order.student_email || 'N/A'}</p>
                <p><strong>Phone:</strong> ${order.student_phone || 'N/A'}</p>
                <p><strong>Shirt Size:</strong> ${order.shirt_size || 'N/A'}</p>
                <p><strong>Quantity:</strong> ${order.quantity || 'N/A'}</p>
                <p><strong>Total Amount:</strong> &#8369;${(order.order_total_amount || 0).toFixed(2)}</p>
                <p><strong>Ordered On:</strong> ${formatDate(order.ordered_at)}</p>
            </div>

            <div class="detail-section">
                <h3>Payment Status</h3>
                ${paymentStatusHtml}
            </div>

            <div class="order-detail-actions">
                ${modalPaymentButtonHtml}
                ${editOrderButtonHtml}
                ${removeOrderButtonHtml}
            </div>
        `;
        
        const modalPayButton = orderDetailContent.querySelector('.paymaya-pay-button-modal');
        if (modalPayButton && !isPaymentSuccessful) {
            modalPayButton.addEventListener('click', handlePaymayaPayment);
        }

        const removeOrderButton = orderDetailContent.querySelector('.remove-order-button');
        if (removeOrderButton) {
            removeOrderButton.addEventListener('click', function() {
                handleDeleteOrder(order.id);
            });
        }

        const editOrderButton = orderDetailContent.querySelector('.edit-order-button');
        if (editOrderButton) {
            editOrderButton.addEventListener('click', async function() { // Added async here
                updateOrderId.value = order.id;
                updateQuantityInput.value = order.quantity;
                
                // Fetch full campaign details for update modal to get prices_by_size
                try {
                    const campaignResponse = await fetch(`/campaigns/${order.campaign.id}`);
                    if (!campaignResponse.ok) {
                        const errorData = await campaignResponse.json();
                        throw new Error(errorData.detail || `Failed to fetch campaign details for order update.`);
                    }
                    const campaign = await campaignResponse.json();
                    currentUpdateCampaignPricesBySize = campaign.prices_by_size || {};

                    // Populate update shirt size select/dropdown
                    updateShirtSizeInput.innerHTML = ''; // Clear previous options
                    if (Object.keys(currentUpdateCampaignPricesBySize).length > 0) {
                        for (const size in currentUpdateCampaignPricesBySize) {
                            const option = document.createElement('option');
                            option.value = size;
                            option.textContent = `${size} (₱${currentUpdateCampaignPricesBySize[size].toFixed(2)})`;
                            updateShirtSizeInput.appendChild(option);
                        }
                        // Set the current order's shirt size as selected
                        updateShirtSizeInput.value = order.shirt_size;
                        currentUpdateSelectedSize = order.shirt_size;
                    } else {
                        updateShirtSizeInput.innerHTML = '<option value="">No sizes available</option>';
                        currentUpdateSelectedSize = '';
                        updateOrderMessage.textContent = 'No sizes and prices defined for this campaign.';
                        updateOrderMessage.style.color = 'red';
                        return;
                    }

                    updateOrderDetailTotalAmount(); // Recalculate total based on loaded values

                    orderDetailModal.style.display = 'none'; 
                    updateOrderModal.style.display = 'block'; 
                    updateOrderMessage.textContent = '';
                } catch (error) {
                    console.error('Error fetching campaign details for order update:', error);
                    alert(`Failed to prepare order update: ${error.message}`);
                }
            });
        }
    }

    // --- Toggle Completed Orders Functionality ---
    function toggleCompletedOrders() {
        allOrderDisplayElements.forEach(orderElement => {
            const paymentStatus = orderElement.dataset.paymentStatus;

            const completedStatuses = ['paid', 'success', 'collected']; 

            if (paymentStatus && completedStatuses.includes(paymentStatus.toLowerCase())) {
                if (hidingCompletedOrders) {
                    orderElement.classList.add('hidden-order'); 
                } else {
                    orderElement.classList.remove('hidden-order'); 
                }
            }
        });

        if (hidingCompletedOrders) {
            toggleCompletedOrdersButton.textContent = 'Show Completed Orders';
        } else {
            toggleCompletedOrdersButton.textContent = 'Hide Completed Orders';
        }
    }

    toggleCompletedOrdersButton.addEventListener('click', () => {
        hidingCompletedOrders = !hidingCompletedOrders;
        toggleCompletedOrders();
    });

    toggleCompletedOrders();


    // --- Section Display (if you have navigation to specific sections) ---
    const hash = window.location.hash;
    const campaignsSection = document.getElementById('campaigns-section');
    const myOrdersSection = document.getElementById('my-orders-section');
    
    campaignsSection.style.display = 'block';
    myOrdersSection.style.display = 'block';

    if (hash === '#my-orders-section') {
        myOrdersSection.scrollIntoView({ behavior: 'smooth' });
    }
});