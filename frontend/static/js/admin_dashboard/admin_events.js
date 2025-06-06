/* JavaScript for toggling the create event form */
    const createEventInput = document.querySelector('.create-event-input');
    const createEventForm = document.querySelector('.create-event-form-fields');
    const backToEventsLink = document.querySelector('.back-to-events');

    if (createEventInput) {
        createEventInput.addEventListener('click', function () {
            this.style.display = 'none';
            createEventForm.style.display = 'block';
            backToEventsLink.style.display = 'block';
        });
    }

    if (backToEventsLink) {
        backToEventsLink.addEventListener('click', function (event) {
            event.preventDefault();
            createEventInput.style.display = 'block';
            createEventForm.style.display = 'none';
            this.style.display = 'none';
        });
    }