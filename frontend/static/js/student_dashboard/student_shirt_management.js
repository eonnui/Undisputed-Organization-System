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
    let currentPricePerShirt = 0;

    const orderDetailModal = document.getElementById('orderDetailModal');
    const closeOrderDetailModalButton = document.getElementById('closeOrderDetailModal');
    const orderDetailContent = document.getElementById('orderDetailContent');
    const modalOrderDetailIdDisplay = document.getElementById('modalOrderDetailId');
    // Note: viewDetailsButtons should be re-queried or attached dynamically if orders are loaded via AJAX
    // For static pages, this is fine if they are present on initial load
    const viewDetailsButtons = document.querySelectorAll('.view-details-button');

    // --- NEW ELEMENTS FOR UPDATE MODAL ---
    const updateOrderModal = document.getElementById('updateOrderModal');
    const closeUpdateOrderModalButton = document.querySelector('#updateOrderModal .close-button');
    const updateOrderForm = document.getElementById('updateOrderForm');
    const updateOrderId = document.getElementById('updateOrderId');
    const updateQuantityInput = document.getElementById('updateQuantity');
    const updateShirtSizeInput = document.getElementById('updateShirtSize');
    const updateDisplayTotalAmount = document.getElementById('updateDisplayTotalAmount');
    const updateOrderTotalAmount = document.getElementById('updateOrderTotalAmount');
    const updateOrderMessage = document.getElementById('updateOrderMessage');
    let currentUpdatePricePerShirt = 0;
    // --- END NEW ELEMENTS ---

    // --- NEW: Select all order elements for filtering and the toggle button ---
    const allOrderDisplayElements = document.querySelectorAll('.order-item, .order-card');
    const toggleCompletedOrdersButton = document.getElementById('toggleCompletedOrdersButton');
    // Keep track of the current state of the toggle button
    let hidingCompletedOrders = true; // Initialize to true, matching the initial button text "Hide Completed Orders"


    const DELETE_ORDER_URL_BASE = '/orders/';
    const UPDATE_ORDER_URL_BASE = '/orders/';

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
        button.addEventListener('click', function() {
            const campaignId = this.dataset.campaignId;
            const campaignTitle = this.dataset.campaignTitle;
            currentPricePerShirt = parseFloat(this.dataset.pricePerShirt);
            modalCampaignId.value = campaignId;
            modalCampaignTitle.textContent = campaignTitle;
            quantityInput.value = 1;
            updateTotalAmount();
            orderModal.style.display = 'block';
            orderMessage.textContent = '';
        });
    });

    quantityInput.addEventListener('input', updateTotalAmount);

    function updateTotalAmount() {
        const quantity = parseInt(quantityInput.value);
        if (isNaN(quantity) || quantity < 1) {
            quantityInput.value = 1;
            const total = currentPricePerShirt;
            displayTotalAmount.textContent = `₱${total.toFixed(2)}`;
            modalOrderTotalAmount.value = total.toFixed(2);
        } else {
            const total = currentPricePerShirt * quantity;
            displayTotalAmount.textContent = `₱${total.toFixed(2)}`;
            modalOrderTotalAmount.value = total.toFixed(2);
        }
    }

    // --- Update Order Modal Price Calculation ---
    function updateOrderDetailTotalAmount() {
        const quantity = parseInt(updateQuantityInput.value);
        if (isNaN(quantity) || quantity < 1) {
            updateQuantityInput.value = 1;
            const total = currentUpdatePricePerShirt;
            updateDisplayTotalAmount.textContent = `₱${total.toFixed(2)}`;
            updateOrderTotalAmount.value = total.toFixed(2);
        } else {
            const total = currentUpdatePricePerShirt * quantity;
            updateDisplayTotalAmount.textContent = `₱${total.toFixed(2)}`;
            updateOrderTotalAmount.value = total.toFixed(2);
        }
    }

    updateQuantityInput.addEventListener('input', updateOrderDetailTotalAmount);

    // --- Form Submissions ---
    orderForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        orderMessage.textContent = 'Submitting order...';
        orderMessage.style.color = 'blue';
        const formData = new FormData(orderForm);
        formData.set('order_total_amount', parseFloat(modalOrderTotalAmount.value));
        try {
            const response = await fetch(CREATE_ORDER_URL, {
                method: 'POST',
                body: formData,
            });
            if (response.ok) {
                const result = await response.json();
                orderMessage.textContent = 'Order placed successfully!';
                orderMessage.style.color = 'green';
                console.log('Order successful:', result);
                setTimeout(() => {
                    orderModal.style.display = 'none';
                    location.reload(); // Reload to reflect new order and re-apply filters
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
                    location.reload(); // Reload to reflect updated order and re-apply filters
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
                location.reload(); // Reload to reflect the deletion and re-apply filters
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
        // Use event delegation for dynamically added buttons if orders are loaded via AJAX
        // or re-query all of them. For static HTML, re-querying like this is fine.
        document.querySelectorAll('.view-details-button').forEach(button => {
            button.removeEventListener('click', handleViewDetailsClick); // Prevent duplicate listeners
            button.addEventListener('click', handleViewDetailsClick);
        });
    }

    async function handleViewDetailsClick() {
        const orderId = this.dataset.orderId;
        modalOrderDetailIdDisplay.textContent = `(ID: ${orderId})`;
        orderDetailContent.innerHTML = '<p class="loading-message">Loading order details...</p>';
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

    // Initial attachment of listeners for view details buttons on page load
    attachViewDetailsButtonListeners();

    // --- Display Order Details in Modal ---
    function displayOrderDetail(order) {
        const formatDate = (dateString) => {
            if (!dateString) return 'N/A';
            const options = { year: 'numeric', month: 'long', day: 'numeric', hour: 'numeric', minute: 'numeric', hour12: true };
            return new Date(dateString).toLocaleDateString('en-US', options);
        };

        let paymentStatusHtml = '';
        // Check if payment is successful for determining button visibility
        const isPaymentSuccessful = order.payment && (order.payment.status === 'paid' || order.payment.status === 'success');
        const orderCanBeRemoved = !isPaymentSuccessful; // Can only remove if not successfully paid
        const orderCanBeEdited = !isPaymentSuccessful; // Can only edit if not successfully paid

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
            campaignDetailsHtml = `
                <h3>Campaign Details</h3>
                <p><strong>Campaign:</strong> ${order.campaign.title || 'N/A'}</p>
                <p><strong>Description:</strong> ${order.campaign.description || 'N/A'}</p>
                <p><strong>Price per Shirt:</strong> &#8369;${(order.campaign.price_per_shirt || 0).toFixed(2)}</p>
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
                <button class="edit-order-button" data-order-id="${order.id}"
                        data-quantity="${order.quantity}"
                        data-shirt-size="${order.shirt_size}"
                        data-price-per-shirt="${order.campaign.price_per_shirt}">
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
        // Attach listeners for buttons within the dynamically loaded content
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
            editOrderButton.addEventListener('click', function() {
                updateOrderId.value = order.id;
                updateQuantityInput.value = order.quantity;
                updateShirtSizeInput.value = order.shirt_size;
                currentUpdatePricePerShirt = order.campaign.price_per_shirt; // Assuming campaign price is available
                updateOrderDetailTotalAmount();

                orderDetailModal.style.display = 'none'; // Hide detail modal
                updateOrderModal.style.display = 'block'; // Show update modal
                updateOrderMessage.textContent = '';
            });
        }
    }


    // --- Toggle Completed Orders Functionality ---
    // Function to apply/remove the 'hidden-order' class based on the toggle state
    function toggleCompletedOrders() {
        allOrderDisplayElements.forEach(orderElement => {
            const paymentStatus = orderElement.dataset.paymentStatus; // Get the status from data attribute

            // Define statuses that should be considered "completed" and thus hidden
            const completedStatuses = ['paid', 'success', 'collected']; // Added 'collected' as a potential completed status

            if (paymentStatus && completedStatuses.includes(paymentStatus.toLowerCase())) {
                if (hidingCompletedOrders) {
                    orderElement.classList.add('hidden-order'); // Hide the element
                } else {
                    orderElement.classList.remove('hidden-order'); // Show the element
                }
            }
        });

        // Update button text and state
        if (hidingCompletedOrders) {
            toggleCompletedOrdersButton.textContent = 'Show Completed Orders';
        } else {
            toggleCompletedOrdersButton.textContent = 'Hide Completed Orders';
        }
    }

    // Add event listener for the toggle button
    toggleCompletedOrdersButton.addEventListener('click', () => {
        hidingCompletedOrders = !hidingCompletedOrders; // Toggle the state
        toggleCompletedOrders(); // Apply the new state
    });

    // --- Initial filtering when the page loads ---
    // Call the filter function once when the DOM is loaded to apply initial hiding
    toggleCompletedOrders();


    // --- Section Display (if you have navigation to specific sections) ---
    const hash = window.location.hash;
    const campaignsSection = document.getElementById('campaigns-section');
    const myOrdersSection = document.getElementById('my-orders-section');
    
    // Default to showing both sections if no hash or an invalid hash is present
    campaignsSection.style.display = 'block';
    myOrdersSection.style.display = 'block';

    if (hash === '#my-orders-section') {
        // If the URL has #my-orders-section, you might want to hide campaigns and scroll to orders
        // For now, we'll just ensure it's visible, as the default above already makes both visible.
        // You could add: campaignsSection.style.display = 'none'; if you only want one section visible.
        myOrdersSection.scrollIntoView({ behavior: 'smooth' });
    }
});