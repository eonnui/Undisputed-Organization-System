const studentSearchFilter = document.getElementById("student-search-filter");
const searchButton = document.querySelector(".search-button");
const yearLevelFilterWrapper = document.getElementById(
  "year-level-filter-wrapper"
);
const yearLevelFilterTrigger = document.getElementById(
  "year-level-filter-trigger"
);
const yearLevelFilterOptions = document.getElementById(
  "year-level-filter-options"
);
const yearLevelDropdown = document.getElementById("year-level-dropdown");
const sectionFilterWrapper = document.getElementById("section-filter-wrapper");
const sectionFilterTrigger = document.getElementById("section-filter-trigger");
const sectionFilterOptions = document.getElementById("section-filter-options");
const sectionDropdown = document.getElementById("section-dropdown");
const studentsTableBody = document.querySelector("#students-table tbody");
const studentsTableHead = document.querySelector("#students-table thead");

let selectedYearLevel = "";
let selectedSection = "";
let sortColumn = "last_name";
let sortDirection = "asc";

/**
 * Displays a temporary message box on the screen.
 * @param {string} message - The message to display.
 * @param {string} type - 'success', 'error', or 'info' (default: 'info').
 */
function displayMessageBox(message, type = "info") {
  const existingMessageBox = document.getElementById("message-box");
  if (existingMessageBox) {
    existingMessageBox.remove();
  }

  const msgBox = document.createElement("div");
  msgBox.id = "message-box";
  msgBox.textContent = message;
  msgBox.classList.add(type);

  document.body.appendChild(msgBox);

  msgBox.addEventListener(
    "animationend",
    () => {
      if (msgBox.parentNode) {
        msgBox.parentNode.removeChild(msgBox);
      }
    },
    { once: true }
  );
}

/**
 * Fetches student data from the API and populates the table.
 * Applies search, filter, and sort parameters.
 */
async function updateStudentsTable() {
  const tableBody = document
    .getElementById("students-table")
    .getElementsByTagName("tbody")[0];
  tableBody.innerHTML = "";

  const studentSearchQuery = document
    .getElementById("student-search-filter")
    .value.trim();

  let url = "/admin/students";
  let queryParams = [];

  if (studentSearchQuery) {
    queryParams.push(`search=${encodeURIComponent(studentSearchQuery)}`);
  }

  if (selectedYearLevel) {
    queryParams.push(`year_level=${encodeURIComponent(selectedYearLevel)}`);
  }

  if (selectedSection) {
    queryParams.push(`section=${encodeURIComponent(selectedSection)}`);
  }

  if (sortColumn) {
    queryParams.push(`sort_by=${encodeURIComponent(sortColumn)}`);
    queryParams.push(`sort_direction=${encodeURIComponent(sortDirection)}`);
  }

  if (queryParams.length > 0) {
    url += "?" + queryParams.join("&");
  }

  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    let data = await response.json();

    if (data.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="7" style="text-align: center;">No students found matching your criteria.</td></tr>`;
      return;
    }

    data.forEach((student) => {
      let row = tableBody.insertRow();
      row.insertCell().textContent = student.student_number;
      row.insertCell().textContent = student.first_name;
      row.insertCell().textContent = student.last_name;
      row.insertCell().textContent = student.year_level;
      row.insertCell().textContent = student.section;
      row.insertCell().textContent = student.email;

      const actionCell = row.insertCell();
      actionCell.innerHTML = `<button class="view-profile-button" data-student-number="${student.student_number}">View</button>`;
    });

    document.querySelectorAll(".view-profile-button").forEach((button) => {
      button.addEventListener("click", async function () {
        const studentNumber = this.dataset.studentNumber;
        await fetchStudentProfileAndShowModal(studentNumber);
      });
    });

    updateSortArrows(sortColumn, sortDirection);
  } catch (error) {
    console.error("Failed to fetch student data:", error);
    displayMessageBox("Error loading student data. Please try again.", "error");
    tableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: red;">Error loading student data.</td></tr>`;
  }
}

/**
 * Fetches a specific student's profile data and displays it in the global modal.
 * @param {string} studentNumber - The student ID to fetch.
 */
