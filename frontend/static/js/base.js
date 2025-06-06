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
                else if (data.organization.theme_color) {
                    root.style.setProperty('--organization-theme-color', data.organization.theme_color);
                }
            } else {
            }

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

async function fetchAndDisplayNotifications(includeRead = true) {
    console.log(`fetchAndDisplayNotifications: Function started. Include read: ${includeRead}`); 
    const notificationsDropdown = document.getElementById('notifications-dropdown');
    notificationsDropdown.innerHTML = '<div class="notification-item">Loading notifications...</div>';

    try {
        let url = '/get_user_notifications';
        if (includeRead) {
            url += '?include_read=true';
        }
        console.log('fetchAndDisplayNotifications: Fetching from URL:', url); 
        const response = await fetch(url, { cache: 'no-store' });

        console.log('fetchAndDisplayNotifications: Received response from notifications API:', response); 
        if (!response.ok) {
            if (response.status === 401) {
                notificationsDropdown.innerHTML = '<div class="notification-item">Please log in to see notifications.</div>';
                console.warn('fetchAndDisplayNotifications: User not authenticated (401) for notifications.'); 
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        const notifications = data.notifications;
        console.log('fetchAndDisplayNotifications: Notifications data received:', notifications); 

        notificationsDropdown.innerHTML = '';

        if (notifications && notifications.length > 0) {
            notifications.forEach(notification => {
                const notificationItem = document.createElement('a');
                notificationItem.classList.add('notification-item');
                
                if (notification.is_read) {
                    notificationItem.classList.add('read');
                    console.log(`Notification ID ${notification.id} is read, applying 'read' class.`); 
                } else {
                    notificationItem.classList.add('unread');
                    console.log(`Notification ID ${notification.id} is unread, applying 'unread' class.`); 
                }
                notificationItem.textContent = notification.message || 'New Notification';

                if (notification.url) {
                    notificationItem.href = notification.url;
                } else {
                    notificationItem.href = '#';
                    notificationItem.style.cursor = 'default';
                }

                if (!notification.is_read && notification.id) {
                    console.log(`Notification ID ${notification.id}: Adding click listener to mark as read.`); 
                    notificationItem.addEventListener('click', async (event) => {
                        console.log(`Notification ID ${notification.id} clicked.`); 
                        if (notificationItem.href === '#' || notificationItem.target === '_blank') {
                            event.preventDefault(); 
                            console.log(`Notification ID ${notification.id}: Default navigation prevented.`);
                        }
                        
                        if (notificationItem.classList.contains('unread')) {
                            console.log(`Notification ID ${notification.id}: Marking as read...`); 
                            let success;
                            if (notification.group_ids) {                                
                                success = await markNotificationsAsReadBulk(notification.group_ids);
                            } else {                                
                                success = await markNotificationAsRead(notification.id);
                            }
                            
                            if (success) {
                                console.log(`Notification ID(s) ${notification.id} (or group) successfully marked as read on backend.`); 
                                await fetchAndDisplayNotifications(true); 
                                console.log(`Notifications re-fetched and re-displayed after marking ID ${notification.id} (or group) as read.`); 
                                
                                if (notification.url && notification.url !== '#' && notificationItem.href === '#') { 
                                    console.log(`Navigating to URL: ${notification.url}`);
                                    window.location.href = notification.url;
                                }
                            } else {
                                console.warn(`Notification ID ${notification.id} (or group): Failed to mark as read on backend.`); 
                            }
                        }
                    });
                }
                notificationsDropdown.appendChild(notificationItem);
            });
        } else {
            notificationsDropdown.innerHTML = '<div class="notification-item">No notifications.</div>';
            console.log('fetchAndDisplayNotifications: No notifications to display.'); 
        }
        console.log('fetchAndDisplayNotifications: Function finished successfully.'); 

    } catch (error) {
        console.error('fetchAndDisplayNotifications: Failed to load notifications:', error); 
        notificationsDropdown.innerHTML = '<div class="notification-item">Failed to load notifications.</div>';
    }
}

async function markNotificationAsRead(notificationId) {
    console.log(`markNotificationAsRead: Attempting to mark notification ID ${notificationId} as read.`); 
    try {
        const response = await fetch(`/${notificationId}/read`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
        });

        console.log(`markNotificationAsRead: Received response for ID ${notificationId}:`, response); 
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`markNotificationAsRead: Failed for ID ${notificationId}: Status ${response.status} - ${errorText}`); 
            return false;
        }
        console.log(`markNotificationAsRead: Successfully marked ID ${notificationId} as read.`); 
        return true;
    } catch (error) {
        console.error(`markNotificationAsRead: Network error for ID ${notificationId}:`, error); 
        return false;
    }
}

async function markNotificationsAsReadBulk(notificationIds) {
    console.log(`markNotificationsAsReadBulk: Attempting to mark notification IDs ${notificationIds} as read.`);
    try {
        const response = await fetch(`/mark_notifications_as_read_bulk`, { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(notificationIds) 
        });

        console.log(`markNotificationsAsReadBulk: Received response for IDs ${notificationIds}:`, response);
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`markNotificationsAsReadBulk: Failed for IDs ${notificationIds}: Status ${response.status} - ${errorText}`);
            return false;
        }
        console.log(`markNotificationsAsReadBulk: Successfully marked IDs ${notificationIds} as read.`);
        return true;
    } catch (error) {
        console.error(`markNotificationsAsReadBulk: Network error for IDs ${notificationIds}:`, error);
        return false;
    }
}

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
                fetchAndDisplayNotifications(true);
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

function initializeSidebarToggle() {
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    const menuToggle = document.getElementById('menu-toggle');
    const menuText = document.querySelector('.top-bar .menu-text');
    const navItems = document.querySelectorAll('.sidebar nav ul li a');
    const logo = document.querySelector('.sidebar .logo');
    let isCollapsed = false;

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
}

document.addEventListener('DOMContentLoaded', function() {
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

    initializeSidebarToggle();
});