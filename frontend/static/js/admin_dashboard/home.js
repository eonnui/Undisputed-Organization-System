document.addEventListener('DOMContentLoaded', function() {
    const trendCtx = document.getElementById('trendChart').getContext('2d');
    const expensesCtx = document.getElementById('expensesChart').getContext('2d');
    const distributionCtx = document.getElementById('distributionChart').getContext('2d');
    const totalMembersValue = document.querySelector('.stat-card:first-child .stat-value');
    const totalCollectedValue = document.querySelector('.stat-card:nth-child(2) .stat-value');
    const academicYearValue = document.querySelector('.stat-card:nth-child(3) .stat-value');
    const academicYearFilterDropdown = document.getElementById('academic-year-filter');
    const semesterFilterDropdown = document.getElementById('semester-filter');
    const outstandingDuesValue = document.querySelector('.stat-card:nth-child(4) .stat-value');

    let trendChart, expensesChart, distributionChart;

    function initializeCharts() {
        // Destroy existing chart instances before creating new ones to prevent memory leaks and rendering issues
        if (trendChart) trendChart.destroy();
        if (expensesChart) expensesChart.destroy();
        if (distributionChart) distributionChart.destroy();

        // Initialize the trend chart for displaying multiple datasets (Total and per Academic Year)
        trendChart = new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: [],        // X-axis labels (months)
                datasets: []       // Array of datasets for different lines
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true, // Enable legend to show different academic years
                        position: 'top', // Position legend at the top of the chart
                        labels: {
                            font: {
                                size: 14 // Font size for legend labels
                            },
                            boxWidth: 20, // Width of the color box in the legend
                            padding: 15 // Padding between legend items
                        }
                    },
                    tooltip: {
                        mode: 'index', // Show tooltips for all datasets at the hovered index
                        intersect: false, // Tooltip shows even if mouse is not directly on a point
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                // Format the value as currency (Philippine Peso) with no decimal places
                                if (context.raw !== null) {
                                    label += '₱' + context.raw.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true, // Start Y-axis from zero
                        ticks: {
                            callback: function (value) {
                                if (value === 0) {
                                    return '₱0';
                                }
                                return '₱' + value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
                            },
                            font: {
                                size: 14
                            }
                        },
                        grid: {
                            color: '#e0e0e0', // Light grey grid lines
                            borderDash: [5, 5], // Dashed grid lines
                        }
                    },
                    x: {
                        grid: {
                            display: false, // Hide X-axis grid lines
                        },
                        ticks: {
                            font: {
                                size: 14
                            }
                        }
                    }
                },
                elements: {
                    line: {
                        shadowColor: 'rgba(0, 0, 0, 0.1)', // Soft shadow for lines
                        shadowBlur: 10,
                        shadowWidth: 3,
                    },
                    point: {
                        shadowColor: 'rgba(0, 0, 0, 0.2)', // Soft shadow for points
                        shadowBlur: 7,
                        shadowWidth: 2,
                    }
                }
            }
        });

        // Initialize the expenses bar chart
        expensesChart = new Chart(expensesCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: '#4285F4', // Blue color for bars
                    borderRadius: 8, // Rounded corners for bars
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false // Hide legend for single dataset
                    },
                    tooltip: { // Tooltip configuration for expenses chart
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.raw !== null) {
                                    label += '₱' + context.raw.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (value) {
                                if (value === 0) {
                                    return '₱0';
                                }
                                return '₱' + value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
                            },
                            font: {
                                size: 12
                            }
                        },
                        grid: {
                            color: '#e0e0e0',
                            borderDash: [3, 3],
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: {
                                size: 12
                            }
                        }
                    }
                },
                BarThickness: 20, // Width of the bars
            }
        });

        // Initialize the fund distribution doughnut chart
        distributionChart = new Chart(distributionCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [ // Colors for doughnut segments
                        '#4285F4',
                        '#A4C2F4',
                        '#D2E3FC'
                    ],
                    borderWidth: 0,
                    hoverOffset: 10, // Offset on hover
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '60%', // Size of the center cutout
                plugins: {
                    legend: {
                        position: 'bottom', // Position legend below the chart
                        labels: {
                            padding: 15,
                            boxWidth: 12,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: { // Tooltip configuration for doughnut chart
                        callbacks: {
                            label: function(context) {
                                let label = context.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.raw !== null) {
                                    label += '₱' + context.raw.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
                                }
                                return label;
                            }
                        }
                    }
                },
                animation: {
                    animateRotate: true, // Rotate animation on load
                    animateScale: true // Scale animation on load
                }
            }
        });
    }

    /**
     * Fetches financial data for trends, expenses, and distribution based on selected filters.
     * @param {string} academicYear - The selected academic year filter.
     * @param {string} semester - The selected semester filter.
     */
    function fetchFinancialData(academicYear, semester) {
        let trendUrl = '/financial_trends';
        let expensesUrl = '/expenses_by_category';
        let distributionUrl = '/fund_distribution';
        const params = [];

        // Add academic year to URL parameters if selected
        if (academicYear && academicYear !== 'Academic Year ▼') {
            params.push(`academic_year=${academicYear}`);
        }
        // Add semester to URL parameters if selected
        if (semester && semester !== 'Semester ▼') {
            params.push(`semester=${semester}`);
        }

        // Construct query string for all URLs
        if (params.length > 0) {
            const queryString = '?' + params.join('&');
            trendUrl += queryString;
            expensesUrl += queryString;
            distributionUrl += queryString;
        }

        console.log("Fetching financial trends from URL:", trendUrl);
        console.log("Fetching expenses by category from URL:", expensesUrl);
        console.log("Fetching fund distribution from URL:", distributionUrl);

        // Fetch data from all three endpoints concurrently
        Promise.all([
            fetch(trendUrl).then(res => res.json()),
            fetch(expensesUrl).then(res => res.json()),
            fetch(distributionUrl).then(res => res.json())
        ])
            .then(([trendData, expensesData, distributionData]) => {
                // Update trendChart with the new dataset structure (multiple lines)
                trendChart.data.labels = trendData.labels;
                trendChart.data.datasets = trendData.datasets; // Assign the array of datasets
                trendChart.update();

                // Update expensesChart
                expensesChart.data.labels = expensesData.labels;
                expensesChart.data.datasets[0].data = expensesData.data;
                expensesChart.update();

                // Update distributionChart
                distributionChart.data.labels = distributionData.labels;
                distributionChart.data.datasets[0].data = distributionData.data;
                distributionChart.update();
            })
            .catch(error => {
                console.error('Error fetching financial data:', error);
            });
    }

    // Initialize all charts on DOM content loaded
    initializeCharts();
    
    // Get initial academic year and semester values for the first data fetch
    const initialAcademicYear = getCalculatedCurrentAcademicYear();
    const initialSemester = semesterFilterDropdown.value; // Get default semester value
    fetchFinancialData(initialAcademicYear, initialSemester);


    /**
     * Fetches and displays total members based on selected academic year and semester.
     * @param {string} academicYear - The selected academic year filter.
     * @param {string} semester - The selected semester filter.
     */
    function fetchTotalMembers(academicYear, semester) {
        let url = '/admin/membership/';
        const params = [];

        if (academicYear && academicYear !== 'Academic Year ▼') {
            params.push(`academic_year=${academicYear}`);
        }
        if (semester && semester !== 'Semester ▼') {
            params.push(`semester=${semester}`);
        }

        if (params.length > 0) {
            url += '?' + params.join('&');
        }

        console.log("Fetching total members from URL:", url);

        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                let totalMemberCount = 0;
                if (Array.isArray(data)) {
                    data.forEach(section => {
                        if (section.section_users_count !== undefined) {
                            totalMemberCount += section.section_users_count;
                        } else {
                            console.warn("Section in /admin/membership/ response missing 'section_users_count' for members for filtered data:", section);
                        }
                    });
                }
                else if (typeof data === 'object' && data.total_members_count !== undefined) {
                    totalMemberCount = data.total_members_count;
                } else {
                    console.warn("Unexpected data format for total members from /admin/membership/ (expected array of sections or object with total_members_count):", data);
                }

                totalMembersValue.textContent = totalMemberCount;
            })
            .catch(error => {
                console.error('Error fetching membership data for total members:', error);
                totalMembersValue.textContent = 'Error';
            });
    }

    /**
     * Fetches and displays total collected fees based on selected academic year and semester.
     * @param {string} academicYear - The selected academic year filter.
     * @param {string} semester - The selected semester filter.
     */
    function fetchTotalCollectedFees(academicYear, semester) {
        let url = '/admin/membership/';
        const params = [];

        if (academicYear && academicYear !== 'Academic Year ▼') {
            params.push(`academic_year=${academicYear}`);
        }
        if (semester && semester !== 'Semester ▼') {
            params.push(`semester=${semester}`);
        }

        if (params.length > 0) {
            url += '?' + params.join('&');
        }

        console.log("Fetching total collected fees from URL:", url);

        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                let totalCollected = 0;
                if (Array.isArray(data)) {
                    data.forEach(section => {
                        if (section.total_paid !== undefined) {
                            totalCollected += section.total_paid;
                        } else {
                            console.warn("Section in /admin/membership/ response missing 'total_paid' for collected fees for filtered data:", section);
                        }
                    });
                }
                else if (typeof data === 'object' && data.total_collected !== undefined) {
                    totalCollected = data.total_collected;
                }
                else {
                    console.warn("Unexpected data format for total collected fees from /admin/membership/ (expected array of sections or object with total_collected):", data);
                }
                totalCollectedValue.textContent = totalCollected.toLocaleString('en-US', { style: 'currency', currency: 'PHP' });
            })
            .catch(error => {
                console.error('Error fetching membership data for total collected fees:', error);
                totalCollectedValue.textContent = 'Error';
            });
    }

    /**
     * Calculates and displays the current academic year in the stat card and sets the dropdown default.
     */
    function displayCurrentAcademicYear() {
        const today = new Date();
        const currentYear = today.getFullYear();
        const currentMonth = today.getMonth(); // 0-indexed

        const academicYearStartMonth = 7; // August (month index 7)

        let startYear, endYear;

        if (currentMonth >= academicYearStartMonth) {
            startYear = currentYear;
            endYear = currentYear + 1;
        } else {
            startYear = currentYear - 1;
            endYear = currentYear;
        }

        const currentAcademicYearText = `${startYear}-${endYear}`;
        academicYearValue.textContent = currentAcademicYearText; // Set initial stat card value

        // Populate academic year filter dropdown with a range of years
        const startYearForDropdown = 2022; // Starting year for dropdown options
        const endYearForDropdown = endYear + 4; // Extend dropdown options 4 years into the future
        let optionsHTML = '';
        for (let year = startYearForDropdown; year <= endYearForDropdown; year++) {
            const yearPair = `${year}-${year + 1}`;
            optionsHTML += `<option value="${yearPair}">${yearPair}</option>`;
        }
        academicYearFilterDropdown.innerHTML = optionsHTML;
        academicYearFilterDropdown.value = currentAcademicYearText; // Set dropdown to current academic year
    }

    displayCurrentAcademicYear();

    /**
     * Fetches and displays the total outstanding dues amount.
     * @param {string} academicYear - The selected academic year filter.
     * @param {string} semester - The selected semester filter.
     */
    function fetchOutstandingDuesAmount(academicYear, semester) {
        console.log(`Fetching outstanding dues amount for Academic Year: ${academicYear}, Semester: ${semester}`);

        let url = `/admin/outstanding_dues/`;
        const params = [];

        if (academicYear && academicYear !== 'Academic Year ▼') {
            params.push(`academic_year=${academicYear}`);
        }
        if (semester && semester !== 'Semester ▼') {
            params.push(`semester=${semester}`);
        }

        if (params.length > 0) {
            url += '?' + params.join('&');
        }

        console.log("Outstanding Dues URL:", url);

        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                let totalOutstandingAmount = 0;

                console.log("Data received from /admin/outstanding_dues/:", data);

                if (Array.isArray(data) && data.length > 0 && data[0] && data[0].total_outstanding_amount !== undefined) {
                    totalOutstandingAmount = data[0].total_outstanding_amount;
                } else if (typeof data === 'object' && data.total_outstanding_amount !== undefined) {
                    totalOutstandingAmount = data.total_outstanding_amount;
                }
                else {
                    totalOutstandingAmount = 0;
                    console.warn("No outstanding dues found or unexpected data format for /admin/outstanding_dues/:", data);
                }

                // Format and display the outstanding dues amount
                outstandingDuesValue.textContent = `₱${totalOutstandingAmount.toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                })}`;
                console.log(
                    `Displayed outstanding dues for AY: ${academicYear}, Semester: ${semester}: ₱${totalOutstandingAmount.toFixed(2)}`
                );

                // Add or update link to unpaid payments page
                const statCard = document.querySelector('.stat-card:nth-child(4)');
                const unpaidLinkHref = `/Admin/payments`;
                if (!statCard.querySelector('.card-link')) {
                    const cardLink = document.createElement('a');
                    cardLink.href = unpaidLinkHref;
                    cardLink.className = 'card-link';
                    statCard.appendChild(cardLink);
                } else {
                    statCard.querySelector('.card-link').href = unpaidLinkHref;
                }
            })
            .catch(error => {
                console.error('Error fetching outstanding dues data:', error);
                outstandingDuesValue.textContent = 'Error';
                console.log(`Displaying error for outstanding dues.`);
            });
    }

    /**
     * Calculates the current academic year based on the current date.
     * @returns {string} The current academic year in "YYYY-YYYY" format.
     */
    function getCalculatedCurrentAcademicYear() {
        const today = new Date();
        const currentYear = today.getFullYear();
        const currentMonth = today.getMonth(); // 0-indexed

        const academicYearStartMonth = 7; // August

        let startYear, endYear;
        if (currentMonth >= academicYearStartMonth) {
            startYear = currentYear;
            endYear = currentYear + 1;
        } else {
            startYear = currentYear - 1;
            endYear = currentYear;
        }
        return `${startYear}-${endYear}`;
    }

    // --- Membership Fee Tracker Logic ---
    const academicYearSelect = document.getElementById('academic-year-filter');
    const semesterSelect = document.getElementById('semester-filter');
    const membershipTableBody = document.querySelector('.tracker-section table tbody');

    /**
     * Populates the membership fee tracker table with data.
     * @param {Array<Object>} data - Array of member data.
     */
    function populateMembershipTable(data) {
        membershipTableBody.innerHTML = ''; // Clear existing rows
        if (data.length === 0) {
            membershipTableBody.innerHTML = '<tr><td colspan="3" style="text-align: center;">No data available for the selected filters.</td></tr>';
            return;
        }
        data.forEach(item => {
            const row = membershipTableBody.insertRow();
            const nameCell = row.insertCell();
            const yearSecCell = row.insertCell();
            const amountPaidCell = row.insertCell();

            nameCell.textContent = `${item.first_name} ${item.last_name}`;
            yearSecCell.textContent = `${item.year_level} - ${item.section}`;
            amountPaidCell.textContent = `₱${item.total_paid}`;
        });
    }

    /**
     * Fetches membership data for the tracker table.
     * @param {string} academicYear - The academic year filter.
     * @param {string} semester - The semester filter.
     */
    function fetchMembershipData(academicYear = null, semester = null) {
        let url = '/admin/individual_members/';
        const params = [];

        // Determine effective academic year for the fetch
        let effectiveAcademicYear = academicYear;
        if (!effectiveAcademicYear || effectiveAcademicYear === 'Academic Year ▼') {
            effectiveAcademicYear = getCalculatedCurrentAcademicYear();
            // Update the dropdown value if it's not already set to the calculated current AY
            if (academicYearSelect.value !== effectiveAcademicYear) {
                academicYearSelect.value = effectiveAcademicYear;
            }
        }
        params.push(`academic_year=${effectiveAcademicYear}`);

        // Determine effective semester for the fetch
        let effectiveSemester = semesterSelect.value;
        if (effectiveSemester && effectiveSemester !== 'Semester ▼') {
            params.push(`semester=${effectiveSemester}`);
        }

        url += '?' + params.join('&');
        console.log("Fetching membership data for tracker from URL:", url);

        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                populateMembershipTable(data);
            })
            .catch(error => {
                console.error('Error fetching membership data for tracker:', error);
                membershipTableBody.innerHTML = '<tr><td colspan="3">Error loading data.</td></tr>';
            });
    }

    // --- Initial loads of all data when the page loads ---
    // Get the current academic year and semester values to use for initial data fetches
    const currentAcademicYear = academicYearFilterDropdown.value;
    const currentSemester = semesterFilterDropdown.value;

    fetchMembershipData(currentAcademicYear, currentSemester);
    fetchOutstandingDuesAmount(currentAcademicYear, currentSemester);
    fetchTotalCollectedFees(currentAcademicYear, currentSemester);
    fetchTotalMembers(currentAcademicYear, currentSemester);
    fetchFinancialData(currentAcademicYear, currentSemester);

    // --- Event listeners for filter changes ---
    // When academic year filter changes, re-fetch all relevant data
    academicYearSelect.addEventListener('change', function () {
        const selectedAcademicYear = this.value;
        const selectedSemester = semesterSelect.value;

        // Update the Academic Year stat card with the newly selected year
        academicYearValue.textContent = selectedAcademicYear;

        fetchMembershipData(selectedAcademicYear, selectedSemester);
        fetchOutstandingDuesAmount(selectedAcademicYear, selectedSemester);
        fetchTotalCollectedFees(selectedAcademicYear, selectedSemester);
        fetchTotalMembers(selectedAcademicYear, selectedSemester);
        initializeCharts(); // Re-initialize charts to clear old datasets and apply new data
        fetchFinancialData(selectedAcademicYear, selectedSemester);
    });

    // When semester filter changes, re-fetch all relevant data
    semesterSelect.addEventListener('change', function () {
        const selectedAcademicYear = academicYearSelect.value;
        const selectedSemester = this.value;

        fetchMembershipData(selectedAcademicYear, selectedSemester);
        fetchOutstandingDuesAmount(selectedAcademicYear, selectedSemester);
        fetchTotalCollectedFees(selectedAcademicYear, selectedSemester);
        fetchTotalMembers(selectedAcademicYear, selectedSemester);
        initializeCharts(); // Re-initialize charts to clear old datasets and apply new data
        fetchFinancialData(selectedAcademicYear, selectedSemester);
    });

    // --- Custom dropdown logic for better UI interaction ---
    document.querySelectorAll('.filter-select').forEach(select => {
        const valueDisplay = select.querySelector('.filter-select-value');
        const optionsContainer = document.createElement('ul');
        optionsContainer.classList.add('filter-select-options');
        select.appendChild(optionsContainer);

        const originalSelect = select.querySelector('select');

        /**
         * Populates the custom dropdown options based on the original select element.
         */
        const populateCustomDropdown = () => {
            optionsContainer.innerHTML = ''; // Clear existing custom options
            Array.from(originalSelect.options).forEach((option) => {
                const li = document.createElement('li');
                li.textContent = option.textContent;
                li.dataset.value = option.value;
                optionsContainer.appendChild(li);

                // Set initial display value for the custom dropdown
                if (originalSelect.value === option.value) {
                    valueDisplay.textContent = option.textContent;
                }

                // Add click listener to custom options
                li.addEventListener('click', function (event) {
                    valueDisplay.textContent = this.textContent;
                    originalSelect.value = this.dataset.value;
                    originalSelect.dispatchEvent(new Event('change')); // Trigger change event on original select
                    select.classList.remove('open'); // Close the custom dropdown
                    optionsContainer.style.maxHeight = null; // Reset max height
                    event.stopPropagation(); // Prevent event bubbling
                });
            });
        };

        populateCustomDropdown(); // Initial population

        // Use MutationObserver to re-populate custom dropdown if original select options change
        const observer = new MutationObserver(populateCustomDropdown);
        observer.observe(originalSelect, { childList: true });


        // Toggle custom dropdown visibility on click of the display value
        valueDisplay.addEventListener('click', function (event) {
            select.classList.toggle('open');
            optionsContainer.style.maxHeight = select.classList.contains('open') ? '200px' : null; // Limit height for scrolling
            event.stopPropagation(); // Prevent event bubbling
        });

        // Close custom dropdown if clicked outside
        document.addEventListener('click', function (event) {
            if (!select.contains(event.target)) {
                select.classList.remove('open');
                optionsContainer.style.maxHeight = null;
            }
        });
    });
});
