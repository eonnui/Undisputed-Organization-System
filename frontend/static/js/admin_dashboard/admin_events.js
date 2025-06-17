document.addEventListener("DOMContentLoaded", function () {
  const createEventInput = document.querySelector(".create-event-input");
  const createEventFormFields = document.querySelector(
    ".create-event-form-fields"
  );
  const backToEventsLink = document.querySelector(".back-to-events");

  if (createEventInput && createEventFormFields && backToEventsLink) {
    createEventInput.addEventListener("click", function () {
      this.style.display = "none";
      createEventFormFields.style.display = "block";
      backToEventsLink.style.display = "block";
    });

    backToEventsLink.addEventListener("click", function (event) {
      event.preventDefault();
      createEventInput.style.display = "block";
      createEventFormFields.style.display = "none";
      this.style.display = "none";
    });
  }

  const dateTimeInput = document.getElementById("date");
  if (dateTimeInput) {
    const now = new Date();
    const year = now.getFullYear();
    const month = (now.getMonth() + 1).toString().padStart(2, "0");
    const day = now.getDate().toString().padStart(2, "0");
    const hours = now.getHours().toString().padStart(2, "0");
    const minutes = now.getMinutes().toString().padStart(2, "0");
    dateTimeInput.min = `${year}-${month}-${day}T${hours}:${minutes}`;
  }

  const eventTags = document.querySelectorAll(".event-tag");
  eventTags.forEach((tag) => {
    const imageOnHover = tag.querySelector(".image-on-hover");
    if (imageOnHover) {
      tag.addEventListener("mouseenter", () => {
        imageOnHover.style.display = "block";
        imageOnHover.style.position = "absolute";
        imageOnHover.style.zIndex = "10";
        imageOnHover.style.maxWidth = "200px";
        imageOnHover.style.height = "auto";
        imageOnHover.style.border = "1px solid #ccc";
        imageOnHover.style.borderRadius = "8px";
        imageOnHover.style.boxShadow = "0 4px 8px rgba(0,0,0,0.2)";
      });

      tag.addEventListener("mouseleave", () => {
        imageOnHover.style.display = "none";
      });
    }
  });

  const globalModal = document.getElementById("global-modal");
  const globalModalBody = document.getElementById("modal-body");
  const globalModalCloseButton = globalModal
    ? globalModal.querySelector(".modal-close-btn")
    : null;

  const clickableCards = document.querySelectorAll(
    ".event-card.clickable-card"
  );

  async function openGlobalModal(eventData) {
    if (!globalModal || !globalModalBody) {
      console.error("Global modal elements not found.");
      return;
    }

    globalModalBody.innerHTML = `
            <div class="modal-two-columns">
                <div class="modal-left-column">
                    <img src="${
                      eventData.imageUrl
                    }" alt="Event Image" class="modal-image">
                    <h3 id="modalEventTitle">${eventData.title}</h3>
                    <p class="modal-classification"><span id="modalEventClassification" class="tag-${eventData.classification.toLowerCase()}">${
      eventData.classification
    }</span></p>
                    <p id="modalEventDescription">${eventData.description}</p>
                    <p><strong>Date:</strong> <span id="modalEventDate">${
                      eventData.date
                    }</span></p>
                    <p><strong>Time:</strong> <span id="modalEventTime">${
                      eventData.time
                    }</span></p>
                    <p><strong>Location:</strong> <span id="modalEventLocation">${
                      eventData.location
                    }</span></p>
                </div>
                <div class="modal-right-column">
                    <h4 class="participants-header">Participants List <span id="modalEventParticipantsCount" class="participants-header-count">(${
                      eventData.joinedCount
                    }/${eventData.maxParticipants})</span></h4>
                    <ul id="modalParticipantsList" class="participants-list">
                        <li>Loading participants...</li>
                    </ul>
                </div>
            </div>
        `;

    const currentModalParticipantsList = globalModalBody.querySelector(
      "#modalParticipantsList"
    );

    const eventId = eventData.eventId;
    const participantsUrl = `/api/events/${eventId}/participants`;

    try {
      const response = await fetch(participantsUrl);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          `Error ${response.status}: ${
            errorData.detail || "Failed to fetch participants."
          }`
        );
      }
      const participants = await response.json();

      currentModalParticipantsList.innerHTML = "";
      if (participants && participants.length > 0) {
        participants.forEach((participant) => {
          const listItem = document.createElement("li");
          listItem.textContent =
            participant.name +
            (participant.section ? ` (${participant.section})` : "");
          currentModalParticipantsList.appendChild(listItem);
        });
      } else {
        const listItem = document.createElement("li");
        listItem.textContent = "No participants yet.";
        currentModalParticipantsList.appendChild(listItem);
      }
    } catch (error) {
      console.error("Error fetching participants:", error);
      currentModalParticipantsList.innerHTML = `<li>Error loading participants: ${
        error.message || "Unknown error"
      }.</li>`;
    }

    globalModal.classList.add("is-visible");
  }

  function closeGlobalModal() {
    if (globalModal) {
      globalModal.classList.remove("is-visible");
      globalModalBody.innerHTML = "";
    }
  }

  clickableCards.forEach((card) => {
    card.addEventListener("click", function (event) {
      if (
        event.target.closest(".delete-button") ||
        event.target.closest(".delete-form")
      ) {
        return;
      }

      const eventData = {
        eventId: this.dataset.eventId,
        title: this.dataset.title,
        classification: this.dataset.classification,
        description: this.dataset.description,
        date: this.dataset.date,
        time: this.dataset.time,
        location: this.dataset.location,
        maxParticipants: this.dataset.maxParticipants,
        joinedCount: this.dataset.joinedCount,
        imageUrl: this.dataset.imageUrl,
      };
      openGlobalModal(eventData);
    });

    card.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();

        if (
          document.activeElement.closest(".delete-button") ||
          document.activeElement.closest(".delete-form")
        ) {
          return;
        }

        const eventData = {
          eventId: this.dataset.eventId,
          title: this.dataset.title,
          classification: this.dataset.classification,
          description: this.dataset.description,
          date: this.dataset.date,
          time: this.dataset.time,
          location: this.dataset.location,
          maxParticipants: this.dataset.maxParticipants,
          joinedCount: this.dataset.joinedCount,
          imageUrl: this.dataset.imageUrl,
        };
        openGlobalModal(eventData);
      }
    });
  });

  if (globalModalCloseButton) {
    globalModalCloseButton.addEventListener("click", closeGlobalModal);
  }

  if (globalModal) {
    globalModal.addEventListener("click", function (event) {
      if (event.target === globalModal) {
        closeGlobalModal();
      }
    });
  }

  document.addEventListener("keydown", function (event) {
    if (
      event.key === "Escape" &&
      globalModal &&
      globalModal.classList.contains("is-visible")
    ) {
      closeGlobalModal();
    }
  });
});
