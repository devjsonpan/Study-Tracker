// Shared utility loaded on every authenticated page.
// Handles dark mode persistence, the profile dropdown toggle, and mobile nav auto-scroll.

function getThemeKey() {
    // Per-user key so multiple accounts on the same browser don't share theme preferences
    return window.USERNAME ? 'theme_' + window.USERNAME : 'theme';
}

// Apply dark theme before the DOM renders to avoid a flash of unstyled content
(function() {
    if (localStorage.getItem(getThemeKey()) === 'dark') {
        document.documentElement.classList.add('dark-theme');
    }
})();

document.addEventListener('DOMContentLoaded', function() {
    var buttons = document.getElementsByClassName("profile-button");
    for (var i = 0; i < buttons.length; i++) {
        buttons[i].addEventListener('click', function(event) {
            var btn = this;
            setTimeout(function() {
                var dropdown = document.querySelector('.dropdown-content');
                if (dropdown && dropdown.classList.contains('show')) {
                    btn.innerText = 'Profile ▲';
                } else {
                    btn.innerText = 'Profile ▼';
                }
            }, 0);
        });
    }
});

// Close dropdown if clicked outside
window.onclick = function(event) {
  if (!event.target.matches('.profile-button')) {
    var dropdowns = document.getElementsByClassName("dropdown-content");
    for (var i = 0; i < dropdowns.length; i++) {
      var openDropdown = dropdowns[i];
      if (openDropdown.classList.contains('show')) {
        openDropdown.classList.remove('show');
      }
    }
    var buttons = document.getElementsByClassName("profile-button");
    for (var i = 0; i < buttons.length; i++) {
        buttons[i].innerText = 'Profile ▼';
    }
  }
}

// Mobile nav auto-scroll — centers the active nav button when the side panel overflows on small screens
document.addEventListener("DOMContentLoaded", function () {
    // The active page's nav button always has href="#" (set per-template)
    const activeBtn = document.querySelector('.side-panel a.button[href="#"]');
    if (!activeBtn) return;

    // Highlight active tab visually
    activeBtn.style.backgroundColor = 'rgba(102, 126, 234, 0.3)';
    activeBtn.style.boxShadow = '0 2px 8px rgba(102, 126, 234, 0.3)';
    activeBtn.style.color = 'white';

    const sidePanel = document.querySelector('.side-panel');
    if (window.innerWidth <= 900 && sidePanel) {
        // Center the active button in the scrollable nav
        sidePanel.scrollLeft = activeBtn.offsetLeft - (sidePanel.offsetWidth / 2) + (activeBtn.offsetWidth / 2);
    }
});
