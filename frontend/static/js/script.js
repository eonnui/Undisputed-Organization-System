document.addEventListener('DOMContentLoaded', function() {
    const app = document.getElementById('app');
    let currentForm = 'login';
    let registrationSuccessMessage = '';
    let forgotPasswordIdentifier = ''; // Store student number or email for code verification
    let organizations = []; // Store fetched organizations

    // --- START: applyUserTheme function (added/updated) ---
    async function applyUserTheme() {
        console.log("Attempting to apply user theme...");
        try {
            // 1. Make an API request to your backend to get user details
            //    No Authorization header needed if session middleware handles authentication.
            const response = await fetch('/get_user_data', { // Use your actual endpoint URL
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                // Handle HTTP errors (e.g., 401 Unauthorized if session is invalid, 404 Not Found)
                const errorData = await response.json();
                console.error('Failed to fetch user data:', errorData.detail || response.statusText);
                // If user is not authenticated (e.g., 401), you might want to redirect to login
                if (response.status === 401) {
                    console.log("User not authenticated. Redirecting to login or showing login form.");
                    // Example: If you have a function to show login form
                    // currentForm = 'login';
                    // render();
                }
                return;
            }

            const userData = await response.json();
            console.log('User data received for theme application:', userData);

            // 2. Access the theme_color from the organization object
            //    Ensure userData.organization exists and has theme_color
            const themeColor = userData.organization ? userData.organization.theme_color : null;
            const organizationName = userData.organization ? userData.organization.name : 'Guest';

            if (themeColor) {
                // 3. Apply the theme_color as a CSS Custom Property (Variable)
                //    This sets a variable --organization-theme-color on the <html> element
                //    which can then be used throughout your CSS.
                document.documentElement.style.setProperty('--organization-theme-color', themeColor);
                console.log(`Applied theme color: ${themeColor} for organization: ${organizationName}`);

                // Optional: Update a specific element's text with the organization name
                const orgNameDisplay = document.getElementById('organizationNameDisplay');
                if (orgNameDisplay) {
                    orgNameDisplay.textContent = organizationName;
                }

            } else {
                console.log("No organization or theme color found for this user. Applying default theme.");
                // Optionally apply a default theme or remove any existing custom theme
                document.documentElement.style.removeProperty('--organization-theme-color');
                const orgNameDisplay = document.getElementById('organizationNameDisplay');
                if (orgNameDisplay) {
                    orgNameDisplay.textContent = 'No Organization'; // Or a default like 'Guest'
                }
            }

        } catch (error) {
            console.error('An unexpected error occurred during theme application:', error);
        }
    }
    // --- END: applyUserTheme function ---


    function renderLoginForm() {
        return `
            <div class="wrapper">
                <h1>LOGIN</h1>
                ${registrationSuccessMessage ? `<div class="notification success show">${registrationSuccessMessage}</div>` : ''}
                <form class="form" id="login-form">
                    <div class="input-group">
                        <label for="login-student-number">Student Number</label>
                        <input type="text" id="login-student-number" placeholder="Enter your student number" required />
                        <div class="error-message" id="login-student-number-error"></div>
                    </div>

                    <div class="input-group">
                        <label for="login-password">Password</label>
                        <div class="password-input-wrapper">
                            <input type="password" id="login-password" placeholder="Enter your password" required />
                            <button type="button" class="view-password-button" data-target="login-password">Show</button>
                        </div>
                        <div class="error-message" id="login-password-error"></div>
                    </div>

                    <button type="submit" class="login-button">Login</button>

                    <button type="button" class="forgot-password" id="toggle-to-forgot-password">Forgot Password?</button>

                    <div class="form-switch">
                        <p>Don't have an account?</p>
                        <button type="button" class="link-button" id="toggle-to-signup">
                            Register here
                        </button>
                    </div>
                    <div class="form-switch" style="margin-top: 10px;">
                        <p>Are you an admin?</p>
                        <button type="button" class="link-button" id="toggle-to-admin-signup">
                            Admin Registration
                        </button>
                    </div>
                    </form>
            </div>
        `;
    }

    function renderSignupForm() {
        let organizationOptions = '<option value="" disabled selected>Select your organization</option>';
        if (organizations.length > 0) {
            organizations.forEach(org => {
                // Keep value as ID, but we will extract the name on submit
                organizationOptions += `<option value="${org.id}">${org.name}</option>`;
            });
        } else {
            organizationOptions = '<option value="" disabled>Loading organizations...</option>'; // Or some loading message
        }

        return `
            <div class="wrapper">
                <h1>SIGN UP</h1>
                <form class="form" id="signup-form">
                    <div class="input-group">
                        <label for="signup-student-number">Student Number</label>
                        <input type="text" id="signup-student-number" placeholder="Enter your student number" required />
                        <div class="error-message" id="signup-student-number-error"></div>
                    </div>

                    <div class="input-group">
                        <label for="signup-email">Student Email</label>
                        <input type="email" id="signup-email" placeholder="Enter your email" required />
                        <div class="error-message" id="signup-email-error"></div>
                    </div>

                    <div class="input-group">
                        <label for="signup-organization">Select Organization</label>
                        <div class="select-wrapper">
                            <select id="signup-organization">
                                ${organizationOptions}
                            </select>
                        </div>
                        <div class="error-message" id="signup-organization-error"></div>
                    </div>

                    <div class="input-group">
                        <label for="signup-first-name">First Name</label>
                        <input type="text" id="signup-first-name" placeholder="Enter your first name" required />
                        <div class="error-message" id="signup-first-name-error"></div>
                    </div>

                    <div class="input-group">
                        <label for="signup-last-name">Last Name</label>
                        <input type="text" id="signup-last-name" placeholder="Enter your last name" required />
                        <div class="error-message" id="signup-last-name-error"></div>
                    </div>

                    <div class="input-group">
                        <label for="signup-password">Password</label>
                        <div class="password-input-wrapper">
                            <input type="password" id="signup-password" placeholder="Create a password" required />
                            <button type="button" class="view-password-button" data-target="signup-password">Show</button>
                        </div>
                        <div class="error-message" id="signup-password-error"></div>
                        <p class="password-requirements" style="font-size: 0.7em; color: #ddd; margin-top: 0.2rem;">Password must be at least 8 characters and include uppercase, lowercase, and a number.</p>
                    </div>

                    <div class="input-group">
                        <label for="signup-confirm-password">Confirm Password</label>
                        <div class="password-input-wrapper">
                            <input type="password" id="signup-confirm-password" placeholder="Confirm your password" required />
                            <button type="button" class="view-password-button" data-target="signup-confirm-password">Show</button>
                        </div>
                        <div class="error-message" id="signup-confirm-password-error"></div>
                    </div>

                    <button type="submit">Sign Up</button>

                    <div class="form-switch">
                        <p>Already have an account?</p>
                        <button type="button" class="link-button" id="toggle-to-login">
                            Log in here
                        </button>
                    </div>
                </form>
            </div>
        `;
    }

    function renderForgotPasswordForm() {
        return `
            <div class="wrapper">
                <h1>FORGOT PASSWORD</h1>
                <form class="form" id="forgot-password-form">
                    <div class="input-group">
                        <label for="forgot-password-identifier">Student Number or Email</label>
                        <input type="text" id="forgot-password-identifier" placeholder="Enter your student number or email" required />
                        <div class="error-message" id="forgot-password-identifier-error"></div>
                    </div>

                    <button type="submit">Send Reset Code</button>

                    <div class="form-switch">
                        <button type="button" class="link-button" id="toggle-to-login-from-forgot">
                            Back to Login
                        </button>
                    </div>
                </form>
            </div>
        `;
    }

    function renderResetPasswordCodeForm() {
        return `
            <div class="wrapper">
                <h1>RESET PASSWORD</h1>
                <p style="text-align: center; margin-bottom: 15px; font-family: 'DM Sans'; font-size: 0.9em; color: #ddd;">Enter the verification code sent to your email.</p>
                <form class="form" id="reset-password-code-form">
                    <div class="input-group">
                        <label for="reset-code">Verification Code</label>
                        <input type="text" id="reset-code" placeholder="Enter the code" required />
                        <div class="error-message" id="reset-code-error"></div>
                    </div>

                    <div class="input-group">
                        <label for="new-password">New Password</label>
                        <div class="password-input-wrapper">
                            <input type="password" id="new-password" placeholder="Enter new password" required />
                            <button type="button" class="view-password-button" data-target="new-password">Show</button>
                        </div>
                        <div class="error-message" id="new-password-error"></div>
                        <p class="password-requirements" style="font-size: 0.7em; color: #ddd; margin-top: 0.2rem;">Password must be at least 8 characters and include uppercase, lowercase, and a number.</p>
                    </div>

                    <div class="input-group">
                        <label for="confirm-new-password">Confirm New Password</label>
                        <div class="password-input-wrapper">
                            <input type="password" id="confirm-new-password" placeholder="Confirm new password" required />
                            <button type="button" class="view-password-button" data-target="confirm-new-password">Show</button>
                        </div>
                        <div class="error-message" id="confirm-new-password-error"></div>
                    </div>

                    <button type="submit">Reset Password</button>

                    <div class="form-switch">
                        <button type="button" class="link-button" id="toggle-to-login-from-reset">
                            Back to Login
                        </button>
                    </div>
                </form>
            </div>
        `;
    }

    // --- NEW: renderAdminSignupForm function ---
    // This function generates the HTML for the admin signup form.
    function renderAdminSignupForm() {
        // Determine which section (new org vs. existing org) should be visible initially.
        // It checks the state of the radio buttons, defaulting to 'new-organization' if not found.
        const isNewOrganizationChecked = document.getElementById('new-organization-radio') ?
                                         document.getElementById('new-organization-radio').checked :
                                         true; // Default to new organization if not rendered yet.

        let newOrgFieldsStyle = isNewOrganizationChecked ? 'display: block;' : 'display: none;';
        let existingOrgFieldsStyle = isNewOrganizationChecked ? 'display: none;' : 'display: block;';

        // Populate options for the existing organization dropdown
        let organizationOptions = '<option value="" disabled selected>Select an existing organization</option>';
        if (existingOrganizationsForAdmin.length > 0) {
            existingOrganizationsForAdmin.forEach(org => {
                organizationOptions += `<option value="${org.id}">${org.name}</option>`;
            });
        } else {
            organizationOptions = '<option value="" disabled>Loading organizations...</option>';
        }

        return `
            <div class="wrapper">
                <h1>Admin Registration</h1>
                <form class="form" id="admin-signup-form">
                    <div class="input-group">
                        <label>Registration Type</label>
                        <div class="radio-group">
                            <input type="radio" id="new-organization-radio" name="registration-type" value="new-organization" ${isNewOrganizationChecked ? 'checked' : ''}>
                            <label for="new-organization-radio">Register a new organization</label>
                        </div>
                        <div class="radio-group">
                            <input type="radio" id="existing-organization-radio" name="registration-type" value="existing-organization" ${!isNewOrganizationChecked ? 'checked' : ''}>
                            <label for="existing-organization-radio">Register as admin for existing organization</label>
                        </div>
                    </div>

                    <div id="new-org-fields" style="${newOrgFieldsStyle}">
                        <div class="input-group">
                            <label for="admin-signup-org-name">Organization Name</label>
                            <input type="text" id="admin-signup-org-name" name="organizationName" placeholder="Enter new organization name" ${isNewOrganizationChecked ? 'required' : ''} />
                            <div class="error-message" id="admin-signup-org-name-error"></div>
                        </div>

                        <div class="input-group">
                            <label for="admin-signup-theme-color">Theme Color</label>
                            <div style="display: flex; gap: 10px;">
                                <input type="text" id="admin-signup-theme-color-text" name="themeColorText" placeholder="e.g., #RRGGBB" value="#6B00B9" ${isNewOrganizationChecked ? 'required' : ''} style="flex-grow: 1;" />
                                <input type="color" id="admin-signup-theme-color-picker" name="themeColorPicker" value="#6B00B9" style="width: 50px; height: 38px; border: none; padding: 0;" />
                            </div>
                            <div class="error-message" id="admin-signup-theme-color-error"></div>
                        </div>
                    </div>

                    <div id="existing-org-fields" style="${existingOrgFieldsStyle}">
                        <div class="input-group">
                            <label for="admin-signup-select-organization">Select Organization</label>
                            <div class="select-wrapper">
                                <select id="admin-signup-select-organization" name="organizationId" ${!isNewOrganizationChecked ? 'required' : ''}>
                                    ${organizationOptions}
                                </select>
                            </div>
                            <div class="error-message" id="admin-signup-select-organization-error"></div>
                        </div>
                    </div>

                    <div class="input-group">
                        <label for="admin-signup-email">Admin Email</label>
                        <input type="email" id="admin-signup-email" name="adminEmail" placeholder="Enter your email" required />
                        <div class="error-message" id="admin-signup-email-error"></div>
                    </div>

                    <div class="input-group">
                        <label for="admin-signup-first-name">First Name</label>
                        <input type="text" id="admin-signup-first-name" name="firstName" placeholder="Enter your first name" required />
                        <div class="error-message" id="admin-signup-first-name-error"></div>
                    </div>

                    <div class="input-group">
                        <label for="admin-signup-last-name">Last Name</label>
                        <input type="text" id="admin-signup-last-name" name="lastName" placeholder="Enter your last name" required />
                        <div class="error-message" id="admin-signup-last-name-error"></div>
                    </div>

                    <div class="input-group">
                        <label for="admin-signup-password">Password</label>
                        <div class="password-input-wrapper">
                            <input type="password" id="admin-signup-password" name="password" placeholder="Create a password" required />
                            <button type="button" class="view-password-button" data-target="admin-signup-password">Show</button>
                        </div>
                        <div class="error-message" id="admin-signup-password-error"></div>
                        </div>
                    <div class="input-group">
                        <label for="admin-signup-confirm-password">Confirm Password</label>
                        <div class="password-input-wrapper">
                            <input type="password" id="admin-signup-confirm-password" name="confirmPassword" placeholder="Confirm your password" required />
                            <button type="button" class="view-password-button" data-target="admin-signup-confirm-password">Show</button>
                        </div>
                        <div class="error-message" id="admin-signup-confirm-password-error"></div>
                    </div>

                    <div class="input-group">
                        <label for="admin-signup-position">Position</label>
                        <div class="select-wrapper">
                            <select id="admin-signup-position" name="position" required>
                                <option value="" disabled selected>Select your position</option>
                                <option value="President">President</option>
                                <option value="Vice President">Vice President</option>
                                <option value="Secretary">Secretary</option>
                                <option value="Treasurer">Treasurer</option>
                                <option value="Adviser">Adviser</option>
                                <option value="Other">Other</option>
                            </select>
                        </div>
                        <div class="error-message" id="admin-signup-position-error"></div>
                    </div>

                    <button type="submit">Continue</button>

                    <div class="form-switch">
                        <p>Already have an account?</p>
                        <button type="button" class="link-button" id="toggle-to-login-from-admin-signup">
                            Login here
                        </button>
                    </div>
                </form>
            </div>
        `;
    }
    // --- END NEW: renderAdminSignupForm function ---


    // --- ORIGINAL render function (modified to add admin-signup case) ---
    function render() {
        if (currentForm === 'login') {
            app.innerHTML = renderLoginForm();
            setupEventListenersForLoginForm();
            // Clear success message after rendering login form
            registrationSuccessMessage = '';
        } else if (currentForm === 'signup') {
            app.innerHTML = renderSignupForm();
            setupEventListenersForSignupForm();
        } else if (currentForm === 'forgot-password') {
            app.innerHTML = renderForgotPasswordForm();
            setupEventListenersForForgotPasswordForm();
        } else if (currentForm === 'reset-password-code') {
            app.innerHTML = renderResetPasswordCodeForm();
            setupEventListenersForResetPasswordCodeForm();
        } else if (currentForm === 'admin-signup') { // NEW: Admin Signup case
            app.innerHTML = renderAdminSignupForm();
            setupEventListenersForAdminSignupForm(); // NEW: Setup event listeners for admin signup
        }
        setupViewPasswordButtons();
    }
    // --- END ORIGINAL render function ---


    function setupEventListenersForLoginForm() {
        document.getElementById('toggle-to-signup')?.addEventListener('click', () => {
            currentForm = 'signup';
            render();
        });
        document.getElementById('toggle-to-forgot-password')?.addEventListener('click', () => {
            currentForm = 'forgot-password';
            render();
        });
        document.getElementById('login-form')?.addEventListener('submit', handleLogin);
        // --- NEW: Event listener for Admin Signup toggle in Login form ---
        document.getElementById('toggle-to-admin-signup')?.addEventListener('click', () => {
            currentForm = 'admin-signup';
            render();
        });
        // --- END NEW ---
    }

    function setupEventListenersForSignupForm() {
        document.getElementById('toggle-to-login')?.addEventListener('click', () => {
            currentForm = 'login';
            render();
        });
        document.getElementById('signup-form')?.addEventListener('submit', handleSignup);
    }

    function setupEventListenersForForgotPasswordForm() {
        document.getElementById('toggle-to-login-from-forgot')?.addEventListener('click', () => {
            currentForm = 'login';
            render();
        });
        document.getElementById('forgot-password-form')?.addEventListener('submit', handleForgotPassword);
    }

    function setupEventListenersForResetPasswordCodeForm() {
        document.getElementById('toggle-to-login-from-reset')?.addEventListener('click', () => {
            currentForm = 'login';
            render();
        });
        document.getElementById('reset-password-code-form')?.addEventListener('submit', handleResetPasswordCode);
    }

    function setupViewPasswordButtons() {
        const buttons = document.querySelectorAll('.view-password-button');
        buttons.forEach(button => {
            button.addEventListener('click', function() {
                const targetId = this.dataset.target;
                const passwordInput = document.getElementById(targetId);
                if (passwordInput.type === 'password') {
                    passwordInput.type = 'text';
                    this.textContent = 'Hide';
                } else {
                    passwordInput.type = 'password';
                    this.textContent = 'Show';
                }
            });
        });
    }

    async function handleLogin(e) {
        e.preventDefault();

        const identifier = document.getElementById('login-student-number').value; // Use identifier
        const password = document.getElementById('login-password').value;

        // Clear previous errors
        displayError('login-student-number', ''); // consistent error display
        displayError('login-password', '');

        let isValid = true;

        if (!identifier) { // Changed to identifier
            displayError('login-student-number', 'Student number or Email is required.'); // generic message
            isValid = false;
        }

        if (!password) {
            displayError('login-password', 'Password is required.');
            isValid = false;
        }

        if (!isValid) {
            return; // Stop the login process if any validation fails
        }

        try {
            const response = await fetch('/api/login/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    identifier: identifier, // Use identifier
                    password: password,
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                if (data.detail) {
                    displayError('login-password', data.detail); // Show error from backend
                } else {
                    displayNotification('Login failed. Please try again.', 'error');
                }
                return;
            }

            displayNotification('Login successful!', 'success');
            // After successful login, apply the theme.
            // The backend session should now be set.
            await applyUserTheme(); // <--- CALL applyUserTheme HERE after successful login

            // Redirect based on user_role from the response.
            if (data.user_role === 'admin') {
                window.location.href = '/admin_dashboard'; // Or wherever admins go
            } else {
                window.location.href = '/home'; // Regular users
            }

        } catch (error) {
            displayNotification('An unexpected error occurred. Please try again.', 'error');
            console.error("Login error:", error);
        }
    }


    async function handleSignup(e) {
        e.preventDefault();

        const studentNumber = document.getElementById('signup-student-number').value;
        const email = document.getElementById('signup-email').value;
        // --- START FRONTEND ADJUSTMENT ---
        // Get the selected <option> element
        const organizationSelect = document.getElementById('signup-organization');
        // Get the text content (name) of the selected option, not its value (ID)
        const organizationName = organizationSelect.options[organizationSelect.selectedIndex].textContent;
        // --- END FRONTEND ADJUSTMENT ---
        const firstName = document.getElementById('signup-first-name').value;
        const lastName = document.getElementById('signup-last-name').value;
        const password = document.getElementById('signup-password').value;
        const confirmPassword = document.getElementById('signup-confirm-password').value;

        // Clear previous errors
        displayError('signup-student-number', '');
        displayError('signup-email', '');
        displayError('signup-organization', '');
        displayError('signup-first-name', '');
        displayError('signup-last-name', '');
        displayError('signup-password', '');
        displayError('signup-confirm-password', '');

        // Validation checks
        let isValid = true;

        if (isNaN(studentNumber) || studentNumber === "") {
            displayError('signup-student-number', 'Student number must be a number.');
            isValid = false;
        } else if (studentNumber.length != 9) {
            displayError('signup-student-number', 'Student number must be 9 digits.');
            isValid = false;
        }

        if (!email) {
            displayError('signup-email', 'Email is required.');
            isValid = false;
        } else if (!/\S+@\S+\.\S+/.test(email)) {
            displayError('signup-email', 'Invalid email format.');
            isValid = false;
        }

        // --- START FRONTEND ADJUSTMENT ---
        // Check if a valid organization name was selected
        if (!organizationName || organizationSelect.selectedIndex === 0) { // Also check if default option is selected
            displayError('signup-organization', 'Please select an organization.');
            isValid = false;
        }
        // --- END FRONTEND ADJUSTMENT ---

        if (!firstName) {
            displayError('signup-first-name', 'First name is required.');
            isValid = false;
        } else if (!/^[a-zA-Z\s]*$/.test(firstName)) {
            displayError('signup-first-name', 'First name should only contain letters and spaces.');
            isValid = false;
        }

        if (!lastName) {
            displayError('signup-last-name', 'Last name is required.');
            isValid = false;
        } else if (!/^[a-zA-Z\s]*$/.test(lastName)) {
            displayError('signup-last-name', 'Last name should only contain letters and spaces.');
            isValid = false;
        }

        const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{8,}$/;
        if (!passwordRegex.test(password)) {
            displayError('signup-password', 'Password must be at least 8 characters and contain at least one uppercase letter, one lowercase letter, and one number.');
            isValid = false;
        }

        if (password !== confirmPassword) {
            displayError('signup-confirm-password', 'Passwords do not match.');
            isValid = false;
        }

        if (!isValid) {
            return; // Stop the signup process if any validation fails
        }

        const userData = {
            student_number: studentNumber,
            email: email,
            // --- START FRONTEND ADJUSTMENT ---
            organization: organizationName, // Send the organization NAME here
            // --- END FRONTEND ADJUSTMENT ---
            first_name: firstName,
            last_name: lastName,
            password: password
        };

        try {
            const response = await fetch('/api/signup/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(userData)
            });

            const data = await response.json();

            if (!response.ok) {
                // **FIX:  Check for specific error messages from the backend**
                if (data.detail === 'Student number already registered') {
                    displayError('signup-student-number', 'This student number is already registered.');
                } else if (data.detail === 'Email already registered') {
                    displayError('signup-email', 'This email is already registered.');
                } else if (data.detail === 'First and last name combination already registered') { // ADDED THIS
                    displayError('signup-first-name', 'This first and last name combination is already registered.');
                    displayError('signup-last-name', ''); // Clear any previous last name error
                } else if (data.detail && data.detail.includes("Organization")) {
                    displayError('signup-organization', data.detail);
                }
                else {
                    // For *any other* error from the backend, show a generic message
                    displayNotification(data.detail || 'Signup failed. Please try again.', 'error');
                }
                return; // Stop the signup process
            }

            // Success Message for Login Form (You might want to move this)
            registrationSuccessMessage = 'Registration successful! Please log in.';

            // Redirect to Login (You might want to move this)
            currentForm = 'login';
            render();

        } catch (error) {
            // This catch block handles network errors and other exceptions
            console.error("Signup error:", error);
            displayNotification('An unexpected error occurred during signup. Please try again.', 'error');
        }
    }

    function displayError(inputId, message) {
        const errorElement = document.getElementById(inputId + '-error');
        if (errorElement) {
            errorElement.textContent = message;
        }
    }

    function displayNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type} show`;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(()=> notification.remove(), 300);
        }, 3000);
    }

    // organizations array is already defined globally at the top
    // let organizations = [];

    async function fetchOrganizations() {
        try {
            const response = await fetch('/api/organizations/');
            if (!response.ok) {
                throw new Error('Failed to fetch organizations');
            }
            const data = await response.json();
            organizations = data;
            render();
        } catch (error) {
            console.error("Error fetching organizations:", error);
            displayNotification('Failed to load organizations. Please try again later.', 'error');
            organizations = [];
            render();
        }
    }

    async function handleForgotPassword(e) {
        e.preventDefault();
        const identifier = document.getElementById('forgot-password-identifier').value;

        displayError('forgot-password-identifier', '');

        if (!identifier) {
            displayError('forgot-password-identifier', 'Student number or email is required.');
            return;
        }

        try {
            const response = await fetch('/api/forgot-password/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ identifier: identifier }),
            });

            const data = await response.json();

            if (!response.ok) {
                displayError('forgot-password-identifier', data.detail || 'Failed to send reset code.');
                return;
            }

            forgotPasswordIdentifier = identifier; // Store for next step
            currentForm = 'reset-password-code';
            render();

        } catch (error) {
            console.error("Forgot password error:", error);
            displayNotification('An unexpected error occurred. Please try again.', 'error');
        }
    }

    async function handleResetPasswordCode(e) {
        e.preventDefault();

        const code = document.getElementById('reset-code').value;
        const newPassword = document.getElementById('new-password').value;
        const confirmNewPassword = document.getElementById('confirm-new-password').value;

        // Clear errors
        displayError('reset-code', '');
        displayError('new-password', '');
        displayError('confirm-new-password', '');

        let isValid = true;

        if (!code) {
            displayError('reset-code', 'Verification code is required.');
            isValid = false;
        }

        const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{8,}$/;
        if (!passwordRegex.test(newPassword)) {
            displayError('new-password', 'Password must be at least 8 characters and contain at least one uppercase letter, one lowercase letter, and one number.');
            isValid = false;
        }


        if (newPassword !== confirmNewPassword) {
            displayError('confirm-new-password', 'Passwords do not match.');
            isValid = false;
        }

        if (!isValid) {
            return;
        }

        try {
            const response = await fetch('/api/reset-password/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    identifier: forgotPasswordIdentifier,
                    code: code,
                    new_password: newPassword,
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                displayError('reset-code', data.detail || 'Failed to reset password.');
                return;
            }

            displayNotification('Password reset successfully! Please log in.', 'success');
            currentForm = 'login';
            render();

        } catch (error) {
            console.error("Reset password error:", error);
            displayNotification('An unexpected error occurred. Please try again.', 'error');
        }
    }

    // --- NEW: Global variable for admin organizations ---
    let existingOrganizationsForAdmin = [];
    // --- END NEW ---

    // --- NEW: setupEventListenersForAdminSignupForm function ---
    // This function sets up event listeners specifically for the admin signup form.
    function setupEventListenersForAdminSignupForm() {
        // Listener for the "Back to Login" button
        document.getElementById('toggle-to-login-from-admin-signup')?.addEventListener('click', () => {
            currentForm = 'login';
            render();
        });

        // Get references to the input fields that need dynamic 'required' attribute handling
        const orgNameInput = document.getElementById('admin-signup-org-name');
        const themeColorTextInput = document.getElementById('admin-signup-theme-color-text'); // Changed ID
        const themeColorPickerInput = document.getElementById('admin-signup-theme-color-picker'); // Changed ID
        const selectOrgInput = document.getElementById('admin-signup-select-organization');

        // Event listeners for the radio buttons to toggle form sections and 'required' attributes
        document.querySelectorAll('input[name="registration-type"]').forEach(radio => {
            radio.addEventListener('change', function() {
                const newOrgFields = document.getElementById('new-org-fields');
                const existingOrgFields = document.getElementById('existing-org-fields');

                if (this.value === 'new-organization') {
                    newOrgFields.style.display = 'block';
                    existingOrgFields.style.display = 'none';

                    // Set 'required' for new organization fields
                    if (orgNameInput) orgNameInput.required = true;
                    if (themeColorTextInput) themeColorTextInput.required = true; // Use text input for required
                    if (themeColorPickerInput) themeColorPickerInput.required = false; // Picker is not required

                    // Remove 'required' for existing organization fields
                    if (selectOrgInput) selectOrgInput.required = false;

                    // Clear errors for the hidden section to prevent stale messages
                    displayError('admin-signup-select-organization', '');
                } else {
                    newOrgFields.style.display = 'none';
                    existingOrgFields.style.display = 'block';

                    // Remove 'required' for new organization fields
                    if (orgNameInput) orgNameInput.required = false;
                    if (themeColorTextInput) themeColorTextInput.required = false; // Use text input for required
                    if (themeColorPickerInput) themeColorPickerInput.required = false; // Picker is not required

                    // Set 'required' for existing organization fields
                    if (selectOrgInput) selectOrgInput.required = true;

                    // Clear errors for the hidden section to prevent stale messages
                    displayError('admin-signup-org-name', '');
                    displayError('admin-signup-theme-color', '');
                }
            });
        });

        // Initial setup of 'required' attributes based on the default checked radio button
        const initialNewOrgChecked = document.getElementById('new-organization-radio')?.checked;
        if (orgNameInput) orgNameInput.required = initialNewOrgChecked;
        if (themeColorTextInput) themeColorTextInput.required = initialNewOrgChecked;
        if (themeColorPickerInput) themeColorPickerInput.required = false; // Picker is never required
        if (selectOrgInput) selectOrgInput.required = !initialNewOrgChecked;

        // Add event listener for color picker to update text input
        if (themeColorPickerInput && themeColorTextInput) {
            themeColorPickerInput.addEventListener('input', function() {
                themeColorTextInput.value = this.value;
            });
            // Also ensure text input updates picker if user types a valid hex
            themeColorTextInput.addEventListener('input', function() {
                const hexRegex = /^#([0-9A-F]{3}){1,2}$/i;
                if (hexRegex.test(this.value)) {
                    themeColorPickerInput.value = this.value;
                }
            });
        }

        // Listener for the form submission
        document.getElementById('admin-signup-form')?.addEventListener('submit', handleAdminSignup);
    }
    // --- END NEW: setupEventListenersForAdminSignupForm function ---

    // --- NEW: fetchExistingOrganizationsForAdmin function ---
    // This function fetches the list of existing organizations from the backend
    // to populate the dropdown for admin registration.
    async function fetchExistingOrganizationsForAdmin() {
        try {
            const response = await fetch('/api/organizations/'); // Assuming this endpoint provides all organizations
            if (!response.ok) {
                throw new Error('Failed to fetch existing organizations');
            }
            const data = await response.json();
            existingOrganizationsForAdmin = data; // Store the fetched organizations
            render(); // Re-render the form to populate the dropdown with new data
        } catch (error) {
            console.error("Error fetching existing organizations for admin:", error);
            displayNotification('Failed to load existing organizations for admin. Please try again later.', 'error');
            existingOrganizationsForAdmin = []; // Clear organizations on error
            render();
        }
    }
    // --- END NEW: fetchExistingOrganizationsForAdmin function ---

    // --- NEW: handleAdminSignup function ---
    // This function handles the submission of the admin registration form.
    async function handleAdminSignup(e) {
        e.preventDefault();

        // Determine which registration type is selected (new org vs. existing org)
        const newOrgRadio = document.getElementById('new-organization-radio');
        const isNewOrganization = newOrgRadio.checked;

        // Get common form field values
        const email = document.getElementById('admin-signup-email').value;
        const firstName = document.getElementById('admin-signup-first-name').value;
        const lastName = document.getElementById('admin-signup-last-name').value;
        const adminName = `${firstName} ${lastName}`; // Combine first and last name for the 'name' field in backend schema
        const password = document.getElementById('admin-signup-password').value;
        const confirmPassword = document.getElementById('admin-signup-confirm-password').value;
        const position = document.getElementById('admin-signup-position').value;

        // Clear all previous error messages
        displayError('admin-signup-org-name', '');
        displayError('admin-signup-theme-color', ''); // This is for the combined error display
        displayError('admin-signup-select-organization', '');
        displayError('admin-signup-email', '');
        displayError('admin-signup-first-name', '');
        displayError('admin-signup-last-name', '');
        displayError('admin-signup-password', '');
        displayError('admin-signup-confirm-password', '');
        displayError('admin-signup-position', '');

        let isValid = true; // Flag to track overall form validity

        // Perform common validations for all registration types
        if (!email) {
            displayError('admin-signup-email', 'Email is required.');
            isValid = false;
        } else if (!/\S+@\S+\.\S+/.test(email)) {
            displayError('admin-signup-email', 'Invalid email format.');
            isValid = false;
        }

        if (!firstName) {
            displayError('admin-signup-first-name', 'First name is required.');
            isValid = false;
        } else if (!/^[a-zA-Z\s]*$/.test(firstName)) {
            displayError('admin-signup-first-name', 'First name should only contain letters and spaces.');
            isValid = false;
        }

        if (!lastName) {
            displayError('admin-signup-last-name', 'Last name is required.');
            isValid = false;
        } else if (!/^[a-zA-Z\s]*$/.test(lastName)) {
            displayError('admin-signup-last-name', 'Last name should only contain letters and spaces.');
            isValid = false;
        }

        // Removed the password complexity regex validation for admin signup
        if (!password) { // Basic check: password should not be empty
            displayError('admin-signup-password', 'Password is required.');
            isValid = false;
        }

        if (password !== confirmPassword) {
            displayError('admin-signup-confirm-password', 'Passwords do not match.');
            isValid = false;
        }

        if (!position) {
            displayError('admin-signup-position', 'Position is required.');
            isValid = false;
        }

        // If any common validation failed, stop the function
        if (!isValid) {
            return;
        }

        try {
            let organizationId = null;

            if (isNewOrganization) {
                const orgName = document.getElementById('admin-signup-org-name').value;
                const themeColor = document.getElementById('admin-signup-theme-color-text').value; // Get value from text input

                // Validation for theme color format
                const hexColorRegex = /^#([0-9A-F]{3}){1,2}$/i;
                if (!orgName) {
                    displayError('admin-signup-org-name', 'Organization name is required.');
                    isValid = false;
                }
                if (!themeColor) {
                    displayError('admin-signup-theme-color', 'Theme color is required.');
                    isValid = false;
                } else if (!hexColorRegex.test(themeColor)) {
                    displayError('admin-signup-theme-color', 'Invalid hex color format (e.g., #RRGGBB or #RGB).');
                    isValid = false;
                }

                if (!isValid) return; // Stop if new org fields are invalid

                // Step 1: Create Organization
                const orgPayload = {
                    name: orgName,
                    theme_color: themeColor
                };

                const orgResponse = await fetch('/admin/organizations/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(orgPayload)
                });

                const orgData = await orgResponse.json();

                if (!orgResponse.ok) {
                    if (orgData.detail === `Organization with name '${orgName}' already exists.`) {
                        displayError('admin-signup-org-name', 'This organization name already exists.');
                    } else {
                        displayNotification(orgData.detail || 'Organization creation failed. Please try again.', 'error');
                    }
                    return; // Stop processing on error
                }
                organizationId = orgData.id; // Get the ID of the newly created organization

            } else { // Registering as admin for an existing organization
                const organizationSelect = document.getElementById('admin-signup-select-organization');
                organizationId = parseInt(organizationSelect.value); // Get the ID from the selected option

                if (isNaN(organizationId)) {
                    displayError('admin-signup-select-organization', 'Please select a valid organization.');
                    isValid = false;
                }
                if (!isValid) return; // Stop if existing org selection is invalid
            }

            // Step 2: Create Admin (common for both new and existing organization paths)
            const adminPayload = {
                name: adminName,
                email: email,
                password: password,
                position: position, // Assuming backend schema accepts 'position'
                organization_id: organizationId // Link admin to the organization
            };

            const adminResponse = await fetch('/admin/admins/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(adminPayload)
            });

            const adminData = await adminResponse.json();

            if (!adminResponse.ok) {
                if (adminData.detail === `Admin with email '${email}' already exists.`) {
                    displayError('admin-signup-email', 'This email is already registered as an admin.');
                } else {
                    displayNotification(adminData.detail || 'Admin registration failed. Please try again.', 'error');
                }
                return; // Stop processing on error
            }

            // On successful registration, display a success message and redirect to login
            displayNotification('Admin registration successful! Please log in.', 'success');
            currentForm = 'login';
            render();

        } catch (error) {
            // Handle network errors or other unexpected exceptions
            console.error("Admin signup error:", error);
            displayNotification('An unexpected error occurred during admin registration. Please try again.', 'error');
        }
    }
    // --- END NEW: handleAdminSignup function ---


    // --- CALL applyUserTheme on initial page load ---
    applyUserTheme(); // Call this immediately after DOMContentLoaded

    render(); // Initial render of the forms
    fetchOrganizations(); // Fetch organizations for student signup form
    // --- NEW: Call to fetch existing organizations for admin signup ---
    fetchExistingOrganizationsForAdmin();
    // --- END NEW ---
});
