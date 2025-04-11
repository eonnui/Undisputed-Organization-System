document.addEventListener('DOMContentLoaded', function() {
    const app = document.getElementById('app');
    let currentForm = 'login';
    let registrationSuccessMessage = '';
    let forgotPasswordIdentifier = ''; // Store student number or email for code verification

    function renderLoginForm() {
        return `
            <div class="wrapper">
                <h1>LOGIN</h1>
                ${registrationSuccessMessage ? `<div class="success-message" style="color: #A7D1A9; text-align: center; margin-bottom: 10px; font-family: 'DM Sans'; font-weight: bold;">${registrationSuccessMessage}</div>` : ''}
                <form class="form" id="login-form">
                    <div class="input-group">
                        <label for="student-number">Student Number</label>
                        <input type="text" id="login-student-number" placeholder="Enter your student number" required />
                    </div>

                    <div class="input-group">
                        <label for="password">Password</label>
                        <input type="password" id="login-password" placeholder="Enter your password" required />
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
                    </div>

                    <div class="input-group">
                        <label for="email">Student Email</label>
                        <input type="email" id="signup-email" placeholder="Enter your email" required />
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
                    </div>

                    <div class="input-group">
                        <label for="first-name">First Name</label>
                        <input type="text" id="signup-first-name" placeholder="Enter your first name" required />
                    </div>

                    <div class="input-group">
                        <label for="last-name">Last Name</label>
                        <input type="text" id="signup-last-name" placeholder="Enter your last name" required />
                    </div>

                    <div class="input-group">
                        <label for="password">Password</label>
                        <input type="password" id="signup-password" placeholder="Create a password" required />
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
                <p style="text-align: center; margin-bottom: 15px; font-family: 'DM Sans'; font-size: 0.9em; color: #6c757d;">Enter the verification code sent to your email.</p>
                <form class="form" id="reset-password-code-form">
                    <div class="input-group">
                        <label for="reset-code">Verification Code</label>
                        <input type="text" id="reset-code" placeholder="Enter the code" required />
                    </div>

                    <div class="input-group">
                        <label for="new-password">New Password</label>
                        <input type="password" id="new-password" placeholder="Enter new password" required />
                    </div>

                    <div class="input-group">
                        <label for="confirm-new-password">Confirm New Password</label>
                        <input type="password" id="confirm-new-password" placeholder="Confirm new password" required />
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
                    alert('Login failed. Please try again.');
                }
                return; // Stop the login process if the server returns an error.
            }

            alert('Login successful!');
            window.location.href = '/Home';
        } catch (error) {
            alert('An unexpected error occurred. Please try again.'); // Generic error for network issues
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

        // Clear previous errors
        displayError('signup-student-number', '');
        displayError('signup-email', '');
        displayError('signup-organization', '');
        displayError('signup-first-name', '');
        displayError('signup-last-name', '');
        displayError('signup-password', '');

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
        }

        if (!lastName) {
            displayError('signup-last-name', 'Last name is required.');
            isValid = false;
        }

        if (password.length < 8) {
            displayError('signup-password', 'Password must be at least 8 characters long.');
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
                throw new Error(data.detail || 'Signup failed');
            }

            // Success Message for Login Form
            registrationSuccessMessage = 'Registration successful! Please log in.';

            // Redirect to Login
            currentForm = 'login';
            render();

        } catch (error) {
            // Removed the alert here
            console.error("Signup error:", error); // It's good practice to log errors for debugging
            // Optionally, you could display a generic error message to the user
            // displayError('signup-form', 'An error occurred during signup. Please try again.');
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

            alert('A reset code has been sent to your email if the account exists.'); // Modern websites often give this feedback for security
            forgotPasswordIdentifier = identifier; // Store for the next step
            currentForm = 'reset-password-code';
            render();

        } catch (error) {
            alert('An unexpected error occurred. Please try again.');
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
        if (newPassword.length < 8) {
            displayError('new-password', 'New password must be at least 8 characters long.');
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

            alert('Password reset successfully! You can now log in with your new password.');
            currentForm = 'login';
            registrationSuccessMessage = 'Password reset successfully. Please log in.';
            render();

        } catch (error) {
            alert('An unexpected error occurred. Please try again.');
            console.error("Reset password error:", error);
        }
    }

    function displayError(elementId, errorMessage) {
        const inputGroup = document.getElementById(elementId).closest('.input-group');
        let errorElement = inputGroup.querySelector('.error-message');

        if (errorMessage) {
            if (!errorElement) {
                errorElement = document.createElement('div');
                errorElement.classList.add('error-message');
                errorElement.style.color = '#FFC107';
                errorElement.style.fontSize = '12px';
                inputGroup.appendChild(errorElement);
            }
            errorElement.textContent = errorMessage;
        } else {
            if (errorElement) {
                errorElement.remove();
            }
        }
    }

    // Initial render
    render();
});