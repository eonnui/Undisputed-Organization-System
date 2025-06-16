document.addEventListener("DOMContentLoaded", function () {
  function injectCreateCampaignModal() {
    const modalHtml = `
            <div class="modal fade" id="createCampaignModal" tabindex="-1" aria-labelledby="createCampaignModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="createCampaignModalLabel">Create New Shirt Campaign</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
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
                                        <div class="row g-2 mb-2 align-items-center size-price-row">
                                            <div class="col-5">
                                                <input type="text" class="form-control form-control-sm campaign-size" placeholder="Size (e.g., S, M, XL)" required>
                                            </div>
                                            <div class="col-5">
                                                <input type="number" step="0.01" class="form-control form-control-sm campaign-price" placeholder="Price" required>
                                            </div>
                                            <div class="col-2">
                                                <button type="button" class="btn btn-danger btn-sm remove-size-price-row">X</button>
                                            </div>
                                        </div>
                                    </div>
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
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        `;
    document.body.insertAdjacentHTML("beforeend", modalHtml);
  }

  function injectEditCampaignModal() {
    const modalHtml = `
            <div class="modal fade" id="editCampaignModal" tabindex="-1" aria-labelledby="editCampaignModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="editCampaignModalLabel">Edit Shirt Campaign</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <form id="editCampaignForm" enctype="multipart/form-data">
                                <input type="hidden" id="editCampaignId" name="campaign_id">
                                <div class="mb-3">
                                    <label for="editCampaignTitle" class="form-label">Campaign Title</label>
                                    <input type="text" class="form-control" id="editCampaignTitle" name="title" required>
                                </div>
                                <div class="mb-3">
                                    <label for="editCampaignDescription" class="form-label">Description</label>
                                    <textarea class="form-control" id="editCampaignDescription" name="description" rows="3"></textarea>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Prices per Size</label>
                                    <div id="editCampaignSizePricesContainer">
                                    </div>
                                    <button type="button" class="btn btn-secondary btn-sm mt-2" id="addEditCampaignSizePrice">Add Another Size & Price</button>
                                </div>
                                <div class="mb-3">
                                    <label for="editCampaignPreOrderDeadline" class="form-label">Pre-Order Deadline</label>
                                    <input type="datetime-local" class="form-control" id="editCampaignPreOrderDeadline" name="pre_order_deadline" required>
                                </div>
                                <div class="mb-3">
                                    <label for="editCampaignStock" class="form-label">Available Stock</label>
                                    <input type="number" class="form-control" id="editCampaignStock" name="available_stock" required>
                                </div>
                                <div class="mb-3">
                                    <label for="editCampaignSizeChart" class="form-label">Size Chart Image</label>
                                    <input class="form-control" type="file" id="editCampaignSizeChart" name="size_chart_image" accept="image/*">
                                    <small class="form-text text-muted">Upload a new image or leave blank to keep current. Select nothing and submit to remove.</small>
                                    <div id="currentSizeChartImage" class="mt-2"></div>
                                </div>
                                <div class="form-check mb-3">
                                    <input class="form-check-input" type="checkbox" id="editCampaignIsActive" name="is_active">
                                    <label class="form-check-label" for="editCampaignIsActive">
                                        Is Active
                                    </label>
                                </div>
                                <button type="submit" class="btn btn-primary">Update Campaign</button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        `;
    document.body.insertAdjacentHTML("beforeend", modalHtml);
  }

  injectCreateCampaignModal();
  injectEditCampaignModal();

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

  const addCreateCampaignSizePriceButton = document.getElementById(
    "addCreateCampaignSizePrice"
  );
  if (addCreateCampaignSizePriceButton) {
    addCreateCampaignSizePriceButton.addEventListener("click", function () {
      document
        .getElementById("createCampaignSizePricesContainer")
        .appendChild(createSizePriceRow());
    });
  }

  const addEditCampaignSizePriceButton = document.getElementById(
    "addEditCampaignSizePrice"
  );
  if (addEditCampaignSizePriceButton) {
    addEditCampaignSizePriceButton.addEventListener("click", function () {
      document
        .getElementById("editCampaignSizePricesContainer")
        .appendChild(createSizePriceRow());
    });
  }

  document
    .querySelectorAll(
      "#createCampaignSizePricesContainer, #editCampaignSizePricesContainer"
    )
    .forEach((container) => {
      container.addEventListener("click", function (event) {
        if (event.target.classList.contains("remove-size-price-row")) {
          event.target.closest(".size-price-row").remove();
        }
      });
    });

  function collectSizePriceData(containerId) {
    const pricesBySize = {};
    const container = document.getElementById(containerId);
    container.querySelectorAll(".size-price-row").forEach((row) => {
      const sizeInput = row.querySelector(".campaign-size");
      const priceInput = row.querySelector(".campaign-price");
      if (sizeInput && priceInput && sizeInput.value && priceInput.value) {
        pricesBySize[sizeInput.value.trim()] = parseFloat(priceInput.value);
      }
    });
    return pricesBySize;
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
                    }" data-bs-toggle="modal" data-bs-target="#editCampaignModal">Edit</button>
                    <button class="custom-button custom-button-danger delete-campaign-btn" data-campaign-id="${
                      campaign.id
                    }">Delete</button>
                </td>
            `;
    });
  }

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

    formData.delete("price_per_shirt");

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

      const createModalElement = document.getElementById("createCampaignModal");
      const createModal =
        bootstrap.Modal.getInstance(createModalElement) ||
        new bootstrap.Modal(createModalElement);
      createModal.hide();

      form.reset();
      document.getElementById("createCampaignSizePricesContainer").innerHTML =
        "";
      document
        .getElementById("createCampaignSizePricesContainer")
        .appendChild(createSizePriceRow());
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

    formData.delete("price_per_shirt");

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

      const editModalElement = document.getElementById("editCampaignModal");
      const editModal =
        bootstrap.Modal.getInstance(editModalElement) ||
        new bootstrap.Modal(editModalElement);
      editModal.hide();
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

  document
    .querySelector("#campaignsTable tbody")
    .addEventListener("click", async function (event) {
      if (event.target.classList.contains("edit-campaign-btn")) {
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
          document.getElementById("editCampaignId").value = campaign.id;
          document.getElementById("editCampaignTitle").value = campaign.title;
          document.getElementById("editCampaignDescription").value =
            campaign.description || "";
          document.getElementById("editCampaignPreOrderDeadline").value =
            formatDateForInput(campaign.pre_order_deadline);
          document.getElementById("editCampaignStock").value =
            campaign.available_stock;
          document.getElementById("editCampaignIsActive").checked =
            campaign.is_active;
          const currentImageDiv = document.getElementById(
            "currentSizeChartImage"
          );
          if (campaign.size_chart_image_path) {
            currentImageDiv.innerHTML = `<img src="${campaign.size_chart_image_path}" style="max-width: 150px; height: auto;"><p>Current Image</p>`;
          } else {
            currentImageDiv.innerHTML = `<p>No current image.</p>`;
          }
          document.getElementById("editCampaignSizeChart").value = "";

          const editSizePricesContainer = document.getElementById(
            "editCampaignSizePricesContainer"
          );
          editSizePricesContainer.innerHTML = "";
          if (
            campaign.prices_by_size &&
            Object.keys(campaign.prices_by_size).length > 0
          ) {
            for (const size in campaign.prices_by_size) {
              editSizePricesContainer.appendChild(
                createSizePriceRow(size, campaign.prices_by_size[size])
              );
            }
          } else {
            editSizePricesContainer.appendChild(createSizePriceRow());
          }
        } catch (error) {
          console.error("Error fetching campaign for edit:", error);
          showAlert(
            `Failed to load campaign details for editing: ${error.message}`,
            "danger"
          );
        }
      } else if (event.target.classList.contains("delete-campaign-btn")) {
        const campaignId = event.target.dataset.campaignId;
        handleDeleteCampaign(campaignId);
      }
    });

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
      document.querySelector(
        "#ordersTable tbody"
      ).innerHTML = `<tr><td colspan="6" class="text-center">Error loading orders: ${error.message}</td></tr>`;
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

  const createCampaignButton = document.querySelector(
    'button[data-bs-target="#createCampaignModal"]'
  );
  if (createCampaignButton) {
    createCampaignButton.addEventListener("click", function () {
      console.log("Add New Campaign button clicked.");
      const createCampaignSizePricesContainer = document.getElementById(
        "createCampaignSizePricesContainer"
      );
      if (createCampaignSizePricesContainer.children.length === 0) {
        createCampaignSizePricesContainer.appendChild(createSizePriceRow());
      }
    });
  }

  document
    .getElementById("createCampaignForm")
    .addEventListener("submit", handleCreateCampaign);
  document
    .getElementById("editCampaignForm")
    .addEventListener("submit", handleEditCampaign);

  document.getElementById("applyOrderFilters").addEventListener("click", () => {
    const campaignId = document.getElementById("orderCampaignFilter").value;
    fetchOrders(campaignId);
  });

  fetchCampaigns();
  fetchOrders("");
});
