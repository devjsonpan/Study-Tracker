document.addEventListener('DOMContentLoaded', function() {
    const timezoneSelect = document.getElementById('timezone');
    
    // Auto-detect and select the user's timezone if they haven't manually selected one yet
    // Note: This overrides the "Select your timezone..." disabled option for convenience
    if (timezoneSelect && !timezoneSelect.value) {
        const userTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
        if (userTz) {
            const option = Array.from(timezoneSelect.options).find(opt => opt.value === userTz);
            if (option) {
                option.selected = true;
            }
        }
    }
    
    // Initialize TomSelect for the timezone dropdown
    new TomSelect('#timezone', {
        placeholder: 'Search timezone...',
        allowEmptyOption: false,
        create: false,
        maxOptions: null,
    });
});
