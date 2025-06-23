let isNotificationsDropdownOpen = false;
let lastSeenUnreadNotificationIds = new Set();
let notificationPollingTimer = null;
const POLLING_INTERVAL_MS = 30000;


function applyTheme(isDark) {
    const body = document.body;
    const themeIcon = document.querySelector('#theme-toggle .theme-icon'); 

    if (isDark) {
        body.classList.add('dark-theme');
        if (themeIcon) {
            themeIcon.classList.remove('ph-sun'); 
            themeIcon.classList.add('ph-moon'); 
        }
        localStorage.setItem('theme', 'dark'); 
    } else {
        body.classList.remove('dark-theme');
        if (themeIcon) {
            themeIcon.classList.remove('ph-moon'); 
            themeIcon.classList.add('ph-sun'); 
        }
        localStorage.setItem('theme', 'light'); 
    }

    
    
    
    
    
    
    
    applyUserTheme(); 
}


function toggleTheme() {
    const isCurrentlyDarkMode = localStorage.getItem('theme') === 'dark';
    applyTheme(!isCurrentlyDarkMode); 
}


function applyUserTheme() {
    const isDarkMode = localStorage.getItem('theme') === 'dark'; 
    const themeQueryParam = isDarkMode ? '?dark_mode=true' : '';

    fetch(`/get_user_data${themeQueryParam}`) 
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


async function fetchAndDisplayNotifications(includeRead = true) {
    const notificationsDropdown = document.getElementById('notifications-dropdown');
    if (!notificationsDropdown) {
        return [];
    }
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

        const clearAllContainer = document.createElement('div');
        clearAllContainer.classList.add('notification-actions');
        const clearAllBtn = document.createElement('button');
        clearAllBtn.classList.add('clear-all-btn');
        clearAllBtn.textContent = 'Clear All';
        clearAllBtn.onclick = async () => {
            if (await clearAllNotifications()) {
                await fetchAndDisplayNotifications(true);
                updateBadgeBasedOnNewUnread();
            } else {
                alert('Failed to clear all notifications.');
            }
        };
        clearAllContainer.appendChild(clearAllBtn);
        notificationsDropdown.appendChild(clearAllContainer);

        if (!notifications?.length) {
            notificationsDropdown.innerHTML += `
                <div class="notification-item no-notifications">No notifications.</div>
            `;
            return [];
        }

        notifications.forEach(notification => {
            const notificationContainer = document.createElement('div');
            notificationContainer.classList.add('notification-container');

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

            const clearButton = document.createElement('button');
            clearButton.classList.add('clear-notification-btn');
            clearButton.innerHTML = '&times;';
            clearButton.title = 'Clear notification';
            clearButton.addEventListener('click', async (event) => {
                event.stopPropagation();
                event.preventDefault();

                const notificationIdsToClear = notification.group_ids || [notification.id];
                let successCount = 0;
                for (const id of notificationIdsToClear) {
                    if (await clearNotification(id)) {
                        successCount++;
                    }
                }

                if (successCount > 0) {
                    await fetchAndDisplayNotifications(true);
                    updateBadgeBasedOnNewUnread();
                } else {
                    alert('Failed to clear notification.');
                }
            });

            notificationContainer.appendChild(notificationItem);
            notificationContainer.appendChild(clearButton);
            notificationsDropdown.appendChild(notificationContainer);
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

async function clearNotification(notificationId) {
    try {
        const response = await fetch(`/notifications/${notificationId}`, { method: 'DELETE' });
        if (response.status === 204) {
            return true;
        } else {
            return false;
        }
    } catch (error) {
        return false;
    }
}

async function clearAllNotifications() {
    try {
        const response = await fetch(`/notifications/clear_all`, { method: 'DELETE' });
        return response.ok;
    } catch (error) {
        return false;
    }
}

async function updateBadgeBasedOnNewUnread() {
    const unreadBadge = document.getElementById('unread-notifications-badge');
    if (!unreadBadge) return;

    if (isNotificationsDropdownOpen) {
        unreadBadge.textContent = '';
        unreadBadge.classList.add('hidden');
        return;
    }

    try {
        const currentUnreadNotifications = await fetchAndDisplayNotifications(false);
        const currentUnreadIds = new Set();
        currentUnreadNotifications.forEach(notification => {
            (notification.group_ids || [notification.id]).forEach(id => currentUnreadIds.add(id));
        });

        const newUnreadIds = new Set();
        currentUnreadIds.forEach(id => {
            if (!lastSeenUnreadNotificationIds.has(id)) {
                newUnreadIds.add(id);
            }
        });

        const totalNewUnreadCount = newUnreadIds.size;

        if (totalNewUnreadCount > 0) {
            unreadBadge.textContent = totalNewUnreadCount.toString();
            unreadBadge.classList.remove('hidden');
        } else {
            unreadBadge.textContent = '';
            unreadBadge.classList.add('hidden');
        }
    } catch (error) {
        unreadBadge.textContent = '';
        unreadBadge.classList.add('hidden');
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

function setSidebarState(isCollapsed) {
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    const menuText = document.querySelector('.top-bar .menu-text');
    const navTexts = document.querySelectorAll('.sidebar nav ul li a .nav-text');
    const logo = document.querySelector('.sidebar .logo');

    if (!sidebar || !mainContent || !menuText || !logo) {
        return;
    }

    if (isCollapsed) {
        sidebar.classList.add('collapsed');
        mainContent.classList.add('collapsed');
        menuText.textContent = '';
        logo.style.opacity = 0;
        logo.style.pointerEvents = 'none';
        navTexts.forEach(span => span.style.display = 'none');
        localStorage.setItem('sidebarState', 'collapsed');
    } else {
        sidebar.classList.remove('collapsed');
        mainContent.classList.remove('collapsed');
        menuText.textContent = 'Menu';
        logo.style.opacity = 1;
        logo.style.pointerEvents = 'auto';
        navTexts.forEach(span => span.style.display = 'inline-block');
        localStorage.setItem('sidebarState', 'expanded');
    }
}


function initializeSidebarToggle() {
    const menuToggle = document.getElementById('menu-toggle');

    if (!menuToggle) {
        return;
    }

    const savedState = localStorage.getItem('sidebarState');
    if (savedState === 'collapsed') {
        setSidebarState(true);
    } else {
        setSidebarState(false);
    }


    menuToggle.addEventListener('click', () => {
        const isCurrentlyCollapsed = document.querySelector('.sidebar').classList.contains('collapsed');
        setSidebarState(!isCurrentlyCollapsed);
    });
}


document.addEventListener('DOMContentLoaded', function() {
    
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    
    if (savedTheme === null) {
        applyTheme(prefersDark); 
    } else {
        applyTheme(savedTheme === 'dark'); 
    }

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
            localStorage.removeItem('lastSeenUnreadNotificationIds');
        }
    }

    startNotificationPolling();

    const todayDateElement = document.getElementById('today-date');
    if (todayDateElement) {
        const today = new Date();
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        const formattedDate = today.toLocaleDateString('en-PH', options);
        todayDateElement.textContent = formattedDate;
    }

    const themeToggleButton = document.getElementById('theme-toggle');
    if (themeToggleButton) {
        themeToggleButton.addEventListener('click', toggleTheme); 
    }
});