document.addEventListener('DOMContentLoaded', function() {
    const app = document.getElementById('app');
    let currentForm = 'login';

    function renderLoginForm() {
        return `
            <div class="wrapper">
                <h1>LOGIN</h1>
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
                    
                    <button type="button" class="forgot-password">Forgot Password?</button>
                    
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

    function render() {
        app.innerHTML = currentForm === 'login' ? renderLoginForm() : renderSignupForm();
        
        // Add event listeners after rendering
        if (currentForm === 'login') {
            document.getElementById('toggle-to-signup')?.addEventListener('click', () => {
                currentForm = 'signup';
                render();
            });
            
            document.getElementById('login-form')?.addEventListener('submit', handleLogin);
        } else {
            document.getElementById('toggle-to-login')?.addEventListener('click', () => {
                currentForm = 'login';
                render();
            });
            
            document.getElementById('signup-form')?.addEventListener('submit', handleSignup);
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
            // Redirect or do something after successful login
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
    
            // Success Message
            const signupForm = document.getElementById('signup-form');
            const successMessage = document.createElement('div');
            successMessage.textContent = 'Signup successful! Redirecting to login...';
            successMessage.style.color = '#ffffff';
            successMessage.style.textAlign = 'center';
            successMessage.style.marginTop = '6px';
            successMessage.style.fontFamily = 'DM Sans';
            signupForm.appendChild(successMessage);
    
            // Redirect to Login
            setTimeout(() => {
                currentForm = 'login';
                render();
            }, 2000); // Redirect after 2 seconds
    
        } catch (error) {
            alert(error.message); // Or displayError
        }
    }

    function displayError(elementId, errorMessage) {
        const inputGroup = document.getElementById(elementId).closest('.input-group'); // Find the parent input group
        let errorElement = inputGroup.querySelector('.error-message'); // Check if error message is already there
    
        if (errorMessage) {
            if (!errorElement) {
                errorElement = document.createElement('div');
                errorElement.classList.add('error-message');
                errorElement.style.color = '#FFC107';
                errorElement.style.fontSize = '12px';
                inputGroup.appendChild(errorElement); // Append to the input group
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