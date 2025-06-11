document.addEventListener('DOMContentLoaded', function() {
    const heartButtons = document.querySelectorAll('.heart-button');

    heartButtons.forEach(button => {
        button.addEventListener('click', function() {
            const postId = this.dataset.postId;
            const heartCountSpan = this.querySelector('.heart-count');
            const isHeartedInitially = this.classList.contains('hearted');
            const action = isHeartedInitially ? 'unheart' : 'heart';

            let currentCount = parseInt(heartCountSpan.textContent);
            if (action === 'heart') {
                this.classList.add('hearted');
                heartCountSpan.textContent = currentCount + 1;
            } else {
                this.classList.remove('hearted');
                heartCountSpan.textContent = Math.max(0, currentCount - 1);
            }

            fetch(`/bulletin/heart/${postId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `action=${action}`,
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                heartCountSpan.textContent = data.heart_count;

                if (data.is_hearted_by_user) {
                    this.classList.add('hearted');
                } else {
                    this.classList.remove('hearted');
                }
            })
            .catch(error => {
                console.error('Error hearting post:', error);
                if (action === 'heart') {
                    this.classList.remove('hearted');
                    heartCountSpan.textContent = currentCount;
                } else {
                    this.classList.add('hearted');
                    heartCountSpan.textContent = currentCount;
                }
            });
        });
    });

    function fetchRulesWiki() {
        const rulesWikiContainer = document.querySelector('.wiki-posts-list');
        if (!rulesWikiContainer) return; // Ensure element exists before trying to manipulate it

        rulesWikiContainer.innerHTML = '<p>Loading rules and wiki entries...</p>'; 

        fetch('/BulletinBoard')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.text(); 
            })
            .then(htmlString => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(htmlString, 'text/html');
                const newRulesWikiContent = doc.querySelector('.wiki-posts-list');

                if (newRulesWikiContent) {
                    rulesWikiContainer.innerHTML = newRulesWikiContent.innerHTML;
                } else {
                    rulesWikiContainer.innerHTML = '<p>Error: Could not load rules and wiki entries.</p>';
                }
            })
            .catch(error => {
                console.error('Error fetching rules and wiki:', error);
                rulesWikiContainer.innerHTML = '<p>Failed to load rules and wiki entries.</p>';
            });
    }
    
    // Call this after DOM is ready
    fetchRulesWiki();

    // --- Organizational Chart Logic ---
    const orgChartButton = document.getElementById('viewOrgChartButton');
    const orgChartModal = document.getElementById('orgChartModal');
    const closeButton = orgChartModal ? orgChartModal.querySelector('.close-button') : null; // Safely get close button
    const organizationChartContainer = document.getElementById('organizationChartContainer');

    // Helper to create an admin node div with profile, position, and name
    const createAdminNodeDiv = (admin, positionOverride = null) => {
        const adminNode = document.createElement('div');
        adminNode.className = 'org-node admin-node';
        adminNode.style.display = 'flex';
        adminNode.style.flexDirection = 'column';
        adminNode.style.alignItems = 'center';

        const profileDiv = document.createElement('div');
        profileDiv.className = 'profile-circle';
        
        const img = document.createElement('img');
        img.alt = `${admin.first_name}'s Profile`;

        if (admin.profile_picture_url) {
            img.src = admin.profile_picture_url;
        } else {
            img.src = '/static/images/your_image_name.jpg'; // Ensure this path is correct
        }
        profileDiv.appendChild(img);
        adminNode.appendChild(profileDiv);

        const textContainer = document.createElement('div');
        textContainer.style.textAlign = 'center';

        const positionSpan = document.createElement('span');
        positionSpan.className = 'position-text';
        positionSpan.textContent = (positionOverride || admin.position).toUpperCase();
        textContainer.appendChild(positionSpan);

        const nameSpan = document.createElement('span');
        nameSpan.className = 'name-text';
        nameSpan.textContent = ` - ${admin.first_name} ${admin.last_name}`;
        textContainer.appendChild(nameSpan);

        adminNode.appendChild(textContainer);
        return adminNode;
    };

    /**
     * Creates the complete HTML structure for the organizational chart.
     * @param {Array<Object>} admins - An array of admin objects fetched from the backend.
     * @returns {DocumentFragment} A document fragment containing the full HTML chart structure.
     */
    function createOrgChartDisplayElements(admins) {
        const fragment = document.createDocumentFragment();

        const organizationName = (admins.length > 0 && admins[0].organization_name) ?
            String(admins[0].organization_name).toUpperCase() :
            'UNKNOWN ORGANIZATION';

        const organizationNameNode = document.createElement('div');
        organizationNameNode.className = 'org-node org-root';
        organizationNameNode.textContent = organizationName;
        fragment.appendChild(organizationNameNode);

        const positions = {
            'President': [],
            'Vice President-Internal': [],
            'Vice President-External': [],
            'Secretary': [],
            'Treasurer': [],
            'Auditor': [],
            'Public Relation Officer': [],
            'Adviser': []
        };
        admins.forEach(admin => {
            if (positions[admin.position]) {
                positions[admin.position].push(admin);
            }
        });

        let previousGroupAdded = false;

        // PRESIDENT(S)
        if (positions['President'].length > 0) {
            const lineToPresident = document.createElement('div');
            lineToPresident.classList.add('org-line', 'org-vertical-to-branch');
            fragment.appendChild(lineToPresident);

            const presidentBranchContainer = document.createElement('div');
            presidentBranchContainer.classList.add('org-branch-container');

            positions['President'].forEach((admin, index) => {
                const presidentNode = createAdminNodeDiv(admin);
                presidentBranchContainer.appendChild(presidentNode);
                if (index < positions['President'].length - 1) {
                    const horizontalLine = document.createElement('div');
                    horizontalLine.classList.add('org-line', 'org-line-horizontal');
                    presidentBranchContainer.appendChild(horizontalLine);
                }
            });
            fragment.appendChild(presidentBranchContainer);
            previousGroupAdded = true;
        }

        // VPs (Internal/External)
        const vps = [...positions['Vice President-Internal'], ...positions['Vice President-External']];
        if (vps.length > 0) {
            const lineToVPs = document.createElement('div');
            lineToVPs.classList.add('org-line', 'org-vertical-to-branch');
            fragment.appendChild(lineToVPs);

            const vpBranchContainer = document.createElement('div');
            vpBranchContainer.classList.add('org-branch-container');

            vps.forEach((admin, index) => {
                const vpNode = createAdminNodeDiv(admin);
                vpBranchContainer.appendChild(vpNode);
                if (index < vps.length - 1) {
                    const horizontalLine = document.createElement('div');
                    horizontalLine.classList.add('org-line', 'org-line-horizontal');
                    vpBranchContainer.appendChild(horizontalLine);
                }
            });
            fragment.appendChild(vpBranchContainer);
            previousGroupAdded = true;
        }

        // Other core positions
        const otherCorePositions = [
            ...positions['Secretary'],
            ...positions['Treasurer'],
            ...positions['Auditor'],
            ...positions['Public Relation Officer']
        ];

        if (otherCorePositions.length > 0) {
            if (previousGroupAdded) {
                const lineToOthers = document.createElement('div');
                lineToOthers.classList.add('org-line', 'org-vertical-to-branch');
                fragment.appendChild(lineToOthers);
            }

            const otherPositionsBranchContainer = document.createElement('div');
            otherPositionsBranchContainer.classList.add('org-branch-container');

            otherCorePositions.forEach((admin, index) => {
                const adminNode = createAdminNodeDiv(admin);
                otherPositionsBranchContainer.appendChild(adminNode);
                if (index < otherCorePositions.length - 1) {
                    const horizontalLine = document.createElement('div');
                    horizontalLine.classList.add('org-line', 'org-line-horizontal');
                    otherPositionsBranchContainer.appendChild(horizontalLine);
                }
            });
            fragment.appendChild(otherPositionsBranchContainer);
            previousGroupAdded = true;
        }

        // Advisers
        if (positions['Adviser'].length > 0) {
            if (previousGroupAdded) {
                const lineToAdvisers = document.createElement('div');
                lineToAdvisers.classList.add('org-line', 'org-vertical-to-branch');
                fragment.appendChild(lineToAdvisers);
            }

            const adviserSectionHeader = document.createElement('h4');
            adviserSectionHeader.textContent = 'ADVISERS';
            Object.assign(adviserSectionHeader.style, {
                marginTop: '2rem',
                color: 'var(--org-text-primary)',
                fontWeight: '600',
                width: '100%',
                textAlign: 'center',
                paddingBottom: '0.5rem',
                borderBottom: '2px solid var(--org-border-medium)'
            });
            fragment.appendChild(adviserSectionHeader);

            const adviserGroupContainer = document.createElement('div');
            adviserGroupContainer.classList.add('org-branch-container');

            positions['Adviser'].forEach((admin, index) => {
                const adviserNode = createAdminNodeDiv(admin, 'Adviser');
                adviserGroupContainer.appendChild(adviserNode);
                if (index < positions['Adviser'].length - 1) {
                    const horizontalLine = document.createElement('div');
                    horizontalLine.classList.add('org-line', 'org-line-horizontal');
                    adviserGroupContainer.appendChild(horizontalLine);
                }
            });
            fragment.appendChild(adviserGroupContainer);
        }

        return fragment;
    }

    async function fetchAndRenderOrgChart() {
        if (!organizationChartContainer) {
            console.error('Organizational chart container not found.');
            return;
        }

        organizationChartContainer.innerHTML = '<p class="loading-message">Loading organizational chart...</p>';

        try {
            const response = await fetch('/api/admin/org_chart_data');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const admins = await response.json();

            organizationChartContainer.innerHTML = '';
            const chartElements = createOrgChartDisplayElements(admins);
            organizationChartContainer.appendChild(chartElements);

        } catch (error) {
            console.error('Error fetching or rendering organizational chart:', error);
            organizationChartContainer.innerHTML = '<p class="error-message">Failed to load organizational chart. Please try again later.</p>';
        }
    }

    // Ensure elements exist before attaching listeners
    if (orgChartButton && orgChartModal && closeButton) {
        orgChartButton.addEventListener('click', function() {
            orgChartModal.style.display = 'flex'; // Use 'flex' to make it visible and centered
            fetchAndRenderOrgChart();
        });

        closeButton.addEventListener('click', function() {
            orgChartModal.style.display = 'none'; // Hide it
        });

        window.addEventListener('click', function(event) {
            if (event.target === orgChartModal) {
                orgChartModal.style.display = 'none'; // Hide it
            }
        });
    } else {
        console.warn("Organizational chart elements not found. Modal functionality will not be available.");
    }


    // Basic modal styling for demonstration and ensuring responsive layout
    const style = document.createElement('style');
    style.innerHTML = ` 
        /* Modal Styles */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0,0,0,0.7);
            justify-content: center;
            align-items: center;
            padding: 20px;
        }

        .modal-content {
            background-color: var(--org-card-bg);
            margin: auto;
            padding: 30px;
            border-radius: var(--org-radius-lg);
            box-shadow: var(--org-shadow-md);
            width: 90%;
            max-width: 1200px;
            position: relative;
            display: flex;
            flex-direction: column;
            gap: 20px;
            max-height: 90vh;
            overflow-y: auto;
        }

        .modal-close-button {
            color: var(--org-text-secondary);
            position: absolute;
            top: 15px;
            right: 25px;
            font-size: 32px;
            font-weight: bold;
            cursor: pointer;
            transition: color 0.3s ease;
        }

        .modal-close-button:hover,
        .modal-close-button:focus {
            color: var(--org-text-primary);
            text-decoration: none;
            cursor: pointer;
        }

        .modal-body {
            flex-grow: 1;
            overflow-y: auto;
        }

        .modal-body table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            border-radius: var(--org-radius-md);
            overflow: hidden;
        }

        .modal-body th,
        .modal-body td {
            border: 1px solid var(--org-border-medium);
            padding: 12px 15px;
            text-align: left;
            font-size: 0.95em;
        }

        .modal-body th {
            background-color: var(--org-table-header-bg-payments);
            color: var(--org-table-header-text-payments);
            font-weight: 600;
            text-transform: uppercase;
        }

        .modal-body tr:nth-child(even) {
            background-color: var(--org-background-light-alt-darker);
        }

        .modal-body tr:hover {
            background-color: var(--org-hover-effect);
            transition: background-color 0.2s ease;
        }

        /* Organizational Chart Specific Styles */
        .organization-chart-display {
            --org-node-bg: #e0f7fa; /* Light blue */
            --org-node-border: #00bcd4; /* Cyan */
            --org-root-bg: #80deea; /* Slightly darker blue */
            --org-root-border: #0097a7; /* Darker cyan */
            --org-line-color: #78909c; /* Blue-grey */
            --org-text-primary: #263238; /* Dark text */
            --org-text-secondary: #455a64; /* Slightly lighter dark text */
            --org-border-medium: #b0bec5; /* Medium blue-grey for lines */

            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
            font-family: Arial, sans-serif;
            color: var(--org-text-primary);
        }

        .org-node {
            background-color: var(--org-node-bg);
            border: 1px solid var(--org-node-border);
            border-radius: 8px;
            padding: 10px 15px;
            margin: 10px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            min-width: 150px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            flex-shrink: 0;
        }

        .org-node.org-root {
            background-color: var(--org-root-bg);
            border: 2px solid var(--org-root-border);
            padding: 15px 25px;
            font-size: 1.2rem;
            font-weight: bold;
            color: white;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }

        .profile-circle {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background-color: #f0f0f0;
            color: #555;
            display: flex;
            justify-content: center;
            align-items: center;
            font-weight: bold;
            font-size: 1.5rem;
            margin-bottom: 8px;
            overflow: hidden;
            border: 2px solid #ddd;
        }

        .profile-circle img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .position-text {
            font-weight: bold;
            font-size: 0.95rem;
            color: var(--org-text-primary);
        }

        .name-text {
            color: #444;
            font-size: 0.85rem;
            display: block;
            margin-top: 4px;
        }

        .org-branch-container {
            display: flex;
            justify-content: center;
            align-items: flex-start;
            flex-wrap: wrap;
            gap: 1.5rem;
            margin-bottom: 20px;
        }

        .org-line {
            background-color: var(--org-line-color);
            flex-shrink: 0;
        }

        .org-vertical-to-branch {
            width: 2px;
            height: 30px;
            margin: 0 auto;
        }

        .org-line-horizontal {
            height: 2px;
            width: 30px;
            margin: 0 5px;
            align-self: center;
        }

        .adviser-group {
            margin-top: 30px;
            border-top: 1px dashed #ccc;
            padding-top: 20px;
            text-align: center;
            width: 100%;
        }

        .adviser-group h4 {
            color: #666;
            margin-bottom: 15px;
            font-size: 1.1rem;
            font-weight: 600;
        }

        .org-node.adviser-node {
            border: 1px dashed #b0b0b0;
            background-color: #f9f9f9;
        }

        .loading-message, .error-message {
            text-align: center;
            padding: 20px;
            color: #666;
            font-style: italic;
        }

        .error-message {
            color: #dc3545;
            font-weight: bold;
        }

        /* Media queries for responsiveness */
        @media (max-width: 768px) {
            .modal-content {
                width: 95%;
                margin: 2.5vh auto;
                padding: 15px;
            }
            .org-branch-container {
                flex-direction: column;
                gap: 0.5rem;
            }
            .org-line.org-line-horizontal {
                display: none;
            }
            .org-node {
                min-width: unset;
                width: 90%;
                margin: 8px auto;
            }
            .org-node.org-root {
                min-width: unset;
                width: 90%;
                margin-bottom: 15px;
            }
            
            .profile-circle {
                width: 50px;
                height: 50px;
                font-size: 1.2rem;
            }
            .position-text {
                font-size: 0.85rem;
            }
            .name-text {
                font-size: 0.75rem;
            }
        }
    `;
    document.head.appendChild(style);
});
