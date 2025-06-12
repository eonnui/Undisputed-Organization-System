document.addEventListener('DOMContentLoaded', function() {
    // --- Event Creation Form Toggle ---
    const createEventInput = document.querySelector('.create-event-input');
    const createEventFormFields = document.querySelector('.create-event-form-fields');
    const backToEventsLink = document.querySelector('.back-to-events');

    if (createEventInput && createEventFormFields && backToEventsLink) {
        createEventInput.addEventListener('click', function() {
            this.style.display = 'none';
            createEventFormFields.style.display = 'block';
            backToEventsLink.style.display = 'block';
        });

        backToEventsLink.addEventListener('click', function(event) {
            event.preventDefault();
            createEventInput.style.display = 'block';
            createEventFormFields.style.display = 'none';
            this.style.display = 'none';
        });
    }

    // --- Client-side Date Restriction for Event Creation Form ---
    const dateTimeInput = document.getElementById('date');
    if (dateTimeInput) {
        const now = new Date();
        const year = now.getFullYear();
        const month = (now.getMonth() + 1).toString().padStart(2, '0');
        const day = now.getDate().toString().padStart(2, '0');
        const hours = now.getHours().toString().padStart(2, '0');
        const minutes = now.getMinutes().toString().padStart(2, '0');
        dateTimeInput.min = `${year}-${month}-${day}T${hours}:${minutes}`;
    }

    // --- Image on Hover Functionality (If still in HTML) ---
    const eventTags = document.querySelectorAll('.event-tag');
    eventTags.forEach(tag => {
        const imageOnHover = tag.querySelector('.image-on-hover');
        if (imageOnHover) {
            tag.addEventListener('mouseenter', () => {
                imageOnHover.style.display = 'block';
                imageOnHover.style.position = 'absolute';
                imageOnHover.style.zIndex = '10';
                imageOnHover.style.maxWidth = '200px';
                imageOnHover.style.height = 'auto';
                imageOnHover.style.border = '1px solid #ccc';
                imageOnHover.style.borderRadius = '8px';
                imageOnHover.style.boxShadow = '0 4px 8px rgba(0,0,0,0.2)';
            });

            tag.addEventListener('mouseleave', () => {
                imageOnHover.style.display = 'none';
            });
        }
    });

    // --- Modal Functionality ---
    const modal = document.getElementById('eventDetailsModal');
    const closeButton = document.querySelector('.modal-close-button');
    const clickableCards = document.querySelectorAll('.event-card.clickable-card');

    const modalEventImage = document.getElementById('modalEventImage');
    const modalEventTitle = document.getElementById('modalEventTitle');
    const modalEventClassification = document.getElementById('modalEventClassification');
    const modalEventDescription = document.getElementById('modalEventDescription');
    const modalEventDate = document.getElementById('modalEventDate');
    const modalEventTime = document.getElementById('modalEventTime');
    const modalEventLocation = document.getElementById('modalEventLocation');
    const modalEventParticipantsCount = document.getElementById('modalEventParticipantsCount'); // This ID is now inside the header
    const modalParticipantsList = document.getElementById('modalParticipantsList');

    // Function to open the modal
    function openModal(eventData) {
        modalEventImage.src = eventData.imageUrl;
        modalEventTitle.textContent = eventData.title;

        modalEventClassification.textContent = eventData.classification;
        modalEventClassification.className = ''; // Clear existing classes
        modalEventClassification.classList.add(`tag-${eventData.classification.toLowerCase()}`);

        modalEventDescription.textContent = eventData.description;
        modalEventDate.textContent = eventData.date;
        modalEventTime.textContent = eventData.time;
        modalEventLocation.textContent = eventData.location;
        // Update the participant count in its new location
        modalEventParticipantsCount.textContent = `(${eventData.joinedCount}/${eventData.maxParticipants})`; 

        // Clear previous participant list
        modalParticipantsList.innerHTML = '';

        // Populate participants list
        if (eventData.participants && eventData.participants.length > 0) {
            eventData.participants.forEach(participant => {
                const listItem = document.createElement('li');
                listItem.textContent = participant.username || participant; // Handles both object {username: "..."} and plain string
                modalParticipantsList.appendChild(listItem);
            });
        } else {
            const listItem = document.createElement('li');
            listItem.textContent = 'No participants yet.';
            modalParticipantsList.appendChild(listItem);
        }

        modal.style.display = 'flex';
    }

    // Event listeners for opening the modal by clicking the entire card
    clickableCards.forEach(card => {
        card.addEventListener('click', function(event) {
            // Prevent modal from opening if delete button/form is clicked
            if (event.target.closest('.delete-button') || event.target.closest('.delete-form')) {
                return;
            }

            // Parse participants JSON data
            let participants = [];
            try {
                if (this.dataset.participantsJson) {
                    participants = JSON.parse(this.dataset.participantsJson);
                }
            } catch (e) {
                console.error("Error parsing participants JSON:", e);
            }

            const eventData = {
                title: this.dataset.title,
                classification: this.dataset.classification,
                description: this.dataset.description,
                date: this.dataset.date,
                time: this.dataset.time,
                location: this.dataset.location,
                maxParticipants: this.dataset.maxParticipants,
                joinedCount: this.dataset.joinedCount,
                imageUrl: this.dataset.imageUrl,
                participants: participants
            };
            openModal(eventData);
        });

        // Add keyboard accessibility: allow opening modal with Enter key
        card.addEventListener('keydown', function(event) {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();

                if (document.activeElement.closest('.delete-button') || document.activeElement.closest('.delete-form')) {
                    return;
                }

                let participants = [];
                try {
                    if (this.dataset.participantsJson) {
                        participants = JSON.parse(this.dataset.participantsJson);
                    }
                } catch (e) {
                    console.error("Error parsing participants JSON:", e);
                }

                const eventData = {
                    title: this.dataset.title,
                    classification: this.dataset.classification,
                    description: this.dataset.description,
                    date: this.dataset.date,
                    time: this.dataset.time,
                    location: this.dataset.location,
                    maxParticipants: this.dataset.maxParticipants,
                    joinedCount: this.dataset.joinedCount,
                    imageUrl: this.dataset.imageUrl,
                    participants: participants
                };
                openModal(eventData);
            }
        });
    });

    // Event listeners for closing the modal
    if (closeButton) {
        closeButton.addEventListener('click', closeModal);
    }
    if (modal) {
        modal.addEventListener('click', function(event) {
            if (event.target === modal) {
                closeModal();
            }
        });
    }
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape' && modal.style.display === 'flex') {
            closeModal();
        }
    });
});