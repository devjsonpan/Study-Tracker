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
            let title = info.event.title;
            let type = info.event.extendedProps.type === 'task' ? 'Homework Task' : 'Event';

            if (info.event.extendedProps.type === 'task') {
                let status;
                if (info.event.extendedProps.completed) {
                    status = "Completed ✅";
                } else if (new Date() > info.event.start) {
                    status = "Overdue ❌";
                } else {
                    status = "Pending 🕒";
                }
                let deadline = info.event.extendedProps.deadline;
                alert(`--- ${type} ---\n\nTitle: ${title}\nDeadline: ${deadline}\nStatus: ${status}\n\nNote: To modify this item, please visit the ${type}s page.`);
            } else {
                let status = info.event.extendedProps.completed ? "Completed ✅" : "Pending 🕒";
                let start = info.event.extendedProps.real_start;
                let end = info.event.extendedProps.real_end;
                alert(`--- ${type} ---\n\nTitle: ${title}\nStart: ${start}\nEnd: ${end}\nStatus: ${status}\n\nNote: To modify this item, please visit the ${type}s page.`);
            }
            info.jsEvent.preventDefault();
        }
    });

    calendar.render();
});