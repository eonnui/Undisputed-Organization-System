// admin_financial_statement.js

let revenueExpenseChart;
let netIncomeTrendChart;

function toggleView(viewId) {
    const reportCards = document.querySelectorAll('.report-card');
    const toggleButtons = document.querySelectorAll('.report-toggle-button');

    reportCards.forEach(card => {
        card.classList.remove('active');
    });
    toggleButtons.forEach(button => {
        button.classList.remove('active');
    });
    const selectedCard = document.getElementById(viewId);
    if (selectedCard) {
        selectedCard.classList.add('active');
    }
    const selectedButton = Array.from(toggleButtons).find(button =>
        button.dataset.viewId === viewId // Use data-view-id for more robust matching
    );
    if (selectedButton) {
        selectedButton.classList.add('active');
    }

    if (viewId === 'overview' && window.financialData) {
        renderCharts(window.financialData);
    }
    // If you want to re-fetch or re-populate membership data when "Revenues" is clicked
    if (viewId === 'revenues') {
        const currentAcademicYear = academicYearSelect.value || getCalculatedCurrentAcademicYear();
        const currentSemester = semesterSelect.value || ''; // Or '1st Semester' if that's your default
        fetchMembershipData(currentAcademicYear, currentSemester);
    }
}

function renderCharts(data) {
    if (revenueExpenseChart) {
        revenueExpenseChart.destroy();
    }
    if (netIncomeTrendChart) {
        netIncomeTrendChart.destroy();
    }

    const revenueExpenseCtx = document.getElementById('revenue-expense-chart');
    if (revenueExpenseCtx) {
        revenueExpenseChart = new Chart(revenueExpenseCtx, {
            type: 'bar',
            data: {
                // Labels updated to reflect the new definitions
                labels: ['Turnover Money (Total Revenue)', 'Current Academic Year Expenses'], 
                datasets: [{
                    label: 'Year-to-Date (₱)',
                    data: [
                        data.total_revenue_ytd, // This is expected to be 'turnover money from previous years'
                        data.total_expenses_ytd // This is expected to be current AY expenses
                    ],
                    backgroundColor: ['rgba(54, 162, 235, 0.7)', 'rgba(255, 99, 132, 0.7)'],
                    borderColor: ['rgba(54, 162, 235, 1)', 'rgba(255, 99, 132, 1)'],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)',
                            lineWidth: 0.5
                        },
                        ticks: {
                            callback: function(value) {
                                return '₱' + value.toLocaleString();
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: 'rgba(0, 0, 0, 0.8)',
                        borderWidth: 1,
                        animationDuration: 200,
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ₱' + context.parsed.y.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
                            }
                        }
                    }
                },
                animation: {
                    duration: 1000,
                    easing: 'easeInOutQuart'
                }
            }
        });
    }

    const netIncomeCtx = document.getElementById('net-income-trend-chart');
    if (netIncomeCtx) {
        netIncomeTrendChart = new Chart(netIncomeCtx, {
            type: 'line',
            data: {
                labels: data.chart_net_income_labels, 
                datasets: [{
                    // Label updated to reflect the new definition
                    label: 'Net Income (Current AY Membership Fees - Current AY Expenses) (₱)', 
                    data: data.chart_net_income_data,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    borderWidth: 3,
                    fill: true,
                    pointRadius: 6,
                    pointBackgroundColor: 'rgba(75, 192, 192, 1)',
                    pointHoverRadius: 8,
                    pointHoverBackgroundColor: 'rgba(75, 192, 192, 1)',
                    tension: 0.4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)',
                            lineWidth: 0.5
                        },
                        ticks: {
                            callback: function(value) {
                                return '₱' + value.toLocaleString();
                            }
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)',
                            lineWidth: 0.5
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: 'rgba(0, 0, 0, 0.8)',
                        borderWidth: 1,
                        animationDuration: 200,
                        yAlign: 'bottom',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ₱' + context.parsed.y.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
                            }
                        }
                    }
                },
                animation: {
                    duration: 1200,
                    easing: 'easeInOutCubic'
                },
                elements: {
                    line: {
                        capStyle: 'round',
                        joinStyle: 'round',
                    }
                }
            }
        });
    }
}

