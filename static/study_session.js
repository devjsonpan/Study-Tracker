document.addEventListener("DOMContentLoaded", function () {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const saveBtn = document.getElementById('save-btn');
    const timerDisplay = document.getElementById('timerDisplay');
    const timerStatus = document.getElementById('timerStatus');
    const notesGroup = document.getElementById('notes-group');
    const form = document.getElementById('session-form');
    const timeInInput = document.getElementById('time_in');
    const timeOutInput = document.getElementById('time_out');
    const courseInput = document.getElementById('course');
    const topicInput = document.getElementById('topic');

    const username = document.getElementById('current-username').value;
    const storageKey = 'activeStudyStart_' + username;
    const unsavedSessionKey = 'unsavedSession_' + username;

    let startTime = null;
    let timerInterval = null;
    let hasUnsavedSession = false;

    function formatTimeString(dateObj) {
        return dateObj.getHours().toString().padStart(2, '0') + ':' +
               dateObj.getMinutes().toString().padStart(2, '0') + ':' +
               dateObj.getSeconds().toString().padStart(2, '0');
    }

    function updateDisplay(diffMs) {
        let totalSeconds = Math.floor(diffMs / 1000);
        let hours = Math.floor(totalSeconds / 3600);
        let minutes = Math.floor((totalSeconds % 3600) / 60);
        let seconds = totalSeconds % 60;
        timerDisplay.textContent =
            hours.toString().padStart(2, '0') + ':' +
            minutes.toString().padStart(2, '0') + ':' +
            seconds.toString().padStart(2, '0');
    }

    // Restore active session if exists
    let savedSession = localStorage.getItem(storageKey);
    if (savedSession) {
        const saved = JSON.parse(savedSession);
        startTime = new Date(saved.startTime);
        courseInput.value = saved.course;
        topicInput.value = saved.topic;
        courseInput.disabled = true;
        topicInput.disabled = true;
        timerDisplay.classList.add('active');
        timerStatus.textContent = "Session in progress...";
        startBtn.style.display = 'none';
        stopBtn.style.display = 'inline-block';
        timerInterval = setInterval(() => updateDisplay(new Date() - startTime), 1000);
        updateDisplay(new Date() - startTime);
    }

    startBtn.addEventListener('click', function () {
        const breakKey = 'activeBreakStart_' + username;
        if (localStorage.getItem(breakKey)) {
            alert('You have an active break running. Please stop your break before starting a study session.');
            return;
        }
        const course = courseInput.value.trim();
        if (!course) {
            alert('Please enter a course before starting.');
            return;
        }

        startTime = new Date();
        const sessionData = {
            startTime: startTime.getTime(),
            course: courseInput.value,
            topic: topicInput.value
        };
        localStorage.setItem(storageKey, JSON.stringify(sessionData));

        courseInput.disabled = true;
        topicInput.disabled = true;
        timerDisplay.classList.add('active');
        timerStatus.textContent = "Session in progress...";
        startBtn.style.display = 'none';
        stopBtn.style.display = 'inline-block';
        timerInterval = setInterval(() => updateDisplay(new Date() - startTime), 1000);
        updateDisplay(0);
    });

    stopBtn.addEventListener('click', function () {
        if (!startTime) return;
        clearInterval(timerInterval);
        const endTime = new Date();
        timerDisplay.classList.remove('active');

        let diffMs = endTime - startTime;
        if (diffMs < 60000) {
            alert('Session was less than a minute, so no time was logged.');
            localStorage.removeItem(storageKey);
            courseInput.disabled = false;
            topicInput.disabled = false;
            timerStatus.textContent = "Ready to study?";
            startBtn.style.display = 'inline-block';
            stopBtn.style.display = 'none';
            timerDisplay.textContent = "00:00:00";
            startTime = null;
            return;
        }

        timeInInput.value = formatTimeString(startTime);
        timeOutInput.value = formatTimeString(endTime);
        localStorage.removeItem(storageKey);

        // Mark as having unsaved session data
        hasUnsavedSession = true;
        localStorage.setItem(unsavedSessionKey, 'true');

        timerStatus.textContent = "Session stopped. Add notes and save!";
        stopBtn.style.display = 'none';
        notesGroup.style.display = 'block';
        saveBtn.style.display = 'block';
    });

    form.addEventListener('submit', function () {
        // Re-enable disabled fields so they get submitted
        courseInput.disabled = false;
        topicInput.disabled = false;
        // Clear the unsaved session flag since we're saving
        hasUnsavedSession = false;
        localStorage.removeItem(unsavedSessionKey);
    });

    // Function to check if there's unsaved session data
    function checkUnsavedSession() {
        return hasUnsavedSession || localStorage.getItem(unsavedSessionKey) === 'true';
    }

    // Warn when leaving the page without saving
    window.addEventListener('beforeunload', function (e) {
        if (checkUnsavedSession()) {
            e.preventDefault();
            e.returnValue = 'You have an unsaved study session. Are you sure you want to leave?';
            return e.returnValue;
        }
    });

    // Add warning to all navigation links (side panel and profile dropdown) except logout
    const navLinks = document.querySelectorAll('.side-panel a:not(.logout-link), .dropdown-content a:not(.logout-link)');
    navLinks.forEach(link => {
        link.addEventListener('click', function (e) {
            if (checkUnsavedSession()) {
                e.preventDefault();
                const confirmed = window.confirm('You have an unsaved study session. Do you want to leave without saving?');
                if (confirmed) {
                    localStorage.removeItem(unsavedSessionKey);
                    window.location.href = this.href;
                }
            }
        });
    });

    // Update logout link warning to also check for unsaved sessions
    const logoutLink = document.querySelector('.logout-link');
    if (logoutLink) {
        logoutLink.removeEventListener('click', function() {}); // Remove old listener if it exists
        logoutLink.addEventListener('click', function (e) {
            const studyKey = 'activeStudyStart_' + username;
            const breakKey = 'activeBreakStart_' + username;
            const hasUnsavedSession = localStorage.getItem(unsavedSessionKey) === 'true';

            if (localStorage.getItem(studyKey)) {
                e.preventDefault();
                const confirmed = window.confirm('You have a study session currently running. Are you sure you want to logout? Your session will not be saved.');
                if (confirmed) {
                    localStorage.removeItem(studyKey);
                    localStorage.removeItem(unsavedSessionKey);
                    window.location.href = this.href;
                }
            } else if (localStorage.getItem(breakKey)) {
                e.preventDefault();
                const confirmed = window.confirm('You have a break session currently running. Are you sure you want to logout? Your break will not be saved.');
                if (confirmed) {
                    localStorage.removeItem(breakKey);
                    localStorage.removeItem(unsavedSessionKey);
                    window.location.href = this.href;
                }
            } else if (hasUnsavedSession) {
                e.preventDefault();
                const confirmed = window.confirm('You have an unsaved study session. Are you sure you want to logout without saving?');
                if (confirmed) {
                    localStorage.removeItem(unsavedSessionKey);
                    window.location.href = this.href;
                }
            }
        });
    }
});