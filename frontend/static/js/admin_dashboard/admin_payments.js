function openTab(tabName) {
    const tabs = document.querySelectorAll('.tab-content');
    const buttons = document.querySelectorAll('.tab-button');
    for (let i = 0; i < tabs.length; i++) {
        tabs[i].classList.remove('active');
    }
    for (let i = 0; i < buttons.length; i++) {
        buttons[i].classList.remove('active');
    }
    const targetTab = document.getElementById(tabName);
    const targetButton = Array.from(buttons).find(button => button.textContent.toLowerCase() === tabName.toLowerCase());
    if (targetTab) {
        targetTab.classList.add('active');
        if (tabName === 'expenses') {
            loadExpensesTable();
        }
    }
    if (targetButton) {
        targetButton.classList.add('active');
    }
}

document.querySelectorAll('.custom-select-wrapper').forEach(wrapper => {
    const trigger = wrapper.querySelector('.custom-select-trigger');
    const options = wrapper.querySelector('.custom-options');
    const listItems = options.querySelectorAll('li');

    trigger.addEventListener('click', () => {
        document.querySelectorAll('.custom-select-wrapper.open').forEach(openWrapper => {
            if (openWrapper !== wrapper) {
                openWrapper.classList.remove('open');
                openWrapper.querySelector('.custom-options').style.display = 'none';
            }
        });

        wrapper.classList.toggle('open');
        options.style.display = wrapper.classList.contains('open') ? "block" : "none";
    });

    listItems.forEach(item => {
        item.addEventListener('click', () => {
            const value = item.dataset.value;
            trigger.querySelector('span').textContent = item.textContent;
            wrapper.classList.remove('open');
            options.style.display = "none";
            if (wrapper.id === 'academic-year-filter-wrapper') {
                selectedAcademicYear = value;
            } else if (wrapper.id === 'semester-filter-wrapper') {
                selectedSemester = value;
            }
            updateMembershipTable();
        });
    });
});

document.addEventListener('click', (event) => {
    if (!event.target.closest('.custom-select-wrapper')) {
        document.querySelectorAll('.custom-select-wrapper.open').forEach(openWrapper => {
            openWrapper.classList.remove('open');
            openWrapper.querySelector('.custom-options').style.display = 'none';
        });
    }
});

let selectedAcademicYear = "";
let selectedSemester = "";
let sortColumn = "year_level";
let sortDirection = 'desc';

async function updateMembershipTable() {
    const table = document.getElementById("membership-table").getElementsByTagName('tbody')[0];
    table.innerHTML = "";

    let url = "/admin/membership/";
    let queryParams = [];

    if (selectedAcademicYear) {
        queryParams.push(`academic_year=${selectedAcademicYear}`);
    }
    if (selectedSemester) {
        queryParams.push(`semester=${selectedSemester}`);
    }

    if (queryParams.length > 0) {
        url += "?" + queryParams.join("&");
    }

    let totalPaidSum = 0;
    let totalAmountSum = 0;
    let totalPaidMembers = 0;
    let totalMembersCount = 0;
    let overallStatus = "";

    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        let data = await response.json();

        if (sortColumn) {
            data.sort((a, b) => {
                const valA = a[sortColumn];
                const valB = b[sortColumn];

                if (sortColumn === 'total_paid' || sortColumn === 'total_amount') {
                    return (sortDirection === 'asc' ? valA - valB : valB - valA);
                } else {
                    return (sortDirection === 'asc' ? String(valA).localeCompare(String(valB)) : String(valB).localeCompare(String(valA)));
                }
            });
        }

        data.forEach(item => {
            let row = table.insertRow();
            let yearCell = row.insertCell();
            let sectionCell = row.insertCell();
            let totalPaidCell = row.insertCell();
            let totalAmountCell = row.insertCell();
            let statusCell = row.insertCell();
            let listCell = row.insertCell();

            yearCell.textContent = item.year_level;
            sectionCell.textContent = item.section;
            totalPaidCell.textContent = item.total_paid;
            totalAmountCell.textContent = item.total_amount;
            statusCell.textContent = item.status;
            listCell.innerHTML = `<a href="/admin/payments/total_members?year_level=${item.year_level}&section=${item.section}" class="view-history-link">View</a>`;

            totalPaidSum += item.total_paid;
            totalAmountSum += item.total_amount;

            const [paidCountStr, totalCountStr] = item.status.split('/');
            if (paidCountStr && totalCountStr) {
                totalPaidMembers += parseInt(paidCountStr);
                totalMembersCount += parseInt(totalCountStr);
            } else if (item.status) {
                totalMembersCount += parseInt(item.status);
            }
        });

        if (selectedAcademicYear && selectedSemester) {
            overallStatus = `${totalPaidMembers}/${totalMembersCount}`;
        } else {
            overallStatus = `${totalMembersCount}`;
        }

        document.getElementById('total-paid-sum').textContent = totalPaidSum;
        document.getElementById('total-amount-sum').textContent = totalAmountSum;
        document.getElementById('total-status-summary').textContent = overallStatus;

    } catch (error) {
        console.error("Failed to fetch membership data:", error);
        table.innerHTML = `<tr><td colspan="9">Error loading data. Please check console.</td></tr>`;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const yearLevelHeader = document.querySelector('#membership-table th[data-column="year_level"]');
    if (yearLevelHeader) {
        yearLevelHeader.classList.add('desc');
    }

    updateMembershipTable();
    document.querySelectorAll('.update-button').forEach(button => {
        button.addEventListener('click', function (event) {
            const itemId = this.dataset.itemId;
            updatePaymentStatus(event, itemId);
        });
    });

    document.querySelectorAll('#membership-table th.sortable').forEach(header => {
        header.addEventListener('click', function () {
            const clickedColumn = this.dataset.column;
            if (sortColumn === clickedColumn) {
                sortDirection = (sortDirection === 'asc') ? 'desc' : 'asc';
            } else {
                sortColumn = clickedColumn;
                sortDirection = 'asc';
            }

            document.querySelectorAll('#membership-table th.sortable').forEach(th => {
                th.classList.remove('asc', 'desc');
            });

            this.classList.add(sortDirection);

            updateMembershipTable();
        });
    });

    document.getElementById('view-all-payments-button').addEventListener('click', () => openAdminPaymentHistoryModal());

    document.getElementById('add-expense-form').addEventListener('submit', async function(event) {
        event.preventDefault();

        const form = event.target;
        const formData = new FormData(form);
        const expenseData = {};
        formData.forEach((value, key) => {
            if (key === 'amount') {
                expenseData[key] = value ? parseFloat(value) : null;
            } else if (key === 'incurred_at') {
                expenseData[key] = value ? value : null;
            } else {
                expenseData[key] = value;
            }
        });

        if (expenseData.incurred_at === "") delete expenseData.incurred_at;

        try {
            const response = await fetch('/expenses/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(expenseData),
            });

            if (response.ok) {
                const result = await response.json();
                displayMessageBox('Expense added successfully!', 'info');
                form.reset();
                loadExpensesTable();
            } else {
                const errorData = await response.json();
                displayMessageBox(`Error: ${errorData.detail || 'Failed to add expense.'}`, 'error');
                console.error('Failed to add expense:', errorData);
            }
        } catch (error) {
            displayMessageBox('An error occurred while adding the expense.', 'error');
            console.error('Network error or unexpected issue:', error);
        }
    });
});

