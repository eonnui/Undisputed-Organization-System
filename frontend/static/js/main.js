// Function to apply user-specific theme colors
function applyUserTheme() {
    console.log('Attempting to apply user theme...');

    fetch('/get_user_data') // Your backend endpoint to get user and organization data
        .then(response => {
            if (!response.ok) {
                if (response.status === 401) {
                    console.warn('User not authenticated. Using default theme.');
                    return null; // Handle unauthenticated case gracefully
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('User data received for theme application:', data);

            const root = document.documentElement; // The <html> element
            let organizationName = 'Organization System'; // Default name

            if (data && data.organization) {
                organizationName = data.organization.name || organizationName;

                // Priority 1: Apply full custom_palette if available
                if (data.organization.custom_palette) {
                    try {
                        const palette = JSON.parse(data.organization.custom_palette);
                        console.log('Applying custom palette:', palette);
                        for (const varName in palette) {
                            if (palette.hasOwnProperty(varName)) {
                                root.style.setProperty(varName, palette[varName]);
                            }
                        }
                        // If a full palette is applied, the single theme_color might still be used for a primary accent
                        // Or you can define a primary accent within the custom_palette itself (e.g., --org-primary-theme-color)
                        // For now, let's assume if custom_palette exists, it covers everything.
                    } catch (e) {
                        console.error('Error parsing custom_palette JSON:', e);
                        // Fallback to theme_color if custom_palette is invalid JSON
                        if (data.organization.theme_color) {
                            root.style.setProperty('--organization-theme-color', data.organization.theme_color);
                            console.log(`Applied theme color (fallback): ${data.organization.theme_color} for organization: ${organizationName}`);
                        }
                    }
                }
                // Priority 2: Fallback to single theme_color if no custom_palette or parsing failed
                else if (data.organization.theme_color) {
                    root.style.setProperty('--organization-theme-color', data.organization.theme_color);
                    console.log(`Applied theme color: ${data.organization.theme_color} for organization: ${organizationName}`);
                }
            } else {
                console.warn('No organization data found, using default theme.');
            }

            // Update profile name and picture (if present)
            const profilePicElement = document.getElementById('user-profile-pic');
            const profileNameElement = document.getElementById('profile-name');
            if (data && data.first_name && profileNameElement) {
                profileNameElement.textContent = data.first_name;
            } else if (profileNameElement) {
                profileNameElement.textContent = 'Profile'; // Default
            }

            if (data && data.profile_picture && profilePicElement) {
                profilePicElement.src = data.profile_picture;
            } else if (profilePicElement) {
                profilePicElement.src = '/static/images/your_image_name.jpg'; // Default
            }

            // Update organization name display (if you have one in base.html)
            const organizationNameDisplay = document.getElementById('organizationNameDisplay');
            if (organizationNameDisplay) {
                organizationNameDisplay.textContent = organizationName;
            }
        })
        .catch(error => {
            console.error('Error fetching user data for theme:', error);
            // Ensure default profile/organization name is shown on error
            const profilePicElement = document.getElementById('user-profile-pic');
            const profileNameElement = document.getElementById('profile-name');
            const organizationNameDisplay = document.getElementById('organizationNameDisplay');

            if (profileNameElement) profileNameElement.textContent = 'Profile';
            if (profilePicElement) profilePicElement.src = '/static/images/your_image_name.jpg';
            if (organizationNameDisplay) organizationNameDisplay.textContent = 'Organization System';
        });
}

// Initial call when the DOM is loaded
document.addEventListener('DOMContentLoaded', applyUserTheme);

// Sidebar toggle functionality (as previously implemented)
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
            console.error(`Dropdown elements not found for button: ${buttonSelector}, dropdown: ${dropdownId}`);
            return;
        }

        function toggleDropdown() {
            const isExpanded = dropdown.classList.toggle('show');
            button.setAttribute('aria-expanded', isExpanded);
            if (isExpanded) {
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
            if (relatedButton && !event.target.matches(relatedButton) && !openDropdown.contains(event.target)) {
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