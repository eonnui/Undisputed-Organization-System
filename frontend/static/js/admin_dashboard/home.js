document.addEventListener('DOMContentLoaded', function() {
    const trendCtx = document.getElementById('trendChart').getContext('2d');
    const expensesCtx = document.getElementById('expensesChart').getContext('2d');
    const distributionCtx = document.getElementById('distributionChart').getContext('2d');
    const totalMembersValue = document.querySelector('.stat-card:first-child .stat-value');
    const totalCollectedValue = document.querySelector('.stat-card:nth-child(2) .stat-value');
    const academicYearValue = document.querySelector('.stat-card:nth-child(3) .stat-value'); 
    const academicYearFilterDropdown = document.getElementById('academic-year-filter');
    const semesterFilterDropdown = document.getElementById('semester-filter');

    let trendChart, expensesChart, distributionChart;

    function initializeCharts() {
        trendChart = new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Collections',
                    data: [],
                    borderColor: '#4285F4',
                    backgroundColor: 'transparent',
                    tension: 0.4,
                    pointBackgroundColor: '#4285F4',
                    borderWidth: 3,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    fill: false,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (value) {
                                return value === 0 ? '0' : value / 1000 + 'k';
                            },
                            font: {
                                size: 14
                            }
                        },
                        grid: {
                            color: '#e0e0e0',
                            borderDash: [5, 5],
                        }
                    },
                    x: {
                        grid: {
                            display: false,
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
                        shadowColor: 'rgba(0, 0, 0, 0.1)',
                        shadowBlur: 10,
                        shadowWidth: 3,
                    },
                    point: {
                        shadowColor: 'rgba(0, 0, 0, 0.2)',
                        shadowBlur: 7,
                        shadowWidth: 2,
                    }
                }
            }
        });

        expensesChart = new Chart(expensesCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: '#4285F4',
                    borderRadius: 8,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
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
                BarThickness: 20,
            }
        });

        distributionChart = new Chart(distributionCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        '#4285F4',
                        '#A4C2F4',
                        '#D2E3FC'
                    ],
                    borderWidth: 0,
                    hoverOffset: 10,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '60%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            boxWidth: 12,
                            font: {
                                size: 12
                            }
                        }
                    }
                },
                animation: {
                    animateRotate: true,
                    animateScale: true
                }
            }
        });
    }

    function fetchFinancialData() {
        Promise.all([
            fetch('/financial_trends').then(res => res.json()),
            fetch('/expenses_by_category').then(res => res.json()),
            fetch('/fund_distribution').then(res => res.json())
        ])
            .then(([trendData, expensesData, distributionData]) => {
                // Update Trend Chart
                trendChart.data.labels = trendData.labels;
                trendChart.data.datasets[0].data = trendData.data;
                trendChart.update();

                // Update Expenses Chart
                expensesChart.data.labels = expensesData.labels;
                expensesChart.data.datasets[0].data = expensesData.data;
                expensesChart.update();

                // Update Distribution Chart
                distributionChart.data.labels = distributionData.labels;
                distributionChart.data.datasets[0].data = distributionData.data;
                distributionChart.update();
            })
            .catch(error => {
                console.error('Error fetching financial data:', error);
            });
    }

    // Initialize charts
    initializeCharts();

    // Fetch initial data and update charts
    fetchFinancialData();

    // --- Fetch Total Members using /admin/membership/ ---
    function fetchTotalMembers() {
        // This function doesn't seem to have filters for AY/Semester in its current API call.
        // If it should, you'd extend this function similarly to fetchTotalCollectedFees.
        fetch('/admin/membership/') 
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                let totalMemberCount = 0;
                data.forEach(section => {
                    totalMemberCount += section.section_users_count;
                });
                totalMembersValue.textContent = totalMemberCount;
            })
            .catch(error => {
                console.error('Error fetching membership data for total:', error);
                totalMembersValue.textContent = 'Error';
            });
    }

    // Fetch total members on page load
    fetchTotalMembers();

    // --- Fetch Total Collected Fees using /admin/membership/ ---
    // MODIFIED: Now accepts academicYear and semester parameters
    function fetchTotalCollectedFees(academicYear, semester) {
        let url = '/admin/membership/'; // Assuming this endpoint can take filters
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

        console.log("Fetching total collected fees from URL:", url); // Debugging

        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                let totalCollected = 0;
                // Assuming the backend returns an array of sections, each with a total_paid
                // If it returns a single total, you'd adjust this logic.
                if (Array.isArray(data)) {
                    data.forEach(section => {
                        totalCollected += section.total_paid;
                    });
                } else if (typeof data === 'object' && data.total_collected !== undefined) {
                    // If your API provides a direct total, use this:
                    totalCollected = data.total_collected;
                }
                // Default to 0 if data is not as expected or empty
                totalCollectedValue.textContent = totalCollected.toLocaleString('en-US', { style: 'currency', currency: 'PHP' });
            })
            .catch(error => {
                console.error('Error fetching membership data for total collected fees:', error);
                totalCollectedValue.textContent = 'Error';
            });
    }

    // --- Fill Academic Year Stat Card and Set Dropdown Default ---
    function displayCurrentAcademicYear() {
        const today = new Date();
        const currentYear = today.getFullYear();
        const currentMonth = today.getMonth(); // 0-indexed: January is 0, June is 5, July is 6, August is 7

        // As confirmed: If 2024-2025 is current in June 2025, the new academic year (2025-2026) starts later.
        // Let's assume the new academic year starts in August (month 7).
        const academicYearStartMonth = 7; // August

        let startYear, endYear;

        if (currentMonth >= academicYearStartMonth) { 
            // If current month is August (7) or later, the academic year started in currentYear.
            // E.g., Aug 2025 -> 2025-2026
            startYear = currentYear;
            endYear = currentYear + 1;
        } else { 
            // If current month is before August (Jan-July), the academic year started in previousYear.
            // E.g., June 2025 -> 2024-2025 (as currentYear - 1 = 2024)
            startYear = currentYear - 1;
            endYear = currentYear;
        }

        const currentAcademicYearText = `${startYear}-${endYear}`;
        academicYearValue.textContent = currentAcademicYearText;

        // Populate the Academic Year dropdown
        const startYearForDropdown = 2022; // Starting from 2022-2023
        const endYearForDropdown = endYear + 4; // Extend a few years into the future
        let optionsHTML = ''; 
        for (let year = startYearForDropdown; year <= endYearForDropdown; year++) {
            const yearPair = `${year}-${year + 1}`;
            optionsHTML += `<option value="${yearPair}">${yearPair}</option>`;
        }
        academicYearFilterDropdown.innerHTML = optionsHTML;

        // Set the academic year filter dropdown to the current academic year
        academicYearFilterDropdown.value = currentAcademicYearText;
    }

    // Display the current academic year on load
    displayCurrentAcademicYear();

    function fetchOutstandingDuesAmount() {
        // Get current academic year from the stat card (which is already set to current AY)
        const currentAcademicYear = academicYearValue.textContent; 

        // Use the current value of the semester filter dropdown directly (no client-side determination)
        const currentSemester = semesterFilterDropdown.value;

        const outstandingDuesValue = document.querySelector('.stat-card:nth-child(4) .stat-value');

        console.log(`Fetching outstanding dues amount for Academic Year: ${currentAcademicYear}, Semester: ${currentSemester}`);

        // Only send semester parameter if it's not the default "Semester ▼"
        let url = `/admin/outstanding_dues/?academic_year=${currentAcademicYear}`;
        if (currentSemester && currentSemester !== 'Semester ▼') {
            url += `&semester=${currentSemester}`;
        }

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

                // The backend should return data in a consistent format, 
                // e.g., an array with one object containing total_outstanding_amount
                if (Array.isArray(data) && data.length > 0 && data[0].total_outstanding_amount !== undefined) {
                    totalOutstandingAmount = data[0].total_outstanding_amount;
                    console.log("Total outstanding amount:", totalOutstandingAmount);
                }
                else {
                    totalOutstandingAmount = 0; // If no data or unexpected format, assume 0
                    console.log("No outstanding dues found or unexpected data format:", data);
                }

                outstandingDuesValue.textContent = `₱${totalOutstandingAmount.toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                })}`;
                console.log(
                    `Displaying total outstanding dues amount for current semester (using filter: ${currentSemester}, AY: ${currentAcademicYear}): ₱${totalOutstandingAmount.toFixed(2)}`
                );
                
                const statCard = document.querySelector('.stat-card:nth-child(4)');
                const unpaidLinkHref = `/Admin/payments`;
                if (!statCard.querySelector('.card-link')) {
                    const cardLink = document.createElement('a');
                    cardLink.href = unpaidLinkHref;
                    cardLink.className = 'card-link';
                    statCard.appendChild(cardLink);
                    console.log(`Added link to view unpaid amounts: ${unpaidLinkHref}`);
                } else {
                    statCard.querySelector('.card-link').href = unpaidLinkHref;
                    console.log(`Updated link to view unpaid amounts: ${unpaidLinkHref}`);
                }
            })
            .catch(error => {
                console.error('Error fetching outstanding dues data:', error);
                outstandingDuesValue.textContent = 'Error';
                console.log(`Displaying error: Error fetching outstanding dues amount.`);
            });
    }

    // Function to get the calculated current academic year (retained for initial calls)
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

    function populateMembershipTable(data) {
        membershipTableBody.innerHTML = '';
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
            amountPaidCell.textContent = item.total_paid;
        });
    }

    function fetchMembershipData(academicYear = null, semester = null) {
        let url = '/admin/individual_members/';
        const params = [];

        // Determine the academic year to use for the fetch
        let effectiveAcademicYear = academicYear;
        if (!effectiveAcademicYear || effectiveAcademicYear === 'Academic Year ▼') {
            effectiveAcademicYear = getCalculatedCurrentAcademicYear();
            // Ensure the actual select element's value is also set for custom dropdown to pick up
            if (academicYearSelect.value !== effectiveAcademicYear) {
                academicYearSelect.value = effectiveAcademicYear;
            }
        }
        params.push(`academic_year=${effectiveAcademicYear}`);

        // Use the semester value directly from the dropdown, don't determine it client-side
        let effectiveSemester = semesterSelect.value; // Get current value from the dropdown
        if (effectiveSemester && effectiveSemester !== 'Semester ▼') {
            params.push(`semester=${effectiveSemester}`);
        }

        url += '?' + params.join('&');
        console.log("Fetching membership data from URL:", url); // Debugging line

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
                console.error('Error fetching membership data:', error);
                membershipTableBody.innerHTML = '<tr><td colspan="3">Error loading data.</td></tr>';
            });
    }

    // Initial loads for tracker and stat cards
    const initialAcademicYear = getCalculatedCurrentAcademicYear();
    const initialSemester = semesterFilterDropdown.value; // Get the initially set semester filter value

    fetchMembershipData(initialAcademicYear, initialSemester);
    fetchOutstandingDuesAmount(); 
    // MODIFIED: Call fetchTotalCollectedFees with initial values
    fetchTotalCollectedFees(initialAcademicYear, initialSemester);

    // Event listeners for filter changes
    academicYearSelect.addEventListener('change', function () {
        const selectedAcademicYear = this.value;
        const selectedSemester = semesterSelect.value; 
        fetchMembershipData(selectedAcademicYear, selectedSemester);
        fetchOutstandingDuesAmount(); 
        // MODIFIED: Re-fetch total collected fees when filters change
        fetchTotalCollectedFees(selectedAcademicYear, selectedSemester);
    });

    semesterSelect.addEventListener('change', function () {
        const selectedAcademicYear = academicYearSelect.value;
        const selectedSemester = this.value;
        fetchMembershipData(selectedAcademicYear, selectedSemester);
        fetchOutstandingDuesAmount(); 
        // MODIFIED: Re-fetch total collected fees when filters change
        fetchTotalCollectedFees(selectedAcademicYear, selectedSemester);
    });
    
    // Custom dropdown logic (ensures it reflects the current academic year/semester correctly)
    document.querySelectorAll('.filter-select').forEach(select => {
        const valueDisplay = select.querySelector('.filter-select-value');
        const optionsContainer = document.createElement('ul');
        optionsContainer.classList.add('filter-select-options');
        select.appendChild(optionsContainer);

        const originalSelect = select.querySelector('select'); // Get the existing select element
        
        // Populate custom dropdown based on the actual select element's options
        const populateCustomDropdown = () => {
            optionsContainer.innerHTML = ''; // Clear existing options
            Array.from(originalSelect.options).forEach((option) => {
                const li = document.createElement('li');
                li.textContent = option.textContent;
                li.dataset.value = option.value;
                optionsContainer.appendChild(li);

                // Set initial display for custom select
                if (originalSelect.value === option.value) { // Use originalSelect.value for comparison
                    valueDisplay.textContent = option.textContent;
                }

                li.addEventListener('click', function () {
                    valueDisplay.textContent = this.textContent;
                    originalSelect.value = this.dataset.value;
                    originalSelect.dispatchEvent(new Event('change')); 
                    select.classList.remove('open');
                    optionsContainer.style.maxHeight = null; 
                });
            });
        };

        // Populate initially
        populateCustomDropdown();

        // Also re-populate if the original select's options change (e.g., from displayCurrentAcademicYear)
        const observer = new MutationObserver(populateCustomDropdown);
        observer.observe(originalSelect, { childList: true });


        valueDisplay.addEventListener('click', function (event) {
            select.classList.toggle('open');
            optionsContainer.style.maxHeight = select.classList.contains('open') ? '200px' : null;
            event.stopPropagation();
        });
        
        document.addEventListener('click', function (event) {
            if (!select.contains(event.target)) {
                select.classList.remove('open');
                optionsContainer.style.maxHeight = null;
            }
        });
    });
});