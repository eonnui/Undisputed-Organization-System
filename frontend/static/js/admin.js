function applyUserTheme() {
    fetch('/get_user_data')
        .then(response => {
            if (!response.ok) {
                if (response.status === 401) {
                    return null;
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            const root = document.documentElement;
            let organizationName = 'Organization System';

            if (data && data.organization) {
                organizationName = data.organization.name || organizationName;

                // Priority 1: Apply full custom_palette if available
                if (data.organization.custom_palette) {
                    try {
                        const palette = JSON.parse(data.organization.custom_palette);
                        for (const varName in palette) {
                            if (palette.hasOwnProperty(varName)) {
                                root.style.setProperty(varName, palette[varName]);
                            }
                        }
                    } catch (e) {
                        if (data.organization.theme_color) {
                            root.style.setProperty('--organization-theme-color', data.organization.theme_color);
                        }
                    }
                }
                // Priority 2: Fallback to single theme_color if no custom_palette or parsing failed
                else if (data.organization.theme_color) {
                    root.style.setProperty('--organization-theme-color', data.organization.theme_color);
                }
            }

            // Update profile name and picture (if present)
            const profilePicElement = document.getElementById('user-profile-pic');
            const profileNameElement = document.getElementById('profile-name');
            if (data && data.first_name && profileNameElement) {
                profileNameElement.textContent = data.first_name;
            } else if (profileNameElement) {
                profileNameElement.textContent = 'Profile';
            }

            if (data && data.profile_picture && profilePicElement) {
                profilePicElement.src = data.profile_picture;
            } else if (profilePicElement) {
                profilePicElement.src = '/static/images/your_image_name.jpg';
            }

            // Update organization name display
            const organizationNameDisplay = document.getElementById('organizationNameDisplay');
            if (organizationNameDisplay) {
                organizationNameDisplay.textContent = organizationName;
            }
        })
        .catch(error => {
            const profilePicElement = document.getElementById('user-profile-pic');
            const profileNameElement = document.getElementById('profile-name');
            const organizationNameDisplay = document.getElementById('organizationNameDisplay');

            if (profileNameElement) profileNameElement.textContent = 'Profile';
            if (profilePicElement) profilePicElement.src = '/static/images/your_image_name.jpg';
            if (organizationNameDisplay) organizationNameDisplay.textContent = 'Organization System';
        });
}

document.addEventListener('DOMContentLoaded', applyUserTheme);

// Function to fetch and display user notifications
async function fetchAndDisplayNotifications() {
    const notificationsDropdown = document.getElementById('notifications-dropdown');
    notificationsDropdown.innerHTML = '<div class="notification-item">Loading notifications...</div>';

    try {
        const response = await fetch('/get_user_notifications');
        if (!response.ok) {
            if (response.status === 401) {
                notificationsDropdown.innerHTML = '<div class="notification-item">Please log in to see notifications.</div>';
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        const notifications = data.notifications;

        notificationsDropdown.innerHTML = '';

        if (notifications && notifications.length > 0) {
            notifications.forEach(notification => {
                const notificationItem = document.createElement('div');
                notificationItem.classList.add('notification-item');
                notificationItem.textContent = notification.message || notification;
                notificationsDropdown.appendChild(notificationItem);
            });
        } else {
            notificationsDropdown.innerHTML = '<div class="notification-item">No new notifications.</div>';
        }
    } catch (error) {
        notificationsDropdown.innerHTML = '<div class="notification-item">Failed to load notifications.</div>';
    }
}

// Sidebar toggle and dropdown functionality
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    const menuToggle = document.getElementById('menu-toggle');
    const menuText = document.querySelector('.top-bar .menu-text');
    const navItems = document.querySelectorAll('.sidebar nav ul li a');
    const logo = document.querySelector('.sidebar .logo');
    let isCollapsed = false;

    // Function to handle dropdown toggle and accessibility
    function setupDropdown(buttonSelector, dropdownId) {
        const button = document.querySelector(buttonSelector);
        const dropdown = document.getElementById(dropdownId);

        if (!button || !dropdown) {
            return;
        }

        function toggleDropdown() {
            const isExpanded = dropdown.classList.toggle('show');
            button.setAttribute('aria-expanded', isExpanded);

            if (isExpanded) {                
                if (dropdownId === 'notifications-dropdown') {
                    fetchAndDisplayNotifications();
                }
                const firstInteractive = dropdown.querySelector('a, button');
                if (firstInteractive) {
                    firstInteractive.focus();
                }
            } else {
                button.focus();
            }
        }

        function handleKeyboardNavigation(event) {
            if (event.key === 'ArrowDown') {
                event.preventDefault();
                toggleDropdown();
            } else if (event.key === 'Escape' && dropdown.classList.contains('show')) {
                toggleDropdown();
            } else if (event.key === 'Tab' && dropdown.classList.contains('show')) {
                const focusableElements = dropdown.querySelectorAll('a, button');
                if (focusableElements.length > 0) {
                    const firstFocusable = focusableElements[0];
                    const lastFocusable = focusableElements[focusableElements.length - 1];
                    const currentFocus = document.activeElement;

                    if (event.shiftKey && currentFocus === firstFocusable) {
                        event.preventDefault();
                        lastFocusable.focus();
                    } else if (!event.shiftKey && currentFocus === lastFocusable) {
                        event.preventDefault();
                        firstFocusable.focus();
                    }
                }
            }
        }

        button.setAttribute('aria-haspopup', 'true');
        button.setAttribute('aria-expanded', 'false');
        button.addEventListener('click', toggleDropdown);
        button.addEventListener('keydown', handleKeyboardNavigation);
    }

    setupDropdown('.profile-btn', 'profile-dropdown');
    setupDropdown('.notification-btn', 'notifications-dropdown');

    window.addEventListener('click', function(event) {
        document.querySelectorAll('.dropdown-content.show').forEach(openDropdown => {
            const relatedButton = document.querySelector(`[aria-controls="${openDropdown.id}"]`);
            if (relatedButton && !relatedButton.contains(event.target) && !openDropdown.contains(event.target)) {
                openDropdown.classList.remove('show');
                relatedButton.setAttribute('aria-expanded', 'false');
            }
        });
    });

    menuToggle.addEventListener('click', () => {
        if (isCollapsed) {
            sidebar.classList.remove('collapsed');
            mainContent.classList.remove('collapsed');
            menuText.textContent = 'Menu';
            navItems.forEach(navItem => {
                const navTextSpan = navItem.querySelector('.nav-text');
                if (navTextSpan) {
                    navTextSpan.style.display = 'inline-block';
                }
            });
            logo.style.opacity = 1;
            logo.style.pointerEvents = 'auto';
        } else {
            sidebar.classList.add('collapsed');
            mainContent.classList.add('collapsed');
            menuText.textContent = '';
            navItems.forEach(navItem => {
                const navTextSpan = navItem.querySelector('.nav-text');
                if (navTextSpan) {
                    navTextSpan.style.display = 'none';
                }
            });
            logo.style.opacity = 0;
            logo.style.pointerEvents = 'none';
        }
        isCollapsed = !isCollapsed;
    });
});
