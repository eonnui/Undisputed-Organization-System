document.addEventListener("DOMContentLoaded", function () {
  const globalModal = document.getElementById("global-modal");
  const modalBody = globalModal.querySelector("#modal-body");

  const modalTitleElement = globalModal.querySelector(".modal-content h3");
  const modalCloseBtn = globalModal.querySelector(".modal-close-btn");

  function openGlobalModal(title, content = "") {
    if (modalTitleElement) {
      modalTitleElement.innerText = title;
    } else {
      console.warn(
        "No h3 element found in modal-content for title. Appending title."
      );
      const newTitle = document.createElement("h3");
      newTitle.innerText = title;
      modalBody.prepend(newTitle);
    }

    modalBody.innerHTML = "";
    if (typeof content === "string") {
      modalBody.innerHTML = content;
    } else if (content instanceof HTMLElement) {
      modalBody.appendChild(content);
    }

    globalModal.style.display = "flex";
    globalModal.classList.add("is-visible");
    document.body.style.overflow = "hidden";
  }

  function closeGlobalModal() {
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

  const heartButtons = document.querySelectorAll(".heart-button");

  heartButtons.forEach((button) => {
    const postId = button.dataset.postId;
    const heartCountSpan = button.querySelector(".heart-count");

    if (heartCountSpan) {
      heartCountSpan.style.cursor = "pointer";
      heartCountSpan.addEventListener("click", async function (event) {
        event.stopPropagation();

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
                <span class="font-semibold">${liker.first_name} ${
                liker.last_name
              }</span>
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

  function fetchRulesWiki() {
    const rulesWikiContainer = document.querySelector(".wiki-posts-list");
    if (!rulesWikiContainer) return;

    rulesWikiContainer.innerHTML = "<p>Loading rules and wiki entries...</p>";

    fetch("/BulletinBoard")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.text();
      })
      .then((htmlString) => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(htmlString, "text/html");

        const newRulesWikiContent = doc.querySelector(".wiki-posts-list");

        if (newRulesWikiContent) {
          rulesWikiContainer.innerHTML = newRulesWikiContent.innerHTML;
        } else {
          rulesWikiContainer.innerHTML =
            "<p>Error: Could not load rules and wiki entries.</p>";
        }
      })
      .catch((error) => {
        console.error("Error fetching rules and wiki:", error);
        rulesWikiContainer.innerHTML =
          "<p>Failed to load rules and wiki entries.</p>";
      });
  }

  fetchRulesWiki();

  const orgChartButton = document.getElementById("viewOrgChartButton");

  const createAdminNodeDiv = (admin) => {
    const adminNodeWrapper = document.createElement("div");
    adminNodeWrapper.className = "org-node-wrapper";

    adminNodeWrapper.setAttribute("data-admin-id", admin.id);

    const displayMode = document.createElement("div");
    displayMode.className = "org-node org-node-display-mode";

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
      return admins.filter((admin) => admin.position === positionKey);
    };

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
      ...getDisplayAdminsForPosition("PRO"),
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

  if (orgChartButton) {
    orgChartButton.addEventListener("click", function () {
      fetchAndRenderOrgChart();
    });
  }

  document.body.addEventListener("click", function (event) {
    const clickedImage = event.target.closest(".expandable-image");

    if (clickedImage) {
      const imageUrl = clickedImage.src;
      const imageAlt = clickedImage.alt || "Expanded Image";

      const expandedImageElement = document.createElement("img");
      expandedImageElement.src = imageUrl;
      expandedImageElement.alt = imageAlt;
      expandedImageElement.style.maxWidth = "100%";
      expandedImageElement.style.height = "auto";
      expandedImageElement.style.display = "block";
      expandedImageElement.style.margin = "0 auto";
      expandedImageElement.style.borderRadius = "6px";

      openGlobalModal(imageAlt, expandedImageElement);
    }
  });
});
