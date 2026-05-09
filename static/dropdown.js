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
