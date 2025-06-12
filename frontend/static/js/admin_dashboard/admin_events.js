document.addEventListener('DOMContentLoaded', function() {
    // --- Event Creation Form Toggle ---
    const createEventInput = document.querySelector('.create-event-input');
    const createEventFormFields = document.querySelector('.create-event-form-fields'); // Using consistent naming
    const backToEventsLink = document.querySelector('.back-to-events');

    // Show form when input is clicked
    if (createEventInput && createEventFormFields && backToEventsLink) {
        createEventInput.addEventListener('click', function() {
            this.style.display = 'none';
            createEventFormFields.style.display = 'block';
            backToEventsLink.style.display = 'block';
        });
    }

    // Hide form and show input when "Back to Events" is clicked
    if (backToEventsLink && createEventInput && createEventFormFields) { // Ensure all elements exist
        backToEventsLink.addEventListener('click', function(event) {
            event.preventDefault(); // Prevent default link behavior (page refresh)
            createEventInput.style.display = 'block';
            createEventFormFields.style.display = 'none';
            this.style.display = 'none'; // Hide the "Back to Events" link itself
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
    // Please confirm if the .image-on-hover elements are still part of your HTML.
    // If not, you can remove this entire block.
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
    const viewDetailsButtons = document.querySelectorAll('.view-details-button');

    const modalEventImage = document.getElementById('modalEventImage');
    const modalEventTitle = document.getElementById('modalEventTitle');
    const modalEventClassification = document.getElementById('modalEventClassification');
    const modalEventDescription = document.getElementById('modalEventDescription');
    const modalEventDate = document.getElementById('modalEventDate');
    const modalEventTime = document.getElementById('modalEventTime');
    const modalEventLocation = document.getElementById('modalEventLocation');
    const modalEventParticipants = document.getElementById('modalEventParticipants');

    // Function to open the modal
    function openModal(eventData) {
        modalEventImage.src = eventData.imageUrl;
        modalEventTitle.textContent = eventData.title;

        // Update classification tag
        modalEventClassification.textContent = eventData.classification;
        modalEventClassification.className = ''; // Clear existing classes
        modalEventClassification.classList.add(`tag-${eventData.classification.toLowerCase()}`);

        modalEventDescription.textContent = eventData.description;
        modalEventDate.textContent = eventData.date;
        modalEventTime.textContent = eventData.time;
        modalEventLocation.textContent = eventData.location;
        modalEventParticipants.textContent = `${eventData.joinedCount}/${eventData.maxParticipants}`;

        modal.style.display = 'flex'; // Use flex to center the modal
    }

    // Function to close the modal
    function closeModal() {
        modal.style.display = 'none';
    }

    // Event listeners for opening the modal
    viewDetailsButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            event.stopPropagation(); // Prevent card click if there's a listener on the card itself
            const card = this.closest('.event-card');
            if (card) {
                const eventData = {
                    title: card.dataset.title,
                    classification: card.dataset.classification,
                    description: card.dataset.description,
                    date: card.dataset.date,
                    time: card.dataset.time,
                    location: card.dataset.location,
                    maxParticipants: card.dataset.maxParticipants,
                    joinedCount: card.dataset.joinedCount,
                    imageUrl: card.dataset.imageUrl
                };
                openModal(eventData);
            }
        });
    });

    // Event listener for closing the modal using the close button
    if (closeButton) {
        closeButton.addEventListener('click', closeModal);
    }

    // Event listener for closing the modal when clicking outside of it
    if (modal) {
        modal.addEventListener('click', function(event) {
            if (event.target === modal) {
                closeModal();
            }
        });
    }

    // Optional: Close modal with Escape key
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape' && modal.style.display === 'flex') {
            closeModal();
        }
    });
});