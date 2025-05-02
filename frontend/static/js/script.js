document.addEventListener('DOMContentLoaded', function() {
    const app = document.getElementById('app');
    let currentForm = 'login';
    let registrationSuccessMessage = '';
    let forgotPasswordIdentifier = ''; // Store student number or email for code verification

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
                </form>
            </div>
        `;
    }

    function renderSignupForm() {
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
                                <option value="" disabled selected>Select your organization</option>
                                <option value="org1">Organization 1</option>
                                <option value="org2">Organization 2</option>
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
        }
        setupViewPasswordButtons();
    }

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
    
        const identifier = document.getElementById('login-student-number').value; //  Use identifier
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
            //  Redirect based on user_role from the response.
            if (data.user_role === 'admin') {
                window.location.href = '/admin_dashboard'; // Or wherever admins go
            } else {
                window.location.href = '/home'; //  Regular users
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
        const organization = document.getElementById('signup-organization').value;
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
    
        if (!organization) {
            displayError('signup-organization', 'Please select an organization.');
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
            return; // Stop the signup process if any validation fails
        }
    
        const userData = {
            student_number: studentNumber,
            email: email,
            organization: organization,
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
    
    function displayError(inputElementId, message) {
        // Your existing function to display the error message
        const errorElement = document.getElementById(`${inputElementId}-error`); // Example ID
        if (errorElement) {
            errorElement.textContent = message;
        }
    }
    
    


    async function handleForgotPassword(e) {
        e.preventDefault();
        const identifier = document.getElementById('forgot-password-identifier').value;

        // Clear previous error
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
            setTimeout(()=> notification.remove(), 300); //remove element after the animation
        }, 3000);
    }

    render(); // Initial render
});
