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
            let status = info.event.extendedProps.completed ? "Completed ✅" : "Pending 🕒";
            let type = info.event.extendedProps.type === 'task' ? 'Homework Task' : 'Event';
            if (info.event.extendedProps.type === 'task') {
                let start = info.event.start.toLocaleString();
                alert(`--- ${type} ---\n\nTitle: ${title}\nStatus: ${status}\nDeadline: ${start}\n\nNote: To modify this item, please visit the ${type}s page.`);
            } else {    
                let start = info.event.start.toLocaleString();
                let end = info.event.end ? info.event.end.toLocaleString() : 'N/A';
                alert(`--- ${type} ---\n\nTitle: ${title}\nStatus: ${status}\nStart: ${start}\nEnd: ${end}\n\nNote: To modify this item, please visit the ${type}s page.`);
            }
            info.jsEvent.preventDefault();
        }
    });

    calendar.render();
});