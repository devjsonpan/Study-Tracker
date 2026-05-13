document.addEventListener('DOMContentLoaded', function() {
    new TomSelect('#timezone', {
        placeholder: 'Search timezone...',
        allowEmptyOption: false,
        maxOptions: null,
    });
});

setTimeout(function() {
    const flashes = document.querySelectorAll('.flash-success');
    flashes.forEach(function(el) {
        el.style.transition = 'opacity 0.5s ease';
        el.style.opacity = '0';
        setTimeout(function() { el.remove(); }, 500);
    });
}, 3000);

document.querySelector('.logout-link').addEventListener('click', function(e) {
    const username = this.getAttribute('data-username');
    const studyKey = 'activeStudyStart_' + username;
    const breakKey = 'activeBreakStart_' + username;
    if (localStorage.getItem(studyKey)) {
        e.preventDefault();
        const confirmed = window.confirm('You have a study session currently running. Are you sure you want to logout? Your session will not be saved.');
        if (confirmed) {
            localStorage.removeItem(studyKey);
            window.location.href = this.href;
        } else {
            window.location.href = '/session';
        }
    } else if (localStorage.getItem(breakKey)) {
        e.preventDefault();
        const confirmed = window.confirm('You have a break session currently running. Are you sure you want to logout? Your break will not be saved.');
        if (confirmed) {
            localStorage.removeItem(breakKey);
            window.location.href = this.href;
        } else {
            window.location.href = '/break';
        }
    }
});
