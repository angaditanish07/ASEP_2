document.addEventListener('DOMContentLoaded', function() {
    // Toggle sidebar on mobile
    const sidebarToggle = document.querySelectorAll('.sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    const main = document.querySelector('.main');
    
    sidebarToggle.forEach(button => {
        button.addEventListener('click', function() {
            sidebar.classList.toggle('active');
            main.classList.toggle('active');
        });
    });
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Simulate loading data (in a real app, this would be API calls)
    setTimeout(() => {
        // This would be replaced with actual data fetching
        console.log("Loading dashboard data...");
    }, 1000);
    
    // Make tables responsive by adding scroll
    const tables = document.querySelectorAll('.table-responsive');
    tables.forEach(table => {
        if (table.scrollWidth > table.clientWidth) {
            table.classList.add('scrollable');
        }
    });
    
    // Update notification badges
    function updateNotificationCount() {
        // In a real app, this would fetch from an API
        setTimeout(() => {
            const alertBadge = document.querySelector('#alertsDropdown .badge-number');
            const messageBadge = document.querySelector('#messagesDropdown .badge-number');
            
            // Simulate new notifications
            if (Math.random() > 0.7) {
                const currentCount = parseInt(alertBadge.textContent);
                alertBadge.textContent = currentCount + 1;
                alertBadge.classList.add('pulse');
                
                setTimeout(() => {
                    alertBadge.classList.remove('pulse');
                }, 1000);
            }
        }, 5000);
    }
    
    // Check for new notifications every 30 seconds
    setInterval(updateNotificationCount, 30000);
});