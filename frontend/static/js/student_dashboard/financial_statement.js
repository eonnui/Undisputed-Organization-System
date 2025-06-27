const financialDataContainer = document.getElementById('financial-data-container');
const financialDataScript = document.getElementById('financial-data-json');
let financialData;

try {
    financialData = JSON.parse(financialDataScript.textContent);
} catch (e) {
    // Fallback to an empty object if parsing fails
    financialData = {
        user_financials: {
            total_paid_by_user: 0.0,
            total_outstanding_fees: 0.0,
            total_past_due_fees: 0.0,
            collected_fees_by_category: [],
            outstanding_fees_by_category: []
        },
        organization_financials: {
            total_revenue_org: 0.0,
            total_expenses_org: 0.0,
            net_income_org: 0.0,
            expenses_by_category_org: [],
            monthly_data_org: {}
        },
        current_date: "N/A"
    };
}

let currentYear = financialDataContainer.dataset.currentYear;
let academicYear = financialDataContainer.dataset.academicYear; // Get academic year

let today = new Date();
let currentMonthName = new Date(today.getFullYear(), today.getMonth(), 1)
                                .toLocaleString('en-US', { month: 'long' }).toLowerCase();
let lastActiveMonth = currentMonthName;

function populateQuickStats() {
    if (financialData && financialData.current_date) {
        const currentDateElement = document.getElementById('current-date');
        if (currentDateElement) {
            currentDateElement.textContent = financialData.current_date;
        }
    }
}

function formatCurrency(amount) {
    return `₱${amount.toFixed(2)}`;
}

function toggleDashboardView(viewId) {
    const reportCards = document.querySelectorAll('.report-card');
    const toggleButtons = document.querySelectorAll('.toggle-buttons .toggle-btn');

    reportCards.forEach(card => {
        card.classList.remove('active');
    });

    toggleButtons.forEach(button => {
        button.classList.remove('active');
    });

    const targetCard = document.getElementById(`dashboard-${viewId}`);
    const targetButton = document.getElementById(`toggle-${viewId}`);

    if (targetCard) {
        targetCard.classList.add('active');
    }
    if (targetButton) {
        targetButton.classList.add('active');
    }

    if (viewId === 'org-monthly') {
        showMonthlyData(lastActiveMonth);
    }
}

function showMonthlyData(month) {
    lastActiveMonth = month;

    const monthlyDataTable = document.getElementById('monthly-data-table');
    const viewDetailedLink = document.getElementById('view-detailed-monthly-report-link');

    if (!monthlyDataTable) {
        return;
    }
    monthlyDataTable.innerHTML = '';

    if (viewDetailedLink) {
        viewDetailedLink.href = `/student_dashboard/detailed_monthly_report_page?month=${month}&year=${currentYear}&type=organization`;
    }

    const monthlyStats = financialData.organization_financials && financialData.organization_financials.monthly_data_org ?
                         financialData.organization_financials.monthly_data_org[month] : null;

    if (monthlyStats) {
        let startingBalanceRow = monthlyDataTable.insertRow();
        let startingBalanceCellLabel = startingBalanceRow.insertCell();
        let startingBalanceCellAmount = startingBalanceRow.insertCell();
        startingBalanceCellLabel.textContent = 'Starting Balance';
        startingBalanceCellAmount.textContent = formatCurrency(monthlyStats.starting_balance);
        startingBalanceCellAmount.classList.add('amount');

        let inflowsRow = monthlyDataTable.insertRow();
        let inflowsCellLabel = inflowsRow.insertCell();
        let inflowsCellAmount = inflowsRow.insertCell();
        inflowsCellLabel.textContent = 'Total Inflows';
        inflowsCellAmount.textContent = formatCurrency(monthlyStats.inflows);
        inflowsCellAmount.classList.add('amount');

        let outflowsRow = monthlyDataTable.insertRow();
        let outflowsCellLabel = outflowsRow.insertCell();
        let outflowsCellAmount = outflowsRow.insertCell();
        outflowsCellLabel.textContent = 'Total Outflows';
        outflowsCellAmount.textContent = formatCurrency(monthlyStats.outflows);
        outflowsCellAmount.classList.add('amount');

        let endingBalanceRow = monthlyDataTable.insertRow();
        let endingBalanceCellLabel = endingBalanceRow.insertCell();
        let endingBalanceCellAmount = endingBalanceRow.insertCell();
        endingBalanceCellLabel.textContent = 'Ending Balance';
        endingBalanceCellAmount.textContent = formatCurrency(monthlyStats.ending_balance);
        endingBalanceCellAmount.classList.add('amount');
    } else {
        let row = monthlyDataTable.insertRow();
        let cell = row.insertCell();
        cell.colSpan = 2;
        cell.textContent = `No data available for ${month}.`;
        cell.style.textAlign = 'center';
    }

    const monthlyButtons = document.querySelectorAll('#dashboard-org-monthly .monthly-toggles button');
    monthlyButtons.forEach(button => {
        button.classList.remove('active');
        if (button.textContent.toLowerCase() === month) {
            button.classList.add('active');
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    populateQuickStats();
    toggleDashboardView('user-collected');

    // Display academic year in the title
    const academicYearDisplay = document.getElementById('academic-year-display');
    if (academicYearDisplay && academicYear) {
        academicYearDisplay.textContent = `(${academicYear})`;
    }


    document.getElementById('toggle-user-collected').addEventListener('click', () => toggleDashboardView('user-collected'));
    document.getElementById('toggle-user-outstanding').addEventListener('click', () => toggleDashboardView('user-outstanding'));
    document.getElementById('toggle-org-expenses').addEventListener('click', () => toggleDashboardView('org-expenses'));
    document.getElementById('toggle-combined-activity').addEventListener('click', () => toggleDashboardView('combined-activity'));
    document.getElementById('toggle-org-monthly').addEventListener('click', () => toggleDashboardView('org-monthly'));

    const monthlyButtons = document.querySelectorAll('#dashboard-org-monthly .monthly-toggles button');
    monthlyButtons.forEach(button => {
        button.addEventListener('click', function() {
            showMonthlyData(this.textContent.toLowerCase());
        });
    });

    showMonthlyData(lastActiveMonth);
});