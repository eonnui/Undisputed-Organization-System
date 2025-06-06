let isNotificationsDropdownOpen = false;
let lastSeenUnreadNotificationIds = new Set();
let notificationPollingTimer = null;
const POLLING_INTERVAL_MS = 30000;

function applyUserTheme() {
    fetch('/get_user_data')
        .then(response => {
            if (!response.ok) {
                if (response.status === 401) return null;
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            const root = document.documentElement;
            let organizationName = 'Organization System';

            if (data?.organization) {
                organizationName = data.organization.name || organizationName;
                if (data.organization.custom_palette) {
                    try {
                        const palette = JSON.parse(data.organization.custom_palette);
                        for (const varName in palette) {
                            if (Object.prototype.hasOwnProperty.call(palette, varName)) {
                                root.style.setProperty(varName, palette[varName]);
                            }
                        }
                    } catch (e) {
                        if (data.organization.theme_color) {
                            root.style.setProperty('--organization-theme-color', data.organization.theme_color);
                        }
                    }
                } else if (data.organization.theme_color) {
                    root.style.setProperty('--organization-theme-color', data.organization.theme_color);
                }
            }

            const profilePicElement = document.getElementById('user-profile-pic');
            const profileNameElement = document.getElementById('profile-name');
            const organizationNameDisplay = document.getElementById('organizationNameDisplay');

            if (data?.first_name && profileNameElement) {
                profileNameElement.textContent = data.first_name;
            } else if (profileNameElement) {
                profileNameElement.textContent = 'Profile';
            }

            if (data?.profile_picture && profilePicElement) {
                profilePicElement.src = data.profile_picture;
            } else if (profilePicElement) {
                profilePicElement.src = '/static/images/your_image_name.jpg';
            }

            if (organizationNameDisplay) {
                organizationNameDisplay.textContent = organizationName;
            }
        })
        .catch(() => {
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
    const notificationsDropdown = document.getElementById('notifications-dropdown');
    notificationsDropdown.innerHTML = '<div class="notification-item">Loading notifications...</div>';

    try {
        const url = `/get_user_notifications?include_read=${includeRead}`;
        const response = await fetch(url, { cache: 'no-store' });

        if (!response.ok) {
            if (response.status === 401) {
                notificationsDropdown.innerHTML = '<div class="notification-item">Please log in to see notifications.</div>';
                return [];
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        const notifications = data.notifications;

        notificationsDropdown.innerHTML = '';
        if (!notifications?.length) {
            notificationsDropdown.innerHTML = '<div class="notification-item">No notifications.</div>';
            return [];
        }

        notifications.forEach(notification => {
            const notificationItem = document.createElement('a');
            notificationItem.classList.add('notification-item', notification.is_read ? 'read' : 'unread');
            notificationItem.textContent = notification.message || 'New Notification';
            notificationItem.href = notification.url || '#';
            if (!notification.url) notificationItem.style.cursor = 'default';

            if (!notification.is_read && notification.id) {
                notificationItem.addEventListener('click', async (event) => {
                    if (notificationItem.href === '#' || notificationItem.target === '_blank') {
                        event.preventDefault();
                    }
                    
                    if (notificationItem.classList.contains('unread')) {
                        const success = notification.group_ids ? 
                            await markNotificationsAsReadBulk(notification.group_ids) : 
                            await markNotificationAsRead(notification.id);
                        
                        if (success) {                           
                            await fetchAndDisplayNotifications(true);                            
                           
                            updateBadgeBasedOnNewUnread();

                            if (notification.url && notification.url !== '#' && notificationItem.href === '#') { 
                                window.location.href = notification.url;
                            }
                        }
                    }
                });
            }
            notificationsDropdown.appendChild(notificationItem);
        });
        return notifications;
    } catch (error) {
        notificationsDropdown.innerHTML = '<div class="notification-item">Failed to load notifications.</div>';
        return [];
    }
}

async function markNotificationAsRead(notificationId) {
    try {
        const response = await fetch(`/${notificationId}/read`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
        return response.ok;
    } catch (error) {
        return false;
    }
}

async function markNotificationsAsReadBulk(notificationIds) {
    try {
        const response = await fetch(`/mark_notifications_as_read_bulk`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(notificationIds) });
        return response.ok;
    } catch (error) {
        return false;
    }
}

async function updateBadgeBasedOnNewUnread() {
    if (isNotificationsDropdownOpen) return;

    const unreadBadge = document.getElementById('unread-notifications-badge');
    try {
        const notifications = await fetchAndDisplayNotifications(false);
        let newUnreadCount = 0;
        const currentUnreadIds = new Set();

        notifications.forEach(notification => {
            if (!notification.is_read) {
                (notification.group_ids || [notification.id]).forEach(id => currentUnreadIds.add(id));
            }
        });

        currentUnreadIds.forEach(id => {
            if (!lastSeenUnreadNotificationIds.has(id)) {
                newUnreadCount++;
            }
        });

        if (unreadBadge) {
            unreadBadge.textContent = newUnreadCount || '';
            unreadBadge.classList.toggle('hidden', newUnreadCount === 0);
        }
    } catch (error) {
        if (unreadBadge) {
            unreadBadge.textContent = '';
            unreadBadge.classList.add('hidden');
        }
    }
}

function startNotificationPolling() {
    clearInterval(notificationPollingTimer);
    notificationPollingTimer = setInterval(updateBadgeBasedOnNewUnread, POLLING_INTERVAL_MS);
    updateBadgeBasedOnNewUnread();
}

function setupDropdown(buttonSelector, dropdownId) {
    const button = document.querySelector(buttonSelector);
    const dropdown = document.getElementById(dropdownId);
    const unreadBadge = document.getElementById('unread-notifications-badge'); 

    if (!button || !dropdown) return;

    function toggleDropdown() {
        const isExpanded = dropdown.classList.toggle('show');
        button.setAttribute('aria-expanded', isExpanded);

        if (dropdownId === 'notifications-dropdown') {
            isNotificationsDropdownOpen = isExpanded;
            if (isExpanded) {
                if (unreadBadge) {
                    unreadBadge.textContent = '';
                    unreadBadge.classList.add('hidden');
                }
                fetchAndDisplayNotifications(true).then(notifications => {                   
                    lastSeenUnreadNotificationIds.clear();
                    notifications.forEach(notification => {
                        if (!notification.is_read) {
                            (notification.group_ids || [notification.id]).forEach(id => lastSeenUnreadNotificationIds.add(id));
                        }
                    });
                    localStorage.setItem('lastSeenUnreadNotificationIds', JSON.stringify(Array.from(lastSeenUnreadNotificationIds)));
                });
                clearInterval(notificationPollingTimer);
            } else {
                startNotificationPolling();
            }
        }
        
        const firstInteractive = dropdown.querySelector('a, button');
        if (firstInteractive) firstInteractive.focus();
        else if (!isExpanded) button.focus();
    }

    function handleKeyboardNavigation(event) {
        if (event.key === 'ArrowDown') {
            event.preventDefault();
            toggleDropdown();
        } else if (event.key === 'Escape' && dropdown.classList.contains('show')) {
            toggleDropdown();
        } else if (event.key === 'Tab' && dropdown.classList.contains('show')) {
            const focusableElements = Array.from(dropdown.querySelectorAll('a, button'));
            if (!focusableElements.length) return;

            const [firstFocusable, lastFocusable] = [focusableElements[0], focusableElements[focusableElements.length - 1]];
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
    const navTexts = document.querySelectorAll('.sidebar nav ul li a .nav-text');
    const logo = document.querySelector('.sidebar .logo');
    let isCollapsed = false;

    menuToggle.addEventListener('click', () => {
        isCollapsed = !isCollapsed;
        sidebar.classList.toggle('collapsed', isCollapsed);
        mainContent.classList.toggle('collapsed', isCollapsed);
        menuText.textContent = isCollapsed ? '' : 'Menu';
        logo.style.opacity = isCollapsed ? 0 : 1;
        logo.style.pointerEvents = isCollapsed ? 'none' : 'auto';
        navTexts.forEach(span => span.style.display = isCollapsed ? 'none' : 'inline-block');
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
                if (openDropdown.id === 'notifications-dropdown') {
                    isNotificationsDropdownOpen = false;
                    startNotificationPolling();
                }
            }
        });
    });

    initializeSidebarToggle();

    const storedIds = localStorage.getItem('lastSeenUnreadNotificationIds');
    if (storedIds) {
        try {
            lastSeenUnreadNotificationIds = new Set(JSON.parse(storedIds));
        } catch (e) {
            console.error("Error parsing stored notification IDs:", e);
            localStorage.removeItem('lastSeenUnreadNotificationIds');
        }
    }

    startNotificationPolling();
});