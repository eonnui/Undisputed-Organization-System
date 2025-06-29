document.addEventListener("DOMContentLoaded", function () {
  const urlParams = new URLSearchParams(window.location.search);
  const month = urlParams.get("month");
  const year = urlParams.get("year");

  const detailedMonthTitle = document.getElementById("detailed-month-title");
  const detailedMonthDate = document.getElementById("detailed-month-date");
  const detailedMonthlyDataTableBody = document.getElementById(
    "detailed-monthly-data-body"
  );
  const detailedMonthFooter = document.getElementById("detailed-month-footer");

  const footerCashReceived = document.getElementById("footer-cash-received");
  const footerCashDisbursed = document.getElementById("footer-cash-disbursed");
  const footerRunningBalance = document.getElementById(
    "footer-running-balance"
  );

  const reportTypeSelect = document.getElementById("report-type-select");

  // Function to fetch and populate data
  function fetchAndPopulateData() {
    if (month && year) {
      const capitalizedMonth = month.charAt(0).toUpperCase() + month.slice(1);
      detailedMonthTitle.textContent = capitalizedMonth;
      detailedMonthFooter.textContent = capitalizedMonth;
      detailedMonthDate.textContent = `For the month of ${capitalizedMonth} ${year}`;

      const selectedReportType = reportTypeSelect.value;
      let apiUrl = `/api/detailed_monthly_report?month=${month}&year=${year}`;
      if (selectedReportType !== "combined") {
        apiUrl += `&report_type=${selectedReportType}`;
      }

      fetch(apiUrl)
        .then((response) => {
          if (!response.ok) {
            return response
              .json()
              .then((errorData) => {
                console.error(
                  "API Error:",
                  errorData.detail || "Unknown API Error"
                );
                if (response.status === 403) {
                  window.location.href = "/login";
                  throw new Error(
                    "Authentication/Authorization issue. Redirecting..."
                  );
                }
                throw new Error(
                  errorData.detail || `HTTP error! status: ${response.status}`
                );
              })
              .catch(() => {
                return response.text().then((text) => {
                  console.error(
                    "Non-JSON error response received from API:",
                    text
                  );
                  throw new Error(
                    `HTTP error! status: ${response.status}. Server returned unexpected content.`
                  );
                });
              });
          }
          return response.json();
        })
        .then((data) => {
          if (data && data.transactions) {
            populateDetailedTable(data.transactions, {
              received: data.total_inflows,
              disbursed: data.total_outflows,
              running: data.ending_balance,
            });
          } else {
            console.warn("No transaction data found in API response:", data);
            populateDetailedTable([], {
              received: 0,
              disbursed: 0,
              running: 0,
            });
          }
        })
        .catch((error) => {
          console.error("Error fetching detailed monthly data:", error);
          detailedMonthlyDataTableBody.innerHTML = `<tr>
                            <td>--</td>
                            <td colspan="5" style="text-align: center;">Error loading data: ${error.message}. Please try again.</td>
                        </tr>`;
          footerCashReceived.textContent = "₱0.00";
          footerCashDisbursed.textContent = "₱0.00";
          footerRunningBalance.textContent = "₱0.00";
        });
    } else {
      detailedMonthTitle.textContent = "No Month Selected";
      detailedMonthDate.textContent =
        "Please select a month and year from the dashboard.";
      populateDetailedTable([], { received: 0, disbursed: 0, running: 0 });
    }
  }

  // Initial data load
  fetchAndPopulateData();

  // Add event listener for when the report type changes
  reportTypeSelect.addEventListener("change", fetchAndPopulateData);
});

function populateDetailedTable(transactions, totals) {
  const detailedMonthlyDataTableBody = document.getElementById(
    "detailed-monthly-data-body"
  );
  const footerCashReceived = document.getElementById("footer-cash-received");
  const footerCashDisbursed = document.getElementById("footer-cash-disbursed");
  const footerRunningBalance = document.getElementById(
    "footer-running-balance"
  );

  detailedMonthlyDataTableBody.innerHTML = "";

  if (transactions.length === 0) {
    const row = detailedMonthlyDataTableBody.insertRow();
    row.insertCell().textContent = "--";
    row.insertCell().textContent = "No detailed data available for this month.";
    row.insertCell().textContent = "";
    row.insertCell().textContent = "₱0.00";
    row.insertCell().textContent = "₱0.00";
    row.insertCell().textContent = "₱0.00";

    row.cells[3].classList.add("amount");
    row.cells[4].classList.add("amount");
    row.cells[5].classList.add("amount");
  } else {
    transactions.forEach((item) => {
      const row = detailedMonthlyDataTableBody.insertRow();
      row.insertCell().textContent = item.date || "N/A";
      row.insertCell().textContent = item.description || "N/A";
      row.insertCell().textContent = item.status || "N/A";

      const inflow = typeof item.inflow === "number" ? item.inflow : 0;
      const outflow = typeof item.outflow === "number" ? item.outflow : 0;
      const runningBalance =
        typeof item.running_balance === "number" ? item.running_balance : 0;

      row.insertCell().textContent = `₱${inflow.toFixed(2)}`;
      row.insertCell().textContent = `₱${outflow.toFixed(2)}`;
      row.insertCell().textContent = `₱${runningBalance.toFixed(2)}`;

      row.cells[3].classList.add("amount");
      row.cells[4].classList.add("amount");
      row.cells[5].classList.add("amount");
    });
  }

  const totalReceived =
    typeof totals.received === "number" ? totals.received : 0;
  const totalDisbursed =
    typeof totals.disbursed === "number" ? totals.disbursed : 0;
  const totalRunning = typeof totals.running === "number" ? totals.running : 0;

  footerCashReceived.textContent = `₱${totalReceived.toFixed(2)}`;
  footerCashDisbursed.textContent = `₱${totalDisbursed.toFixed(2)}`;
  footerRunningBalance.textContent = `₱${totalRunning.toFixed(2)}`;
}
