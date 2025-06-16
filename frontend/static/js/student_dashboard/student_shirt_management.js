document.addEventListener("DOMContentLoaded", function () {
  const globalModal = document.getElementById("global-modal");
  const globalModalCloseButton = document.querySelector(
    "#global-modal .modal-close-btn"
  );
  const globalModalBody = document.getElementById("modal-body");

  const orderForm = document.getElementById("orderForm");
  const modalCampaignId = document.getElementById("modalCampaignId");
  const modalCampaignTitle = document.getElementById("modalCampaignTitle");
  const quantityInput = document.getElementById("quantity");
  const displayTotalAmount = document.getElementById("displayTotalAmount");
  const modalOrderTotalAmount = document.getElementById(
    "modalOrderTotalAmount"
  );
  const orderMessage = document.getElementById("orderMessage");
  const orderButtons = document.querySelectorAll(".order-button");
  let currentCampaignPricesBySize = {};
  let currentSelectedSize = "";

  const modalOrderDetailIdDisplay =
    document.getElementById("modalOrderDetailId");

  const updateOrderId = document.getElementById("updateOrderId");
  const updateQuantityInput = document.getElementById("updateQuantity");
  const updateShirtSizeInput = document.getElementById("updateShirtSize");
  const updateDisplayTotalAmount = document.getElementById(
    "updateDisplayTotalAmount"
  );
  const updateOrderTotalAmount = document.getElementById(
    "updateOrderTotalAmount"
  );
  const updateOrderMessage = document.getElementById("updateOrderMessage");
  let currentUpdateCampaignPricesBySize = {};
  let currentUpdateSelectedSize = "";

  const allOrderDisplayElements = document.querySelectorAll(
    ".order-item, .order-card"
  );
  const toggleCompletedOrdersButton = document.getElementById(
    "toggleCompletedOrdersButton"
  );
  let hidingCompletedOrders = true;
  const CREATE_ORDER_URL = "/orders/";
  const DELETE_ORDER_URL_BASE = "/orders/";
  const UPDATE_ORDER_URL_BASE = "/orders/";
  const GET_ORDER_DETAILS_URL_BASE = "/orders/";
  const PAYMAYA_CREATE_PAYMENT_URL = "/payments/paymaya/create";

  if (globalModal && globalModalCloseButton) {
    globalModalCloseButton.onclick = () => {
      globalModal.style.display = "none";
      globalModalBody.innerHTML = "";
    };
  } else {
    console.warn(
      "Warning: 'globalModalCloseButton' or 'globalModal' not found. Close button functionality for global modal might be missing."
    );
  }

  window.onclick = (event) => {
    if (event.target === globalModal) {
      globalModal.style.display = "none";
      globalModalBody.innerHTML = "";
    }
  };

  orderButtons.forEach((button) => {
    button.addEventListener("click", async function () {
      const campaignId = this.dataset.campaignId;
      const campaignTitle = this.dataset.campaignTitle;

      const orderFormHtml = `
                <h2>Order for ${campaignTitle}</h2>
                <form id="orderForm" class="order-form">
                    <input type="hidden" id="modalCampaignId" name="campaign_id" value="${campaignId}">
                    <p id="modalCampaignTitle" style="display:none;">${campaignTitle}</p>
                    <div class="form-group">
                        <label for="modalStudentName">Your Name:</label>
                        <input type="text" id="modalStudentName" name="student_name"
                            value="${CURRENT_USER.firstName || ''} ${CURRENT_USER.lastName || ''}" required>
                    </div>
                    <div class="form-group">
                        <label for="modalStudentYearSection">Year & Section:</label>
                        <input type="text" id="modalStudentYearSection" name="student_year_section"
                            value="${CURRENT_USER.yearLevel || ''} ${CURRENT_USER.section || ''}" required>
                    </div>
                    <div class="form-group">
                        <label for="modalStudentEmail">Email (Optional):</label>
                        <input type="email" id="modalStudentEmail" name="student_email"
                            value="${CURRENT_USER.email || ''}">
                    </div>
                    <div class="form-group">
                        <label for="student_phone">Phone (Optional):</label>
                        <input type="tel" id="student_phone" name="student_phone">
                    </div>
                    <div class="form-group">
                        <label for="shirt_size">Shirt Size:</label>
                        <select id="shirt_size" name="shirt_size" required></select>
                    </div>
                    <div class="form-group">
                        <label for="quantity">Quantity:</label>
                        <input type="number" id="quantity" name="quantity" value="1" min="1" required>
                    </div>
                    <div class="form-group total-amount">
                        <span>Total:</span> <span id="displayTotalAmount">₱0.00</span>
                        <input type="hidden" id="modalOrderTotalAmount" name="order_total_amount" value="0.00">
                    </div>                    
                    <button type="submit" class="submit-button">Place Order</button>
                    <div class="form-message" id="orderMessage"></div>
                </form>
            `;

      globalModalBody.innerHTML = orderFormHtml;
      globalModal.style.display = "flex";

      const modalCampaignIdElem = document.getElementById("modalCampaignId");
      const modalCampaignTitleElem =
        document.getElementById("modalCampaignTitle");
      const quantityInputElem = document.getElementById("quantity");
      const displayTotalAmountElem =
        document.getElementById("displayTotalAmount");
      const modalOrderTotalAmountElem = document.getElementById(
        "modalOrderTotalAmount"
      );
      const orderMessageElem = document.getElementById("orderMessage");
      const shirtSizeSelect = document.getElementById("shirt_size");
      const orderFormElem = document.getElementById("orderForm");

      // Get the student name and year/section input fields from the dynamically created form
      const modalStudentNameInput = document.getElementById("modalStudentName");
      const modalStudentYearSectionInput = document.getElementById("modalStudentYearSection");
      const modalStudentEmailInput = document.getElementById("modalStudentEmail");
      const studentPhoneInput = document.getElementById("student_phone");


      orderMessageElem.textContent = "Loading campaign details...";
      orderMessageElem.style.color = "blue";
      try {
        const response = await fetch(`/campaigns/${campaignId}`);
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(
            errorData.detail || `HTTP error! status: ${response.status}`
          );
        }

        const campaign = await response.json();
        currentCampaignPricesBySize = campaign.prices_by_size || {};

        if (shirtSizeSelect) {
          shirtSizeSelect.innerHTML = "";

          if (Object.keys(currentCampaignPricesBySize).length > 0) {
            for (const size in currentCampaignPricesBySize) {
              const option = document.createElement("option");
              option.value = size;
              option.textContent = `${size} (₱${currentCampaignPricesBySize[
                size
              ].toFixed(2)})`;
              shirtSizeSelect.appendChild(option);
            }
            currentSelectedSize = shirtSizeSelect.value;
          } else {
            shirtSizeSelect.innerHTML =
              '<option value="">No sizes available</option>';
            currentSelectedSize = "";
            orderMessageElem.textContent =
              "No sizes and prices defined for this campaign.";
            orderMessageElem.style.color = "red";
            return;
          }
        } else {
          console.warn(
            "Warning: 'shirt_size' select element not found in dynamically loaded form."
          );
          orderMessageElem.textContent =
            "Error: Shirt size selection not available.";
          orderMessageElem.style.color = "red";
          return;
        }

        if (modalCampaignIdElem) modalCampaignIdElem.value = campaignId;
        if (modalCampaignTitleElem)
          modalCampaignTitleElem.textContent = campaignTitle;
        if (quantityInputElem) quantityInputElem.value = 1;

        if (shirtSizeSelect) {
          shirtSizeSelect.addEventListener("change", function () {
            currentSelectedSize = this.value;
            updateTotalAmount(
              quantityInputElem,
              displayTotalAmountElem,
              modalOrderTotalAmountElem
            );
          });
        }

        if (quantityInputElem) {
          quantityInputElem.addEventListener("input", () =>
            updateTotalAmount(
              quantityInputElem,
              displayTotalAmountElem,
              modalOrderTotalAmountElem
            )
          );
        }

        updateTotalAmount(
          quantityInputElem,
          displayTotalAmountElem,
          modalOrderTotalAmountElem
        );
        orderMessageElem.textContent = "";

        if (orderFormElem) {
          orderFormElem.addEventListener("submit", async function (event) {
            event.preventDefault();
            if (orderMessageElem) {
              orderMessageElem.textContent = "Submitting order...";
              orderMessageElem.style.color = "blue";
            }

            const campaignId = modalCampaignIdElem
              ? modalCampaignIdElem.value
              : null;
            const shirtSize = currentSelectedSize;
            const quantity = quantityInputElem
              ? parseInt(quantityInputElem.value)
              : 0;
            const orderTotalAmount = modalOrderTotalAmountElem
              ? parseFloat(modalOrderTotalAmountElem.value)
              : 0;

            console.log("--- Order Submission Data (Before FormData) ---");
            console.log("campaignId:", campaignId);
            console.log("shirtSize:", shirtSize);
            console.log("quantity:", quantity);
            console.log("orderTotalAmount:", orderTotalAmount);
            // Corrected: Use the correct IDs for dynamically created inputs
            console.log(
              "student_name value:",
              modalStudentNameInput ? modalStudentNameInput.value : "N/A"
            );
            console.log(
              "student_year_section value:",
              modalStudentYearSectionInput ? modalStudentYearSectionInput.value : "N/A"
            );
            console.log(
              "student_email value:",
              modalStudentEmailInput ? modalStudentEmailInput.value : "N/A"
            );
            console.log(
              "student_phone value:",
              studentPhoneInput ? studentPhoneInput.value : "N/A"
            );

            if (
              !shirtSize ||
              isNaN(quantity) ||
              quantity < 1 ||
              isNaN(orderTotalAmount) ||
              orderTotalAmount <= 0
            ) {
              if (orderMessageElem) {
                orderMessageElem.textContent =
                  "Please select a size, enter a valid quantity, and ensure total amount is valid.";
                orderMessageElem.style.color = "red";
              }
              return;
            }

            const formData = new FormData();
            if (campaignId) formData.append("campaign_id", campaignId);
            formData.append("shirt_size", shirtSize);
            formData.append("quantity", quantity);

            // Corrected: Append values from the correct dynamically created input fields
            if (modalStudentNameInput)
              formData.append("student_name", modalStudentNameInput.value);
            if (modalStudentYearSectionInput)
              formData.append(
                "student_year_section",
                modalStudentYearSectionInput.value
              );

            if (modalStudentEmailInput && modalStudentEmailInput.value) {
              formData.append("student_email", modalStudentEmailInput.value);
            }
            if (studentPhoneInput && studentPhoneInput.value) {
              formData.append("student_phone", studentPhoneInput.value);
            }

            console.log("Payload sent to server (FormData):", formData);
            try {
              const response = await fetch(CREATE_ORDER_URL, {
                method: "POST",
                body: formData,
              });
              if (response.ok) {
                const result = await response.json();
                if (orderMessageElem) {
                  orderMessageElem.textContent = "Order placed successfully!";
                  orderMessageElem.style.color = "green";
                }
                console.log("Order successful:", result);
                setTimeout(() => {
                  if (globalModal) globalModal.style.display = "none";
                  globalModalBody.innerHTML = "";
                  location.reload();
                }, 1500);
              } else {
                const errorData = await response.json();
                if (orderMessageElem) {
                  orderMessageElem.textContent = `Error: ${
                    errorData.detail || "Failed to place order."
                  }`;
                  orderMessageElem.style.color = "red";
                }
                console.error("Order failed:", errorData);
              }
            } catch (error) {
              if (orderMessageElem) {
                orderMessageElem.textContent = "An unexpected error occurred.";
                orderMessageElem.style.color = "red";
              }
              console.error("Network or other error:", error);
            }
          });
        } else {
          console.warn(
            "Warning: Dynamically created 'orderForm' not found. Order submission functionality might be missing."
          );
        }
      } catch (error) {
        console.error("Error fetching campaign details for order:", error);
        if (orderMessageElem) {
          orderMessageElem.textContent = `Failed to load campaign details: ${error.message}`;
          orderMessageElem.style.color = "red";
        }
      }
    });
  });

  function updateTotalAmount(
    quantityInputRef,
    displayTotalAmountRef,
    modalOrderTotalAmountRef
  ) {
    if (
      !quantityInputRef ||
      !displayTotalAmountRef ||
      !modalOrderTotalAmountRef
    ) {
      console.warn(
        "Missing elements for updateTotalAmount function. Cannot calculate total."
      );
      return;
    }

    const quantity = parseInt(quantityInputRef.value);
    const price = currentCampaignPricesBySize[currentSelectedSize];
    if (
      isNaN(quantity) ||
      quantity < 1 ||
      !currentSelectedSize ||
      isNaN(price)
    ) {
      quantityInputRef.value = 1;
      displayTotalAmountRef.textContent = `₱0.00`;
      modalOrderTotalAmountRef.value = "0.00";
    } else {
      const total = price * quantity;
      displayTotalAmountRef.textContent = `₱${total.toFixed(2)}`;
      modalOrderTotalAmountRef.value = total.toFixed(2);
    }
  }

  function updateOrderDetailTotalAmount(
    updateQuantityInputRef,
    updateDisplayTotalAmountRef,
    updateOrderTotalAmountRef
  ) {
    if (
      !updateQuantityInputRef ||
      !updateDisplayTotalAmountRef ||
      !updateOrderTotalAmountRef
    ) {
      console.warn(
        "Missing elements for updateOrderDetailTotalAmount function. Cannot calculate total."
      );
      return;
    }
    const quantity = parseInt(updateQuantityInputRef.value);
    const price = currentUpdateCampaignPricesBySize[currentUpdateSelectedSize];
    if (
      isNaN(quantity) ||
      quantity < 1 ||
      !currentUpdateSelectedSize ||
      isNaN(price)
    ) {
      updateQuantityInputRef.value = 1;
      updateDisplayTotalAmountRef.textContent = `₱0.00`;
      updateOrderTotalAmountRef.value = "0.00";
    } else {
      const total = price * quantity;
      updateDisplayTotalAmountRef.textContent = `₱${total.toFixed(2)}`;
      updateOrderTotalAmountRef.value = total.toFixed(2);
    }
  }

  const paymayaPayButtons = document.querySelectorAll(".paymaya-pay-button");

  paymayaPayButtons.forEach((button) => {
    button.addEventListener("click", handlePaymayaPayment);
  });
  async function handlePaymayaPayment(event) {
    const button = event.currentTarget;
    const paymentItemId = button.dataset.paymentItemId;
    const orderId = button.dataset.orderId;
    if (!paymentItemId) {
      // Replaced alert() with a custom modal
      showCustomAlert("Payment item ID is missing. Cannot proceed with payment.");
      console.error("Missing paymentItemId for shirt order ID:", orderId);
      return;
    }
    button.disabled = true;
    const originalText = button.textContent;
    button.textContent = "Processing...";
    const formData = new FormData();
    formData.append("payment_item_id", paymentItemId);
    try {
      const response = await fetch(PAYMAYA_CREATE_PAYMENT_URL, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail ||
            `Failed to initiate PayMaya payment for order ${orderId}.`
        );
      }
      const paymentData = await response.json();
      const checkoutUrl = paymentData.redirectUrl;

      if (checkoutUrl) {
        window.location.href = checkoutUrl;
      } else {
        // Replaced alert() with a custom modal
        showCustomAlert(
          "PayMaya checkout URL not found in response. Please try again or contact support."
        );
        console.error("PayMaya response:", paymentData);
      }
    } catch (error) {
      console.error("Error initiating PayMaya payment:", error);
      // Replaced alert() with a custom modal
      showCustomAlert(`Error initiating payment: ${error.message}. Please try again.`);
    } finally {
      button.disabled = false;
      button.textContent = originalText;
    }
  }

  async function handleDeleteOrder(orderId) {
    try {
      const response = await fetch(`${DELETE_ORDER_URL_BASE}${orderId}`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
      });
      if (response.ok) {
        // Find the order element by its data-order-id attribute
        const orderElementToRemove = document.querySelector(`[data-order-id="${orderId}"]`);
        if (orderElementToRemove) {
          // Find the closest parent that represents the entire order card/item and remove it
          const cardToRemove = orderElementToRemove.closest('.order-item') || orderElementToRemove.closest('.order-card');
          if (cardToRemove) {
            cardToRemove.remove();
          }
        }
        // Close the modal after deletion if it's open
        if (globalModal && globalModal.style.display === 'flex') {
          globalModal.style.display = 'none';
          globalModalBody.innerHTML = '';
        }
        
      } else {
        const errorData = await response.json();
        showCustomAlert(
          `Failed to remove order: ${errorData.detail || "Unknown error."}`
        );
        console.error("Failed to remove order:", errorData);
      }
    } catch (error) {
      console.error("Error removing order:", error);
      showCustomAlert(
        `An unexpected error occurred while removing the order: ${error.message}`
      );
    }
  }

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function attachViewDetailsButtonListeners() {
    document.querySelectorAll(".view-details-button").forEach((button) => {
      button.removeEventListener("click", handleViewDetailsClick);
      button.addEventListener("click", handleViewDetailsClick);
    });
  }

  async function handleViewDetailsClick() {
    const orderId = this.dataset.orderId;

    if (globalModalBody)
      globalModalBody.innerHTML =
        '<p class="loading-message">Loading order details...</p>';
    if (globalModal) globalModal.style.display = "flex";
    try {
      const response = await fetch(`${GET_ORDER_DETAILS_URL_BASE}${orderId}`);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to fetch order details.");
      }
      const order = await response.json();
      displayOrderDetail(order);
    } catch (error) {
      console.error("Error fetching order details:", error);
      if (globalModalBody) {
        globalModalBody.innerHTML = `<p class="error-message">Error loading details: ${error.message}</p>`;
      }
    }
  }

  attachViewDetailsButtonListeners();

  function displayOrderDetail(order) {
    if (!globalModalBody) {
      console.warn(
        "Warning: 'globalModalBody' not found. Cannot display order details."
      );
      return;
    }

    const formatDate = (dateString) => {
      if (!dateString) return "N/A";
      const options = {
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "numeric",
        minute: "numeric",
        hour12: true,
      };
      return new Date(dateString).toLocaleDateString("en-US", options);
    };

    let paymentStatusHtml = "";
    const isPaymentSuccessful =
      order.payment &&
      (order.payment.status === "paid" || order.payment.status === "success");
    const orderCanBeRemoved = !isPaymentSuccessful;
    const orderCanBeEdited = !isPaymentSuccessful;

    // Initialize campaignDetailsHtml to an empty string to prevent ReferenceError
    let campaignDetailsHtml = ""; 

    if (order.campaign) {
      let campaignPriceDisplay = "N/A";
      if (
        order.campaign.prices_by_size &&
        order.shirt_size &&
        order.campaign.prices_by_size[order.shirt_size]
      ) {
        campaignPriceDisplay = `&#8369;${order.campaign.prices_by_size[
          order.shirt_size
        ].toFixed(2)} (${order.shirt_size})`;
      } else if (order.campaign.price_per_shirt) {
        campaignPriceDisplay = `&#8369;${order.campaign.price_per_shirt.toFixed(
          2
        )}`;
      }

      campaignDetailsHtml = `
                <h3>Campaign Details</h3>
                <p><strong>Campaign:</strong> ${
                  order.campaign.title || "N/A"
                }</p> 
                <p><strong>Description:</strong> ${
                  order.campaign.description || "N/A"
                }</p> 
                <p><strong>Price per Shirt:</strong> ${campaignPriceDisplay}</p> 
                <p><strong>Pre-order Deadline:</strong> ${new Date(
                  order.campaign.pre_order_deadline
                ).toLocaleDateString("en-US", {
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                })}</p> 
            `;
    } else {
      campaignDetailsHtml = `<h3>Campaign Details</h3><p>Campaign data not available.</p>`;
    }

    if (order.payment) {
      const paymentStatusTagClass = `tag-${
        order.payment.status ? order.payment.status.toLowerCase() : "pending"
      }`;
      paymentStatusHtml = `
                <p><strong>Status:</strong> <span class="order-status-tag ${paymentStatusTagClass}">${
        order.payment.status || "Pending Payment"
      }</span></p> 
                <p><strong>Payment ID:</strong> ${
                  order.payment.paymaya_payment_id || "N/A"
                }</p> 
                <p><strong>Payment Amount:</strong> &#8369;${(
                  order.payment.amount || 0
                ).toFixed(2)}</p> 
                <p><strong>Payment Created:</strong> ${formatDate(
                  order.payment.created_at
                )}</p> 
                <p><strong>Last Updated:</strong> ${formatDate(
                  order.payment.updated_at
                )}</p> 
            `;
    } else {
      paymentStatusHtml = `<p><strong>Status:</strong> <span class="order-status-tag tag-pending">Pending Payment</span></p><p>No payment record found yet.</p>`;
    }

    let modalPaymentButtonHtml = "";   

    // Only show the PayMaya button if the payment is not yet successful and there's a payment_item_id
    if (!isPaymentSuccessful && order.payment_item_id) {
        modalPaymentButtonHtml = `
            <button class="paymaya-pay-button paymaya-pay-button-modal" data-payment-item-id="${order.payment_item_id}" data-order-id="${order.id}">
                Pay with PayMaya
            </button>
        `;
    }


    let removeOrderButtonHtml = "";
    if (orderCanBeRemoved) {
      removeOrderButtonHtml = `
                <button class="remove-order-button" data-order-id="${order.id}">
                    Remove Order
                </button>
            `;
    }

    let editOrderButtonHtml = "";
    if (orderCanBeEdited) {
      editOrderButtonHtml = `
                <button class="edit-order-button" data-order-id="${order.id}">
                    Edit Order
                </button>
            `;
    }

    globalModalBody.innerHTML = `
            <h2>Order Details <span id="modalOrderDetailId">(ID: ${
              order.id
            })</span></h2>
            <div class="detail-section">
                ${campaignDetailsHtml}
            </div>
            <div class="detail-section">
                <h3>Your Order Information</h3>
                <p><strong>Ordered By:</strong> ${
                  order.student_name || "N/A"
                }</p> 
                <p><strong>Student ID:</strong> ${
                  order.student_id || "N/A"
                }</p> 
                <p><strong>Year & Section:</strong> ${
                  order.student_year_section || "N/A"
                }</p> 
                <p><strong>Email:</strong> ${order.student_email || "N/A"}</p> 
                <p><strong>Phone:</strong> ${order.student_phone || "N/A"}</p> 
                <p><strong>Shirt Size:</strong> ${
                  order.shirt_size || "N/A"
                }</p> 
                <p><strong>Quantity:</strong> ${order.quantity || "N/A"}</p> 
                <p><strong>Total Amount:</strong> &#8369;${(
                  order.order_total_amount || 0
                ).toFixed(2)}</p> 
                <p><strong>Ordered On:</strong> ${formatDate(
                  order.ordered_at
                )}</p> 
            </div>

            <div class="detail-section">
                <h3>Payment Status</h3>
                ${paymentStatusHtml}
                ${modalPaymentButtonHtml}
            </div>

            <div class="order-detail-actions">
                ${editOrderButtonHtml}
                ${removeOrderButtonHtml}
            </div>
        `;

    const modalPayButton = globalModalBody.querySelector(
      ".paymaya-pay-button-modal"
    );
    if (modalPayButton && !isPaymentSuccessful) {
      modalPayButton.addEventListener("click", handlePaymayaPayment);
    }

    const removeOrderButton = globalModalBody.querySelector(
      ".remove-order-button"
    );
    if (removeOrderButton) {
      removeOrderButton.addEventListener("click", function () {
        handleDeleteOrder(order.id);
      });
    }

    const editOrderButton = globalModalBody.querySelector(".edit-order-button");
    if (editOrderButton) {
      editOrderButton.addEventListener("click", async function () {
        const updateFormHtml = `
                    <h2>Update Order <span id="updateOrderIdDisplay">(ID: ${order.id})</span></h2>
                    <form id="updateOrderForm" class="update-order-form">
                        <input type="hidden" id="updateOrderId" name="order_id" value="${order.id}">
                        <div class="form-group">
                            <label for="updateShirtSize">Shirt Size:</label>
                            <select id="updateShirtSize" name="shirt_size" required></select>
                        </div>
                        <div class="form-group">
                            <label for="updateQuantity">Quantity:</label>
                            <input type="number" id="updateQuantity" name="quantity" min="1" required>
                        </div>
                        <div class="form-group total-amount">
                            <span>Total:</span> <span id="updateDisplayTotalAmount">₱0.00</span>
                            <input type="hidden" id="updateOrderTotalAmount" name="order_total_amount" value="0.00">
                        </div>
                        <div class="form-message" id="updateOrderMessage"></div>
                        <button type="submit" class="submit-button">Update Order</button>
                    </form>
                `;
        globalModalBody.innerHTML = updateFormHtml;

        const updateOrderIdElem = document.getElementById("updateOrderId");
        const updateQuantityInputElem =
          document.getElementById("updateQuantity");
        const updateShirtSizeInputElem =
          document.getElementById("updateShirtSize");
        const updateDisplayTotalAmountElem = document.getElementById(
          "updateDisplayTotalAmount"
        );
        const updateOrderTotalAmountElem = document.getElementById(
          "updateOrderTotalAmount"
        );
        const updateOrderMessageElem =
          document.getElementById("updateOrderMessage");
        const updateOrderFormElem = document.getElementById("updateOrderForm");

        if (updateOrderIdElem) updateOrderIdElem.value = order.id;
        if (updateQuantityInputElem)
          updateQuantityInputElem.value = order.quantity;

        if (updateOrderMessageElem) {
          updateOrderMessageElem.textContent =
            "Loading campaign details for update...";
          updateOrderMessageElem.style.color = "blue";
        }

        try {
          const campaignResponse = await fetch(
            `/campaigns/${order.campaign.id}`
          );

          if (!campaignResponse.ok) {
            const errorData = await campaignResponse.json();
            throw new Error(
              errorData.detail ||
                `Failed to fetch campaign details for order update.`
            );
          }
          const campaign = await campaignResponse.json();
          currentUpdateCampaignPricesBySize = campaign.prices_by_size || {};

          if (updateShirtSizeInputElem) {
            updateShirtSizeInputElem.innerHTML = "";
            if (Object.keys(currentUpdateCampaignPricesBySize).length > 0) {
              for (const size in currentUpdateCampaignPricesBySize) {
                const option = document.createElement("option");
                option.value = size;
                option.textContent = `${size} (₱${currentUpdateCampaignPricesBySize[
                  size
                ].toFixed(2)})`;
                updateShirtSizeInputElem.appendChild(option);
              }

              updateShirtSizeInputElem.value = order.shirt_size;
              currentUpdateSelectedSize = order.shirt_size;
            } else {
              updateShirtSizeInputElem.innerHTML =
                '<option value="">No sizes available</option>';
              currentUpdateSelectedSize = "";
              if (updateOrderMessageElem) {
                updateOrderMessageElem.textContent =
                  "No sizes and prices defined for this campaign.";
                updateOrderMessageElem.style.color = "red";
              }
              return;
            }
          } else {
            console.warn(
              "Warning: 'updateShirtSizeInput' select element not found in dynamically loaded form."
            );
            if (updateOrderMessageElem) {
              updateOrderMessageElem.textContent =
                "Error: Update shirt size selection not available.";
              updateOrderMessageElem.style.color = "red";
            }
            return;
          }

          if (updateQuantityInputElem) {
            updateQuantityInputElem.addEventListener("input", () =>
              updateOrderDetailTotalAmount(
                updateQuantityInputElem,
                updateDisplayTotalAmountElem,
                updateOrderTotalAmountElem
              )
            );
          }

          if (updateShirtSizeInputElem) {
            updateShirtSizeInputElem.addEventListener("change", function () {
              currentUpdateSelectedSize = this.value;
              updateOrderDetailTotalAmount(
                updateQuantityInputElem,
                updateDisplayTotalAmountElem,
                updateOrderTotalAmountElem
              );
            });
          }

          updateOrderDetailTotalAmount(
            updateQuantityInputElem,
            updateDisplayTotalAmountElem,
            updateOrderTotalAmountElem
          );
          globalModal.style.display = "flex";
          if (updateOrderMessageElem) updateOrderMessageElem.textContent = "";

          if (updateOrderFormElem) {
            updateOrderFormElem.addEventListener(
              "submit",
              async function (event) {
                event.preventDefault();
                if (updateOrderMessageElem) {
                  updateOrderMessageElem.textContent = "Updating order...";
                  updateOrderMessageElem.style.color = "blue";
                }

                const orderId = updateOrderIdElem
                  ? updateOrderIdElem.value
                  : null;
                const updatedQuantity = updateQuantityInputElem
                  ? parseInt(updateQuantityInputElem.value)
                  : 0;
                const updatedShirtSize = updateShirtSizeInputElem
                  ? updateShirtSizeInputElem.value
                  : null;
                const updatedTotalAmount = updateOrderTotalAmountElem
                  ? parseFloat(updateOrderTotalAmountElem.value)
                  : 0;

                if (
                  !updatedShirtSize ||
                  isNaN(updatedQuantity) ||
                  updatedQuantity < 1 ||
                  isNaN(updatedTotalAmount) ||
                  updatedTotalAmount <= 0
                ) {
                  if (updateOrderMessageElem) {
                    updateOrderMessageElem.textContent =
                      "Please select a size, enter a valid quantity, and ensure total amount is valid.";
                    updateOrderMessageElem.style.color = "red";
                  }
                  return;
                }

                const updateData = {
                  quantity: updatedQuantity,
                  shirt_size: updatedShirtSize,
                  order_total_amount: updatedTotalAmount,
                };
                try {
                  const response = await fetch(
                    `${UPDATE_ORDER_URL_BASE}${orderId}`,
                    {
                      method: "PUT",
                      headers: {
                        "Content-Type": "application/json",
                      },
                      body: JSON.stringify(updateData),
                    }
                  );
                  if (response.ok) {
                    const result = await response.json();
                    if (updateOrderMessageElem) {
                      updateOrderMessageElem.textContent =
                        "Order updated successfully!";
                      updateOrderMessageElem.style.color = "green";
                    }
                    console.log("Order update successful:", result);
                    setTimeout(() => {
                      if (globalModal) globalModal.style.display = "none";
                      globalModalBody.innerHTML = "";
                      location.reload();
                    }, 1500);
                  } else {
                    const errorData = await response.json();
                    if (updateOrderMessageElem) {
                      updateOrderMessageElem.textContent = `Error: ${
                        errorData.detail || "Failed to update order."
                      }`;
                      updateOrderMessageElem.style.color = "red";
                    }
                    console.error("Order update failed:", errorData);
                  }
                } catch (error) {
                  if (updateOrderMessageElem) {
                    updateOrderMessageElem.textContent =
                      "An unexpected error occurred.";
                    updateOrderMessageElem.style.color = "red";
                  }
                  console.error("Network or other error:", error);
                }
              }
            );
          } else {
            console.warn(
              "Warning: Dynamically created 'updateOrderForm' not found. Order update functionality might be missing."
            );
          }
        } catch (error) {
          console.error(
            "Error fetching campaign details for order update:",
            error
          );
          // Replaced alert() with a custom modal
          showCustomAlert(`Failed to prepare order update: ${error.message}`);
        }
      });
    }
  }

  function toggleCompletedOrders() {
    allOrderDisplayElements.forEach((orderElement) => {
      const paymentStatus = orderElement.dataset.paymentStatus;

      const completedStatuses = ["paid", "success", "collected"];

      if (
        paymentStatus &&
        completedStatuses.includes(paymentStatus.toLowerCase())
      ) {
        if (hidingCompletedOrders) {
          orderElement.classList.add("hidden-order");
        } else {
          orderElement.classList.remove("hidden-order");
        }
      }
    });
    if (toggleCompletedOrdersButton) {
      if (hidingCompletedOrders) {
        toggleCompletedOrdersButton.textContent = "Show Completed Orders";
      } else {
        toggleCompletedOrdersButton.textContent = "Hide Completed Orders";
      }
    }
  }

  if (toggleCompletedOrdersButton) {
    toggleCompletedOrdersButton.addEventListener("click", () => {
      hidingCompletedOrders = !hidingCompletedOrders;
      toggleCompletedOrders();
    });
    toggleCompletedOrders();
  } else {
    console.warn(
      "Warning: 'toggleCompletedOrdersButton' not found. Toggle functionality might be missing."
    );
  }

  const hash = window.location.hash;
  const campaignsSection = document.getElementById("campaigns-section");
  const myOrdersSection = document.getElementById("my-orders-section");
  if (campaignsSection) {
    campaignsSection.style.display = "block";
  } else {
    console.warn("Warning: 'campaigns-section' not found.");
  }

  if (myOrdersSection) {
    myOrdersSection.style.display = "block";
  } else {
    console.warn("Warning: 'my-orders-section' not found.");
  }

  if (hash === "#my-orders-section" && myOrdersSection) {
    myOrdersSection.scrollIntoView({ behavior: "smooth" });
  }

  // Custom Alert and Confirm Modals
  function showCustomAlert(message, callback) {
    const alertModal = document.createElement('div');
    alertModal.className = 'custom-modal';
    alertModal.innerHTML = `
      <div class="custom-modal-content">
        <p>${message}</p>
        <button class="custom-modal-ok-button">OK</button>
      </div>
    `;
    document.body.appendChild(alertModal);

    alertModal.querySelector('.custom-modal-ok-button').onclick = () => {
      document.body.removeChild(alertModal);
      if (callback) callback();
    };

    alertModal.style.display = 'flex';
  }

  function showCustomConfirm(message, onConfirm, onCancel) {
    const confirmModal = document.createElement('div');
    confirmModal.className = 'custom-modal';
    confirmModal.innerHTML = `
      <div class="custom-modal-content">
        <p>${message}</p>
        <button class="custom-modal-confirm-button">Confirm</button>
        <button class="custom-modal-cancel-button">Cancel</button>
      </div>
    `;
    document.body.appendChild(confirmModal);

    confirmModal.querySelector('.custom-modal-confirm-button').onclick = () => {
      document.body.removeChild(confirmModal);
      if (onConfirm) onConfirm();
    };

    confirmModal.querySelector('.custom-modal-cancel-button').onclick = () => {
      document.body.removeChild(confirmModal);
      if (onCancel) onCancel();
    };

    confirmModal.style.display = 'flex';
  }
});

