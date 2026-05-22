document.addEventListener("DOMContentLoaded", function () {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const timerDisplay = document.getElementById('timerDisplay');
    const timerStatus = document.getElementById('timerStatus');
    const form = document.querySelector('.break-form');
    const timeInInput = document.getElementById('time_in');
    const timeOutInput = document.getElementById('time_out');

    const username = document.getElementById('current-username').value;
    const storageKey = 'activeBreakStart_' + username;

    let startTime = null;
    let timerInterval = null;
    window.allowInternalNavigation = false;

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

    let savedSession = localStorage.getItem(storageKey);
    if (savedSession) {
        try {
            const saved = JSON.parse(savedSession);
            if (typeof saved === 'number') {
                startTime = new Date(saved);
            } else {
                startTime = new Date(saved.startTime);
                totalPausedMs = saved.totalPausedMs || 0;
                isPaused = saved.isPaused || false;
                pauseStartTime = saved.pauseStartTime ? new Date(saved.pauseStartTime) : null;
            }
        } catch (e) {
            startTime = new Date(parseInt(savedSession));
        }

        timerDisplay.classList.add('active');
        startBtn.style.display = 'none';

        if (isPaused) {
            timerStatus.textContent = "Break paused.";
            pauseBtn.style.display = 'none';
            resumeBtn.style.display = 'inline-block';
            stopBtn.style.display = 'inline-block';
            cancelBtn.style.display = 'inline-block';
            updateDisplay(pauseStartTime - startTime - totalPausedMs);
        } else {
            timerStatus.textContent = "Break in progress...";
            pauseBtn.style.display = 'inline-block';
            resumeBtn.style.display = 'none';
            stopBtn.style.display = 'inline-block';
            cancelBtn.style.display = 'inline-block';
            timerInterval = setInterval(() => updateDisplay(new Date() - startTime - totalPausedMs), 1000);
            updateDisplay(new Date() - startTime - totalPausedMs);
        }
    }

    startBtn.addEventListener('click', function () {
        const studyKey = 'activeStudyStart_' + username;
        if (localStorage.getItem(studyKey)) {
            alert('You have an active study session running. Please stop your study session before starting a break.');
            return;
        }
        startTime = new Date();
        totalPausedMs = 0;
        isPaused = false;
        pauseStartTime = null;

        const sessionData = {
            startTime: startTime.getTime(),
            totalPausedMs: totalPausedMs,
            isPaused: isPaused,
            pauseStartTime: pauseStartTime
        };
        localStorage.setItem(storageKey, JSON.stringify(sessionData));

        timerDisplay.classList.add('active');
        timerStatus.textContent = "Break in progress...";
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

        timerStatus.textContent = "Break paused.";
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

        timerStatus.textContent = "Break in progress...";
        resumeBtn.style.display = 'none';
        pauseBtn.style.display = 'inline-block';
        timerInterval = setInterval(() => updateDisplay(new Date() - startTime - totalPausedMs), 1000);
        updateDisplay(new Date() - startTime - totalPausedMs);
    });

    cancelBtn.addEventListener('click', function () {
        const confirmed = window.confirm('Are you sure you want to cancel this break? No time will be logged.');
        if (!confirmed) return;

        clearInterval(timerInterval);
        localStorage.removeItem(storageKey);

        timerStatus.textContent = "Ready to take a break?";
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
        let effectiveDurationMs;
        if (isPaused) {
            effectiveDurationMs = pauseStartTime - startTime - totalPausedMs;
        } else {
            effectiveDurationMs = endTime - startTime - totalPausedMs;
        }

        timerDisplay.classList.remove('active');
        localStorage.removeItem(storageKey);

        if (effectiveDurationMs < 60000) {
            alert('Break was less than a minute, so no time was logged.');
            timerStatus.textContent = "Ready to take a break?";
            startBtn.style.display = 'inline-block';
            stopBtn.style.display = 'none';
            pauseBtn.style.display = 'none';
            resumeBtn.style.display = 'none';
            cancelBtn.style.display = 'none';
            timerDisplay.textContent = "00:00:00";
            startTime = null;
            return;
        }

        let adjustedStartTime = new Date(startTime.getTime() + totalPausedMs);
        if (isPaused) {
            adjustedStartTime = new Date(adjustedStartTime.getTime() + (endTime - pauseStartTime));
        }

        timerStatus.textContent = "Saving break...";
        stopBtn.disabled = true;
        pauseBtn.disabled = true;
        resumeBtn.disabled = true;
        cancelBtn.disabled = true;
        timeInInput.value = formatTimeString(adjustedStartTime);
        timeOutInput.value = formatTimeString(endTime);
        window.allowInternalNavigation = true;
        form.submit();
    });

    // Warn on internal navigation
    const internalNavLinks = document.querySelectorAll('.side-panel a:not(.logout-link), .dropdown-content a:not(.logout-link)');
    internalNavLinks.forEach(link => {
        link.addEventListener('click', function (e) {
            if (localStorage.getItem(storageKey)) {
                e.preventDefault();
                const confirmed = window.confirm('You have an active or unsaved break session. Do you want to leave without saving?');
                if (confirmed) {
                    window.allowInternalNavigation = true;
                    localStorage.removeItem(storageKey);
                    window.location.href = this.href;
                }
            }
        });
    });

    // Warn when leaving the page with an active break session, except for internal navigation
    window.addEventListener('beforeunload', function (e) {
        if (!window.allowInternalNavigation && localStorage.getItem(storageKey)) {
            e.returnValue = 'You have an active or unsaved break session. Are you sure you want to leave?';
            return e.returnValue;
        }
    });
});