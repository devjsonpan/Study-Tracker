// Events page: uses the same AJAX partial-swap pattern as homework.js.
// The edit modal includes client-side start/end validation before submitting
// so the user gets immediate feedback without a round-trip to the server.

document.addEventListener("DOMContentLoaded", function () {
    let mainContent = document.querySelector('.main-content');
    if (!mainContent) return;

    function attachListeners() {
        let actionButtons = document.querySelectorAll('.action-button');
        actionButtons.forEach(button => {
            // Guard against duplicate listeners on re-attach after DOM swap
            if (!button.dataset.listenerAttached) {
                button.dataset.listenerAttached = 'true';

                button.addEventListener('click', function (e) {
                    e.preventDefault(); // Stop the link from redirecting the page

                    let url = this.getAttribute('href');

                    if (this.classList.contains('delete-button')) {
                        // For delete task, check confirm directly
                        if (!confirm('Are you sure you want to delete this event?')) {
                            return;
                        }
                    }

                    // Save exact scroll
                    let currentScroll = mainContent.scrollTop;

                    fetch(url)
                        .then(response => response.text())
                        .then(html => {
                            let parser = new DOMParser();
                            let doc = parser.parseFromString(html, 'text/html');

                            // Swap out only the events portion so there is NO reload blink!
                            let newList = doc.querySelector('.events-list');
                            let currentList = document.querySelector('.events-list');
                            if (newList && currentList) {
                                currentList.innerHTML = newList.innerHTML;
                            }

                            // Attach listeners to the newly created buttons
                            attachListeners();

                            // Restore scroll perfectly
                            mainContent.scrollTop = currentScroll;
                        });
                });
            }
        });
    }

    attachListeners();
});

function editEvent(eventId, eventName, startDatetime, endDatetime, location, description) {
    const modalHTML = `
        <div id="edit-modal" class="modal-overlay">
            <div class="modal-content">
                <h2><i class="fa-solid fa-pen"></i> Edit Event</h2>
                <form id="edit-form" onsubmit="saveEventEdit(event, ${eventId})">
                    <div class="form-group">
                        <label>Event Name:</label>
                        <input type="text" id="edit-event-name" value="${eventName}" required>
                    </div>
                    <div class="form-group">
                        <label>Start:</label>
                        <input type="datetime-local" id="edit-start" value="${startDatetime}" required>
                    </div>
                    <div class="form-group">
                        <label>End:</label>
                        <input type="datetime-local" id="edit-end" value="${endDatetime}" required>
                    </div>
                    <div class="form-group">
                        <label>Location: <span style="font-weight:400; color:#718096; font-size:13px;">(optional)</span></label>
                        <input type="text" id="edit-location" value="${location}">
                    </div>
                    <div class="form-group">
                        <label>Description: <span style="font-weight:400; color:#718096; font-size:13px;">(optional)</span></label>
                        <textarea id="edit-description" rows="3">${description}</textarea>
                    </div>
                    <div class="modal-buttons">
                        <button type="submit" class="save-btn">Save Changes</button>
                        <button type="button" class="cancel-btn" onclick="closeEditModal()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function saveEventEdit(event, eventId) {
    event.preventDefault();

    const start = document.getElementById('edit-start').value;
    const end = document.getElementById('edit-end').value;

    if (start >= end) {
        let errorDiv = document.getElementById('edit-modal-error');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.id = 'edit-modal-error';
            errorDiv.style.cssText = 'background-color: #fed7d7; color: #c53030; padding: 10px 15px; border-radius: 8px; margin-bottom: 15px; font-size: 14px; font-weight: 600; text-align: center;';
            const form = document.getElementById('edit-form');
            form.insertBefore(errorDiv, form.firstChild);
        }
        errorDiv.textContent = 'The start time must be before the end time.';
        return;
    }

    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/edit_event/' + eventId;

    form.appendChild(createHiddenInput('event_name', document.getElementById('edit-event-name').value));
    form.appendChild(createHiddenInput('start_datetime', start));
    form.appendChild(createHiddenInput('end_datetime', end));
    form.appendChild(createHiddenInput('location', document.getElementById('edit-location').value));
    form.appendChild(createHiddenInput('description', document.getElementById('edit-description').value));

    document.body.appendChild(form);
    form.submit();
}

function createHiddenInput(name, value) {
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = name;
    input.value = value;
    return input;
}

function closeEditModal() {
    const modal = document.getElementById('edit-modal');
    if (modal) modal.remove();
}