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
            button.textContent.toLowerCase().includes(viewId)
        );
        if (selectedButton) {
            selectedButton.classList.add('active');
        }

        if (viewId === 'overview' && window.financialData) {
            renderCharts(window.financialData);
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
                    labels: ['Revenue', 'Expenses'],
                    datasets: [{
                        label: 'Year-to-Date (₱)',
                        data: [
                            data.total_revenue_ytd,
                            data.total_expenses_ytd
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
                        label: 'Net Income (₱)',
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
        document.getElementById('current-year').textContent = data.year;
        document.getElementById('total-current-balance').textContent = `₱${data.total_current_balance.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        document.getElementById('total-revenue-ytd').textContent = `₱${data.total_revenue_ytd.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        document.getElementById('total-expenses-ytd').textContent = `₱${data.total_expenses_ytd.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        const netIncomeYTDElement = document.getElementById('net-income-ytd');
        netIncomeYTDElement.textContent = `₱${data.net_income_ytd.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        if (data.net_income_ytd >= 0) {
            netIncomeYTDElement.classList.add('positive');
            netIncomeYTDElement.classList.remove('negative');
        } else {
            netIncomeYTDElement.classList.add('negative');
            netIncomeYTDElement.classList.remove('positive');
        }

        document.getElementById('balance-turnover').textContent = data.balance_turnover.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
        document.getElementById('total-funds-available').textContent = `₱${data.total_funds_available.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        document.getElementById('reporting-date').textContent = data.reporting_date;

        document.getElementById('top-revenue-source').textContent = `${data.top_revenue_source_name} (₱${data.top_revenue_source_amount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})})`;
        document.getElementById('largest-expense').textContent = `${data.largest_expense_category} (₱${data.largest_expense_amount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})})`;
        document.getElementById('profit-margin-ytd').textContent = `${data.profit_margin_ytd.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}%`;

        const revenuesBreakdownBody = document.getElementById('revenues-breakdown-body');
        revenuesBreakdownBody.innerHTML = '';
        data.revenues_breakdown.forEach(item => {
            const row = revenuesBreakdownBody.insertRow();
            row.innerHTML = `
                <td>${item.source}</td>
                <td class="amount">₱${item.amount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>               
                <td>${item.percentage.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}%</td>
            `;
        });
        document.getElementById('total-revenue-footer').textContent = `₱${data.total_revenue_ytd.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;


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


        const monthlySummaryBody = document.getElementById('monthly-summary-body');
        monthlySummaryBody.innerHTML = '';
        let totalMonthlyRevenue = 0;
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
            console.log("Fetched data:", data);
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

    document.addEventListener('DOMContentLoaded', function () {
        fetchFinancialData();
        toggleView('overview');
    });