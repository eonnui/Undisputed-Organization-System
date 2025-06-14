// admin_students_profile.js

// --- DOM Element References ---
const studentProfileModal = document.getElementById('studentProfileModal');
// closeButton is now defined within DOMContentLoaded for better scope
const studentSearchFilter = document.getElementById('student-search-filter');
const searchButton = document.querySelector('.search-button'); // This button is not used as input has an event listener now
const yearLevelFilterWrapper = document.getElementById('year-level-filter-wrapper');
const yearLevelFilterTrigger = document.getElementById('year-level-filter-trigger');
const yearLevelFilterOptions = document.getElementById('year-level-filter-options'); // Not directly used, but implied by custom select logic
const yearLevelDropdown = document.getElementById('year-level-dropdown');
const sectionFilterWrapper = document.getElementById('section-filter-wrapper');
const sectionFilterTrigger = document.getElementById('section-filter-trigger');
const sectionFilterOptions = document.getElementById('section-filter-options'); // Not directly used, but implied by custom select logic
const sectionDropdown = document.getElementById('section-dropdown');
const studentsTableBody = document.querySelector('#students-table tbody');
const studentsTableHead = document.querySelector('#students-table thead');

// --- Global State Variables for Filters and Sorting ---
let selectedYearLevel = "";
let selectedSection = "";
let sortColumn = "last_name"; // Default sort column for better initial view
let sortDirection = 'asc'; // Default sort direction

// --- Utility Functions ---

/**
 * Displays a temporary message box on the screen.
 * @param {string} message - The message to display.
 * @param {string} type - 'success', 'error', or 'info' (default: 'info').
 */
function displayMessageBox(message, type = 'info') {
    // Remove any existing message box to prevent multiple messages
    const existingMessageBox = document.getElementById('message-box');
    if (existingMessageBox) {
        existingMessageBox.remove();
    }

    const msgBox = document.createElement('div');
    msgBox.id = 'message-box'; // Assign an ID for easy removal
    msgBox.textContent = message;
    msgBox.classList.add(type); // Add type class for styling (e.g., 'error', 'info')

    document.body.appendChild(msgBox);

    // The fadeOut animation is handled by CSS @keyframes now, which is smoother.
    // We just need to remove the element after the animation completes.
    msgBox.addEventListener('animationend', () => {
        if (msgBox.parentNode) {
            msgBox.parentNode.removeChild(msgBox);
        }
    }, { once: true }); // Ensure the event listener only fires once
}


/**
 * Fetches student data from the API and populates the table.
 * Applies search, filter, and sort parameters.
 */
async function updateStudentsTable() {
    const tableBody = document.getElementById("students-table").getElementsByTagName('tbody')[0];
    tableBody.innerHTML = ""; // Clear existing table data

    const studentSearchQuery = document.getElementById('student-search-filter').value.trim();

    let url = "/admin/students"; // Base URL for the API endpoint
    let queryParams = [];

    // Add search query if present
    if (studentSearchQuery) {
        queryParams.push(`search=${encodeURIComponent(studentSearchQuery)}`);
    }
    // Add year level filter if selected
    if (selectedYearLevel) {
        queryParams.push(`year_level=${encodeURIComponent(selectedYearLevel)}`);
    }
    // Add section filter if selected
    if (selectedSection) {
        queryParams.push(`section=${encodeURIComponent(selectedSection)}`);
    }
    // Add sorting parameters
    if (sortColumn) {
        queryParams.push(`sort_by=${encodeURIComponent(sortColumn)}`);
        queryParams.push(`sort_direction=${encodeURIComponent(sortDirection)}`);
    }

    // Construct the final URL with query parameters
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

        // Populate the table with fetched student data
        data.forEach(student => {
            let row = tableBody.insertRow();
            row.insertCell().textContent = student.student_number;
            row.insertCell().textContent = student.first_name;
            row.insertCell().textContent = student.last_name;
            row.insertCell().textContent = student.year_level;
            row.insertCell().textContent = student.section;
            row.insertCell().textContent = student.email;
            // Modified: Use data-attribute and a class for modal trigger
            const actionCell = row.insertCell();
            actionCell.innerHTML = `<button class="view-profile-button" data-student-number="${student.student_number}">View Profile</button>`;
        });

        // Attach event listeners to the newly created "View Profile" buttons
        document.querySelectorAll('.view-profile-button').forEach(button => {
            button.addEventListener('click', async function() {
                const studentNumber = this.dataset.studentNumber;
                await fetchStudentProfileAndShowModal(studentNumber);
            });
        });

        // Update sort arrows after populating table
        updateSortArrows(sortColumn, sortDirection);

    } catch (error) {
        console.error("Failed to fetch student data:", error);
        displayMessageBox("Error loading student data. Please try again.", "error"); // Use the message box for errors
        tableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: red;">Error loading student data.</td></tr>`;
    }
}

/**
 * Fetches a specific student's profile data and displays it in the modal.
 * @param {string} studentNumber - The student ID to fetch.
 */
