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

    // Modified fetchFinancialData to accept academicYear and semester
    function fetchFinancialData(academicYear, semester) {
        let trendUrl = '/financial_trends';
        let expensesUrl = '/expenses_by_category';
        let distributionUrl = '/fund_distribution';
        const params = [];

        if (academicYear && academicYear !== 'Academic Year ▼') {
            params.push(`academic_year=${academicYear}`);
        }
        if (semester && semester !== 'Semester ▼') {
            params.push(`semester=${semester}`);
        }

        if (params.length > 0) {
            const queryString = '?' + params.join('&');
            trendUrl += queryString;
            expensesUrl += queryString;
            distributionUrl += queryString;
        }

        console.log("Fetching financial trends from URL:", trendUrl);
        console.log("Fetching expenses by category from URL:", expensesUrl);
        console.log("Fetching fund distribution from URL:", distributionUrl);


        Promise.all([
            fetch(trendUrl).then(res => res.json()),
            fetch(expensesUrl).then(res => res.json()),
            fetch(distributionUrl).then(res => res.json())
        ])
            .then(([trendData, expensesData, distributionData]) => {
                trendChart.data.labels = trendData.labels;
                trendChart.data.datasets[0].data = trendData.data;
                trendChart.update();

                expensesChart.data.labels = expensesData.labels;
                expensesChart.data.datasets[0].data = expensesData.data;
                expensesChart.update();

                distributionChart.data.labels = distributionData.labels;
                distributionChart.data.datasets[0].data = distributionData.data;
                distributionChart.update();
            })
            .catch(error => {
                console.error('Error fetching financial data:', error);
            });
    }

    initializeCharts();
    // Initial fetch for financial data with default filters
    const initialAcademicYear = getCalculatedCurrentAcademicYear();
    const initialSemester = semesterFilterDropdown.value; // Get default semester value
    fetchFinancialData(initialAcademicYear, initialSemester);


    // --- Fetch Total Members ---
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

    // --- Fetch Total Collected Fees ---
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

    // --- Fill Academic Year Stat Card and Set Dropdown Default ---
    function displayCurrentAcademicYear() {
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

        const currentAcademicYearText = `${startYear}-${endYear}`;
        academicYearValue.textContent = currentAcademicYearText; // Set initial stat card value

        const startYearForDropdown = 2022;
        const endYearForDropdown = endYear + 4;
        let optionsHTML = '';
        for (let year = startYearForDropdown; year <= endYearForDropdown; year++) {
            const yearPair = `${year}-${year + 1}`;
            optionsHTML += `<option value="${yearPair}">${yearPair}</option>`;
        }
        academicYearFilterDropdown.innerHTML = optionsHTML;
        academicYearFilterDropdown.value = currentAcademicYearText;
    }

    displayCurrentAcademicYear();

    // --- Fetch Outstanding Dues Amount ---
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

                outstandingDuesValue.textContent = `₱${totalOutstandingAmount.toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                })}`;
                console.log(
                    `Displayed outstanding dues for AY: ${academicYear}, Semester: ${semester}: ₱${totalOutstandingAmount.toFixed(2)}`
                );

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
            amountPaidCell.textContent = `₱${item.total_paid}`;
        });
    }

    function fetchMembershipData(academicYear = null, semester = null) {
        let url = '/admin/individual_members/';
        const params = [];

        let effectiveAcademicYear = academicYear;
        if (!effectiveAcademicYear || effectiveAcademicYear === 'Academic Year ▼') {
            effectiveAcademicYear = getCalculatedCurrentAcademicYear();
            if (academicYearSelect.value !== effectiveAcademicYear) {
                academicYearSelect.value = effectiveAcademicYear;
            }
        }
        params.push(`academic_year=${effectiveAcademicYear}`);

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

    // --- Initial loads ---
    // The initialAcademicYear and initialSemester are already correctly set by displayCurrentAcademicYear()
    // and the default value of the semester dropdown.
    // We just need to make sure all data fetching functions are called with these values.
    const currentAcademicYear = academicYearFilterDropdown.value;
    const currentSemester = semesterFilterDropdown.value;

    fetchMembershipData(currentAcademicYear, currentSemester);
    fetchOutstandingDuesAmount(currentAcademicYear, currentSemester);
    fetchTotalCollectedFees(currentAcademicYear, currentSemester);
    fetchTotalMembers(currentAcademicYear, currentSemester);
    fetchFinancialData(currentAcademicYear, currentSemester); // Added this line

    // --- Event listeners for filter changes ---
    academicYearSelect.addEventListener('change', function () {
        const selectedAcademicYear = this.value;
        const selectedSemester = semesterSelect.value;

        // --- ADDED LINE: Update the Academic Year stat card ---
        academicYearValue.textContent = selectedAcademicYear;

        fetchMembershipData(selectedAcademicYear, selectedSemester);
        fetchOutstandingDuesAmount(selectedAcademicYear, selectedSemester);
        fetchTotalCollectedFees(selectedAcademicYear, selectedSemester);
        fetchTotalMembers(selectedAcademicYear, selectedSemester);
        fetchFinancialData(selectedAcademicYear, selectedSemester); // Added this line
    });

    semesterSelect.addEventListener('change', function () {
        const selectedAcademicYear = academicYearSelect.value;
        const selectedSemester = this.value;

        fetchMembershipData(selectedAcademicYear, selectedSemester);
        fetchOutstandingDuesAmount(selectedAcademicYear, selectedSemester);
        fetchTotalCollectedFees(selectedAcademicYear, selectedSemester);
        fetchTotalMembers(selectedAcademicYear, selectedSemester);
        fetchFinancialData(selectedAcademicYear, selectedSemester); // Added this line
    });

    // --- Custom dropdown logic ---
    document.querySelectorAll('.filter-select').forEach(select => {
        const valueDisplay = select.querySelector('.filter-select-value');
        const optionsContainer = document.createElement('ul');
        optionsContainer.classList.add('filter-select-options');
        select.appendChild(optionsContainer);

        const originalSelect = select.querySelector('select');

        const populateCustomDropdown = () => {
            optionsContainer.innerHTML = '';
            Array.from(originalSelect.options).forEach((option) => {
                const li = document.createElement('li');
                li.textContent = option.textContent;
                li.dataset.value = option.value;
                optionsContainer.appendChild(li);

                if (originalSelect.value === option.value) {
                    valueDisplay.textContent = option.textContent;
                }

                li.addEventListener('click', function (event) {
                    valueDisplay.textContent = this.textContent;
                    originalSelect.value = this.dataset.value;
                    originalSelect.dispatchEvent(new Event('change'));
                    select.classList.remove('open');
                    optionsContainer.style.maxHeight = null;
                    event.stopPropagation();
                });
            });
        };

        populateCustomDropdown();

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