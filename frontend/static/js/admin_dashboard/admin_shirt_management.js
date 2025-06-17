document.addEventListener("DOMContentLoaded", function () {
    console.log("admin_shirt_management.js: DOMContentLoaded fired.");

    // Get references to the global modal elements from your parent template
    const globalModal = document.getElementById('global-modal');
    const modalContent = globalModal ? globalModal.querySelector('.modal-content') : null; // We might not need this explicitly but good for reference
    const modalBody = globalModal ? document.getElementById('modal-body') : null; // This is where dynamic content goes
    const closeModalBtn = globalModal ? globalModal.querySelector('.modal-close-btn') : null;

    // Add console logs for initial element checks
    if (!globalModal) {
        console.error("admin_shirt_management.js: global-modal element not found!");
    } else {
        console.log("admin_shirt_management.js: global-modal found.", globalModal);
    }
    if (!modalBody) {
        console.error("admin_shirt_management.js: modal-body element not found!");
    } else {
        console.log("admin_shirt_management.js: modal-body found.", modalBody);
    }
    if (!closeModalBtn) {
        console.warn("admin_shirt_management.js: Close button (.modal-close-btn) not found for global modal.");
    }


    // Function to open the global modal with specific title and content
    function openGlobalModal(title, contentHtml) {
        console.log("openGlobalModal: Attempting to open modal with title:", title);

        if (!modalBody) {
            console.error("openGlobalModal: Necessary modal element (#modal-body) not found. Cannot set content.");
            return; // Exit if essential elements are missing
        }

        // Clear previous content of modal-body
        modalBody.innerHTML = '';

        // Inject the title and then the content HTML directly into the modalBody
        // This structure assumes your CSS has styling for h5 within modal-body if needed.
        modalBody.innerHTML = `
            <h5 class="modal-title">${title}</h5>
            <div class="modal-content-body">${contentHtml}</div>
        `;
        console.log("openGlobalModal: Modal title and content HTML set in modalBody.");

        if (globalModal) {
            globalModal.classList.add('is-visible'); // Use 'is-visible' as per your CSS
            console.log("openGlobalModal: 'is-visible' class added to globalModal.");
        } else {
            console.error("openGlobalModal: globalModal not found, cannot add 'is-visible' class.");
        }
    }

    // Function to close the global modal
    function closeGlobalModal() {
        console.log("closeGlobalModal: Attempting to close modal.");
        if (globalModal) {
            globalModal.classList.remove('is-visible'); // Use 'is-visible' as per your CSS
            console.log("closeGlobalModal: 'is-visible' class removed from globalModal.");
        } else {
            console.error("closeGlobalModal: globalModal not found, cannot remove 'is-visible' class.");
        }

        if (modalBody) {
            modalBody.innerHTML = ''; // Clear modal content on close
            console.log("closeGlobalModal: modalBody content cleared.");
        }
    }

    // Add event listener for the global modal's close button
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeGlobalModal);
        console.log("admin_shirt_management.js: Close button event listener attached.");
    }

    // Close modal if user clicks directly on the overlay (outside modal content)
    if (globalModal) {
        globalModal.addEventListener('click', function(event) {
            if (event.target === globalModal) {
                closeGlobalModal();
            }
        });
        console.log("admin_shirt_management.js: Global modal overlay click listener attached.");
    }

    // --- Data fetching and utility functions (these remain largely the same) ---
    const adminDataElement = document.getElementById("adminData");
    const adminId = adminDataElement
        ? adminDataElement.dataset.adminId
            ? parseInt(adminDataElement.dataset.adminId)
            : null
        : null;
    const organizationId = adminDataElement
        ? adminDataElement.dataset.organizationId
            ? parseInt(adminDataElement.dataset.organizationId)
            : null
        : null;

    function formatDateForInput(dateString, includeTime = true) {
        const date = new Date(dateString);
        const year = date.getFullYear();
        const month = (date.getMonth() + 1).toString().padStart(2, "0");
        const day = date.getDate().toString().padStart(2, "0");
        if (includeTime) {
            const hours = date.getHours().toString().padStart(2, "0");
            const minutes = date.getMinutes().toString().padStart(2, "0");
            return `${year}-${month}-${day}T${hours}:${minutes}`;
        } else {
            return `${year}-${month}-${day}`;
        }
    }

    function showAlert(message, type = "success") {
        const alertDiv = document.createElement("div");
        alertDiv.className = `custom-alert custom-alert-${type} custom-alert-dismissible`;
        alertDiv.innerHTML = `
                ${message}
                <button type="button" class="custom-close-btn" aria-label="Close">&times;</button>
            `;
        document.querySelector(".container-fluid").prepend(alertDiv);
        alertDiv
            .querySelector(".custom-close-btn")
            .addEventListener("click", function () {
                console.log("Alert close button clicked.");
                alertDiv.remove();
            });
        setTimeout(() => alertDiv.remove(), 5000);
    }

    function createSizePriceRow(size = "", price = "") {
        const row = document.createElement("div");
        row.classList.add(
            "row",
            "g-2",
            "mb-2",
            "align-items-center",
            "size-price-row"
        );
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

    // Event listener for adding/removing size/price rows within the modal forms
    // This listener is delegated to `modalBody` because the forms are dynamically added.
    if (modalBody) { // Ensure modalBody exists before attaching listener
        modalBody.addEventListener('click', function(event) {
            if (event.target.id === 'addCreateCampaignSizePrice') {
                const container = document.getElementById("createCampaignSizePricesContainer");
                if (container) {
                    container.appendChild(createSizePriceRow());
                    console.log("Added new size/price row for create campaign.");
                } else {
                    console.error("createCampaignSizePricesContainer not found when adding row.");
                }
            } else if (event.target.id === 'addEditCampaignSizePrice') {
                const container = document.getElementById("editCampaignSizePricesContainer");
                if (container) {
                    container.appendChild(createSizePriceRow());
                    console.log("Added new size/price row for edit campaign.");
                } else {
                    console.error("editCampaignSizePricesContainer not found when adding row.");
                }
            } else if (event.target.classList.contains("remove-size-price-row")) {
                event.target.closest(".size-price-row").remove();
                console.log("Removed size/price row.");
            }
        });
    } else {
        console.error("admin_shirt_management.js: modalBody not found, cannot attach size/price row event listener.");
    }


    function collectSizePriceData(containerId) {
        const pricesBySize = {};
        const container = document.getElementById(containerId);
        if (!container) return pricesBySize; // Ensure container exists
        container.querySelectorAll(".size-price-row").forEach((row) => {
            const sizeInput = row.querySelector(".campaign-size");
            const priceInput = row.querySelector(".campaign-price");
            if (sizeInput && priceInput && sizeInput.value && priceInput.value) {
                pricesBySize[sizeInput.value.trim()] = parseFloat(priceInput.value);
            }
        });
        return pricesBySize;
    }

    // --- Campaign Management Functions ---

    async function handleCreateCampaign(event) {
        event.preventDefault();
        const form = event.target;
        const formData = new FormData(form);

        formData.set(
            "is_active",
            form.querySelector("#campaignIsActive").checked ? "true" : "false"
        );

        const pricesBySize = collectSizePriceData(
            "createCampaignSizePricesContainer"
        );
        if (Object.keys(pricesBySize).length === 0) {
            showAlert("Please add at least one size and price.", "danger");
            return;
        }
        formData.append("prices_by_size", JSON.stringify(pricesBySize));
        formData.delete("price_per_shirt"); // Remove if not used

        try {
            const response = await fetch("/campaigns/", {
                method: "POST",
                body: formData,
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(
                    errorData.detail || `HTTP error! status: ${response.status}`
                );
            }
            const newCampaign = await response.json();
            showAlert("Campaign created successfully!");
            fetchCampaigns();
            closeGlobalModal(); // Use the global modal close function
            form.reset(); // Reset the form fields
            document.getElementById("createCampaignSizePricesContainer").innerHTML = ''; // Clear size/price rows
            document.getElementById("createCampaignSizePricesContainer").appendChild(createSizePriceRow()); // Add one default row
        } catch (error) {
            console.error("Error creating campaign:", error);
            showAlert(`Failed to create campaign: ${error.message}`, "danger");
        }
    }

    async function handleEditCampaign(event) {
        event.preventDefault();
        const form = event.target;
        const campaignId = form.querySelector("#editCampaignId").value;
        const formData = new FormData(form);

        formData.set(
            "is_active",
            form.querySelector("#editCampaignIsActive").checked ? "true" : "false"
        );

        const pricesBySize = collectSizePriceData(
            "editCampaignSizePricesContainer"
        );
        if (Object.keys(pricesBySize).length === 0) {
            showAlert("Please add at least one size and price.", "danger");
            return;
        }
        formData.append("prices_by_size", JSON.stringify(pricesBySize));
        formData.delete("price_per_shirt"); // Remove if not used

        try {
            const response = await fetch(`/campaigns/${campaignId}`, {
                method: "PUT",
                body: formData,
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(
                    errorData.detail || `HTTP error! status: ${response.status}`
                );
            }
            const updatedCampaign = await response.json();
            showAlert("Campaign updated successfully!");
            fetchCampaigns();
            closeGlobalModal(); // Use the global modal close function
        } catch (error) {
            console.error("Error updating campaign:", error);
            showAlert(`Failed to update campaign: ${error.message}`, "danger");
        }
    }

    async function handleDeleteCampaign(campaignId) {
        if (
            !confirm(
                "Are you sure you want to delete this campaign? This action cannot be undone."
            )
        ) {
            return;
        }
        try {
            const response = await fetch(`/campaigns/${campaignId}`, {
                method: "DELETE",
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(
                    errorData.detail || `HTTP error! status: ${response.status}`
                );
            }
            showAlert("Campaign deleted successfully!");
            fetchCampaigns();
        } catch (error) {
            console.error("Error deleting campaign:", error);
            showAlert(`Failed to delete campaign: ${error.message}`, "danger");
        }
    }

    function populateCampaignsTable(campaigns) {
        const tbody = document.querySelector("#campaignsTable tbody");
        tbody.innerHTML = "";
        campaigns.forEach((campaign) => {
            const descriptionSnippet = campaign.description
                ? campaign.description.substring(
                      0,
                      Math.min(campaign.description.length, 50)
                  ) + "..."
                : "No description";
            let priceDisplay = "";
            if (campaign.prices_by_size) {
                const sizes = Object.keys(campaign.prices_by_size);
                if (sizes.length > 0) {
                    const firstSize = sizes[0];
                    const firstPrice = campaign.prices_by_size[firstSize];
                    priceDisplay = `₱${firstPrice.toFixed(2)} (${firstSize})`;
                } else {
                    priceDisplay = "N/A";
                }
            } else if (campaign.price_per_shirt) {
                priceDisplay = `₱${campaign.price_per_shirt.toFixed(2)}`;
            } else {
                priceDisplay = "N/A";
            }

            const row = tbody.insertRow();
            row.innerHTML = `
                    <td>${campaign.title}</td>
                    <td>${descriptionSnippet}</td>
                    <td>${priceDisplay}</td>
                    <td>${new Date(
                        campaign.pre_order_deadline
                    ).toLocaleDateString()}</td>
                    <td>${campaign.available_stock}</td>
                    <td>${campaign.is_active ? "Yes" : "No"}</td>
                    <td>
                        ${
                            campaign.size_chart_image_path
                                ? `<img src="${campaign.size_chart_image_path}" alt="Size Chart" style="max-width: 80px; height: auto;">`
                                : "No Image"
                        }
                    </td>
                    <td>
                        <button class="custom-button custom-button-info edit-campaign-btn" data-campaign-id="${
                            campaign.id
                        }">Edit</button>
                        <button class="custom-button custom-button-danger delete-campaign-btn" data-campaign-id="${
                            campaign.id
                        }">Delete</button>
                    </td>
                `;
        });
    }

    async function fetchCampaigns() {
        try {
            const response = await fetch(`/campaigns/`);
            if (!response.ok)
                throw new Error(`HTTP error! status: ${response.status}`);
            const campaigns = await response.json();
            populateCampaignsTable(campaigns);
            populateCampaignFilter(campaigns);
        } catch (error) {
            console.error("Error fetching campaigns:", error);
            showAlert("Failed to load campaigns.", "danger");
        }
    }


    // --- Order Management Functions ---

    async function fetchOrders(campaignId = null) {
        let url;
        if (campaignId && campaignId !== "") {
            url = `/orders/campaign/${campaignId}`;
        } else {
            url = `/orders/`;
        }
        url += `?skip=0&limit=200`;

        try {
            const response = await fetch(url, {
                method: "GET",
                headers: {
                    "Content-Type": "application/json",
                },
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(
                    `HTTP error! Status: ${response.status}, Detail: ${
                        errorData.detail || response.statusText
                    }`
                );
            }
            const orders = await response.json();
            populateOrdersTable(orders);
        } catch (error) {
            console.error("Error fetching orders:", error);
            showAlert(`Failed to load orders: ${error.message}`, "danger");
            document.querySelector("#ordersTable tbody").innerHTML = `<tr><td colspan="6" class="text-center">Error loading orders: ${error.message}</td></tr>`;
        }
    }

    function populateOrdersTable(orders) {
        const tbody = document.querySelector("#ordersTable tbody");
        tbody.innerHTML = "";
        if (orders.length === 0) {
            tbody.innerHTML =
                '<tr><td colspan="6" class="text-center">No orders found for this selection.</td></tr>';
            return;
        }
        orders.forEach((order) => {
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
        const select = document.getElementById("orderCampaignFilter");
        select.innerHTML = '<option value="">All Campaigns</option>';
        campaigns.forEach((campaign) => {
            const option = document.createElement("option");
            option.value = campaign.id;
            option.textContent = campaign.title;
            select.appendChild(option);
        });
    }

    // --- Modal Content HTML (now defined as template literals) ---

    // HTML for the Create Campaign Form
    const createCampaignFormHtml = `
        <form id="createCampaignForm" enctype="multipart/form-data">
            <div class="mb-3">
                <label for="campaignTitle" class="form-label">Campaign Title</label>
                <input type="text" class="form-control" id="campaignTitle" name="title" required>
            </div>
            <div class="mb-3">
                <label for="campaignDescription" class="form-label">Description</label>
                <textarea class="form-control" id="campaignDescription" name="description" rows="3"></textarea>
            </div>
            <div class="mb-3">
                <label class="form-label">Prices per Size</label>
                <div id="createCampaignSizePricesContainer">
                    ${createSizePriceRow().outerHTML} </div>
                <button type="button" class="btn btn-secondary btn-sm mt-2" id="addCreateCampaignSizePrice">Add Another Size & Price</button>
            </div>
            <div class="mb-3">
                <label for="preOrderDeadline" class="form-label">Pre-Order Deadline</label>
                <input type="datetime-local" class="form-control" id="preOrderDeadline" name="pre_order_deadline" required>
            </div>
            <div class="mb-3">
                <label for="campaignStock" class="form-label">Available Stock</label>
                <input type="number" class="form-control" id="campaignStock" name="available_stock" required>
            </div>
            <div class="mb-3">
                <label for="campaignSizeChart" class="form-label">Size Chart Image</label>
                <input class="form-control" type="file" id="campaignSizeChart" name="size_chart_image" accept="image/*">
                <small class="form-text text-muted">Upload a new image for the size chart.</small>
            </div>
            <div class="form-check mb-3">
                <input class="form-check-input" type="checkbox" id="campaignIsActive" name="is_active">
                <label class="form-check-label" for="campaignIsActive">
                    Is Active
                </label>
            </div>
            <button type="submit" class="btn btn-primary">Create Campaign</button>
            <button type="button" class="btn btn-secondary" id="cancelCreateCampaign">Cancel</button>
        </form>
    `;

    // HTML for the Edit Campaign Form (will be populated dynamically)
    const editCampaignFormTemplate = (campaign) => {
        let sizePricesHtml = '';
        if (campaign.prices_by_size && Object.keys(campaign.prices_by_size).length > 0) {
            for (const size in campaign.prices_by_size) {
                sizePricesHtml += createSizePriceRow(size, campaign.prices_by_size[size]).outerHTML;
            }
        } else {
            sizePricesHtml += createSizePriceRow().outerHTML;
        }

        return `
            <form id="editCampaignForm" enctype="multipart/form-data">
                <input type="hidden" id="editCampaignId" name="campaign_id" value="${campaign.id}">
                <div class="mb-3">
                    <label for="editCampaignTitle" class="form-label">Campaign Title</label>
                    <input type="text" class="form-control" id="editCampaignTitle" name="title" value="${campaign.title}" required>
                </div>
                <div class="mb-3">
                    <label for="editCampaignDescription" class="form-label">Description</label>
                    <textarea class="form-control" id="editCampaignDescription" name="description" rows="3">${campaign.description || ""}</textarea>
                </div>
                <div class="mb-3">
                    <label class="form-label">Prices per Size</label>
                    <div id="editCampaignSizePricesContainer">
                        ${sizePricesHtml}
                    </div>
                    <button type="button" class="btn btn-secondary btn-sm mt-2" id="addEditCampaignSizePrice">Add Another Size & Price</button>
                </div>
                <div class="mb-3">
                    <label for="editCampaignPreOrderDeadline" class="form-label">Pre-Order Deadline</label>
                    <input type="datetime-local" class="form-control" id="editCampaignPreOrderDeadline" name="pre_order_deadline" value="${formatDateForInput(campaign.pre_order_deadline)}" required>
                </div>
                <div class="mb-3">
                    <label for="editCampaignStock" class="form-label">Available Stock</label>
                    <input type="number" class="form-control" id="editCampaignStock" name="available_stock" value="${campaign.available_stock}" required>
                </div>
                <div class="mb-3">
                    <label for="editCampaignSizeChart" class="form-label">Size Chart Image</label>
                    <input class="form-control" type="file" id="editCampaignSizeChart" name="size_chart_image" accept="image/*">
                    <small class="form-text text-muted">Upload a new image or leave blank to keep current. Select nothing and submit to remove.</small>
                    <div id="currentSizeChartImage" class="mt-2">
                        ${campaign.size_chart_image_path ? `<img src="${campaign.size_chart_image_path}" style="max-width: 150px; height: auto;"><p>Current Image</p>` : `<p>No current image.</p>`}
                    </div>
                </div>
                <div class="form-check mb-3">
                    <input class="form-check-input" type="checkbox" id="editCampaignIsActive" name="is_active" ${campaign.is_active ? 'checked' : ''}>
                    <label class="form-check-label" for="editCampaignIsActive">
                        Is Active
                    </label>
                </div>
                <button type="submit" class="btn btn-primary">Update Campaign</button>
                <button type="button" class="btn btn-secondary" id="cancelEditCampaign">Cancel</button>
            </form>
        `;
    };

    // --- Event Listeners for Opening Modals ---

    // Event listener for the "Add New Campaign" button
    const openCreateCampaignModalBtn = document.getElementById('openCreateCampaignModalBtn');
    if (openCreateCampaignModalBtn) {
        console.log("admin_shirt_management.js: openCreateCampaignModalBtn found, attaching listener.");
        openCreateCampaignModalBtn.addEventListener('click', function() {
            console.log("Add New Campaign button CLICKED!");
            openGlobalModal("Create New Shirt Campaign", createCampaignFormHtml);

            // Attach submit listener for the dynamically added form
            const form = document.getElementById("createCampaignForm");
            if (form) {
                form.addEventListener("submit", handleCreateCampaign);
                console.log("Listener attached to createCampaignForm.");
            } else {
                console.error("createCampaignForm not found after opening modal!");
            }
            // Attach cancel listener
            const cancelBtn = document.getElementById('cancelCreateCampaign');
            if (cancelBtn) {
                cancelBtn.addEventListener('click', closeGlobalModal);
                console.log("Listener attached to cancelCreateCampaign button.");
            } else {
                console.warn("cancelCreateCampaign button not found after opening modal.");
            }
        });
    } else {
        console.error("admin_shirt_management.js: openCreateCampaignModalBtn NOT found! Check HTML ID.");
    }


    // Event listener for "Edit" and "Delete" buttons (delegated to campaignsTable tbody)
    const campaignsTableBody = document.querySelector("#campaignsTable tbody"); // Get reference to avoid repeated queries
    if (campaignsTableBody) {
        console.log("admin_shirt_management.js: campaignsTable tbody found, attaching delegated listener.");
        campaignsTableBody.addEventListener("click", async function (event) {
            console.log("Campaigns table click detected.", event.target);
            if (event.target.classList.contains("edit-campaign-btn")) {
                console.log("Edit campaign button clicked.");
                const campaignId = event.target.dataset.campaignId;
                try {
                    const response = await fetch(`/campaigns/${campaignId}`);
                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(
                            errorData.detail || `HTTP error! status: ${response.status}`
                        );
                    }
                    const campaign = await response.json();

                    openGlobalModal("Edit Shirt Campaign", editCampaignFormTemplate(campaign));

                    const form = document.getElementById("editCampaignForm");
                    if (form) {
                        form.addEventListener("submit", handleEditCampaign);
                        console.log("Listener attached to editCampaignForm.");
                    } else {
                        console.error("editCampaignForm not found after opening modal!");
                    }
                    const cancelBtn = document.getElementById('cancelEditCampaign');
                    if (cancelBtn) {
                        cancelBtn.addEventListener('click', closeGlobalModal);
                        console.log("Listener attached to cancelEditCampaign button.");
                    } else {
                        console.warn("cancelEditCampaign button not found after opening modal.");
                    }

                } catch (error) {
                    console.error("Error fetching campaign for edit:", error);
                    showAlert(
                        `Failed to load campaign details for editing: ${error.message}`,
                        "danger"
                    );
                }
            } else if (event.target.classList.contains("delete-campaign-btn")) {
                console.log("Delete campaign button clicked.");
                const campaignId = event.target.dataset.campaignId;
                handleDeleteCampaign(campaignId);
            }
        });
    } else {
        console.error("admin_shirt_management.js: campaignsTable tbody NOT found! Check HTML structure.");
    }


    // Event listener for filtering orders
    const applyOrderFiltersBtn = document.getElementById("applyOrderFilters");
    if (applyOrderFiltersBtn) {
        applyOrderFiltersBtn.addEventListener("click", () => {
            console.log("Apply Order Filters button clicked.");
            const campaignId = document.getElementById("orderCampaignFilter").value;
            fetchOrders(campaignId);
        });
    } else {
        console.error("admin_shirt_management.js: applyOrderFilters button NOT found!");
    }


    // Initial data load when the DOM is ready
    console.log("admin_shirt_management.js: Calling fetchCampaigns and fetchOrders...");
    fetchCampaigns();
    fetchOrders("");
});