async function fetchStudentProfileAndShowModal(studentNumber) {
  const globalModal = document.getElementById("global-modal");
  const modalBody = document.getElementById("modal-body");

  if (!globalModal || !modalBody) {
    console.error("Global modal or modal body not found in parent template.");
    displayMessageBox("Error: Global modal not available.", "error");
    return;
  }

  try {
    const response = await fetch(`/admin/students/profile/${studentNumber}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const student = await response.json();

    const contentHTML = `
        <h3 id="modalStudentName">${student.first_name || ""} ${
      student.last_name || ""
    }</h3>
        <div class="modal-profile-details">
            ${
              student.profile_picture
                ? `<div class="profile-item student-photo-container"><img src="${student.profile_picture}" alt="Student Photo" class="student-profile-photo"></div>`
                : '<div class="profile-item student-photo-container student-photo-placeholder">👤</div>'
            }
            <div class="profile-item">
                <strong>Student ID:</strong> <span id="modalStudentNumber">${
                  student.student_number || "N/A"
                }</span>
            </div>
            <div class="profile-item">
                <strong>Email:</strong> <span id="modalEmail">${
                  student.email || "N/A"
                }</span>
            </div>
            <div class="profile-item">
                <strong>Year Level:</strong> <span id="modalYearLevel">${
                  student.year_level || "N/A"
                }</span>
            </div>
            <div class="profile-item">
                <strong>Section:</strong> <span id="modalSection">${
                  student.section || "N/A"
                }</span>
            </div>
            <div class="profile-item">
                <strong>Campus:</strong> <span id="modalCampus">${
                  student.campus || "N/A"
                }</span>
            </div>
            <div class="profile-item">
                <strong>Course:</strong> <span id="modalCourse">${
                  student.course || "N/A"
                }</span>
            </div>
            <div class="profile-item">
                <strong>School Year:</strong> <span id="modalSchoolYear">${
                  student.school_year || "N/A"
                }</span>
            </div>
            <div class="profile-item">
                <strong>Address:</strong> <span id="modalAddress">${
                  student.address || "N/A"
                }</span>
            </div>
            <div class="profile-item">
                <strong>Birthdate:</strong> <span id="modalBirthdate">${
                  student.birthdate || "N/A"
                }</span>
            </div>
            <div class="profile-item">
                <strong>Sex:</strong> <span id="modalSex">${
                  student.sex || "N/A"
                }</span>
            </div>
            <div class="profile-item">
                <strong>Guardian Name:</strong> <span id="modalGuardianName">${
                  student.guardian_name || "N/A"
                }</span>
            </div>
            <div class="profile-item">
                <strong>Guardian Contact:</strong> <span id="modalGuardianContact">${
                  student.guardian_contact || "N/A"
                }</span>
            </div>            
        </div>
    `;

    modalBody.innerHTML = contentHTML;

    if (typeof showGlobalModal === "function") {
      showGlobalModal();
    } else {
      globalModal.style.display = "flex";
    }
  } catch (error) {
    console.error("Failed to fetch student profile:", error);
    displayMessageBox(
      "Error loading student profile. Please try again.",
      "error"
    );
  }
}

/**
 * Updates the sort arrow indicators in the table header.
 * @param {string} column - The column that was sorted.
 * @param {string} direction - The sort direction.
 */
function updateSortArrows(column, direction) {
  document.querySelectorAll(".students-table th.sortable").forEach((th) => {
    th.classList.remove("asc", "desc");
  });
  const sortedTh = document.querySelector(
    `.students-table th[data-column="${column}"]`
  );
  if (sortedTh) {
    sortedTh.classList.add(direction);
  }
}

document.addEventListener("DOMContentLoaded", function () {
  const globalModal = document.getElementById("global-modal");
  const globalCloseButton = globalModal
    ? globalModal.querySelector(".modal-close-btn")
    : null;

  document.querySelectorAll(".custom-select-wrapper").forEach((wrapper) => {
    const trigger = wrapper.querySelector(".custom-select-trigger");
    const options = wrapper.querySelector(".custom-options");
    const listItems = options.querySelectorAll("li");

    trigger.addEventListener("click", () => {
      document
        .querySelectorAll(".custom-select-wrapper.open")
        .forEach((openWrapper) => {
          if (openWrapper !== wrapper) {
            openWrapper.classList.remove("open");
            openWrapper.querySelector(".custom-options").style.display = "none";
          }
        });

      const isOpen = wrapper.classList.toggle("open");
      options.style.display = isOpen ? "block" : "none";
    });

    listItems.forEach((item) => {
      item.addEventListener("click", () => {
        const value = item.dataset.value;
        trigger.querySelector("span").textContent = item.textContent;
        wrapper.classList.remove("open");
        options.style.display = "none";

        if (wrapper.id === "year-level-filter-wrapper") {
          selectedYearLevel = value;
        } else if (wrapper.id === "section-filter-wrapper") {
          selectedSection = value;
        }
        updateStudentsTable();
      });
    });
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".custom-select-wrapper")) {
      document
        .querySelectorAll(".custom-select-wrapper.open")
        .forEach((openWrapper) => {
          openWrapper.classList.remove("open");
          openWrapper.querySelector(".custom-options").style.display = "none";
        });
    }
  });

  document.querySelectorAll("#students-table th.sortable").forEach((header) => {
    header.addEventListener("click", function () {
      const clickedColumn = this.dataset.column;

      if (sortColumn === clickedColumn) {
        sortDirection = sortDirection === "asc" ? "desc" : "asc";
      } else {
        sortColumn = clickedColumn;
        sortDirection = "asc";
      }

      updateStudentsTable();
    });
  });

  updateStudentsTable();

  document
    .getElementById("student-search-filter")
    .addEventListener("input", function () {
      updateStudentsTable();
    });

  if (globalCloseButton) {
    globalCloseButton.addEventListener("click", () => {
      if (typeof hideGlobalModal === "function") {
        hideGlobalModal();
      } else {
        globalModal.style.display = "none";
      }
    });
  }

  window.addEventListener("click", (event) => {
    if (event.target === globalModal) {
      if (typeof hideGlobalModal === "function") {
        hideGlobalModal();
      } else {
        globalModal.style.display = "none";
      }
    }
  });
});
