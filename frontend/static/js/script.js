document.addEventListener('DOMContentLoaded', function() {
    const app = document.getElementById('app');
    let currentForm = 'login';
    let registrationSuccessMessage = '';
    let forgotPasswordIdentifier = '';
    let organizations = [];
    let courseToOrganizationMap = {};
    let takenPositions = [];

    async function applyUserTheme() {
        try {
            const response = await fetch('/get_user_data', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            if (!response.ok) {
                const errorData = await response.json();
                if (response.status === 401) {
                }
                return;
            }
            const userData = await response.json();
            const themeColor = userData.organization ? userData.organization.theme_color : null;
            const organizationName = userData.organization ? userData.organization.name : 'Guest';
            if (themeColor) {
                document.documentElement.style.setProperty('--organization-theme-color', themeColor);
                const orgNameDisplay = document.getElementById('organizationNameDisplay');
                if (orgNameDisplay) {
                    orgNameDisplay.textContent = organizationName;
                }
            } else {
                document.documentElement.style.removeProperty('--organization-theme-color');
                const orgNameDisplay = document.getElementById('organizationNameDisplay');
                if (orgNameDisplay) {
                    orgNameDisplay.textContent = 'No Organization';
                }
            }
            const registrationStatusDisplay = document.getElementById('registrationStatus');
            if (registrationStatusDisplay && typeof userData.is_verified === 'boolean') {
                const statusString = userData.is_verified ? "Verified" : "Not Verified";
                if (typeof setRegistrationStatus === 'function') {
                    setRegistrationStatus(statusString);
                } else {
                    registrationStatusDisplay.textContent = statusString;
                    registrationStatusDisplay.className = userData.is_verified ? 'verified' : 'unverified';
                }
            }
        } catch (error) {
        }
    }

    // Renders login form
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
                        <p>REGISTER</p>
                        <div class="registration-options">
                            <button type="button" class="link-button" id="toggle-to-signup">
                                As a student
                            </button>
                            <div class="divider">
                                <p> | </p>
                            </div>
                            <button type="button" class="link-button" id="toggle-to-admin-signup">
                                As an admin
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        `;
    }

    // Renders signup form
    function renderSignupForm() {
        let courseOptionsHtml = '<option value="" disabled selected>Select your Course</option>';
        if (organizations.length > 0) {
            organizations.forEach(org => {
                if (org.primary_course_code) {
                    courseOptionsHtml += `<option value="${org.primary_course_code}">${org.primary_course_code}</option>`;
                }
            });
        } else {
            courseOptionsHtml += '<option value="" disabled>Loading courses...</option>';
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
                        <label for="signup-course">Select Course</label>
                        <div class="select-wrapper">
                            <select id="signup-course" required>
                                ${courseOptionsHtml}
                            </select>
                        </div>
                        <div class="error-message" id="signup-course-error"></div>
                    </div>
                    <div class="input-group">
                        <label for="signup-organization-display">Assigned Organization</label>
                        <input type="text" id="signup-organization-display" value="Please select a course" readonly />
                        <input type="hidden" id="signup-organization-id" name="organizationId" />
                        <input type="hidden" id="signup-organization-name-hidden" name="organizationName" /> <div class="error-message" id="signup-organization-error"></div>
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

    // Renders forgot password form
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

    // Renders reset password code form
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

    // Renders admin signup form
    function renderAdminSignupForm() {
        const isNewOrganizationChecked = document.getElementById('new-organization-radio') ?
                                                document.getElementById('new-organization-radio').checked :
                                                true;
        let newOrgFieldsStyle = isNewOrganizationChecked ? 'display: block;' : 'display: none;';
        let existingOrgFieldsStyle = isNewOrganizationChecked ? 'display: none;' : 'display: block;';
        let organizationOptions = '<option value="" disabled selected>Select an existing organization</option>';
        if (existingOrganizationsForAdmin.length > 0) {
            existingOrganizationsForAdmin.forEach(org => {
                organizationOptions += `<option value="${org.id}">${org.name}</option>`;
            });
        } else {
            organizationOptions = '<option value="" disabled>Loading organizations...</option>';
        }

        const allPositions = [
            "President",
            "Vice President-Internal",
            "Vice President-External",
            "Secretary",
            "Treasurer",
            "Adviser 1",
            "Adviser 2",
            "Auditor",
            "PRO"
        ];

        let positionOptions = '<option value="" disabled selected>Select your position</option>';
        allPositions.forEach(pos => {
            if (!takenPositions.includes(pos)) {
                positionOptions += `<option value="${pos}">${pos}</option>`;
            }
        });


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
                        <div class="input-group">
                            <label for="admin-signup-primary-course">Primary Course Code (e.g., BSBA)</label>
                            <input type="text" id="admin-signup-primary-course" name="primaryCourse" placeholder="Enter primary course code" ${isNewOrganizationChecked ? 'required' : ''} />
                            <div class="error-message" id="admin-signup-primary-course-error"></div>
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
                                ${positionOptions}
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

    // Main render function
    function render() {
        if (currentForm === 'login') {
            app.innerHTML = renderLoginForm();
            setupEventListenersForLoginForm();
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
        } else if (currentForm === 'admin-signup') {
            app.innerHTML = renderAdminSignupForm();
            setupEventListenersForAdminSignupForm();
            const selectOrgInput = document.getElementById('admin-signup-select-organization');
            if (selectOrgInput && selectOrgInput.value && !document.getElementById('new-organization-radio').checked) {
                fetchTakenPositions(parseInt(selectOrgInput.value));
            }
        }
        setupViewPasswordButtons();
    }

    // Event listeners for login form
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
        document.getElementById('toggle-to-admin-signup')?.addEventListener('click', () => {
            currentForm = 'admin-signup';
            takenPositions = [];
            render();
        });
    }

    // Event listeners for signup form
    function setupEventListenersForSignupForm() {
        document.getElementById('toggle-to-login')?.addEventListener('click', () => {
            currentForm = 'login';
            render();
        });
        document.getElementById('signup-form')?.addEventListener('submit', handleSignup);
        document.getElementById('signup-course')?.addEventListener('change', function() {
            const selectedCourseCode = this.value;
            const organizationDisplayInput = document.getElementById('signup-organization-display');
            const organizationIdInput = document.getElementById('signup-organization-id');
            const organizationNameHiddenInput = document.getElementById('signup-organization-name-hidden');
            if (selectedCourseCode && courseToOrganizationMap[selectedCourseCode]) {
                const org = courseToOrganizationMap[selectedCourseCode];
                organizationDisplayInput.value = org.name;
                organizationIdInput.value = org.id;
                organizationNameHiddenInput.value = org.name;
                displayError('signup-organization', '');
            } else {
                organizationDisplayInput.value = "No organization found for this course.";
                organizationIdInput.value = "";
                organizationNameHiddenInput.value = "";
                displayError('signup-organization', 'Invalid course selected or no organization mapped.');
            }
        });
    }

    // Event listeners for forgot password form
    function setupEventListenersForForgotPasswordForm() {
        document.getElementById('toggle-to-login-from-forgot')?.addEventListener('click', () => {
            currentForm = 'login';
            render();
        });
        document.getElementById('forgot-password-form')?.addEventListener('submit', handleForgotPassword);
    }

    // Event listeners for reset password code form
    function setupEventListenersForResetPasswordCodeForm() {
        document.getElementById('toggle-to-login-from-reset')?.addEventListener('click', () => {
            currentForm = 'login';
            render();
        });
        document.getElementById('reset-password-code-form')?.addEventListener('submit', handleResetPasswordCode);
    }

    // Password show/hide buttons
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

    // Handles login submit
    async function handleLogin(e) {
        e.preventDefault();
        const identifier = document.getElementById('login-student-number').value;
        const password = document.getElementById('login-password').value;
        displayError('login-student-number', '');
        displayError('login-password', '');
        let isValid = true;
        if (!identifier) {
            displayError('login-student-number', 'Student number or Email is required.');
            isValid = false;
        }
        if (!password) {
            displayError('login-password', 'Password is required.');
            isValid = false;
        }
        if (!isValid) {
            return;
        }
        try {
            const response = await fetch('/api/login/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    identifier: identifier,
                    password: password,
                }),
            });
            const data = await response.json();
            if (!response.ok) {
                if (data.detail) {
                    displayError('login-password', data.detail);
                } else {
                    displayNotification('Login failed. Please try again.', 'error');
                }
                return;
            }
            displayNotification('Login successful!', 'success');
            await applyUserTheme();
            if (data.user_role === 'admin') {
                window.location.href = '/admin_dashboard';
            } else {
                window.location.href = '/home';
            }
        } catch (error) {
            displayNotification('An unexpected error occurred. Please try again.', 'error');
        }
    }

    // Handles signup submit
    async function handleSignup(e) {
        e.preventDefault();
        const studentNumber = document.getElementById('signup-student-number').value;
        const email = document.getElementById('signup-email').value;
        const course = document.getElementById('signup-course').value;
        const organizationId = document.getElementById('signup-organization-id').value;
        const organizationName = document.getElementById('signup-organization-name-hidden').value;
        const firstName = document.getElementById('signup-first-name').value;
        const lastName = document.getElementById('signup-last-name').value;
        const password = document.getElementById('signup-password').value;
        const confirmPassword = document.getElementById('signup-confirm-password').value;
        displayError('signup-student-number', '');
        displayError('signup-email', '');
        displayError('signup-course', '');
        displayError('signup-organization', '');
        displayError('signup-first-name', '');
        displayError('signup-last-name', '');
        displayError('signup-password', '');
        displayError('signup-confirm-password', '');
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
        if (!course) {
            displayError('signup-course', 'Please select your course.');
            isValid = false;
        } else if (!organizationName) {
            displayError('signup-organization', 'No organization name found for the selected course.');
            isValid = false;
        }
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
            return;
        }
        const userData = {
            student_number: studentNumber,
            email: email,
            organization: organizationName,
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
                if (data.detail === 'Student number already registered') {
                    displayError('signup-student-number', 'This student number is already registered.');
                } else if (data.detail === 'Email already registered') {
                    displayError('signup-email', 'This email is already registered.');
                } else if (data.detail === 'First and last name combination already registered') {
                    displayError('signup-first-name', 'This first and last name combination is already registered.');
                    displayError('signup-last-name', '');
                } else if (data.detail && data.detail.includes("Organization")) {
                    displayError('signup-organization', data.detail);
                } else if (data.detail && data.detail.includes("Invalid course")) {
                    displayError('signup-course', data.detail);
                } else {
                    displayNotification(data.detail || 'Signup failed. Please try again.', 'error');
                }
                return;
            }
            registrationSuccessMessage = `Registration successful!
Please log in.`;
            currentForm = 'login';
            render();
        } catch (error) {
            displayNotification('An unexpected error occurred during signup. Please try again.', 'error');
        }
    }

    // Shows error message for input
    function displayError(inputId, message) {
        const errorElement = document.getElementById(inputId + '-error');
        if (errorElement) {
            errorElement.textContent = message;
        }
    }

    // Shows notification
    function displayNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type} show`;
        notification.textContent = message;
        document.body.appendChild(notification);
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    // Fetches organizations for signup
    async function fetchOrganizations() {
        try {
            const response = await fetch('/api/organizations/');
            if (!response.ok) {
                throw new Error('Failed to fetch organizations');
            }
            const data = await response.json();
            organizations = data;
            courseToOrganizationMap = {};
            data.forEach(org => {
                if (org.primary_course_code) {
                    courseToOrganizationMap[org.primary_course_code] = org;
                }
            });
            render();
        } catch (error) {
            organizations = [];
            render();
        }
    }

    // Handles forgot password submit
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
            forgotPasswordIdentifier = identifier;
            currentForm = 'reset-password-code';
            render();
        } catch (error) {
            displayNotification('An unexpected error occurred. Please try again.', 'error');
        }
    }

    // Handles reset password code submit
    async function handleResetPasswordCode(e) {
        e.preventDefault();
        const code = document.getElementById('reset-code').value;
        const newPassword = document.getElementById('new-password').value;
        const confirmNewPassword = document.getElementById('confirm-new-password').value;
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
            displayNotification('An unexpected error occurred. Please try again.', 'error');
        }
    }

    let existingOrganizationsForAdmin = [];

    // Fetches taken positions for a given organization
    async function fetchTakenPositions(organizationId) {
        try {
            const response = await fetch(`/api/admin/organizations/${organizationId}/taken_positions`);
            if (!response.ok) {
                throw new Error('Failed to fetch taken positions');
            }
            const data = await response.json();
            takenPositions = data;
            updatePositionDropdown();
        } catch (error) {
            displayNotification('Failed to load taken positions for the selected organization.', 'error');
            takenPositions = []; 
            updatePositionDropdown(); 
        }
    }

    // Function to update the position dropdown
    function updatePositionDropdown() {
        const positionSelect = document.getElementById('admin-signup-position');
        if (!positionSelect) return;

        const allPositions = [
            "President",
            "Vice President-Internal",
            "Vice President-External",
            "Secretary",
            "Treasurer",
            "Adviser 1",
            "Adviser 2",
            "Auditor",
            "PRO"
        ];

        let positionOptionsHtml = '<option value="" disabled selected>Select your position</option>';
        allPositions.forEach(pos => {
            if (!takenPositions.includes(pos)) {
                positionOptionsHtml += `<option value="${pos}">${pos}</option>`;
            }
        });
        positionSelect.innerHTML = positionOptionsHtml;
    }


    // Event listeners for admin signup form
    function setupEventListenersForAdminSignupForm() {
        document.getElementById('toggle-to-login-from-admin-signup')?.addEventListener('click', () => {
            currentForm = 'login';
            render();
        });
        const orgNameInput = document.getElementById('admin-signup-org-name');
        const themeColorTextInput = document.getElementById('admin-signup-theme-color-text');
        const themeColorPickerInput = document.getElementById('admin-signup-theme-color-picker');
        const primaryCourseInput = document.getElementById('admin-signup-primary-course');
        const selectOrgInput = document.getElementById('admin-signup-select-organization');

        document.querySelectorAll('input[name="registration-type"]').forEach(radio => {
            radio.addEventListener('change', function() {
                const newOrgFields = document.getElementById('new-org-fields');
                const existingOrgFields = document.getElementById('existing-org-fields');
                if (this.value === 'new-organization') {
                    newOrgFields.style.display = 'block';
                    existingOrgFields.style.display = 'none';
                    if (orgNameInput) orgNameInput.required = true;
                    if (themeColorTextInput) themeColorTextInput.required = true;
                    if (themeColorPickerInput) themeColorPickerInput.required = false;
                    if (primaryCourseInput) primaryCourseInput.required = true;
                    if (selectOrgInput) selectOrgInput.required = false;
                    displayError('admin-signup-select-organization', '');
                    takenPositions = [];
                    updatePositionDropdown();
                } else {
                    newOrgFields.style.display = 'none';
                    existingOrgFields.style.display = 'block';
                    if (orgNameInput) orgNameInput.required = false;
                    if (themeColorTextInput) themeColorTextInput.required = false;
                    if (themeColorPickerInput) themeColorPickerInput.required = false;
                    if (primaryCourseInput) primaryCourseInput.required = false;
                    if (selectOrgInput) selectOrgInput.required = true;
                    displayError('admin-signup-org-name', '');
                    displayError('admin-signup-theme-color', '');
                    displayError('admin-signup-primary-course', '');

                    if (selectOrgInput.value) {
                        fetchTakenPositions(parseInt(selectOrgInput.value));
                    } else {
                        takenPositions = [];
                        updatePositionDropdown(); 
                    }
                }
            });
        });

        // Add event listener for when an existing organization is selected
        selectOrgInput?.addEventListener('change', function() {
            const selectedOrgId = parseInt(this.value);
            if (!isNaN(selectedOrgId)) {
                fetchTakenPositions(selectedOrgId);
            } else {
                takenPositions = [];
                updatePositionDropdown(); 
            }
        });

        const initialNewOrgChecked = document.getElementById('new-organization-radio')?.checked;
        if (orgNameInput) orgNameInput.required = initialNewOrgChecked;
        if (themeColorTextInput) themeColorTextInput.required = initialNewOrgChecked;
        if (themeColorPickerInput) themeColorPickerInput.required = false;
        if (primaryCourseInput) primaryCourseInput.required = initialNewOrgChecked;
        if (selectOrgInput) selectOrgInput.required = !initialNewOrgChecked;
        if (themeColorPickerInput && themeColorTextInput) {
            themeColorPickerInput.addEventListener('input', function() {
                themeColorTextInput.value = this.value;
            });
            themeColorTextInput.addEventListener('input', function() {
                const hexRegex = /^#([0-9A-F]{3}){1,2}$/i;
                if (hexRegex.test(this.value)) {
                    themeColorPickerInput.value = this.value;
                }
            });
        }
        document.getElementById('admin-signup-form')?.addEventListener('submit', handleAdminSignup);
    }

    // Fetches organizations for admin signup
    async function fetchExistingOrganizationsForAdmin() {
        try {
            const response = await fetch('/api/organizations/');
            if (!response.ok) {
                throw new Error('Failed to fetch existing organizations');
            }
            const data = await response.json();
            existingOrganizationsForAdmin = data;
            render();
        } catch (error) {
            existingOrganizationsForAdmin = [];
            render();
        }
    }

    // Handles admin signup submit
    async function handleAdminSignup(e) {
        e.preventDefault();
        const newOrgRadio = document.getElementById('new-organization-radio');
        const isNewOrganization = newOrgRadio.checked;
        const email = document.getElementById('admin-signup-email').value;
        const firstName = document.getElementById('admin-signup-first-name').value;
        const lastName = document.getElementById('admin-signup-last-name').value;
        const adminName = `${firstName} ${lastName}`;
        const password = document.getElementById('admin-signup-password').value;
        const confirmPassword = document.getElementById('admin-signup-confirm-password').value;
        const position = document.getElementById('admin-signup-position').value;
        displayError('admin-signup-org-name', '');
        displayError('admin-signup-theme-color', '');
        displayError('admin-signup-primary-course', '');
        displayError('admin-signup-select-organization', '');
        displayError('admin-signup-email', '');
        displayError('admin-signup-first-name', '');
        displayError('admin-signup-last-name', '');
        displayError('admin-signup-password', '');
        displayError('admin-signup-confirm-password', '');
        displayError('admin-signup-position', '');
        let isValid = true;
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
        if (!password) {
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
        if (!isValid) {
            return;
        }
        try {
            let organizationId = null;
            if (isNewOrganization) {
                const orgName = document.getElementById('admin-signup-org-name').value;
                const themeColor = document.getElementById('admin-signup-theme-color-text').value;
                const primaryCourse = document.getElementById('admin-signup-primary-course').value;
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
                if (!primaryCourse) {
                    displayError('admin-signup-primary-course', 'Primary course code is required.');
                    isValid = false;
                }
                if (!isValid) return;
                const orgPayload = {
                    name: orgName,
                    theme_color: themeColor,
                    primary_course_code: primaryCourse
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
                    return;
                }
                organizationId = orgData.id;
            } else {
                const organizationSelect = document.getElementById('admin-signup-select-organization');
                organizationId = parseInt(organizationSelect.value);
                if (isNaN(organizationId)) {
                    displayError('admin-signup-select-organization', 'Please select a valid organization.');
                    isValid = false;
                }
                if (!isValid) return;
            }
            const adminPayload = {
                first_name: firstName,
                last_name: lastName,
                email: email,
                password: password,
                position: position,
                organization_id: organizationId
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
                return;
            }
            displayNotification('Admin registration successful! Please log in.', 'success');
            currentForm = 'login';
            render();
        } catch (error) {
            displayNotification('An unexpected error occurred during admin registration. Please try again.', 'error');
        }
    }

    applyUserTheme();
    render();
    fetchOrganizations();
    fetchExistingOrganizationsForAdmin();
});
