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
                        <label for="student-number">Student Number</label>
                        <input type="text" id="login-student-number" placeholder="Enter your student number" required />
                        <div class="error-message" id="login-student-number-error"></div>
                    </div>

                    <div class="input-group">
                        <label for="password">Password</label>
                        <input type="password" id="login-password" placeholder="Enter your password" required />
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
                        <label for="student-number">Student Number</label>
                        <input type="text" id="signup-student-number" placeholder="Enter your student number" required />
                        <div class="error-message" id="signup-student-number-error"></div>
                    </div>

                    <div class="input-group">
                        <label for="email">Student Email</label>
                        <input type="email" id="signup-email" placeholder="Enter your email" required />
                        <div class="error-message" id="signup-email-error"></div>
                    </div>

                    <div class="input-group">
                        <label for="organization">Select Organization</label>
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
                        <label for="first-name">First Name</label>
                        <input type="text" id="signup-first-name" placeholder="Enter your first name" required />
                        <div class="error-message" id="signup-first-name-error"></div>
                    </div>

                    <div class="input-group">
                        <label for="last-name">Last Name</label>
                        <input type="text" id="signup-last-name" placeholder="Enter your last name" required />
                        <div class="error-message" id="signup-last-name-error"></div>
                    </div>

                    <div class="input-group">
                        <label for="password">Password</label>
                        <input type="password" id="signup-password" placeholder="Create a password" required />
                        <div class="error-message" id="signup-password-error"></div>
                        <p class="password-requirements" style="font-size: 0.7em; color: #ddd; margin-top: 0.2rem;">Password must be at least 8 characters and include uppercase, lowercase, and a number.</p>
                    </div>

                    <div class="input-group">
                        <label for="confirm-password">Confirm Password</label>
                        <input type="password" id="signup-confirm-password" placeholder="Confirm your password" required />
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
                        <input type="password" id="new-password" placeholder="Enter new password" required />
                        <div class="error-message" id="new-password-error"></div>
                        <p class="password-requirements" style="font-size: 0.7em; color: #ddd; margin-top: 0.2rem;">Password must be at least 8 characters and include uppercase, lowercase, and a number.</p>
                    </div>

                    <div class="input-group">
                        <label for="confirm-new-password">Confirm New Password</label>
                        <input type="password" id="confirm-new-password" placeholder="Confirm new password" required />
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
            document.getElementById('toggle-to-signup')?.addEventListener('click', () => {
                currentForm = 'signup';
                render();
            });
            document.getElementById('toggle-to-forgot-password')?.addEventListener('click', () => {
                currentForm = 'forgot-password';
                render();
            });
            document.getElementById('login-form')?.addEventListener('submit', handleLogin);
            // Clear success message after rendering login form
            registrationSuccessMessage = '';
        } else if (currentForm === 'signup') {
            app.innerHTML = renderSignupForm();
            document.getElementById('toggle-to-login')?.addEventListener('click', () => {
                currentForm = 'login';
                render();
            });
            document.getElementById('signup-form')?.addEventListener('submit', handleSignup);
        } else if (currentForm === 'forgot-password') {
            app.innerHTML = renderForgotPasswordForm();
            document.getElementById('toggle-to-login-from-forgot')?.addEventListener('click', () => {
                currentForm = 'login';
                render();
            });
            document.getElementById('forgot-password-form')?.addEventListener('submit', handleForgotPassword);
        } else if (currentForm === 'reset-password-code') {
            app.innerHTML = renderResetPasswordCodeForm();
            document.getElementById('toggle-to-login-from-reset')?.addEventListener('click', () => {
                currentForm = 'login';
                render();
            });
            document.getElementById('reset-password-code-form')?.addEventListener('submit', handleResetPasswordCode);
        }
    }

    async function handleLogin(e) {
        e.preventDefault();

        const studentNumber = document.getElementById('login-student-number').value;
        const password = document.getElementById('login-password').value;

        // Clear previous errors
        displayError('login-student-number', '');
        displayError('login-password', '');

        let isValid = true;

        if (!studentNumber) {
            displayError('login-student-number', 'Student number is required.');
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
                    student_number: studentNumber,
                    password: password,
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                if (data.detail) {
                    displayError('login-password', data.detail); // Display error detail from server
                } else {
                    displayNotification('Login failed. Please try again.', 'error');
                }
                return; // Stop the login process if the server returns an error.
            }

            displayNotification('Login successful!', 'success');
            window.location.href = '/home';
        } catch (error) {
            displayNotification('An unexpected error occurred. Please try again.', 'error'); // Generic error for network issues
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
                // Check if the error is due to an already registered student
                if (data.detail && data.detail.includes('already registered')) {
                    displayError('signup-student-number', 'This student number is already registered.');
                    return; // Stop the signup process
                }
                throw new Error(data.detail || 'Signup failed');
            }
    
            // Success Message for Login Form
            registrationSuccessMessage = 'Registration successful! Please log in.';
    
            // Redirect to Login
            currentForm = 'login';
            render();
    
        } catch (error) {
            console.error("Signup error:", error);
            displayNotification('An error occurred during signup. Please try again.', 'error');
        }
    }

    
    async function handleForgotPassword(e) {
        e.preventDefault();
        const identifier = document.getElementById('forgot-password-identifier').value;

        // Basic client-side validation
        if (!identifier) {
            displayError('forgot-password-identifier', 'Please enter your student number or email.');
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
                displayError('forgot-password-identifier', data.detail || 'Failed to send reset code. Please try again.');
                return;
            }

            displayNotification('A reset code has been sent to your email if the account exists.', 'info'); // Modern websites often give this feedback for security
            forgotPasswordIdentifier = identifier; // Store for the next step
            currentForm = 'reset-password-code';
            render();

        } catch (error) {
            displayNotification('An unexpected error occurred. Please try again.', 'error');
            console.error("Forgot password error:", error);
        }
    }

    async function handleResetPasswordCode(e) {
        e.preventDefault();
        const resetCode = document.getElementById('reset-code').value;
        const newPassword = document.getElementById('new-password').value;
        const confirmNewPassword = document.getElementById('confirm-new-password').value;

        // Basic client-side validation
        if (!resetCode) {
            displayError('reset-code', 'Please enter the verification code.');
            return;
        }

        const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{8,}$/;
        if (!passwordRegex.test(newPassword)) {
            displayError('new-password', 'New password must be at least 8 characters and include uppercase, lowercase, and a number.');
            return;
        }

        if (newPassword !== confirmNewPassword) {
            displayError('confirm-new-password', 'Passwords do not match.');
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
                    code: resetCode,
                    new_password: newPassword,
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                displayError('reset-code', data.detail || 'Invalid reset code or request. Please try again.');
                return;
            }

            displayNotification('Password reset successfully! You can now log in with your new password.', 'success');
            currentForm = 'login';
            registrationSuccessMessage = 'Password reset successfully. Please log in.';
            render();

        } catch (error) {
            displayNotification('An unexpected error occurred. Please try again.', 'error');
            console.error("Reset password error:", error);
        }
    }

    function displayError(elementId, errorMessage) {
        const errorElement = document.getElementById(elementId + '-error');
        if (errorElement) {
            errorElement.textContent = errorMessage;
        } else {
            const inputElement = document.getElementById(elementId);
            const inputGroup = inputElement ? inputElement.closest('.input-group') : null;
            if (inputGroup) {
                const newErrorElement = document.createElement('div');
                newErrorElement.classList.add('error-message');
                newErrorElement.id = elementId + '-error';
                newErrorElement.textContent = errorMessage;
                inputGroup.appendChild(newErrorElement);
            }
        }
    }

    function displayNotification(message, type = 'info') {
        const notificationDiv = document.createElement('div');
        notificationDiv.classList.add('notification', type);
        notificationDiv.textContent = message;
        app.appendChild(notificationDiv);
        setTimeout(() => {
            notificationDiv.classList.add('show');
            setTimeout(() => {
                notificationDiv.classList.remove('show');
                setTimeout(() => {
                    notificationDiv.remove();
                }, 300); // Fade out duration
            }, 3000); // Display duration
        }, 100); // Small delay to ensure it's added to the DOM
    }

    // Initial render
    render();
});