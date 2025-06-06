const eventsPageUrl = "/Events"; 

document.addEventListener('DOMContentLoaded', function() {
    fetchUpcomingEvents();

    loadFAQs();

    document.querySelectorAll('.announcement-card').forEach(card => {
        card.style.cursor = 'pointer';
        card.addEventListener('click', function() {
            window.location.href = this.dataset.url;
        });
    });

    const upcomingEventsTitle = document.getElementById('upcoming-events-title');
    if (upcomingEventsTitle) {
        upcomingEventsTitle.style.cursor = 'pointer';
        upcomingEventsTitle.addEventListener('click', function() {
            window.location.href = upcomingEventsTitle.dataset.eventsUrl;
        });
    }
});

async function fetchUpcomingEvents() {
    const eventsContainer = document.getElementById('events-container');

    try {
        const response = await fetch('/api/events/upcoming_summary');

        if (!response.ok) {
            throw new Error('Failed to fetch events');
        }

        const events = await response.json();
        displayEvents(events);

    } catch (error) {
        console.error('Error fetching events:', error);
        displayFallbackEvents();
    }
}

function displayEvents(events) {
    const eventsContainer = document.getElementById('events-container');

    eventsContainer.innerHTML = '';

    if (!events || events.length === 0) {
        eventsContainer.innerHTML = '<div class="empty-state">No upcoming events at this time.</div>';
        return;
    }

    events.forEach(event => {
        const eventItem = document.createElement('div');
        eventItem.className = 'event-item';
        eventItem.style.cursor = 'pointer';
        eventItem.addEventListener('click', function() {
            window.location.href = eventsPageUrl;
        });

        const classificationClass = event.classification ? event.classification.toLowerCase().replace(/\s/g, '-') : 'general';
        const eventTag = `<span class="event-tag tag-${classificationClass}">${event.classification || 'Event'}</span>`;

        eventItem.innerHTML = `
            ${eventTag}
            <div class="event-title">${event.title}</div>
            <div class="event-date">${formatDate(event.date)}</div>
            <div class="event-location">${event.location}</div>
        `;

        eventsContainer.appendChild(eventItem);
    });
}

function displayFallbackEvents() {
    const fallbackEvents = [
        {
            event_id: 1,
            title: "Welcome Freshers Meet & Greet",
            date: new Date("2025-08-15T10:00:00"),
            location: "University Grand Hall",
            classification: "Social"
        },
        {
            event_id: 2,
            title: "Introduction to Research Methods",
            date: new Date("2025-08-20T14:00:00"),
            location: "Library Conference Room",
            classification: "Academic"
        },
        {
            event_id: 3,
            title: "Campus Clean-up Drive",
            date: new Date("2025-09-01T09:00:00"),
            location: "Central Campus Grounds",
            classification: "Community"
        }
    ];
    displayEvents(fallbackEvents);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return date.toLocaleDateString('en-US', options);
}

const faqData = [
    {
        question: "What is the schedule for student orientation?",
        answer: "The student orientation will be held on August 20, 2025, from 9:00 AM to 12:00 PM in the main auditorium."
    },
    {
        question: "How do I access the online learning platform?",
        answer: "You can access the online learning platform by visiting our website and clicking on the 'Student Portal' link. Use your student ID and password to log in."
    },
    {
        question: "Who should I contact for academic advising?",
        answer: "For academic advising, please contact the Dean's office of your respective faculty. You can find their contact information on the university website under the 'Academics' section."
    },
    {
        question: "How do I apply for scholarships and financial aid?",
        answer: "Scholarship and financial aid applications are available through the Financial Aid Office. Visit the Financial Aid section on our website for more information."
    }
];

function loadFAQs() {
    const faqContainer = document.getElementById('faq-container');

    if (faqData.length === 0) {
        faqContainer.innerHTML = '<div class="empty-state">No FAQs available at this time.</div>';
        return;
    }

    faqData.forEach((faq, index) => {
        const faqItem = document.createElement('div');
        faqItem.className = 'faq-item';
        faqItem.id = `faq-${index}`;

        faqItem.innerHTML = `
            <div class="faq-question">${faq.question}</div>
            <div class="faq-answer">${faq.answer}</div>
        `;

        faqContainer.appendChild(faqItem);

        const questionElement = faqItem.querySelector('.faq-question');
        questionElement.addEventListener('click', function() {
            faqItem.classList.toggle('open');
        });
    });
}