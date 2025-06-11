document.addEventListener('DOMContentLoaded', () => {
    // --- Bulletin Board Post Logic ---
    const createPostInput = document.querySelector('.create-post-input');
    const createPostForm = document.querySelector('.create-post-form-fields');
    const backToBulletinLink = document.querySelector('.back-to-bulletin');

    if (createPostInput) {
        createPostInput.addEventListener('click', function () {
            this.style.display = 'none';
            createPostForm.style.display = 'block';
            backToBulletinLink.style.display = 'block';
        });
    }

    if (backToBulletinLink) {
        backToBulletinLink.addEventListener('click', function (event) {
            event.preventDefault();
            createPostInput.style.display = 'block';
            createPostForm.style.display = 'none';
            this.style.display = 'none';
        });
    }

    // --- Wiki Post Related Logic ---
    function toggleEditMode(postId, showEdit) {
        const postCard = document.getElementById(`wiki-post-${postId}`);
        if (postCard) {
            const displayMode = postCard.querySelector('.wiki-post-display-mode');
            const editMode = postCard.querySelector('.wiki-post-edit-mode');

            if (showEdit) {
                if (displayMode) displayMode.style.display = 'none';
                if (editMode) editMode.style.display = 'block';
                postCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
            } else {
                if (displayMode) displayMode.style.display = 'block';
                if (editMode) editMode.style.display = 'none';
            }
        }
    }

    const urlParams = new URLSearchParams(window.location.search);
    const editPostId = urlParams.get('edit_wiki_post_id');

    if (editPostId) {
        toggleEditMode(editPostId, true);
    }

    document.querySelectorAll('.wiki-edit-button').forEach(button => {
        button.addEventListener('click', (event) => {
            const postId = event.target.dataset.postId;
            toggleEditMode(postId, true);
        });
    });

    document.querySelectorAll('.cancel-edit-button').forEach(button => {
        button.addEventListener('click', (event) => {
            const postId = event.target.dataset.postId;
            toggleEditMode(postId, false);
        });
    });

    document.querySelectorAll('.edit-wiki-post-form').forEach(form => {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const postId = form.dataset.postId || form.querySelector('input[name="post_id"]').value;
            const formData = new FormData(form);

            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    const messageBox = document.createElement('div');
                    messageBox.className = 'message-box success';
                    messageBox.textContent = 'Post updated successfully!';
                    document.body.appendChild(messageBox);
                    setTimeout(() => messageBox.remove(), 3000);
                    toggleEditMode(postId, false);
                    window.location.reload();
                } else {
                    const errorText = await response.text();
                    const messageBox = document.createElement('div');
                    messageBox.className = 'message-box error';
                    messageBox.textContent = `Failed to update post: ${errorText}`;
                    document.body.appendChild(messageBox);
                    setTimeout(() => messageBox.remove(), 3000);
                }
            } catch (error) {
                console.error('Error submitting edit form:', error);
                const messageBox = document.createElement('div');
                messageBox.className = 'message-box error';
                messageBox.textContent = 'An error occurred during submission.';
                document.body.appendChild(messageBox);
                setTimeout(() => messageBox.remove(), 3000);
            }
        });
    });

    // --- Create Wiki Post Logic ---
    const createWikiInput = document.querySelector('.create-wiki-input');
    const createWikiPostForm = document.querySelector('.create-wiki-post-form');
    const cancelCreateWikiButton = document.querySelector('.cancel-create-wiki-button');

    if (createWikiInput && createWikiPostForm && cancelCreateWikiButton) {
        createWikiInput.addEventListener('click', function() {
            createWikiInput.style.display = 'none';
            createWikiPostForm.style.display = 'flex';
            cancelCreateWikiButton.style.display = 'inline-block';
        });

        cancelCreateWikiButton.addEventListener('click', function() {
            createWikiInput.style.display = 'block';
            createWikiPostForm.style.display = 'none';
            cancelCreateWikiButton.style.display = 'none';
            createWikiPostForm.reset();
        });
    }

    // --- Organizational Chart Logic ---
    const orgChartButton = document.getElementById('viewOrgChartButton');
    const orgChartModal = document.getElementById('orgChartModal');
    const closeButton = orgChartModal.querySelector('.close-button');
    const organizationChartContainer = document.getElementById('organizationChartContainer');
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
            img.src = '/static/images/your_image_name.jpg'; 
        }
        profileDiv.appendChild(img);
        adminNode.appendChild(profileDiv);

        // Position and Name Text Container
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

        // VPs (Internal/External) - assume they report to President (or the President group)
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

        // --- Advisers (as a separate section) ---
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

    // Function to fetch and render the organizational chart content
    async function fetchAndRenderOrgChart() {
        if (!organizationChartContainer) return; 

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

    // Event listener to open the modal
    orgChartButton.addEventListener('click', function() {
        orgChartModal.style.display = 'flex';
        fetchAndRenderOrgChart(); 
    });

    // Event listener to close the modal
    closeButton.addEventListener('click', function() {
        orgChartModal.style.display = 'none';
    });

    // Close the modal if the user clicks outside of it
    window.addEventListener('click', function(event) {
        if (event.target === orgChartModal) {
            orgChartModal.style.display = 'none';
        }
    });

    // Basic modal styling for demonstration and ensuring responsive layout
    const style = document.createElement('style');
    style.innerHTML = `  
      
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
       
        .name-text {
            color: #444; 
            font-size: 0.85rem;
            display: block; 
            margin-top: 4px; 
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

        .message-box {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            padding: 10px 20px;
            border-radius: 5px;
            color: white;
            z-index: 1001;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
            opacity: 0;
            transition: opacity 0.5s ease-in-out;
        }     

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