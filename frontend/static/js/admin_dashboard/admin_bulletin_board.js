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

  const createAdminNodeDiv = (admin, positionOverride = null) => {
    const adminNode = document.createElement("div");
    adminNode.className = "org-node admin-node";
    adminNode.style.display = "flex";
    adminNode.style.flexDirection = "column";
    adminNode.style.alignItems = "center";

    const profileDiv = document.createElement("div");
    profileDiv.className = "profile-circle";

    const img = document.createElement("img");
    img.alt = `${admin.first_name}'s Profile`;

    if (admin.profile_picture_url) {
      img.src = admin.profile_picture_url;
    } else {
      img.src = "/static/images/your_image_name.jpg";
    }
    profileDiv.appendChild(img);
    adminNode.appendChild(profileDiv);

    const textContainer = document.createElement("div");
    textContainer.style.textAlign = "center";

    const positionSpan = document.createElement("span");
    positionSpan.className = "position-text";
    positionSpan.textContent = (
      positionOverride || admin.position
    ).toUpperCase();
    textContainer.appendChild(positionSpan);

    const nameSpan = document.createElement("span");
    nameSpan.className = "name-text";
    nameSpan.textContent = ` - ${admin.first_name} ${admin.last_name}`;
    textContainer.appendChild(nameSpan);

    adminNode.appendChild(textContainer);
    return adminNode;
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

    const positions = {
      President: [],
      "Vice President-Internal": [],
      "Vice President-External": [],
      Secretary: [],
      Treasurer: [],
      Auditor: [],
      "Public Relation Officer": [],
      Adviser: [],
    };
    admins.forEach((admin) => {
      if (positions[admin.position]) {
        positions[admin.position].push(admin);
      }
    });

    let previousGroupAdded = false;

    if (positions["President"].length > 0) {
      const lineToPresident = document.createElement("div");
      lineToPresident.classList.add("org-line", "org-vertical-to-branch");
      fragment.appendChild(lineToPresident);

      const presidentBranchContainer = document.createElement("div");
      presidentBranchContainer.classList.add("org-branch-container");

      positions["President"].forEach((admin, index) => {
        const presidentNode = createAdminNodeDiv(admin);
        presidentBranchContainer.appendChild(presidentNode);
        if (index < positions["President"].length - 1) {
          const horizontalLine = document.createElement("div");
          horizontalLine.classList.add("org-line", "org-line-horizontal");
          presidentBranchContainer.appendChild(horizontalLine);
        }
      });
      fragment.appendChild(presidentBranchContainer);
      previousGroupAdded = true;
    }

    const vps = [
      ...positions["Vice President-Internal"],
      ...positions["Vice President-External"],
    ];
    if (vps.length > 0) {
      const lineToVPs = document.createElement("div");
      lineToVPs.classList.add("org-line", "org-vertical-to-branch");
      fragment.appendChild(lineToVPs);

      const vpBranchContainer = document.createElement("div");
      vpBranchContainer.classList.add("org-branch-container");

      vps.forEach((admin, index) => {
        const vpNode = createAdminNodeDiv(admin);
        vpBranchContainer.appendChild(vpNode);
        if (index < vps.length - 1) {
          const horizontalLine = document.createElement("div");
          horizontalLine.classList.add("org-line", "org-line-horizontal");
          vpBranchContainer.appendChild(horizontalLine);
        }
      });
      fragment.appendChild(vpBranchContainer);
      previousGroupAdded = true;
    }

    const otherCorePositions = [
      ...positions["Secretary"],
      ...positions["Treasurer"],
      ...positions["Auditor"],
      ...positions["Public Relation Officer"],
    ];

    if (otherCorePositions.length > 0) {
      if (previousGroupAdded) {
        const lineToOthers = document.createElement("div");
        lineToOthers.classList.add("org-line", "org-vertical-to-branch");
        fragment.appendChild(lineToOthers);
      }

      const otherPositionsBranchContainer = document.createElement("div");
      otherPositionsBranchContainer.classList.add("org-branch-container");

      otherCorePositions.forEach((admin, index) => {
        const adminNode = createAdminNodeDiv(admin);
        otherPositionsBranchContainer.appendChild(adminNode);
        if (index < otherCorePositions.length - 1) {
          const horizontalLine = document.createElement("div");
          horizontalLine.classList.add("org-line", "org-line-horizontal");
          otherPositionsBranchContainer.appendChild(horizontalLine);
        }
      });
      fragment.appendChild(otherPositionsBranchContainer);
      previousGroupAdded = true;
    }

    if (positions["Adviser"].length > 0) {
      if (previousGroupAdded) {
        const lineToAdvisers = document.createElement("div");
        lineToAdvisers.classList.add("org-line", "org-vertical-to-branch");
        fragment.appendChild(lineToAdvisers);
      }

      const adviserSectionHeader = document.createElement("h4");
      adviserSectionHeader.textContent = "ADVISERS";
      Object.assign(adviserSectionHeader.style, {
        marginTop: "2rem",
        color: "var(--org-text-primary)",
        fontWeight: "600",
        width: "100%",
        textAlign: "center",
        paddingBottom: "0.5rem",
        borderBottom: "2px solid var(--org-border-medium)",
      });
      fragment.appendChild(adviserSectionHeader);

      const adviserGroupContainer = document.createElement("div");
      adviserGroupContainer.classList.add("org-branch-container");

      positions["Adviser"].forEach((admin, index) => {
        const adviserNode = createAdminNodeDiv(admin, "Adviser");
        adviserGroupContainer.appendChild(adviserNode);
        if (index < positions["Adviser"].length - 1) {
          const horizontalLine = document.createElement("div");
          horizontalLine.classList.add("org-line", "org-line-horizontal");
          adviserGroupContainer.appendChild(horizontalLine);
        }
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
