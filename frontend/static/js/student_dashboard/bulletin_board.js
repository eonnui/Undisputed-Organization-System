document.addEventListener("DOMContentLoaded", function () {
  const globalModal = document.getElementById("global-modal");
  const modalBody = globalModal.querySelector("#modal-body");

  const modalTitleElement = globalModal.querySelector(".modal-content h3");
  const modalCloseBtn = globalModal.querySelector(".modal-close-btn");

  function openGlobalModal(title, contentHtml) {
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
    modalBody.innerHTML = contentHtml;
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
    button.addEventListener("click", function () {
      const postId = this.dataset.postId;
      const heartCountSpan = this.querySelector(".heart-count");
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
  const organizationChartContainerInHiddenDiv = document.getElementById(
    "organizationChartContent"
  );

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

  /**
   * Creates the complete HTML structure for the organizational chart.
   * @param {Array<Object>} admins - An array of admin objects fetched from the backend.
   * @returns {DocumentFragment} A document fragment containing the full HTML chart structure.
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
    const tempOrgChartContainer = document.createElement("div");
    tempOrgChartContainer.innerHTML =
      '<p class="loading-message">Loading organizational chart...</p>';

    try {
      const response = await fetch("/api/admin/org_chart_data");
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const admins = await response.json();

      tempOrgChartContainer.innerHTML = "";
      const chartElements = createOrgChartDisplayElements(admins);
      tempOrgChartContainer.appendChild(chartElements);

      openGlobalModal("Organizational Chart", tempOrgChartContainer.innerHTML);
    } catch (error) {
      console.error("Error fetching or rendering organizational chart:", error);

      openGlobalModal(
        "Error Loading Chart",
        '<p class="error-message">Failed to load organizational chart. Please try again later.</p>'
      );
    }
  }

  if (orgChartButton) {
    orgChartButton.addEventListener("click", function () {
      fetchAndRenderOrgChart();
    });
  }
});
