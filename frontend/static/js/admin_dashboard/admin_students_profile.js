let selectedYearLevel = "";
let selectedSection = "";
let sortColumn = "last_name"; // Default sort column for better initial view
let sortDirection = 'asc'; // Default sort direction

document.addEventListener('DOMContentLoaded', function() {
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

            // Remove existing sort indicators from all headers
            document.querySelectorAll('#students-table th.sortable').forEach(th => {
                th.classList.remove('asc', 'desc');
            });

            // Add sort indicator to the clicked header
            this.classList.add(sortDirection);

            updateStudentsTable(); // Update table when sort changes
        });
    });

    // Initial load of the table
    updateStudentsTable();

    // Event listener for the search input
    document.getElementById('student-search-filter').addEventListener('input', function() {
        updateStudentsTable();
    });

    // Modal close button functionality
    const modal = document.getElementById('studentProfileModal');
    const closeButton = modal.querySelector('.close-button');

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

    } catch (error) {
        console.error("Failed to fetch student data:", error);
        displayMessageBox("Error loading student data. Please try again.", "error"); // Use the message box for errors
        tableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: red;">Error loading student data.</td></tr>`;
    }
}

// New function to fetch student profile and show modal
async function fetchStudentProfileAndShowModal(studentNumber) {
    const modal = document.getElementById('studentProfileModal');
    const modalStudentName = document.getElementById('modalStudentName');
    const modalStudentNumber = document.getElementById('modalStudentNumber');
    const modalEmail = document.getElementById('modalEmail');
    const modalYearLevel = document.getElementById('modalYearLevel');
    const modalSection = document.getElementById('modalSection');
    const modalCampus = document.getElementById('modalCampus');
    const modalCourse = document.getElementById('modalCourse');
    const modalSchoolYear = document.getElementById('modalSchoolYear');
    const modalAddress = document.getElementById('modalAddress');
    const modalBirthdate = document.getElementById('modalBirthdate');
    const modalSex = document.getElementById('modalSex');
    const modalGuardianName = document.getElementById('modalGuardianName');
    const modalGuardianContact = document.getElementById('modalGuardianContact');

    try {
        const response = await fetch(`/admin/students/profile/${studentNumber}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const student = await response.json();

        // Populate modal with student data
        modalStudentName.textContent = `${student.first_name} ${student.last_name}`;
        modalStudentNumber.textContent = student.student_number;
        modalEmail.textContent = student.email;
        modalYearLevel.textContent = student.year_level || 'N/A';
        modalSection.textContent = student.section || 'N/A';
        modalCampus.textContent = student.campus || 'N/A';
        modalCourse.textContent = student.course || 'N/A';
        modalSchoolYear.textContent = student.school_year || 'N/A';
        modalAddress.textContent = student.address || 'N/A';
        modalBirthdate.textContent = student.birthdate || 'N/A';
        modalSex.textContent = student.sex || 'N/A';
        modalGuardianName.textContent = student.guardian_name || 'N/A';
        modalGuardianContact.textContent = student.guardian_contact || 'N/A';


        modal.style.display = 'block'; // Show the modal

    } catch (error) {
        console.error("Failed to fetch student profile:", error);
        displayMessageBox("Error loading student profile. Please try again.", "error");
    }
}


// Function to display messages (re-used and slightly enhanced)
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