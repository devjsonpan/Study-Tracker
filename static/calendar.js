document.addEventListener('DOMContentLoaded', function () {
    var calendarEl = document.getElementById('calendar');

    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        events: calendarEvents,
        height: 'auto',
        contentHeight: 600,
        dayMaxEvents: true,
        scrollTime: '08:00:00',
        slotMinTime: '00:00:00',
        slotMaxTime: '24:00:00',
        eventMinHeight: 20,
        slotEventOverlap: false,
        eventTimeFormat: {
            hour: '2-digit',
            minute: '2-digit',
            meridiem: true
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
                alert(`--- ${type} ---\n\nTitle: ${title}\nStatus: ${status}\nDeadline: ${deadline}\n\nNote: To modify this item, please visit the ${type}s page.`);
            } else {
                let status = info.event.extendedProps.completed ? "Completed ✅" : "Pending 🕒";
                let start = info.event.start.toLocaleString();
                let end = info.event.end ? info.event.end.toLocaleString() : 'N/A';
                alert(`--- ${type} ---\n\nTitle: ${title}\nStatus: ${status}\nStart: ${start}\nEnd: ${end}\n\nNote: To modify this item, please visit the ${type}s page.`);
            }
            info.jsEvent.preventDefault();
        }
    });

    calendar.render();
});