function populateDashboard(data) {
    // Stat card values - based on NEW definitions
    // Display the full academic year (e.g., "2024-2025")
    document.getElementById('current-year').textContent = data.year; 
    
    // total_revenue_ytd is now 'turnover money from previous years'
    document.getElementById('total-revenue-ytd').textContent = `₱${data.total_revenue_ytd.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    
    // total_expenses_ytd remains expenses for the current academic year
    document.getElementById('total-expenses-ytd').textContent = `₱${data.total_expenses_ytd.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    
    // net_income_ytd is now 'membership fees collected from current academic year' minus current AY expenses
    const netIncomeYTDElement = document.getElementById('net-income-ytd');
    netIncomeYTDElement.textContent = `₱${data.net_income_ytd.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    if (data.net_income_ytd >= 0) {
        netIncomeYTDElement.classList.add('positive');
        netIncomeYTDElement.classList.remove('negative');
    } else {
        netIncomeYTDElement.classList.add('negative');
        netIncomeYTDElement.classList.remove('positive');
    }

    // total_current_balance is now 'turnover money (total_revenue_ytd) + net income (current AY membership fees - expenses)'
    document.getElementById('total-current-balance').textContent = `₱${data.total_current_balance.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

    // Removed redundant elements from here based on previous conversation
    // document.getElementById('balance-turnover').textContent = `₱${data.balance_turnover.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    // document.getElementById('total-funds-available').textContent = `₱${data.total_funds_available.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    
    document.getElementById('reporting-date').textContent = data.reporting_date;

    // Overview metrics - these might need adjustment based on how the backend provides "top revenue source"
    // if 'revenue' now strictly means 'turnover'. Assuming it still refers to actual incoming money.
    document.getElementById('top-revenue-source').textContent = `${data.top_revenue_source_name} (₱${data.top_revenue_source_amount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})})`;
    document.getElementById('largest-expense').textContent = `${data.largest_expense_category} (₱${data.largest_expense_amount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})})`;
    document.getElementById('profit-margin-ytd').textContent = `${data.profit_margin_ytd.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}%`;

    // Revenues Breakdown Table
    const revenuesBreakdownBody = document.getElementById('revenues-breakdown-body');
    revenuesBreakdownBody.innerHTML = '';
    // This will now primarily display 'Turnover from Previous Years' and potentially other current-year revenues
    // that are *not* membership fees. You'll need your backend to structure this array accordingly.
    data.revenues_breakdown.forEach(item => {
        const row = revenuesBreakdownBody.insertRow();
        row.innerHTML = `
            <td>${item.source}</td>
            <td class="amount">₱${item.amount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
            <td>${item.percentage.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}%</td>
        `;
    });
    // The footer for "Total Revenue" now represents the "turnover money"
    document.getElementById('total-revenue-footer').textContent = `₱${data.total_revenue_ytd.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;


    // Expenses Breakdown Table (remains the same)
    const expensesBreakdownBody = document.getElementById('expenses-breakdown-body');
    expensesBreakdownBody.innerHTML = '';
    data.expenses_breakdown.forEach(item => {
        const row = expensesBreakdownBody.insertRow();
        row.innerHTML = `
            <td>${item.category}</td>
            <td class="amount">₱${item.amount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
            <td>${item.percentage.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}%</td>
        `;
    });
    document.getElementById('total-expenses-footer').textContent = `₱${data.total_expenses_ytd.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;


    // Monthly Summary Table (Net Income here should reflect current AY membership fees - expenses per month)
    const monthlySummaryBody = document.getElementById('monthly-summary-body');
    monthlySummaryBody.innerHTML = '';
    let totalMonthlyRevenue = 0; // This 'revenue' in monthly summary might still be overall income, not just turnover
    let totalMonthlyExpenses = 0;
    let totalMonthlyNetIncome = 0;

    data.monthly_summary.forEach(item => {
        const row = monthlySummaryBody.insertRow();
        const netIncomeClass = item.net_income >= 0 ? 'positive' : 'negative';
        row.innerHTML = `
            <td>${item.month}</td>
            <td class="amount positive">₱${item.revenue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
            <td class="amount negative">₱${item.expenses.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
            <td class="amount ${netIncomeClass}">₱${item.net_income.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
        `;
        totalMonthlyRevenue += item.revenue;
        totalMonthlyExpenses += item.expenses;
        totalMonthlyNetIncome += item.net_income;
    });

    document.getElementById('monthly-total-revenue-footer').textContent = `₱${totalMonthlyRevenue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById('monthly-total-expenses-footer').textContent = `₱${totalMonthlyExpenses.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    const monthlyNetIncomeFooter = document.getElementById('monthly-net-income-footer');
    monthlyNetIncomeFooter.textContent = `₱${totalMonthlyNetIncome.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    if (totalMonthlyNetIncome >= 0) {
        monthlyNetIncomeFooter.classList.add('positive');
        monthlyNetIncomeFooter.classList.remove('negative');
    } else {
        monthlyNetIncomeFooter.classList.add('negative');
        monthlyNetIncomeFooter.classList.remove('positive');
    }


    // Accounts Balances Table (remains the same)
    const accountsBalancesBody = document.getElementById('accounts-balances-body');
    accountsBalancesBody.innerHTML = '';
    let totalAccountBalance = 0;
    data.accounts_balances.forEach(item => {
        const row = accountsBalancesBody.insertRow();
        const statusClass = item.status.toLowerCase() + '-status';
        row.innerHTML = `
            <td>${item.account}</td>
            <td class="amount">₱${item.balance.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
            <td>${item.last_transaction}</td>
            <td class="${statusClass}">${item.status}</td>
        `;
        totalAccountBalance += item.balance;
    });
    document.getElementById('total-accounts-balance-footer').textContent = `₱${totalAccountBalance.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

    window.financialData = data;
    renderCharts(data);
}

async function fetchFinancialData() {
    try {
        const response = await fetch('/api/admin/financial_data');
        if (!response.ok) {
            let errorMessage = `HTTP error! status: ${response.status}`;
            try {
                const errorData = await response.json();
                if (errorData && errorData.detail) {
                    errorMessage += ` - Detail: ${errorData.detail}`;
                }
            } catch (jsonError) {
            }
            throw new Error(errorMessage);
        }
        const data = await response.json();
        console.log("Fetched main financial data:", data);
        populateDashboard(data);
    } catch (error) {
        console.error("Error fetching financial data:", error);
        document.querySelector('.dashboard-container').innerHTML = `
            <div style="text-align: center; color: red; font-size: 1.2em; padding: 50px;">
                Failed to load financial data. Please ensure you are logged in and authorized, then try again later.
                <br>
                Error: ${error.message}
            </div>
        `;
    }
}

// Helper to get the currently displayed or calculated academic year
function getCalculatedCurrentAcademicYear() {
    const today = new Date();
    const currentYear = today.getFullYear();
    const currentMonth = today.getMonth(); // 0-indexed

    const academicYearStartMonth = 7; // August (0-indexed, so 7 is August)

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

// --- Membership Fee Tracker Logic (Integrated into Revenues) ---
const academicYearSelect = document.getElementById('academicYearSelect'); // Renamed ID for clarity within this file
const semesterSelect = document.getElementById('semesterSelect');       // Renamed ID for clarity within this file
const membershipTableBody = document.getElementById('membershipTableBody'); // Using the correct ID from HTML

function populateMembershipTable(data) {
    membershipTableBody.innerHTML = '';
    if (!data || !Array.isArray(data.members) || data.members.length === 0) {
        membershipTableBody.innerHTML = '<tr><td colspan="4" style="text-align: center;">No data available for the selected filters.</td></tr>';
        document.getElementById('total-paid-members').textContent = '0';
        document.getElementById('total-unpaid-members').textContent = '0';
        document.getElementById('total-members-count').textContent = '0';
        return;
    }
    
    // Update summary cards for membership
    document.getElementById('total-paid-members').textContent = data.total_paid_members !== undefined ? data.total_paid_members : '0';
    document.getElementById('total-unpaid-members').textContent = data.total_unpaid_members !== undefined ? data.total_unpaid_members : '0';
    document.getElementById('total-members-count').textContent = data.total_members_count !== undefined ? data.total_members_count : '0';

    data.members.forEach(item => {
        const row = membershipTableBody.insertRow();
        const nameCell = row.insertCell();
        const yearSecCell = row.insertCell();
        const amountPaidCell = row.insertCell();
        const statusCell = row.insertCell();

        nameCell.textContent = `${item.first_name} ${item.last_name}`;
        yearSecCell.textContent = `${item.year_level} - ${item.section}`;
        amountPaidCell.textContent = `₱${(item.total_paid || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        statusCell.textContent = item.status || 'N/A';
        statusCell.classList.add(item.status ? item.status.toLowerCase().replace(' ', '-') : ''); // Add class for styling if needed
    });
}

async function fetchMembershipData(academicYear, semester) {
    let url = '/api/admin/membership_tracker_data'; // New backend endpoint for detailed membership data
    const params = [];

    // Always ensure academic_year is present in the request
    if (academicYear && academicYear !== 'Academic Year ▼') {
        params.push(`academic_year=${academicYear}`);
    } else {
        // If no academic year is explicitly selected, default to current academic year
        academicYear = getCalculatedCurrentAcademicYear();
        academicYearSelect.value = academicYear; // Ensure dropdown reflects default
        params.push(`academic_year=${academicYear}`);
    }

    if (semester && semester !== 'Semester ▼' && semester !== '') { // Added '' check for initial empty option
        params.push(`semester=${semester}`);
    }
    
    if (params.length > 0) {
        url += '?' + params.join('&');
    }

    console.log("Fetching membership data for tracker from URL:", url);

    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log("Membership data received:", data);
        populateMembershipTable(data);
    } catch (error) {
        console.error('Error fetching membership data for tracker:', error);
        membershipTableBody.innerHTML = '<tr><td colspan="4">Error loading membership data.</td></tr>';
        document.getElementById('total-paid-members').textContent = 'Error';
        document.getElementById('total-unpaid-members').textContent = 'Error';
        document.getElementById('total-members-count').textContent = 'Error';
    }
}


// Function to populate academic year dropdown
function populateAcademicYearDropdown() {
    const startYearForDropdown = 2022; // Start from 2022-2023
    const currentYear = new Date().getFullYear();
    const currentMonth = new Date().getMonth();
    let endYearForDropdown;

    // Determine the furthest academic year to show in dropdown (current AY + a few future years)
    if (currentMonth >= 7) { // If current month is August (7) or later
        endYearForDropdown = currentYear + 1 + 3; // e.g., 2024-2025 (current) + 3 future years
    } else {
        endYearForDropdown = currentYear + 3; // e.g., 2023-2024 (current) + 3 future years
    }

    let optionsHTML = '<option value="Academic Year ▼">Academic Year ▼</option>'; // Default option
    for (let year = startYearForDropdown; year <= endYearForDropdown; year++) {
        const yearPair = `${year}-${year + 1}`;
        optionsHTML += `<option value="${yearPair}">${yearPair}</option>`;
    }
    academicYearSelect.innerHTML = optionsHTML;
    // Set default value to the calculated current academic year
    academicYearSelect.value = getCalculatedCurrentAcademicYear();
}

// Function to populate semester dropdown
function populateSemesterDropdown() {
    semesterSelect.innerHTML = `
        <option value="Semester ▼">Semester ▼</option>
        <option value="1st Semester">1st Semester</option>
        <option value="2nd Semester">2nd Semester</option>
    `;
    // You might want to set a default semester if needed, e.g., based on current month
}


document.addEventListener('DOMContentLoaded', function () {
    // Initial fetch for main financial dashboard data
    fetchFinancialData();
    toggleView('overview'); // Set initial view

    // Populate dropdowns for membership tracker
    populateAcademicYearDropdown();
    populateSemesterDropdown();

    // Initial load for membership tracker section with current AY and default semester
    const initialAcademicYear = academicYearSelect.value; // This will be the auto-selected current AY
    const initialSemester = semesterSelect.value;
    fetchMembershipData(initialAcademicYear, initialSemester);

    // Event listeners for membership tracker filters
    academicYearSelect.addEventListener('change', function () {
        const selectedAcademicYear = this.value;
        const selectedSemester = semesterSelect.value;
        fetchMembershipData(selectedAcademicYear, selectedSemester);
    });

    semesterSelect.addEventListener('change', function () {
        const selectedAcademicYear = academicYearSelect.value;
        const selectedSemester = this.value;
        fetchMembershipData(selectedAcademicYear, selectedSemester);
    });

    // --- Custom dropdown logic (remains mostly the same, but adapted for new dropdown IDs) ---
    // Make sure your custom dropdown logic targets the correct new IDs (`academicYearSelect`, `semesterSelect`)
    // or keep the general `.filter-select` class if that's what your custom dropdown uses.
    document.querySelectorAll('.filters-container select').forEach(originalSelect => {
        const customSelectWrapper = document.createElement('div');
        customSelectWrapper.classList.add('custom-filter-select');
        originalSelect.parentNode.insertBefore(customSelectWrapper, originalSelect);
        customSelectWrapper.appendChild(originalSelect);

        const valueDisplay = document.createElement('div');
        valueDisplay.classList.add('filter-select-value');
        valueDisplay.textContent = originalSelect.options[originalSelect.selectedIndex].textContent;
        customSelectWrapper.appendChild(valueDisplay);

        const optionsContainer = document.createElement('ul');
        optionsContainer.classList.add('filter-select-options');
        customSelectWrapper.appendChild(optionsContainer);

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
                    customSelectWrapper.classList.remove('open');
                    optionsContainer.style.maxHeight = null;
                    event.stopPropagation();
                });
            });
        };

        populateCustomDropdown();

        // Observe changes to the original select's options (e.g., when populated dynamically)
        const observer = new MutationObserver(populateCustomDropdown);
        observer.observe(originalSelect, { childList: true });

        valueDisplay.addEventListener('click', function (event) {
            customSelectWrapper.classList.toggle('open');
            optionsContainer.style.maxHeight = customSelectWrapper.classList.contains('open') ? '200px' : null;
            event.stopPropagation();
        });

        document.addEventListener('click', function (event) {
            if (!customSelectWrapper.contains(event.target)) {
                customSelectWrapper.classList.remove('open');
                optionsContainer.style.maxHeight = null;
            }
        });
    });
});