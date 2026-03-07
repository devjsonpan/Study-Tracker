document.addEventListener('DOMContentLoaded', function () {
    var calendarEl = document.getElementById('calendar');

    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev',
            center: 'title today',
            right: 'next'
        },
        events: calendarEvents,
        height: 'auto',
        contentHeight: 600,
        dayMaxEvents: true,
        eventTimeFormat: {
            hour: '2-digit',
            minute: '2-digit',
            meridiem: true
        },
        eventContent: function(info) {
            const timeText = info.timeText;
            const title = info.event.title;
            const isTask = info.event.extendedProps.type === 'task';

            if (isTask) {
                const color = info.event.backgroundColor;
                return { html: `<div style="display: flex; align-items: center; overflow: hidden; white-space: nowrap; max-width: 100%;">
                    <span style="width: 8px; height: 8px; border-radius: 50%; background-color: ${color}; flex-shrink: 0; margin-right: 4px;"></span>
                    <span style="flex-shrink: 0;">${timeText} —&nbsp;</span>
                    <span style="overflow: hidden; text-overflow: ellipsis;">${title}</span>
                </div>` };
            } else {
                return { html: `<div style="display: flex; align-items: center; overflow: hidden; white-space: nowrap; max-width: 100%;">
                    <span style="flex-shrink: 0; margin-right: 4px;">${timeText ? timeText + ' — ' : '— '}</span>
                    <span style="overflow: hidden; text-overflow: ellipsis;">${title}</span>
                </div>` };
            }
        },
        eventClick: function (info) {
            const title = info.event.title;
            const type = info.event.extendedProps.type === 'task' ? 'Homework Task' : 'Event';
            const props = info.event.extendedProps;

            let statusClass, statusText;
            if (props.completed) {
                statusClass = 'completed'; statusText = 'Completed ✅';
            } else if (info.event.extendedProps.type === 'task' && new Date() > info.event.start) {
                statusClass = 'overdue'; statusText = 'Overdue ❌';
            } else {
                statusClass = 'pending'; statusText = 'Pending 🕒';
            }

            let rows = '';

            if (props.type === 'task') {
                rows = `
                    <div class="modal-row">
                        <span class="modal-label">Title</span>
                        <span class="modal-value">${title}</span>
                    </div>
                    <div class="modal-row">
                        <span class="modal-label">Status</span>
                        <span class="modal-status ${statusClass}">${statusText}</span>
                    </div>
                    <hr class="modal-divider">
                    <div class="modal-row">
                        <span class="modal-label">Deadline</span>
                        <span class="modal-value">${props.deadline}</span>
                    </div>
                    <div class="modal-row">
                        <span class="modal-label">Description</span>
                        <span class="modal-value">${props.description}</span>
                    </div>`;
            } else {
                rows = `
                    <div class="modal-row">
                        <span class="modal-label">Title</span>
                        <span class="modal-value">${title}</span>
                    </div>
                    <div class="modal-row">
                        <span class="modal-label">Status</span>
                        <span class="modal-status ${statusClass}">${statusText}</span>
                    </div>
                    <hr class="modal-divider">
                    <div class="modal-row">
                        <span class="modal-label">Start</span>
                        <span class="modal-value">${props.real_start}</span>
                    </div>
                    <div class="modal-row">
                        <span class="modal-label">End</span>
                        <span class="modal-value">${props.real_end}</span>
                    </div>
                    <div class="modal-row">
                        <span class="modal-label">Location</span>
                        <span class="modal-value">${props.location}</span>
                    </div>
                    <div class="modal-row">
                        <span class="modal-label">Description</span>
                        <span class="modal-value">${props.description}</span>
                    </div>`;
            }

            document.getElementById('modal-content').innerHTML = `
                <h2>${type === 'Homework Task' ? '✅' : '🗓️'} ${type}</h2>
                ${rows}
                <p class="modal-note">To modify this item, visit the ${type}s page.</p>
            `;

            document.getElementById('event-modal').style.display = 'block';
            info.jsEvent.preventDefault();
        },
    });

    calendar.render();

    document.getElementById('modal-close').addEventListener('click', function() {
        document.getElementById('event-modal').style.display = 'none';
    });
});