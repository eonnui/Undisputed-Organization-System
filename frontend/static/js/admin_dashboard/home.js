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
    function fetchTotalCollectedFees() {
      fetch('/admin/membership/')
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          return response.json();
        })
        .then(data => {
          let totalCollected = 0;
          data.forEach(section => {
            totalCollected += section.total_paid;
          });
          totalCollectedValue.textContent = totalCollected.toLocaleString('en-US', { style: 'currency', currency: 'PHP' });
        })
        .catch(error => {
          console.error('Error fetching membership data for total collected fees:', error);
          totalCollectedValue.textContent = 'Error';
        });
    }

    // Fetch total collected fees on page load
    fetchTotalCollectedFees();
    // --- Fill Academic Year Stat Card ---
    function displayCurrentAcademicYear() {
      const today = new Date();
      const currentYear = today.getFullYear();
      const currentMonth = today.getMonth(); 

      const academicYearStartMonth = 5; 

      let startYear, endYear;

      if (currentMonth > academicYearStartMonth) {
        startYear = currentYear;
        endYear = currentYear + 1;
      } else {
        startYear = currentYear - 1;
        endYear = currentYear;
      }

      academicYearValue.textContent = `${startYear}-${endYear}`;

      // Populate the Academic Year dropdown
      const startYearForDropdown = 2022; 
      const endYearForDropdown = endYear + 4; 
      let optionsHTML = '<option>Academic Year ▼</option>';
      for (let year = startYearForDropdown; year <= endYearForDropdown; year++) {
        const yearPair = `${year}-${year + 1}`;
        optionsHTML += `<option value="${yearPair}">${yearPair}</option>`;
      }
      academicYearFilterDropdown.innerHTML = optionsHTML;
    }

    // Display the current academic year on load
    displayCurrentAcademicYear();

    function fetchOutstandingDuesAmount() {
      // Get current academic year from the stat card
      const currentAcademicYear = document.querySelector('.stat-card:nth-child(3) .stat-value').textContent;

      // Determine current semester.  
      const selectedSemester = semesterFilterDropdown.value;
      let currentSemester;
      if (selectedSemester !== 'Semester ▼') {
        currentSemester = selectedSemester;
      } else {
        const today = new Date();
        const currentMonth = today.getMonth();
        const semester1StartMonth = 6;
        const semester2StartMonth = 0;
        if (currentMonth >= semester1StartMonth && currentMonth <= 11) {
          currentSemester = "1st";
        } else {
          currentSemester = "2nd";
        }
      }

      const outstandingDuesValue = document.querySelector('.stat-card:nth-child(4) .stat-value');

      console.log(`Fetching outstanding dues amount for Academic Year: ${currentAcademicYear}, Semester: ${currentSemester}`);

      fetch(`/admin/outstanding_dues/?academic_year=${currentAcademicYear}&semester=${currentSemester}`)
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          return response.json();
        })
        .then(data => {
          let totalOutstandingAmount = 0;

          console.log("Data received from /admin/outstanding_dues/:", data); 

          if (Array.isArray(data) && data.length > 0) {
            totalOutstandingAmount = data[0].total_outstanding_amount;
            console.log("Total outstanding amount:", totalOutstandingAmount);
          }
          else if (Array.isArray(data) && data.length === 0) {
            totalOutstandingAmount = 0;
            console.log("No outstanding dues found for the selection.");
          }
          else {
            console.error("Unexpected data format. Expected a list with one dictionary or an empty list.", data);
            outstandingDuesValue.textContent = 'Error';
            return;
          }

          outstandingDuesValue.textContent = `₱${totalOutstandingAmount.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}`;
          console.log(
            `Displaying total outstanding dues amount for current semester (${currentSemester}, ${currentAcademicYear}): ₱${totalOutstandingAmount.toFixed(2)}`
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
          console.log(`Displaying error: Error fetching outstanding dues amount for current semester`);
        });
    }

    // Call fetchOutstandingDuesAmount
    fetchOutstandingDuesAmount();

    // --- Membership Fee Tracker Logic ---
    const academicYearSelect = document.getElementById('academic-year-filter');
    const semesterSelect = document.getElementById('semester-filter');
    const membershipTableBody = document.querySelector('.tracker-section table tbody');

    function populateMembershipTable(data) {
      membershipTableBody.innerHTML = '';
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
      if (academicYear && academicYear !== 'Academic Year ▼') {
        params.push(`academic_year=${academicYear}`);
      }
      if (semester && semester !== 'Semester ▼') {
        params.push(`semester=${semester}`);
      }
      if (params.length > 0) {
        url += '?' + params.join('&');
      }

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
    // Initial load of membership data
    fetchMembershipData();

    // Event listeners for filter changes
    academicYearSelect.addEventListener('change', function () {
      const selectedAcademicYear = this.value;
      const selectedSemester = semesterSelect.value;
      fetchMembershipData(selectedAcademicYear, selectedSemester);
      fetchOutstandingDuesAmount(); 
    });

    semesterSelect.addEventListener('change', function () {
      const selectedAcademicYear = academicYearSelect.value;
      const selectedSemester = this.value;
      fetchMembershipData(selectedAcademicYear, selectedSemester);
      fetchOutstandingDuesAmount(); 
    });
    
    document.querySelectorAll('.filter-select').forEach(select => {
      const valueDisplay = select.querySelector('.filter-select-value');
      const optionsContainer = document.createElement('ul');
      optionsContainer.classList.add('filter-select-options');
      select.appendChild(optionsContainer);

      const originalSelect = document.createElement('select');
      originalSelect.style.display = 'none';
      select.appendChild(originalSelect);

      const defaultOptionText = select.querySelector('option:first-child').textContent;
      const originalOptions = Array.from(select.querySelectorAll('option'));

      originalOptions.forEach((option, index) => {
        const li = document.createElement('li');
        li.textContent = option.textContent;
        li.dataset.value = option.value;
        optionsContainer.appendChild(li);
        const originalOption = document.createElement('option');
        originalOption.value = option.value;
        originalOption.textContent = option.textContent;
        if (index === 0) {
          originalOption.selected = true;
          valueDisplay.textContent = defaultOptionText;
        }
        originalSelect.appendChild(originalOption);

        li.addEventListener('click', function () {
          valueDisplay.textContent = this.textContent;
          originalSelect.value = this.dataset.value;
          originalSelect.dispatchEvent(new Event('change')); 
          select.classList.remove('open');
          optionsContainer.style.maxHeight = null; 
        });
      });

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