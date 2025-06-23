document.addEventListener("DOMContentLoaded", () => {
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

  function toggleEditMode(postId, showEdit) {
    const postCard = document.getElementById(`wiki-post-${postId}`);
    if (postCard) {
      const displayMode = postCard.querySelector(".wiki-post-display-mode");
      const editMode = postCard.querySelector(".wiki-post-edit-mode");

      if (showEdit) {
        if (displayMode) displayMode.style.display = "none";
        if (editMode) editMode.style.display = "block";
        postCard.scrollIntoView({ behavior: "smooth", block: "center" });
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

  const globalModal = document.getElementById("global-modal");
  const globalModalBody = document.getElementById("modal-body");
  const globalModalCloseButton = globalModal
    ? globalModal.querySelector(".modal-close-btn")
    : null;

  function toggleOrgChartEditMode(adminId, showEdit) {
    const adminNodeWrapper = globalModalBody.querySelector(
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

  async function saveOrgChartNode(adminId, formElement) {
    const isDefaultNode =
      adminId.startsWith("default_") || adminId.startsWith("new_placeholder_");
    console.log(`Saving node: ${adminId}, isDefaultNode: ${isDefaultNode}`);

    if (isDefaultNode) {
      const formData = new FormData(formElement);
      const profilePictureFile = formData.get("chart_picture");

      const textData = {};
      for (const [key, value] of formData.entries()) {
        if (key !== "chart_picture") {
          textData[key] = value;
        }
      }

      let newChartNodeId = adminId;

      try {
        const textResponse = await fetch(
          `/api/admin/org_chart_node/${adminId}`,
          {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(textData),
          }
        );

        if (!textResponse.ok) {
          const errorText = await textResponse.text();
          throw new Error(`Text data save failed: ${errorText}`);
        }

        const responseData = await textResponse.json();

        newChartNodeId = responseData.id;

        let pictureUpdateSuccess = true;
        if (profilePictureFile && profilePictureFile.size > 0) {
          const pictureFormData = new FormData();
          pictureFormData.append("chart_picture", profilePictureFile);

          const pictureResponse = await fetch(
            `/api/admin/org_chart_node/${newChartNodeId}/profile_picture`,
            {
              method: "PUT",
              body: pictureFormData,
            }
          );

          if (!pictureResponse.ok) {
            const errorText = await pictureResponse.text();
            console.error("Profile picture upload failed:", errorText);
            pictureUpdateSuccess = false;
            const messageBox = document.createElement("div");
            messageBox.className = "message-box error";
            messageBox.textContent = `Profile picture update failed: ${errorText}. Text data saved.`;
            document.body.appendChild(messageBox);
            setTimeout(() => messageBox.remove(), 5000);
          }
        }

        const messageBox = document.createElement("div");
        messageBox.className = "message-box success";
        messageBox.textContent = `New officer added successfully!${
          pictureUpdateSuccess ? "" : " (Picture had issues)"
        }`;
        document.body.appendChild(messageBox);
        setTimeout(() => messageBox.remove(), 3000);

        await fetchAndRenderOrgChart();
        toggleOrgChartEditMode(newChartNodeId, false);
        return;
      } catch (error) {
        console.error("Error creating new org chart node:", error);
        const messageBox = document.createElement("div");
        messageBox.className = "message-box error";
        messageBox.textContent = `An error occurred during new officer creation: ${error.message}`;
        document.body.appendChild(messageBox);
        setTimeout(() => messageBox.remove(), 5000);
        return;
      }
    }

    const formData = new FormData(formElement);
    const profilePictureFile = formData.get("chart_picture");

    const textData = {};
    for (const [key, value] of formData.entries()) {
      if (key !== "chart_picture") {
        textData[key] = value;
      }
    }

    try {
      const textResponse = await fetch(`/api/admin/org_chart_node/${adminId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(textData),
      });

      if (!textResponse.ok) {
        const errorText = await textResponse.text();
        throw new Error(`Text update failed: ${errorText}`);
      }

      let pictureUpdateSuccess = true;
      if (profilePictureFile && profilePictureFile.size > 0) {
        const pictureFormData = new FormData();
        pictureFormData.append("chart_picture", profilePictureFile);

        const pictureResponse = await fetch(
          `/api/admin/org_chart_node/${adminId}/profile_picture`,
          {
            method: "PUT",

            body: pictureFormData,
          }
        );

        if (!pictureResponse.ok) {
          const errorText = await pictureResponse.text();
          console.error("Profile picture upload failed:", errorText);
          pictureUpdateSuccess = false;
          const messageBox = document.createElement("div");
          messageBox.className = "message-box error";
          messageBox.textContent = `Profile picture update failed: ${errorText}. Text data saved.`;
          document.body.appendChild(messageBox);
          setTimeout(() => messageBox.remove(), 5000);
        } else {
          const responseData = await pictureResponse.json();
          const adminNodeWrapper = globalModalBody.querySelector(
            `.org-node-wrapper[data-admin-id="${adminId}"]`
          );
          if (adminNodeWrapper) {
            const imgElement = adminNodeWrapper.querySelector(
              ".org-node-display-mode .profile-circle img"
            );
            if (imgElement && responseData.chart_picture_url) {
              imgElement.src = responseData.chart_picture_url;
            }
          }
        }
      }

      const messageBox = document.createElement("div");
      messageBox.className = "message-box success";
      messageBox.textContent = `Admin data updated successfully!${
        pictureUpdateSuccess ? "" : " (Picture had issues)"
      }`;
      document.body.appendChild(messageBox);
      setTimeout(() => messageBox.remove(), 3000);

      await fetchAndRenderOrgChart();
      toggleOrgChartEditMode(adminId, false);
    } catch (error) {
      console.error("Error saving org chart node:", error);
      const messageBox = document.createElement("div");
      messageBox.className = "message-box error";
      messageBox.textContent = `An error occurred during save: ${error.message}`;
      document.body.appendChild(messageBox);
      setTimeout(() => messageBox.remove(), 5000);
    }
  }

  const createAdminNodeDiv = (admin, positionOverride = null) => {
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
    profileDiv.appendChild(img);
    displayMode.appendChild(profileDiv);

    const textContainer = document.createElement("div");
    textContainer.className = "text-container";

    const positionSpan = document.createElement("span");
    positionSpan.className = "position-text";
    positionSpan.textContent = (
      positionOverride ||
      admin.position ||
      "POSITION"
    ).toUpperCase();
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

    const createInputField = (name, value, placeholder) => {
      const input = document.createElement("input");
      input.type = "text";
      input.name = name;
      input.value = value;
      input.placeholder = placeholder;
      input.classList.add("org-node-input-field");

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
      positionOverride || admin.position || "",
      "Position"
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

    const getDisplayAdminsForPosition = (positionKey) => {
      const filteredAdmins = admins.filter(
        (admin) => admin.position === positionKey
      );

      if (filteredAdmins.length > 0) {
        return filteredAdmins;
      } else if (DEFAULT_JS_ORG_OFFICERS[positionKey]) {
        const defaultOfficer = DEFAULT_JS_ORG_OFFICERS[positionKey];
        return [{ ...defaultOfficer, organization_name: organizationName }];
      }
      return [];
    };

    const createBranchStructure = (parentFragment, adminsForBranch) => {
      if (adminsForBranch.length === 0) return;

      if (adminsForBranch.length > 1) {
        const horizontalBranchWrapper = document.createElement("div");
        horizontalBranchWrapper.classList.add("org-branch-wrapper");

        const nodesContainer = document.createElement("div");
        nodesContainer.classList.add("org-branch-container");

        adminsForBranch.forEach((admin, index) => {
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

    const adviserData = getDisplayAdminsForPosition("Adviser");
    if (adviserData.length > 0) {
      if (fragment.children.length > 1) {
        const hr = document.createElement("hr");
        hr.classList.add("section-divider");
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
        adviserGroupContainer.appendChild(createAdminNodeDiv(admin, "Adviser"));
      });
      fragment.appendChild(adviserGroupContainer);
    }

    return fragment;
  }

  async function fetchAndRenderOrgChart() {
    if (!globalModalBody) return;

    globalModalBody.innerHTML =
      '<p class="loading-message">Loading organizational chart...</p>';

    try {
      const response = await fetch("/api/admin/org_chart_data");
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const admins = await response.json();

      globalModalBody.innerHTML = "";

      const chartElements = createOrgChartDisplayElements(admins);
      globalModalBody.appendChild(chartElements);
    } catch (error) {
      console.error("Error fetching or rendering organizational chart:", error);
      globalModalBody.innerHTML =
        '<p class="error-message">Failed to load organizational chart. Please try again later.</p>';
    }
  }

  if (orgChartButton && globalModal) {
    orgChartButton.addEventListener("click", function () {
      globalModal.style.display = "flex";
      fetchAndRenderOrgChart();
    });
  }

  if (globalModalCloseButton && globalModal) {
    globalModalCloseButton.addEventListener("click", function () {
      globalModal.style.display = "none";
      globalModalBody.innerHTML = "";
    });
  }

  if (globalModal) {
    window.addEventListener("click", function (event) {
      if (event.target === globalModal) {
        globalModal.style.display = "none";
        globalModalBody.innerHTML = "";
      }
    });
  }
});
