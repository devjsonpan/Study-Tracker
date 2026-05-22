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
    window.allowInternalNavigation = false

    const pauseBtn = document.getElementById('pauseBtn');
    const resumeBtn = document.getElementById('resumeBtn');
    const cancelBtn = document.getElementById('cancelBtn');
    let totalPausedMs = 0;
    let isPaused = false;
    let pauseStartTime = null;

    function formatTimeString(dateObj) {
        const y = dateObj.getFullYear();
        const m = (dateObj.getMonth() + 1).toString().padStart(2, '0');
        const d = dateObj.getDate().toString().padStart(2, '0');
        const H = dateObj.getHours().toString().padStart(2, '0');
        const M = dateObj.getMinutes().toString().padStart(2, '0');
        const S = dateObj.getSeconds().toString().padStart(2, '0');
        return `${y}-${m}-${d} ${H}:${M}:${S}`;
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
        totalPausedMs = saved.totalPausedMs || 0;
        isPaused = saved.isPaused || false;
        pauseStartTime = saved.pauseStartTime ? new Date(saved.pauseStartTime) : null;

        courseInput.disabled = true;
        topicInput.disabled = true;
        timerDisplay.classList.add('active');

        startBtn.style.display = 'none';

        if (isPaused) {
            timerStatus.textContent = "Session paused.";
            pauseBtn.style.display = 'none';
            resumeBtn.style.display = 'inline-block';
            stopBtn.style.display = 'inline-block';
            cancelBtn.style.display = 'inline-block';
            updateDisplay(pauseStartTime - startTime - totalPausedMs);
        } else {
            timerStatus.textContent = "Session in progress...";
            pauseBtn.style.display = 'inline-block';
            resumeBtn.style.display = 'none';
            stopBtn.style.display = 'inline-block';
            cancelBtn.style.display = 'inline-block';
            timerInterval = setInterval(() => updateDisplay(new Date() - startTime - totalPausedMs), 1000);
            updateDisplay(new Date() - startTime - totalPausedMs);
        }
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
        totalPausedMs = 0;
        isPaused = false;
        pauseStartTime = null;

        const sessionData = {
            startTime: startTime.getTime(),
            course: courseInput.value,
            topic: topicInput.value,
            totalPausedMs: totalPausedMs,
            isPaused: isPaused,
            pauseStartTime: pauseStartTime
        };
        localStorage.setItem(storageKey, JSON.stringify(sessionData));

        courseInput.disabled = true;
        topicInput.disabled = true;
        timerDisplay.classList.add('active');
        timerStatus.textContent = "Session in progress...";
        startBtn.style.display = 'none';
        pauseBtn.style.display = 'inline-block';
        stopBtn.style.display = 'inline-block';
        cancelBtn.style.display = 'inline-block';
        timerInterval = setInterval(() => updateDisplay(new Date() - startTime - totalPausedMs), 1000);
        updateDisplay(0);
    });

    pauseBtn.addEventListener('click', function () {
        if (isPaused) return;
        isPaused = true;
        pauseStartTime = new Date();
        clearInterval(timerInterval);

        const sessionData = JSON.parse(localStorage.getItem(storageKey));
        sessionData.isPaused = isPaused;
        sessionData.pauseStartTime = pauseStartTime.getTime();
        localStorage.setItem(storageKey, JSON.stringify(sessionData));

        timerStatus.textContent = "Session paused.";
        pauseBtn.style.display = 'none';
        resumeBtn.style.display = 'inline-block';
    });

    resumeBtn.addEventListener('click', function () {
        if (!isPaused) return;
        isPaused = false;
        const now = new Date();
        totalPausedMs += (now - pauseStartTime);
        pauseStartTime = null;

        const sessionData = JSON.parse(localStorage.getItem(storageKey));
        sessionData.isPaused = isPaused;
        sessionData.pauseStartTime = null;
        sessionData.totalPausedMs = totalPausedMs;
        localStorage.setItem(storageKey, JSON.stringify(sessionData));

        timerStatus.textContent = "Session in progress...";
        resumeBtn.style.display = 'none';
        pauseBtn.style.display = 'inline-block';
        timerInterval = setInterval(() => updateDisplay(new Date() - startTime - totalPausedMs), 1000);
        updateDisplay(new Date() - startTime - totalPausedMs);
    });

    cancelBtn.addEventListener('click', function () {
        const confirmed = window.confirm('Are you sure you want to cancel this session? No time will be logged.');
        if (!confirmed) return;

        clearInterval(timerInterval);
        localStorage.removeItem(storageKey);

        courseInput.disabled = false;
        topicInput.disabled = false;
        timerStatus.textContent = "Ready to study?";
        startBtn.style.display = 'inline-block';
        stopBtn.style.display = 'none';
        pauseBtn.style.display = 'none';
        resumeBtn.style.display = 'none';
        cancelBtn.style.display = 'none';
        timerDisplay.textContent = "00:00:00";
        timerDisplay.classList.remove('active');
        startTime = null;
    });

    stopBtn.addEventListener('click', function () {
        if (!startTime) return;
        clearInterval(timerInterval);

        let endTime = new Date();
        // If stopped while paused, don't include the time spent paused as part of the total time.
        // Actually, the simplest way is to calculate the effective duration:
        let effectiveDurationMs;
        if (isPaused) {
            effectiveDurationMs = pauseStartTime - startTime - totalPausedMs;
            // The time out would actually be when it was paused to represent actual study time end, or we can just say endTime is now, but subtract totalPausedMs + current pause time. 
            // Wait, the backend expects time_in and time_out. If we have a long pause, the total duration is out - in. 
            // We can't tell the backend about pauses. The easiest way is to adjust time_in forward by the total paused amount.
        } else {
            effectiveDurationMs = endTime - startTime - totalPausedMs;
        }

        timerDisplay.classList.remove('active');

        if (effectiveDurationMs < 60000) {
            alert('Session was less than a minute, so no time was logged.');
            localStorage.removeItem(storageKey);
            courseInput.disabled = false;
            topicInput.disabled = false;
            timerStatus.textContent = "Ready to study?";
            startBtn.style.display = 'inline-block';
            stopBtn.style.display = 'none';
            pauseBtn.style.display = 'none';
            resumeBtn.style.display = 'none';
            cancelBtn.style.display = 'none';
            timerDisplay.textContent = "00:00:00";
            startTime = null;
            return;
        }

        // To make the duration correct based on start/end, we can just push startTime forward by the total paused ms.
        let adjustedStartTime = new Date(startTime.getTime() + totalPausedMs);
        if (isPaused) {
            adjustedStartTime = new Date(adjustedStartTime.getTime() + (endTime - pauseStartTime));
        }

        timeInInput.value = formatTimeString(adjustedStartTime);
        timeOutInput.value = formatTimeString(endTime);
        localStorage.removeItem(storageKey);

        // Mark as having unsaved session data
        hasUnsavedSession = true;
        localStorage.setItem(unsavedSessionKey, 'true');

        timerStatus.textContent = "Session stopped. Add notes and save!";
        stopBtn.style.display = 'none';
        pauseBtn.style.display = 'none';
        resumeBtn.style.display = 'none';
        cancelBtn.style.display = 'none';
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
        // Allow navigation after form submit
        window.allowInternalNavigation = true;
    });

    // Function to check if there's unsaved or running session data
    function checkUnsavedSession() {
        return hasUnsavedSession || localStorage.getItem(unsavedSessionKey) === 'true' || localStorage.getItem(storageKey) !== null;
    }

    // Warn when leaving the page without saving
    window.addEventListener('beforeunload', function (e) {
        if (!window.allowInternalNavigation && checkUnsavedSession()) {
            e.preventDefault();
            e.returnValue = 'You have an unsaved or active study session. Are you sure you want to leave?';
            return e.returnValue;
        }
    });

    // Add warning to all navigation links (side panel and profile dropdown) except logout
    const navLinks = document.querySelectorAll('.side-panel a:not(.logout-link), .dropdown-content a:not(.logout-link)');
    navLinks.forEach(link => {
        link.addEventListener('click', function (e) {
            if (checkUnsavedSession()) {
                e.preventDefault();
                const confirmed = window.confirm('You have an active or unsaved study session. Do you want to leave without saving?');
                if (confirmed) {
                    window.allowInternalNavigation = true;
                    localStorage.removeItem(unsavedSessionKey);
                    localStorage.removeItem(storageKey);
                    window.location.href = this.href;
                }
            }
        });
    });

    // Update logout link warning to also check for unsaved sessions
    const logoutLink = document.querySelector('.logout-link');
    if (logoutLink) {
        logoutLink.removeEventListener('click', function () { }); // Remove old listener if it exists
        logoutLink.addEventListener('click', function (e) {
            const studyKey = 'activeStudyStart_' + username;
            const breakKey = 'activeBreakStart_' + username;
            const hasUnsavedSession = localStorage.getItem(unsavedSessionKey) === 'true';

            if (localStorage.getItem(studyKey)) {
                e.preventDefault();
                const confirmed = window.confirm('You have an active or unsaved study session. Are you sure you want to logout? Your session will not be saved.');
                if (confirmed) {
                    window.allowInternalNavigation = true;
                    localStorage.removeItem(studyKey);
                    localStorage.removeItem(unsavedSessionKey);
                    window.location.href = this.href;
                }
            } else if (localStorage.getItem(breakKey)) {
                e.preventDefault();
                const confirmed = window.confirm('You have an active or unsaved break session. Are you sure you want to logout? Your break will not be saved.');
                if (confirmed) {
                    window.allowInternalNavigation = true;
                    localStorage.removeItem(breakKey);
                    localStorage.removeItem(unsavedSessionKey);
                    window.location.href = this.href;
                }
            } else if (hasUnsavedSession) {
                e.preventDefault();
                const confirmed = window.confirm('You have an active or unsaved study session. Are you sure you want to logout without saving?');
                if (confirmed) {
                    window.allowInternalNavigation = true;
                    localStorage.removeItem(unsavedSessionKey);
                    window.location.href = this.href;
                }
            }
        });
    }
});