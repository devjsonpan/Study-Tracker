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

    let savedSession = localStorage.getItem(storageKey);
    if (savedSession) {
        startTime = new Date(parseInt(savedSession));
        timerDisplay.classList.add('active');
        timerStatus.textContent = "Break in progress...";
        startBtn.style.display = 'none';
        stopBtn.style.display = 'inline-block';
        timerInterval = setInterval(() => updateDisplay(new Date() - startTime), 1000);
        updateDisplay(new Date() - startTime);
    }

    startBtn.addEventListener('click', function () {
        const studyKey = 'activeStudyStart_' + username;
        if (localStorage.getItem(studyKey)) {
            alert('You have an active study session running. Please stop your study session before starting a break.');
            return;
        }
        startTime = new Date();
        localStorage.setItem(storageKey, startTime.getTime());
        timerDisplay.classList.add('active');
        timerStatus.textContent = "Break in progress...";
        startBtn.style.display = 'none';
        stopBtn.style.display = 'inline-block';
        timerInterval = setInterval(() => updateDisplay(new Date() - startTime), 1000);
        updateDisplay(0);
    });

    let allowInternalNavigation = false;

    stopBtn.addEventListener('click', function () {
        if (!startTime) return;
        clearInterval(timerInterval);
        const endTime = new Date();
        timerDisplay.classList.remove('active');
        localStorage.removeItem(storageKey);

        let diffMs = endTime - startTime;
        if (diffMs < 60000) {
            alert('Break was less than a minute, so no time was logged.');
            timerStatus.textContent = "Ready to take a break?";
            startBtn.style.display = 'inline-block';
            stopBtn.style.display = 'none';
            timerDisplay.textContent = "00:00:00";
            startTime = null;
            return;
        }

        timerStatus.textContent = "Saving break...";
        stopBtn.disabled = true;
        timeInInput.value = formatTimeString(startTime);
        timeOutInput.value = formatTimeString(endTime);
        form.submit();
    });

    // Allow normal site navigation without warning
    const internalNavLinks = document.querySelectorAll('.side-panel a:not(.logout-link), .dropdown-content a:not(.logout-link)');
    internalNavLinks.forEach(link => {
        link.addEventListener('click', function () {
            allowInternalNavigation = true;
        });
    });

    // Warn when leaving the page with an active break session, except for internal navigation
    window.addEventListener('beforeunload', function (e) {
        if (!allowInternalNavigation && localStorage.getItem(storageKey)) {
            e.returnValue = 'You have a break session currently running. Are you sure you want to leave?';
            return e.returnValue;
        }
    });
});