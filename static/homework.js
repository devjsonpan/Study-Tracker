// Homework page: complete, delete, and star actions update the list via an AJAX partial
// swap rather than a full page reload, so scroll position is preserved.
// attachListeners() is called after each swap to re-bind handlers on the new HTML —
// without this, buttons in the freshly injected content would be unresponsive.

document.addEventListener("DOMContentLoaded", function () {
    let mainContent = document.querySelector('.main-content');
    if (!mainContent) return;

    function attachListeners() {
        let actionButtons = document.querySelectorAll('.action-button');
        actionButtons.forEach(button => {
            // Guard against duplicate listeners being added on repeated attachListeners() calls
            if (!button.dataset.listenerAttached) {
                button.dataset.listenerAttached = 'true';

                button.addEventListener('click', function (e) {
                    e.preventDefault(); // Stop the link from redirecting the page

                    let url = this.getAttribute('href');

                    if (this.classList.contains('delete-button')) {
                        // For delete task, check confirm directly
                        if (!confirm('Are you sure you want to delete this task?')) {
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

                            // Swap out only the tasks portion so there is NO reload blink!
                            let newList = doc.querySelector('.homework-list');
                            let currentList = document.querySelector('.homework-list');
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

function editTask(taskId, course, taskName, dueDate, description) {
    const modalHTML = `
        <div id="edit-modal" class="modal-overlay">
            <div class="modal-content">
                <h2><i class="fa-solid fa-pen"></i> Edit Task</h2>
                <form id="edit-form" onsubmit="saveTaskEdit(event, ${taskId})">
                    <div class="form-group">
                        <label>Course:</label>
                        <input type="text" id="edit-course" value="${course}" required>
                    </div>
                    <div class="form-group">
                        <label>Task:</label>
                        <input type="text" id="edit-task-name" value="${taskName}" required>
                    </div>
                    <div class="form-group">
                        <label>Deadline:</label>
                        <input type="datetime-local" id="edit-due-date" value="${dueDate}" required>
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

function saveTaskEdit(event, taskId) {
    event.preventDefault();

    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/edit_task/' + taskId;

    form.appendChild(createHiddenInput('course', document.getElementById('edit-course').value));
    form.appendChild(createHiddenInput('task_name', document.getElementById('edit-task-name').value));
    form.appendChild(createHiddenInput('due_date', document.getElementById('edit-due-date').value));
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