document.addEventListener("DOMContentLoaded", () => {
  const globalModal = document.getElementById("global-modal");
  const modalBody = globalModal
    ? globalModal.querySelector("#modal-body")
    : null;
  const modalTitleElement = globalModal
    ? globalModal.querySelector(".modal-content h3")
    : null;
  const modalCloseBtn = globalModal
    ? globalModal.querySelector(".modal-close-btn")
    : null;

  /**
   * Opens the global modal with a specified title.
   * @param {string} title - The title to display in the modal header.
   */
  function openGlobalModal(title) {
    if (!globalModal || !modalBody) {
      console.error("Global modal elements not found.");
      return;
    }
    if (modalTitleElement) {
      modalTitleElement.innerText = title;
    } else {
      console.warn(
        "No h3 element found in modal-content for title. Appending title."
      );
      const newTitle = document.createElement("h3");
      newTitle.innerText = title;
      modalBody.innerHTML = "";
      modalBody.prepend(newTitle);
    }

    globalModal.style.display = "flex";
    globalModal.classList.add("is-visible");
    document.body.style.overflow = "hidden";
  }

  /**
   * Closes the global modal and clears its content.
   */
  function closeGlobalModal() {
    if (!globalModal || !modalBody) {
      console.error("Global modal elements not found for closing.");
      return;
    }
    globalModal.style.display = "none";
    globalModal.classList.remove("is-visible");
    document.body.style.overflow = "";
    modalBody.innerHTML = "";
    if (modalTitleElement) {
      modalTitleElement.innerText = "";
    }
  }

  if (modalCloseBtn) {
    modalCloseBtn.addEventListener("click", closeGlobalModal);
  }

  if (globalModal) {
    globalModal.addEventListener("click", function (event) {
      if (event.target === globalModal) {
        closeGlobalModal();
      }
    });
  }

  document.addEventListener("keydown", function (event) {
    if (
      event.key === "Escape" &&
      globalModal &&
      globalModal.classList.contains("is-visible")
    ) {
      closeGlobalModal();
    }
  });

  const createPostInput = document.querySelector(".create-post-input");
  const createPostForm = document.querySelector(".create-post-form-fields");
  const backToBulletinLink = document.querySelector(".back-to-bulletin");

  if (createPostInput) {
    createPostInput.addEventListener("click", function () {
      this.style.display = "none";
      createPostForm.style.display = "block";
      backToBulletinLink.style.display = "block";
    });
  }

  if (backToBulletinLink) {
    backToBulletinLink.addEventListener("click", function (event) {
      event.preventDefault();
      createPostInput.style.display = "block";
      createPostForm.style.display = "none";
      this.style.display = "none";
    });
  }

  /**
   * Toggles the edit mode for a wiki post card.
   * @param {string} postId - The ID of the post to toggle.
   * @param {boolean} showEdit - True to show edit mode, false to show display mode.
   */
  function toggleEditMode(postId, showEdit) {
    const postCard = document.getElementById(`wiki-post-${postId}`);
    if (postCard) {
      const displayMode = postCard.querySelector(".wiki-post-display-mode");
      const editMode = postCard.querySelector(".wiki-post-edit-mode");

      if (showEdit) {
        if (displayMode) displayMode.style.display = "none";
        if (editMode) editMode.style.display = "block";
        postCard.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      } else {
        if (displayMode) displayMode.style.display = "block";
        if (editMode) editMode.style.display = "none";
      }
    }
  }

  const urlParams = new URLSearchParams(window.location.search);
  const editPostId = urlParams.get("edit_wiki_post_id");

  if (editPostId) {
    toggleEditMode(editPostId, true);
  }

  document.querySelectorAll(".wiki-edit-button").forEach((button) => {
    button.addEventListener("click", (event) => {
      const postId = event.target.dataset.postId;
      toggleEditMode(postId, true);
    });
  });

  document.querySelectorAll(".cancel-edit-button").forEach((button) => {
    button.addEventListener("click", (event) => {
      const postId = event.target.dataset.postId;
      toggleEditMode(postId, false);
    });
  });

  document.querySelectorAll(".edit-wiki-post-form").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const postId =
        form.dataset.postId ||
        form.querySelector('input[name="post_id"]').value;
      const formData = new FormData(form);

      try {
        const response = await fetch(form.action, {
          method: "POST",
          body: formData,
        });

        if (response.ok) {
          const messageBox = document.createElement("div");
          messageBox.className = "message-box success";
          messageBox.textContent = "Post updated successfully!";
          document.body.appendChild(messageBox);
          setTimeout(() => messageBox.remove(), 3000);
          toggleEditMode(postId, false);
          window.location.reload();
        } else {
          const errorText = await response.text();
          const messageBox = document.createElement("div");
          messageBox.className = "message-box error";
          messageBox.textContent = `Failed to update post: ${errorText}`;
          document.body.appendChild(messageBox);
          setTimeout(() => messageBox.remove(), 3000);
        }
      } catch (error) {
        console.error("Error submitting edit form:", error);
        const messageBox = document.createElement("div");
        messageBox.className = "message-box error";
        messageBox.textContent = "An error occurred during submission.";
        document.body.appendChild(messageBox);
        setTimeout(() => messageBox.remove(), 3000);
      }
    });
  });

  const heartButtons = document.querySelectorAll(".heart-button");

  heartButtons.forEach((button) => {
    const postId = button.dataset.postId;
    const heartCountSpan = button.querySelector(".heart-count");

    if (heartCountSpan) {
      heartCountSpan.style.cursor = "pointer";
      heartCountSpan.addEventListener("click", async function (event) {
        event.stopPropagation();

        if (!globalModal || !modalBody) {
          console.error("Global modal elements not available for likers view.");
          return;
        }

        openGlobalModal("Users Who Liked This Post");
        modalBody.innerHTML =
          '<p class="loading-message">Loading likers...</p>';

        try {
          const response = await fetch(`/bulletin/heart/${postId}/users`);
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          const data = await response.json();

          modalBody.innerHTML = "";

          if (data.likers && data.likers.length > 0) {
            const likersList = document.createElement("ul");
            likersList.classList.add("likers-list", "list-none", "p-0", "m-0");
            data.likers.forEach((liker) => {
              const listItem = document.createElement("li");
              listItem.classList.add(
                "liker-item",
                "py-2",
                "border-b",
                "border-gray-200",
                "last:border-b-0",
                "flex",
                "items-center"
              );

              const profilePicDiv = document.createElement("div");
              profilePicDiv.classList.add(
                "liker-profile-pic-container",
                "mr-3"
              );

              const profilePic = document.createElement("img");

              profilePic.src = liker.profile_picture.startsWith("/")
                ? liker.profile_picture
                : "/" + liker.profile_picture;
              profilePic.alt = `${liker.first_name} ${liker.last_name}'s Profile Picture`;
              profilePic.classList.add(
                "w-10",
                "h-10",
                "rounded-full",
                "object-cover",
                "liker-profile-pic"
              );

              profilePic.onerror = function () {
                this.onerror = null;
                this.src = "/static/images/default_profile.png";
              };

              profilePicDiv.appendChild(profilePic);
              listItem.appendChild(profilePicDiv);

              const textContentDiv = document.createElement("div");
              textContentDiv.innerHTML = `
                                <span class="font-semibold">${
                                  liker.first_name
                                } ${liker.last_name}</span>
                                ${
                                  liker.email
                                    ? `<span class="text-gray-600 text-sm ml-1">(${liker.email})</span>`
                                    : ""
                                }
                            `;
              listItem.appendChild(textContentDiv);

              likersList.appendChild(listItem);
            });
            modalBody.appendChild(likersList);
          } else {
            modalBody.innerHTML =
              "<p class='text-center text-gray-500'>No users have liked this post yet.</p>";
          }
        } catch (error) {
          console.error("Error fetching likers:", error);
          modalBody.innerHTML =
            '<p class="error-message text-center text-red-600">Failed to load likers. Please try again later.</p>';
        }
      });
    }

    button.addEventListener("click", function () {
      const isHeartedInitially = this.classList.contains("hearted");
      const action = isHeartedInitially ? "unheart" : "heart";

      let currentCount = parseInt(heartCountSpan.textContent);
      if (action === "heart") {
        this.classList.add("hearted");
        heartCountSpan.textContent = currentCount + 1;
      } else {
        this.classList.remove("hearted");
        heartCountSpan.textContent = Math.max(0, currentCount - 1);
      }

      fetch(`/bulletin/heart/${postId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: `action=${action}`,
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          return response.json();
        })
        .then((data) => {
          heartCountSpan.textContent = data.heart_count;

          if (data.is_hearted_by_user) {
            this.classList.add("hearted");
          } else {
            this.classList.remove("hearted");
          }
        })
        .catch((error) => {
          console.error("Error hearting post:", error);

          if (action === "heart") {
            this.classList.remove("hearted");
            heartCountSpan.textContent = currentCount;
          } else {
            this.classList.add("hearted");
            heartCountSpan.textContent = currentCount;
          }
        });
    });
  });

  const threeDotsButtons = document.querySelectorAll(".three-dots-button");

  threeDotsButtons.forEach((button) => {
    button.addEventListener("click", function () {
      document
        .querySelectorAll(".wiki-post-actions:not(.hidden)")
        .forEach((openMenu) => {
          if (openMenu !== this.nextElementSibling) {
            openMenu.classList.add("hidden");
          }
        });

      const actionsWrapper = this.closest(".wiki-post-actions-wrapper");
      const actionsMenu = actionsWrapper
        ? actionsWrapper.querySelector(".wiki-post-actions")
        : null;

      if (actionsMenu) {
        actionsMenu.classList.toggle("hidden");
      }
    });
  });

  document.addEventListener("click", function (event) {
    if (
      !event.target.closest(".three-dots-button") &&
      !event.target.closest(".wiki-post-actions")
    ) {
      document
        .querySelectorAll(".wiki-post-actions:not(.hidden)")
        .forEach((openMenu) => {
          openMenu.classList.add("hidden");
        });
    }
  });

  const createWikiInput = document.querySelector(".create-wiki-input");
  const createWikiPostForm = document.querySelector(".create-wiki-post-form");
  const cancelCreateWikiButton = document.querySelector(
    ".cancel-create-wiki-button"
  );

  if (createWikiInput && createWikiPostForm && cancelCreateWikiButton) {
    createWikiInput.addEventListener("click", function () {
      createWikiInput.style.display = "none";
      createWikiPostForm.style.display = "flex";
      cancelCreateWikiButton.style.display = "inline-block";
    });

    cancelCreateWikiButton.addEventListener("click", function () {
      createWikiInput.style.display = "block";
      createWikiPostForm.style.display = "none";
      cancelCreateWikiButton.style.display = "none";
      createWikiPostForm.reset();
    });
  }

  const orgChartButton = document.getElementById("viewOrgChartButton");

  /**
   * Toggles the edit mode for an organizational chart node.
   * @param {string} adminId - The ID of the admin node to toggle.
   * @param {boolean} showEdit - True to show edit mode, false to show display mode.
   */
  function toggleOrgChartEditMode(adminId, showEdit) {
    const adminNodeWrapper = modalBody.querySelector(
      `.org-node-wrapper[data-admin-id="${adminId}"]`
    );
    if (adminNodeWrapper) {
      const displayMode = adminNodeWrapper.querySelector(
        ".org-node-display-mode"
      );
      const editMode = adminNodeWrapper.querySelector(".org-node-edit-mode");

      if (showEdit) {
        if (displayMode) displayMode.style.display = "none";
        if (editMode) editMode.style.display = "flex";
      } else {
        if (displayMode) displayMode.style.display = "flex";
        if (editMode) editMode.style.display = "none";
      }
    }
  }

  /**
   * Saves an organizational chart node via API.
   * Handles both new node creation and existing node updates.
   * @param {string} adminId - The ID of the admin node (can be a placeholder for new nodes).
   * @param {HTMLFormElement} formElement - The form element containing the data to save.
   */
  async function saveOrgChartNode(adminId, formElement) {
    const isNewOrgChartNode = adminId.startsWith("new_placeholder_");
    const formData = new FormData(formElement);
    const profilePictureFile = formData.get("chart_picture");

    const textData = {};
    for (const [key, value] of formData.entries()) {
      if (key !== "chart_picture") {
        textData[key] = value;
      }
    }

    let actualNodeIdToSend = adminId;

    try {
      let apiUrl = "";
      let httpMethod = "PUT";

      if (isNewOrgChartNode) {
        apiUrl = "/api/admin/org_chart_node";
        httpMethod = "POST";
        delete textData.id;
      } else {
        apiUrl = `/api/admin/org_chart_node/${adminId}`;
      }

      const textResponse = await fetch(apiUrl, {
        method: httpMethod,
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(textData),
      });

      if (!textResponse.ok) {
        const errorText = await textResponse.text();
        throw new Error(`Text data save failed: ${errorText}`);
      }

      const responseData = await textResponse.json();

      if (isNewOrgChartNode) {
        actualNodeIdToSend = responseData.id;
      } else {
        actualNodeIdToSend = adminId;
      }

      if (profilePictureFile && profilePictureFile.size > 0) {
        const pictureUrl = `/api/admin/org_chart_node/${actualNodeIdToSend}/profile_picture`;

        const pictureFormData = new FormData();
        pictureFormData.append("chart_picture", profilePictureFile);

        const pictureResponse = await fetch(pictureUrl, {
          method: "PUT",
          body: pictureFormData,
        });

        if (!pictureResponse.ok) {
          const errorText = await pictureResponse.text();
          console.error("Profile picture upload failed:", errorText);
        }
      }

      await fetchAndRenderOrgChart();

      toggleOrgChartEditMode(actualNodeIdToSend, false);
    } catch (error) {
      console.error("Error saving org chart node:", error);
    }
  }

  /**
   * Creates a DOM element for an individual admin node in the organizational chart.
   * Includes both display and editable modes.
   * @param {object} admin - The admin data object.
   * @returns {HTMLElement} The created div element for the admin node.
   */
  const createAdminNodeDiv = (admin) => {
    const adminId = admin.id;

    const adminNodeWrapper = document.createElement("div");
    adminNodeWrapper.className = "org-node-wrapper";
    adminNodeWrapper.setAttribute("data-admin-id", adminId);

    const displayMode = document.createElement("div");
    displayMode.className = "org-node org-node-display-mode";

    displayMode.addEventListener("click", () =>
      toggleOrgChartEditMode(adminId, true)
    );

    const profileDiv = document.createElement("div");
    profileDiv.className = "profile-circle";
    const img = document.createElement("img");
    img.alt = `${admin.first_name}'s Profile`;
    img.src = admin.chart_picture_url || "/static/images/your_image_name.jpg";

    img.onerror = function () {
      this.onerror = null;
      this.src = "/static/images/your_image_name.jpg";
    };
    profileDiv.appendChild(img);
    displayMode.appendChild(profileDiv);

    const textContainer = document.createElement("div");
    textContainer.className = "text-container";

    const positionSpan = document.createElement("span");
    positionSpan.className = "position-text";
    positionSpan.textContent = (admin.position || "POSITION").toUpperCase();
    textContainer.appendChild(positionSpan);

    const nameSpan = document.createElement("span");
    nameSpan.className = "name-text";
    nameSpan.textContent = ` - ${admin.first_name || ""} ${
      admin.last_name || ""
    }`;
    textContainer.appendChild(nameSpan);

    displayMode.appendChild(textContainer);
    adminNodeWrapper.appendChild(displayMode);

    const editForm = document.createElement("form");
    editForm.className = "org-node org-node-edit-mode";
    editForm.style.display = "none";

    const hiddenIdInput = document.createElement("input");
    hiddenIdInput.type = "hidden";
    hiddenIdInput.name = "id";
    hiddenIdInput.value = admin.id.startsWith("chart_node_")
      ? admin.id.replace("chart_node_", "")
      : admin.id;
    editForm.appendChild(hiddenIdInput);

    const hiddenPositionInput = document.createElement("input");
    hiddenPositionInput.type = "hidden";
    hiddenPositionInput.name = "position";
    hiddenPositionInput.value = admin.position || "";
    editForm.appendChild(hiddenPositionInput);

    const editProfileDiv = document.createElement("div");
    editProfileDiv.className = "profile-circle-edit";
    const editImg = document.createElement("img");
    editImg.alt = "Profile Preview";
    editImg.src =
      admin.chart_picture_url || "/static/images/your_image_name.jpg";
    editProfileDiv.appendChild(editImg);
    editForm.appendChild(editProfileDiv);

    const fileInputId = `chart_picture_input_${adminId}`;
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.name = "chart_picture";
    fileInput.id = fileInputId;
    fileInput.accept = "image/*";
    fileInput.classList.add("chart-picture-input");
    fileInput.style.display = "none";

    const fileInputLabel = document.createElement("label");
    fileInputLabel.htmlFor = fileInputId;
    fileInputLabel.classList.add("custom-file-upload");
    fileInputLabel.textContent = "Change Picture";

    fileInput.addEventListener("change", (event) => {
      const file = event.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
          editImg.src = e.target.result;
        };
        reader.readAsDataURL(file);
      }
    });

    editForm.appendChild(fileInputLabel);
    editForm.appendChild(fileInput);

    /**
     * Helper to create input fields for the edit form.
     * @param {string} name - The name attribute for the input.
     * @param {string} value - The initial value of the input.
     * @param {string} placeholder - The placeholder text.
     * @param {boolean} isEditable - Whether the input should be editable (default: true).
     * @returns {HTMLElement} The created input element.
     */
    const createInputField = (name, value, placeholder, isEditable = true) => {
      const input = document.createElement("input");
      input.type = "text";
      input.name = name;
      input.value = value;
      input.placeholder = placeholder;
      input.classList.add("org-node-input-field");
      input.readOnly = !isEditable;
      if (!isEditable) {
        input.classList.add("read-only-input");
      }
      return input;
    };

    const firstNameInput = createInputField(
      "first_name",
      admin.first_name || "",
      "First Name"
    );
    const lastNameInput = createInputField(
      "last_name",
      admin.last_name || "",
      "Last Name"
    );

    const positionInput = createInputField(
      "position",
      admin.position || "",
      "Position",
      !(
        adminId.startsWith("new_placeholder_") ||
        adminId.startsWith("chart_node_")
      )
    );

    editForm.appendChild(firstNameInput);
    editForm.appendChild(lastNameInput);
    editForm.appendChild(positionInput);

    const buttonsContainer = document.createElement("div");
    buttonsContainer.classList.add("org-node-buttons-container");

    const saveButton = document.createElement("button");
    saveButton.textContent = "Save";
    saveButton.className = "btn btn-success";
    saveButton.type = "button";
    saveButton.addEventListener("click", () =>
      saveOrgChartNode(adminId, editForm)
    );
    buttonsContainer.appendChild(saveButton);

    const cancelButton = document.createElement("button");
    cancelButton.textContent = "Cancel";
    cancelButton.className = "btn btn-secondary";
    cancelButton.type = "button";
    cancelButton.addEventListener("click", () =>
      toggleOrgChartEditMode(adminId, false)
    );
    buttonsContainer.appendChild(cancelButton);

    editForm.appendChild(buttonsContainer);
    adminNodeWrapper.appendChild(editForm);

    return adminNodeWrapper;
  };

  /**
   * Creates and returns a document fragment containing the organizational chart display elements.
   * @param {Array<Object>} admins - An array of admin data objects.
   * @returns {DocumentFragment} The document fragment with the org chart.
   */
  function createOrgChartDisplayElements(admins) {
    const fragment = document.createDocumentFragment();

    const organizationName =
      admins.length > 0 && admins[0].organization_name
        ? String(admins[0].organization_name).toUpperCase()
        : "UNKNOWN ORGANIZATION";

    const organizationNameNode = document.createElement("div");
    organizationNameNode.className = "org-node org-root";
    organizationNameNode.textContent = organizationName;
    fragment.appendChild(organizationNameNode);

    /**
     * Filters admins by a specific position key.
     * @param {string} positionKey - The position to filter by.
     * @returns {Array<Object>} An array of admin objects for the given position.
     */
    const getDisplayAdminsForPosition = (positionKey) => {
      return admins.filter((admin) => admin.position === positionKey);
    };

    /**
     * Creates a branch structure for a group of admins.
     * Handles both single nodes and horizontal branches for multiple nodes.
     * @param {DocumentFragment} parentFragment - The fragment to append the branch to.
     * @param {Array<Object>} adminsForBranch - The array of admin objects for this branch.
     */
    const createBranchStructure = (parentFragment, adminsForBranch) => {
      if (adminsForBranch.length === 0) return;

      if (adminsForBranch.length > 1) {
        const horizontalBranchWrapper = document.createElement("div");
        horizontalBranchWrapper.classList.add("org-branch-wrapper");

        const nodesContainer = document.createElement("div");
        nodesContainer.classList.add("org-branch-container");

        adminsForBranch.forEach((admin) => {
          const nodeWrapper = document.createElement("div");
          nodeWrapper.classList.add("org-node-vertical-connection");

          const dropLine = document.createElement("div");
          dropLine.classList.add("org-line", "org-vertical-from-branch-top");
          nodeWrapper.appendChild(dropLine);

          nodeWrapper.appendChild(createAdminNodeDiv(admin));
          const verticalLineBelowNode = document.createElement("div");
          verticalLineBelowNode.classList.add(
            "org-line",
            "org-vertical-to-sub-branch"
          );
          nodeWrapper.appendChild(verticalLineBelowNode);
          nodesContainer.appendChild(nodeWrapper);
        });

        horizontalBranchWrapper.appendChild(nodesContainer);
        parentFragment.appendChild(horizontalBranchWrapper);
      } else {
        parentFragment.appendChild(createAdminNodeDiv(adminsForBranch[0]));
      }
    };

    const presidentData = getDisplayAdminsForPosition("President");
    if (presidentData.length > 0) {
      const presidentNode = createAdminNodeDiv(presidentData[0]);
      presidentNode.classList.add("org-root-wrapper");

      const verticalLine = document.createElement("div");
      verticalLine.classList.add("org-line", "org-vertical");

      const rootNodeAndLineContainer = document.createElement("div");
      rootNodeAndLineContainer.classList.add("root-node-and-line-container");
      rootNodeAndLineContainer.appendChild(presidentNode);
      rootNodeAndLineContainer.appendChild(verticalLine);
      fragment.appendChild(rootNodeAndLineContainer);

      const connectionLineContainer = document.createElement("div");
      connectionLineContainer.classList.add("org-connection-line-container");

      const verticalStub = document.createElement("div");
      verticalStub.classList.add("org-line", "org-vertical-stub");
      connectionLineContainer.appendChild(verticalStub);

      const horizontalConnectionLine = document.createElement("div");
      horizontalConnectionLine.classList.add(
        "org-line",
        "org-line-horizontal-connection"
      );
      connectionLineContainer.appendChild(horizontalConnectionLine);

      fragment.appendChild(connectionLineContainer);
    }

    const vps = [
      ...getDisplayAdminsForPosition("Vice President-Internal"),
      ...getDisplayAdminsForPosition("Vice President-External"),
    ];
    if (vps.length > 0) {
      createBranchStructure(fragment, vps);
    }

    const otherCorePositions = [
      ...getDisplayAdminsForPosition("Secretary"),
      ...getDisplayAdminsForPosition("Treasurer"),
      ...getDisplayAdminsForPosition("Auditor"),
      ...getDisplayAdminsForPosition("Public Relation Officer"),
    ];

    if (otherCorePositions.length > 0) {
      const subBranchConnectionContainer = document.createElement("div");
      subBranchConnectionContainer.classList.add(
        "org-sub-branch-connection-container"
      );

      const horizontalSubBranchLine = document.createElement("div");
      horizontalSubBranchLine.classList.add(
        "org-line",
        "org-line-horizontal-sub-branch"
      );
      subBranchConnectionContainer.appendChild(horizontalSubBranchLine);

      const subNodesContainer = document.createElement("div");
      subNodesContainer.classList.add("org-branch-container");

      otherCorePositions.forEach((admin) => {
        const nodeWrapper = document.createElement("div");
        nodeWrapper.classList.add("org-node-vertical-connection");

        const dropLine = document.createElement("div");
        dropLine.classList.add("org-line", "org-vertical-from-branch-top");
        nodeWrapper.appendChild(dropLine);

        nodeWrapper.appendChild(createAdminNodeDiv(admin));
        subNodesContainer.appendChild(nodeWrapper);
      });

      subBranchConnectionContainer.appendChild(subNodesContainer);
      fragment.appendChild(subBranchConnectionContainer);
    }

    const adviserData = [
      ...getDisplayAdminsForPosition("Adviser 1"),
      ...getDisplayAdminsForPosition("Adviser 2"),
    ];

    if (adviserData.length > 0) {
      if (fragment.children.length > 1) {
        const hr = document.createElement("hr");
        hr.classList.add("section-divider");
        fragment.appendChild(hr);
      }

      const adviserSectionHeader = document.createElement("h4");
      adviserSectionHeader.textContent = "ADVISERS";
      adviserSectionHeader.classList.add("adviser-section-header");

      fragment.appendChild(adviserSectionHeader);

      const adviserGroupContainer = document.createElement("div");
      adviserGroupContainer.classList.add(
        "org-branch-container",
        "adviser-group-container"
      );

      adviserData.forEach((admin) => {
        adviserGroupContainer.appendChild(createAdminNodeDiv(admin));
      });
      fragment.appendChild(adviserGroupContainer);
    }

    return fragment;
  }

  /**
   * Fetches organizational chart data from the API and renders it in the modal.
   */
  async function fetchAndRenderOrgChart() {
    if (!modalBody) return;

    openGlobalModal("Organizational Chart");
    modalBody.innerHTML =
      '<p class="loading-message">Loading organizational chart...</p>';

    try {
      const response = await fetch("/api/admin/org_chart_data");
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const admins = await response.json();

      modalBody.innerHTML = "";

      const chartElements = createOrgChartDisplayElements(admins);
      modalBody.appendChild(chartElements);
    } catch (error) {
      console.error("Error fetching or rendering organizational chart:", error);
      modalBody.innerHTML =
        '<p class="error-message">Failed to load organizational chart. Please try again later.</p>';
    }
  }

  if (orgChartButton && globalModal) {
    orgChartButton.addEventListener("click", function () {
      fetchAndRenderOrgChart();
    });
  }
});
