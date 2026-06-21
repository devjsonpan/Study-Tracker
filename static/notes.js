// Notes page: delete and edit actions via modal.
// Edit uses a dynamically created form POST so the server receives standard form data —
// no JSON endpoint needed, and it matches the existing Flask route's request.form.get() calls.

function deleteNote(noteId) {
    if (confirm('Are you sure you want to delete this note? This cannot be undone.')) {
        window.location = '/delete_note/' + noteId;
    }
}

function editNote(noteId) {
    const noteCard = document.getElementById('note-' + noteId);
    
    const courseClone = noteCard.querySelector('.note-course').cloneNode(true);
    const starToggle = courseClone.querySelector('.star-toggle');
    if (starToggle) starToggle.remove();
    const course = courseClone.textContent.trim();
    const topicElement = noteCard.querySelector('.note-topic');
    const topic = topicElement ? topicElement.textContent.replace('Topic:', '').trim() : '';
    const notes = noteCard.querySelector('.note-content').textContent.trim();
    
    showEditModal(noteId, course, topic, notes);
}

function showEditModal(noteId, course, topic, notes) {
    const modalHTML = `
        <div id="edit-modal" class="modal-overlay">
            <div class="modal-content">
                <h2><i class="fa-solid fa-pen"></i> Edit Note</h2>
                <form id="edit-form" onsubmit="saveEdit(event, ${noteId})">
                    <div class="form-group">
                        <label>Course:</label>
                        <input type="text" id="edit-course" value="${course}" required>
                    </div>
                    <div class="form-group">
                        <label>Topic:</label>
                        <input type="text" id="edit-topic" value="${topic}">
                    </div>
                    <div class="form-group">
                        <label>Notes:</label>
                        <textarea id="edit-notes">${notes}</textarea>
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

function saveEdit(event, noteId) {
    event.preventDefault();
    
    const course = document.getElementById('edit-course').value;
    const topic = document.getElementById('edit-topic').value;
    const notes = document.getElementById('edit-notes').value;
    
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/edit_note/' + noteId;
    
    form.appendChild(createHiddenInput('course', course));
    form.appendChild(createHiddenInput('topic', topic));
    form.appendChild(createHiddenInput('notes', notes));
    
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
    if (modal) {
        modal.remove();
    }
}