async function updatePaymentStatus(event, itemId) {
    event.preventDefault();

    const statusSelect = document.getElementById(`status-select-${itemId}`);
    const selectedStatus = statusSelect.value;

    try {
        const response = await fetch(`/admin/payment/${itemId}/update_status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `status=${encodeURIComponent(selectedStatus)}`,
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const statusCell = event.target.closest('tr').querySelector('td:nth-child(6)');
        statusCell.textContent = selectedStatus;
        statusCell.className = selectedStatus.toLowerCase();
    } catch (error) {
        console.error("Failed to update payment status:", error);
        displayMessageBox('Failed to update status. Please check the console for more details.', 'error');
    }
}

function filterPaymentsByStudentId() {
    const filterInput = document.getElementById('student-id-filter');
    const studentId = filterInput.value.trim();
    const paymentTables = document.querySelectorAll('#payments .payments-table');

    paymentTables.forEach(table => {
        const tableStudentId = table.dataset.studentId;
        if (studentId === "" || tableStudentId === studentId) {
            table.style.display = "";
        } else {
            table.style.display = "none";
        }
    });
}

function filterPaymentsByStudentIdAndHistory() {
    const studentId = document.getElementById('student-id-filter').value.trim();

    const paymentTables = document.querySelectorAll('#payments .payments-table');
    paymentTables.forEach(table => {
        const tableStudentId = table.dataset.studentId;
        if (studentId === "" || tableStudentId === studentId) {
            table.style.display = "";
        } else {
            table.style.display = "none";
        }
    });

    const modal = document.getElementById('allMembersPaymentHistoryModal');
    if (modal.style.display === 'flex') { 
        openAdminPaymentHistoryModal(studentId); 
    }
}


document.addEventListener('DOMContentLoaded', function() {
    if (window.location.hash.startsWith('#payments')) {
        openTab('payments');
        const urlParams = new URLSearchParams(window.location.hash.substring(1));
        const studentIdFromHash = urlParams.get('student_id');
        if (studentIdFromHash) {
            const filterInput = document.getElementById('student-id-filter');
            if (filterInput) {
                filterInput.value = studentIdFromHash;
                setTimeout(() => filterPaymentsByStudentIdAndHistory(), 150);
            }
        }
    }
});

async function openAdminPaymentHistoryModal(studentIdFromFilter = '') {
    const modal = document.getElementById('allMembersPaymentHistoryModal');
    const loadingMessage = document.getElementById('loading-message');
    const noDataMessage = document.getElementById('no-data-message');
    const paymentsTable = document.getElementById('all-members-payments-table');
    const tableBody = paymentsTable.querySelector('tbody');

    modal.style.display = 'flex';
    loadingMessage.style.display = 'block';
    paymentsTable.style.display = 'none';
    noDataMessage.style.display = 'none';
    tableBody.innerHTML = ''; 

    let url = '/admin/Payments/History';
    const studentNumber = studentIdFromFilter || document.getElementById('student-id-filter').value.trim();
    if (studentNumber) {
        url += `?student_number=${encodeURIComponent(studentNumber)}`;
    }

    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        loadingMessage.style.display = 'none';

        if (data.payment_history && data.payment_history.length > 0) {
            data.payment_history.forEach(item => {
                const row = tableBody.insertRow();
                row.insertCell().textContent = item.user_name;
                row.insertCell().textContent = item.student_number;
                row.insertCell().textContent = item.item.payment_item ? item.item.payment_item.academic_year : 'N/A';
                row.insertCell().textContent = item.item.payment_item ? item.item.payment_item.semester : 'N/A';
                row.insertCell().textContent = item.item.payment_item ? item.item.payment_item.fee : 'N/A';
                row.insertCell().textContent = item.item.payment_item && item.item.payment_item.due_date ? item.item.payment_item.due_date : 'Not Set';
                const statusCell = row.insertCell();
                statusCell.textContent = item.status;
                statusCell.className = item.status.toLowerCase().replace(' ', '-');
                row.insertCell().textContent = item.payment_date ? item.payment_date.substring(0, 10) : 'N/A'; 
            });
            paymentsTable.style.display = 'table';
        } else {
            noDataMessage.style.display = 'block';
        }
    } catch (error) {
        console.error("Failed to fetch all members' payment history:", error);
        loadingMessage.style.display = 'none';
        displayMessageBox('Error loading payment history. Please try again later.', 'error');
        noDataMessage.textContent = 'Error loading payment history.';
        noDataMessage.style.display = 'block';
    }
}


function closeAdminPaymentHistoryModal() {
    const modal = document.getElementById('allMembersPaymentHistoryModal');
    modal.style.display = 'none';
}

window.addEventListener('click', function(event) {
    const modal = document.getElementById('allMembersPaymentHistoryModal');
    if (event.target == modal) {
        closeAdminPaymentHistoryModal();
    }
});

function displayMessageBox(message, type = 'info') {
    const msgBox = document.createElement('div');
    msgBox.textContent = message;
    msgBox.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        padding: 20px;
        background-color: ${type === 'error' ? '#f44336' : '#4CAF50'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        z-index: 1001;
        font-family: sans-serif;
        text-align: center;
        animation: fadeOut 3s forwards;
    `;
    document.body.appendChild(msgBox);

    const styleSheet = document.createElement('style');
    styleSheet.innerHTML = `
        @keyframes fadeOut {
            0% { opacity: 1; }
            80% { opacity: 1; }
            100% { opacity: 0; display: none; }
        }
    `;
    document.head.appendChild(styleSheet);

    setTimeout(() => {
        if (msgBox.parentNode) {
            msgBox.parentNode.removeChild(msgBox);
        }
        if (styleSheet.parentNode) {
            styleSheet.parentNode.removeChild(styleSheet);
        }
    }, 3000);
}

async function loadExpensesTable() {
    const tableBody = document.querySelector('#expenses-table tbody');
    const totalExpensesSumElement = document.getElementById('total-expenses-sum');
    const noExpensesMessage = document.getElementById('no-expenses-message');
    tableBody.innerHTML = '';
    totalExpensesSumElement.textContent = '0.00';

    try {
        const response = await fetch('/expenses/');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const expenses = await response.json();

        let totalExpenses = 0;

        if (expenses.length > 0) {
            noExpensesMessage.style.display = 'none';
            expenses.forEach(expense => {
                const row = tableBody.insertRow();
                row.insertCell().textContent = expense.description;
                row.insertCell().textContent = `₱${expense.amount.toFixed(2)}`;
                row.insertCell().textContent = expense.category || 'N/A';
                row.insertCell().textContent = expense.incurred_at;
                row.insertCell().textContent = expense.admin ? `${expense.admin.first_name} ${expense.admin.last_name} (${expense.admin.position || 'Admin'})` : 'Unknown Admin';
                totalExpenses += expense.amount;
            });
            totalExpensesSumElement.textContent = `₱${totalExpenses.toFixed(2)}`;
        } else {
            noExpensesMessage.style.display = 'block';
        }
    } catch (error) {
        console.error("Failed to fetch expenses:", error);
        tableBody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: red;">Error loading expenses. Please try again.</td></tr>`;
        noExpensesMessage.style.display = 'none';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('expenses').classList.contains('active')) {
        loadExpensesTable();
    }
});