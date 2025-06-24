function displayNotification(message, type = "info") {
  const notification = document.createElement("div");
  notification.style.position = "fixed";
  notification.style.bottom = "20px";
  notification.style.left = "50%";
  notification.style.transform = "translateX(-50%)";
  notification.style.padding = "15px";
  notification.style.borderRadius = "8px";
  notification.style.zIndex = "1000";
  notification.style.backgroundColor =
    type === "success" ? "#28a745" : type === "error" ? "#dc3545" : "#3498db";
  notification.style.color = "white";
  notification.style.fontWeight = "bold";
  notification.style.boxShadow = "0 4px 12px rgba(0, 0, 0, 0.15)";
  notification.style.opacity = "0";
  notification.style.transition = "opacity 0.3s ease-in-out";
  notification.textContent = message;
  document.body.appendChild(notification);

  void notification.offsetWidth;
  notification.style.opacity = "1";

  setTimeout(() => {
    notification.style.opacity = "0";
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

document.addEventListener("DOMContentLoaded", function () {
  const orgId = document.getElementById("organizationId").value;
  const themeColorInput = document.getElementById("themeColorInput");
  const themeColorPicker = document.getElementById("themeColorPicker");
  const saveThemeButton = document.getElementById("saveThemeColorButton");
  const themeColorError = document.getElementById("themeColorError");

  const logoFileInput = document.getElementById("logoFileInput");
  const uploadLogoButton = document.getElementById("uploadLogoButton");
  const logoUploadError = document.getElementById("logoUploadError");
  const currentLogoPreview = document.getElementById("currentLogoPreview");
  const customLogoUploadLabel = document.querySelector(
    ".custom-logo-upload-label"
  );

  const profilePictureInput = document.getElementById("profilePictureInput");
  const uploadProfilePictureButton = document.getElementById(
    "uploadProfilePictureButton"
  );
  const profilePictureError = document.getElementById("profilePictureError");
  const currentProfilePicturePreview = document.getElementById(
    "currentProfilePicturePreview"
  );
  const customProfilePictureUploadLabel = document.querySelector(
    ".custom-profile-picture-upload-label"
  );
  const noProfilePictureMessage = document.getElementById(
    "noProfilePictureMessage"
  );

  async function loadAdminProfilePicture() {
    console.log("Loading admin profile picture on page load...");
    try {
      const response = await fetch("/api/admin/me/profile");
      if (response.ok) {
        const data = await response.json();
        console.log("Admin profile data fetched:", data);
        if (data.profile_picture) {
          const profilePictureUrl = `${
            data.profile_picture
          }?t=${new Date().getTime()}`;
          currentProfilePicturePreview.src = profilePictureUrl;
          currentProfilePicturePreview.style.display = "block";

          currentProfilePicturePreview.setAttribute(
            "data-initial-src",
            data.profile_picture
          );
          if (noProfilePictureMessage)
            noProfilePictureMessage.style.display = "none";
          console.log("Profile picture set to:", profilePictureUrl);
        } else {
          currentProfilePicturePreview.src =
            "/static/images/default_profile.jpg";
          currentProfilePicturePreview.style.display = "block";
          currentProfilePicturePreview.setAttribute(
            "data-initial-src",
            "/static/images/default_profile.jpg"
          );
          if (noProfilePictureMessage)
            noProfilePictureMessage.style.display = "none";
          console.log("No profile picture from backend, setting to default.");
        }
      } else {
        console.error(
          "Failed to fetch admin profile for initial load:",
          response.status,
          response.statusText
        );

        currentProfilePicturePreview.src = "/static/images/default_profile.jpg";
        currentProfilePicturePreview.style.display = "block";
        currentProfilePicturePreview.setAttribute(
          "data-initial-src",
          "/static/images/default_profile.jpg"
        );
        if (noProfilePictureMessage)
          noProfilePictureMessage.style.display = "none";
      }
    } catch (error) {
      console.error("Error fetching admin profile:", error);

      currentProfilePicturePreview.src = "/static/images/default_profile.jpg";
      currentProfilePicturePreview.style.display = "block";
      currentProfilePicturePreview.setAttribute(
        "data-initial-src",
        "/static/images/default_profile.jpg"
      );
      if (noProfilePictureMessage)
        noProfilePictureMessage.style.display = "none";
    }
  }

  loadAdminProfilePicture();

  themeColorInput.addEventListener("input", function () {
    const hexRegex = /^#([0-9A-F]{3}){1,2}$/i;
    if (hexRegex.test(this.value)) {
      themeColorPicker.value = this.value;
      themeColorError.textContent = "";
    } else {
      themeColorError.textContent =
        "Invalid hex color format (e.g., #RRGGBB or #RGB).";
    }
  });

  themeColorPicker.addEventListener("input", function () {
    themeColorInput.value = this.value;
    themeColorError.textContent = "";
  });

  saveThemeButton.addEventListener("click", async function () {
    const newThemeColor = themeColorInput.value;
    const hexRegex = /^#([0-9A-F]{3}){1,2}$/i;
    if (!newThemeColor || !hexRegex.test(newThemeColor)) {
      themeColorError.textContent =
        "Please enter a valid hex color (e.g., #RRGGBB).";
      return;
    } else {
      themeColorError.textContent = "";
    }

    if (!orgId) {
      displayNotification(
        "Organization ID not found. Cannot update theme.",
        "error"
      );
      return;
    }

    try {
      const response = await fetch(`/api/admin/organizations/${orgId}/theme`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_theme_color: newThemeColor }),
      });
      const data = await response.json();

      if (response.ok) {
        displayNotification(data.message, "success");
        document.documentElement.style.setProperty(
          "--organization-theme-color",
          newThemeColor
        );
      } else {
        displayNotification(
          "Error updating theme: " + (data.detail || "Unknown error"),
          "error"
        );
      }
    } catch (error) {
      console.error("Fetch error:", error);
      displayNotification("An error occurred while saving the theme.", "error");
    }
  });

  if (customLogoUploadLabel) {
    customLogoUploadLabel.addEventListener("click", () => {
      logoFileInput.click();
    });
  }

  logoFileInput.addEventListener("change", function () {
    if (this.files && this.files[0]) {
      const file = this.files[0];
      const allowedTypes = [
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/svg+xml",
      ];
      if (!allowedTypes.includes(file.type)) {
        logoUploadError.textContent =
          "Invalid file type. Only PNG, JPG, JPEG, GIF, SVG are allowed.";
        uploadLogoButton.disabled = true;
        currentLogoPreview.style.display = "none";
        if (customLogoUploadLabel)
          customLogoUploadLabel.textContent = "Choose Logo File";
      } else {
        logoUploadError.textContent = "";
        uploadLogoButton.disabled = false;
        if (customLogoUploadLabel)
          customLogoUploadLabel.textContent = file.name;

        const reader = new FileReader();
        reader.onload = function (e) {
          currentLogoPreview.src = e.target.result;
          currentLogoPreview.style.display = "block";
          const noLogoMessage = currentLogoPreview.previousElementSibling;
          if (
            noLogoMessage &&
            noLogoMessage.tagName === "P" &&
            noLogoMessage.textContent.includes("No logo uploaded yet")
          ) {
            noLogoMessage.style.display = "none";
          }
        };
        reader.readAsDataURL(file);
      }
    } else {
      uploadLogoButton.disabled = false;
      logoUploadError.textContent = "";
      if (customLogoUploadLabel)
        customLogoUploadLabel.textContent = "Choose Logo File";

      if (currentLogoPreview.getAttribute("data-initial-src")) {
        currentLogoPreview.src =
          currentLogoPreview.getAttribute("data-initial-src");
        currentLogoPreview.style.display = "block";
      } else {
        currentLogoPreview.src = "";
        currentLogoPreview.style.display = "none";
      }
      const noLogoMessage = currentLogoPreview.previousElementSibling;
      if (
        noLogoMessage &&
        noLogoMessage.tagName === "P" &&
        noLogoMessage.textContent.includes("No logo uploaded yet") &&
        !currentLogoPreview.src
      ) {
        noLogoMessage.style.display = "block";
      }
    }
  });

  uploadLogoButton.addEventListener("click", async function () {
    if (!orgId) {
      displayNotification(
        "Organization ID not found. Cannot upload logo.",
        "error"
      );
      return;
    }

    const file = logoFileInput.files[0];
    if (!file) {
      logoUploadError.textContent = "Please select a logo file to upload.";
      return;
    }

    const allowedTypes = [
      "image/png",
      "image/jpeg",
      "image/gif",
      "image/svg+xml",
    ];
    if (!allowedTypes.includes(file.type)) {
      logoUploadError.textContent =
        "Invalid file type. Only PNG, JPG, JPEG, GIF, SVG are allowed.";
      return;
    } else {
      logoUploadError.textContent = "";
    }

    const formData = new FormData();
    formData.append("logo_file", file);

    try {
      const response = await fetch(`/api/admin/organizations/${orgId}/logo`, {
        method: "PUT",
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        displayNotification(data.message, "success");
        if (data.logo_url && currentLogoPreview) {
          currentLogoPreview.src = data.logo_url;
          currentLogoPreview.style.display = "block";
          const noLogoMessage = currentLogoPreview.previousElementSibling;
          if (
            noLogoMessage &&
            noLogoMessage.tagName === "P" &&
            noLogoMessage.textContent.includes("No logo uploaded yet")
          ) {
            noLogoMessage.style.display = "none";
          }
        }
        logoFileInput.value = "";
        if (customLogoUploadLabel)
          customLogoUploadLabel.textContent = "Choose Logo File";
      } else {
        displayNotification(
          "Error uploading logo: " + (data.detail || "Unknown error"),
          "error"
        );
      }
    } catch (error) {
      console.error("Fetch error:", error);
      displayNotification(
        "An error occurred while uploading the logo.",
        "error"
      );
    }
  });

  if (currentLogoPreview && currentLogoPreview.src) {
    currentLogoPreview.setAttribute("data-initial-src", currentLogoPreview.src);
  }

  if (customProfilePictureUploadLabel) {
    customProfilePictureUploadLabel.addEventListener("click", () => {
      profilePictureInput.click();
    });
  }

  profilePictureInput.addEventListener("change", function () {
    console.log("Profile picture input changed.");
    if (this.files && this.files[0]) {
      const file = this.files[0];
      const allowedTypes = [
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/svg+xml",
      ];

      if (!allowedTypes.includes(file.type)) {
        profilePictureError.textContent =
          "Invalid file type. Only PNG, JPG, JPEG, GIF, SVG are allowed.";
        uploadProfilePictureButton.disabled = true;
        currentProfilePicturePreview.style.display = "none";
        if (noProfilePictureMessage)
          noProfilePictureMessage.style.display = "block";
        if (customProfilePictureUploadLabel)
          customProfilePictureUploadLabel.textContent =
            "Choose Profile Picture";
        console.log("Invalid file type selected.");
      } else {
        profilePictureError.textContent = "";
        uploadProfilePictureButton.disabled = false;
        if (customProfilePictureUploadLabel)
          customProfilePictureUploadLabel.textContent = file.name;

        const reader = new FileReader();
        reader.onload = function (e) {
          currentProfilePicturePreview.src = e.target.result;
          currentProfilePicturePreview.style.display = "block";
          if (noProfilePictureMessage)
            noProfilePictureMessage.style.display = "none";
          console.log(
            "Client-side preview set. Current src:",
            currentProfilePicturePreview.src
          );
        };
        reader.readAsDataURL(file);
      }
    } else {
      console.log("No file selected, reverting preview.");

      uploadProfilePictureButton.disabled = true;
      profilePictureError.textContent = "";
      if (customProfilePictureUploadLabel)
        customProfilePictureUploadLabel.textContent = "Choose Profile Picture";

      loadAdminProfilePicture();
    }
  });

  uploadProfilePictureButton.addEventListener("click", async function () {
    console.log("Upload profile picture button clicked.");

    const file = profilePictureInput.files[0];
    if (!file) {
      profilePictureError.textContent =
        "Please select a profile picture file to upload.";
      console.log("No file selected for upload.");
      return;
    }

    const allowedTypes = [
      "image/png",
      "image/jpeg",
      "image/gif",
      "image/svg+xml",
    ];
    if (!allowedTypes.includes(file.type)) {
      profilePictureError.textContent =
        "Invalid file type. Only PNG, JPG, JPEG, GIF, SVG are allowed.";
      console.log("Invalid file type for upload.");
      return;
    } else {
      profilePictureError.textContent = "";
    }

    const formData = new FormData();
    formData.append("profile_picture_file", file);

    try {
      console.log("Attempting to upload profile picture...");
      const response = await fetch(`/api/admin/me/profile_picture`, {
        method: "PUT",
        body: formData,
      });

      const data = await response.json();
      console.log("Backend response data:", data);

      if (response.ok) {
        displayNotification(data.message, "success");
        if (data.profile_picture_url && currentProfilePicturePreview) {
          const newProfilePictureUrl = `${
            data.profile_picture_url
          }?t=${new Date().getTime()}`;
          console.log("Setting preview src to:", newProfilePictureUrl);
          currentProfilePicturePreview.src = newProfilePictureUrl;

          currentProfilePicturePreview.style.display = "block";

          currentProfilePicturePreview.setAttribute(
            "data-initial-src",
            data.profile_picture_url
          );
          if (noProfilePictureMessage)
            noProfilePictureMessage.style.display = "none";

          setTimeout(
            () =>
              console.log(
                "Final preview src (after timeout):",
                currentProfilePicturePreview.src
              ),
            100
          );
        }
        profilePictureInput.value = "";
        if (customProfilePictureUploadLabel)
          customProfilePictureUploadLabel.textContent =
            "Choose Profile Picture";
        uploadProfilePictureButton.disabled = true;
      } else {
        displayNotification(
          "Error uploading profile picture: " +
            (data.detail || "Unknown error"),
          "error"
        );
        console.error("Error response from backend:", data);
      }
    } catch (error) {
      console.error("Fetch error:", error);
      displayNotification(
        "An error occurred while uploading the profile picture.",
        "error"
      );
    }
  });

  let currentPage = 1;
  const limit = 20;

  async function fetchAdminLogs() {
    let url = `/admin-logs?skip=${(currentPage - 1) * limit}&limit=${limit}`;

    try {
      const response = await fetch(url);
      if (!response.ok) {
        if (response.status === 403) {
          displayNotification(
            "You are not authorized to view admin logs.",
            "error"
          );
        } else {
          displayNotification("Failed to fetch admin logs.", "error");
        }
        console.error("Failed to fetch admin logs:", response.statusText);
        renderLogs([]);
        return;
      }
      const logs = await response.json();
      renderLogs(logs);
    } catch (error) {
      console.error("Error fetching admin logs:", error);
      displayNotification(
        "An error occurred while fetching admin logs.",
        "error"
      );
      renderLogs([]);
    }
  }

  function renderLogs(logs) {
    const tableBody = document.getElementById("logTableBody");
    tableBody.innerHTML = "";

    if (logs.length === 0) {
      tableBody.innerHTML =
        '<tr><td colspan="5" style="text-align: center; padding: 10px; color: #555;">No logs found.</td></tr>';
      return;
    }

    logs.forEach((log) => {
      const row = document.createElement("tr");

      const timestamp = new Date(log.timestamp).toLocaleString();
      const adminName = log.admin_name || "N/A";
      const actionType = log.action_type || "N/A";
      const description = log.description || "No description provided.";
      const ipAddress = log.ip_address || "N/A";

      row.innerHTML = `
                <td>${timestamp}</td>
                <td>${adminName}</td>
                <td>${actionType}</td>
                <td>${description}</td>
                <td>${ipAddress}</td>
            `;
      tableBody.appendChild(row);
    });
  }

  fetchAdminLogs();

  const prevPageBtn = document.getElementById("prevPageBtn");
  const nextPageBtn = document.getElementById("nextPageBtn");

  if (prevPageBtn && nextPageBtn) {
    prevPageBtn.addEventListener("click", () => {
      if (currentPage > 1) {
        currentPage--;
        fetchAdminLogs();
      }
    });

    nextPageBtn.addEventListener("click", () => {
      currentPage++;
      fetchAdminLogs();
    });
  }

  const existingAdminsTableBody = document.getElementById(
    "existingAdminsTableBody"
  );

  async function fetchAndDisplayExistingAdmins() {
    if (!existingAdminsTableBody) {
      console.warn(
        "Existing Admins table body not found. Cannot display admins."
      );
      return;
    }

    try {
      const response = await fetch("/api/admin/existing_admins");
      if (!response.ok) {
        if (response.status === 403) {
          displayNotification(
            "You are not authorized to view the list of existing administrators.",
            "error"
          );
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const admins = await response.json();

      existingAdminsTableBody.innerHTML = "";

      if (admins.length === 0) {
        existingAdminsTableBody.innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 10px; color: #555;">No active administrators found for this organization.</td></tr>`;
        return;
      }

      admins.forEach((admin) => {
        const row = document.createElement("tr");

        const adminName = `${admin.first_name || ""} ${
          admin.last_name || ""
        }`.trim();
        const position = admin.position || "N/A";
        const pictureUrl =
          admin.profile_picture || "/static/images/default_profile.jpg";

        row.innerHTML = `
                    <td data-label="Picture">
                        <img src="${pictureUrl}" alt="${adminName}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover; margin-right: 10px;">
                    </td>
                    <td data-label="Name">${adminName || "N/A"}</td>
                    <td data-label="Position">${position}</td>
                    <td data-label="Status">Active</td> 
                `;
        existingAdminsTableBody.appendChild(row);
      });
    } catch (error) {
      console.error("Error fetching existing administrators:", error);
      existingAdminsTableBody.innerHTML = `<tr><td colspan="4" style="color: var(--org-error); text-align: center; padding: 10px;">Failed to load administrator list.</td></tr>`;
    }
  }

  fetchAndDisplayExistingAdmins();
});