async function fetchStudentProfileAndShowModal(studentNumber) {
    const modal = document.getElementById('studentProfileModal');
    // Select the photo placeholder
    const photoPlaceholder = document.querySelector('.student-photo-placeholder');

    // Get all span elements within profile-item for dynamic population
    const modalElements = {
        modalStudentName: document.getElementById('modalStudentName'),
        modalStudentNumber: document.getElementById('modalStudentNumber'),
        modalEmail: document.getElementById('modalEmail'),
        modalYearLevel: document.getElementById('modalYearLevel'),
        modalSection: document.getElementById('modalSection'),
        modalCampus: document.getElementById('modalCampus'),
        modalCourse: document.getElementById('modalCourse'),
        modalSchoolYear: document.getElementById('modalSchoolYear'),
        modalAddress: document.getElementById('modalAddress'),
        modalBirthdate: document.getElementById('modalBirthdate'),
        modalSex: document.getElementById('modalSex'),
        modalGuardianName: document.getElementById('modalGuardianName'),
        modalGuardianContact: document.getElementById('modalGuardianContact')
    };

    try {
        const response = await fetch(`/admin/students/profile/${studentNumber}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const student = await response.json();

        // Populate modal with student data
        modalElements.modalStudentName.textContent = `${student.first_name || ''} ${student.last_name || ''}`;
        modalElements.modalStudentNumber.textContent = student.student_number || 'N/A';
        modalElements.modalEmail.textContent = student.email || 'N/A';
        modalElements.modalYearLevel.textContent = student.year_level || 'N/A';
        modalElements.modalSection.textContent = student.section || 'N/A';
        modalElements.modalCampus.textContent = student.campus || 'N/A';
        modalElements.modalCourse.textContent = student.course || 'N/A';
        modalElements.modalSchoolYear.textContent = student.school_year || 'N/A';
        modalElements.modalAddress.textContent = student.address || 'N/A';
        modalElements.modalBirthdate.textContent = student.birthdate || 'N/A';
        modalElements.modalSex.textContent = student.sex || 'N/A';
        modalElements.modalGuardianName.textContent = student.guardian_name || 'N/A';
        modalElements.modalGuardianContact.textContent = student.guardian_contact || 'N/A';

        // Populate student photo
        if (photoPlaceholder) {
            photoPlaceholder.innerHTML = ''; // Clear existing content
            if (student.photo) {
                const img = document.createElement('img');
                img.src = student.photo;
                img.alt = `${student.first_name || ''} ${student.last_name || ''} Photo`;
                photoPlaceholder.appendChild(img);
            } else {
                // Fallback for no photo, e.g., an icon or text
                photoPlaceholder.textContent = '👤'; // Unicode person icon
            }
        }

        modal.style.display = 'flex'; // Show the modal using flex to center it

    } catch (error) {
        console.error("Failed to fetch student profile:", error);
        displayMessageBox("Error loading student profile. Please try again.", "error");
    }
}


/**
 * Updates the sort arrow indicators in the table header.
 * @param {string} column - The column that was sorted.
 * @param {string} direction - The sort direction.
 */
function updateSortArrows(column, direction) {
    document.querySelectorAll('.students-table th.sortable').forEach(th => {
        th.classList.remove('asc', 'desc');
    });
    const sortedTh = document.querySelector(`.students-table th[data-column="${column}"]`);
    if (sortedTh) {
        sortedTh.classList.add(direction);
    }
}


// --- Event Listeners and Initial Setup ---
document.addEventListener('DOMContentLoaded', function() {
    // Get modal and close button references
    const modal = document.getElementById('studentProfileModal');
    const closeButton = modal.querySelector('.close-button');

    // Initialize custom select dropdowns for Year Level and Section
    document.querySelectorAll('.custom-select-wrapper').forEach(wrapper => {
        const trigger = wrapper.querySelector('.custom-select-trigger');
        const options = wrapper.querySelector('.custom-options');
        const listItems = options.querySelectorAll('li');

        trigger.addEventListener('click', () => {
            // Close other open dropdowns
            document.querySelectorAll('.custom-select-wrapper.open').forEach(openWrapper => {
                if (openWrapper !== wrapper) {
                    openWrapper.classList.remove('open');
                    openWrapper.querySelector('.custom-options').style.display = 'none'; // Ensure display is set to none
                }
            });

            // Toggle current dropdown
            const isOpen = wrapper.classList.toggle('open');
            options.style.display = isOpen ? "block" : "none";
        });

        listItems.forEach(item => {
            item.addEventListener('click', () => {
                const value = item.dataset.value;
                trigger.querySelector('span').textContent = item.textContent; // Update trigger text
                wrapper.classList.remove('open');
                options.style.display = "none"; // Hide options after selection

                if (wrapper.id === 'year-level-filter-wrapper') {
                    selectedYearLevel = value;
                } else if (wrapper.id === 'section-filter-wrapper') {
                    selectedSection = value;
                }
                updateStudentsTable(); // Update table when filter changes
            });
        });
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', (event) => {
        if (!event.target.closest('.custom-select-wrapper')) {
            document.querySelectorAll('.custom-select-wrapper.open').forEach(openWrapper => {
                openWrapper.classList.remove('open');
                openWrapper.querySelector('.custom-options').style.display = 'none';
            });
        }
    });

    // Add event listeners for sorting table headers
    document.querySelectorAll('#students-table th.sortable').forEach(header => {
        header.addEventListener('click', function () {
            const clickedColumn = this.dataset.column;

            // Determine sort direction
            if (sortColumn === clickedColumn) {
                sortDirection = (sortDirection === 'asc') ? 'desc' : 'asc';
            } else {
                sortColumn = clickedColumn;
                sortDirection = 'asc'; // Default to ascending for new column
            }

            // Update table when sort changes (this will also call updateSortArrows)
            updateStudentsTable();
        });
    });

    // Initial load of the table
    updateStudentsTable();

    // Event listener for the search input
    document.getElementById('student-search-filter').addEventListener('input', function() {
        updateStudentsTable();
    });

    // Modal close button functionality
    closeButton.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    // Close modal when clicking outside of the modal content
    window.addEventListener('click', (event) => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
});
