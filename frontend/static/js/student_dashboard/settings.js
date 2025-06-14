// This console.log helps confirm that your JavaScript file is being loaded by the browser.
console.log("----- settings.js script loaded! -----");

document.addEventListener('DOMContentLoaded', () => {
    // This console.log helps confirm that the DOMContentLoaded event has fired.
    console.log('DOMContentLoaded event fired! Initializing script...');

    // Get form elements
    const studentInfoForm = document.getElementById('studentInfoForm');
    const profilePictureForm = document.getElementById('profilePictureForm');
    const securityForm = document.getElementById('securityForm');
    const registrationFormOnly = document.getElementById('registrationFormOnly');

    // Get clear button elements - CORRECTED IDs to match HTML
    const clearStudentInfoFormBtn = document.getElementById('clearStudentInfoForm');
    // REMOVED: clearProfilePictureBtn and clearRegistrationFormOnlyBtn from here
    const clearSecurityFormBtn = document.getElementById('clearSecurityForm');

    // Get other display elements
    const registrationStatusDisplay = document.getElementById('registrationStatus');

    // Utility function to set registration status display
    function setRegistrationStatus(status) {
        if (registrationStatusDisplay) {
            registrationStatusDisplay.textContent = status === 'Verified' ? 'Verified' : 'Not Verified';
            registrationStatusDisplay.className = status === 'Verified' ? 'verified' : 'unverified';
        }
    }

    // Utility function to toggle display/input for editable fields
    function makeFieldEditable(displayElementId, inputElementId) {
        const displayElement = document.getElementById(displayElementId);
        const inputElement = document.getElementById(inputElementId);

        if (displayElement && inputElement) {
            displayElement.style.display = 'none';
            inputElement.style.display = 'block';
            inputElement.focus();

            inputElement.addEventListener('blur', () => {
                // For date inputs, format the date for display
                let displayValue = inputElement.value;
                if (inputElement.type === 'date' && inputElement.value) {
                    try {
                        displayValue = new Date(inputElement.value).toLocaleDateString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit' });
                    } catch (e) {
                        displayValue = inputElement.value; // Fallback if date parsing fails
                    }
                }
                displayElement.textContent = displayValue;
                displayElement.style.display = 'block';
                inputElement.style.display = 'none';
            });
        }
    }

    // Utility function to display error messages
    function showError(inputElementId, message) {
        const errorElement = document.getElementById(inputElementId + 'Error');
        const smallTextElement = document.getElementById(inputElementId + 'SmallText');

        if (errorElement) {
            errorElement.textContent = message;
        }
        if (smallTextElement) {
            smallTextElement.style.display = 'block';
            smallTextElement.style.color = 'red';
        }
    }

    // Utility function to clear error messages
    function clearError(inputElementId) {
        const errorElement = document.getElementById(inputElementId + 'Error');
        const smallTextElement = document.getElementById(inputElementId + 'SmallText');

        if (errorElement) {
            errorElement.textContent = '';
        }
        if (smallTextElement) {
            smallTextElement.style.display = 'none'; // Hide small text on clear error
            smallTextElement.style.color = 'var(--org-text-secondary)'; // Reset color
        }
    }

    // Utility function for input validation
    function validateInput(inputElement, validationRules) {
        let isValid = true;
        clearError(inputElement.id); // Clear previous errors first

        for (const rule of validationRules) {
            if (rule.check(inputElement.value, inputElement)) {
                showError(inputElement.id, rule.message);
                isValid = false;
                break; // Stop on first error for this input
            }
        }
        return isValid;
    }

    // Core function to reset forms
    function resetForm(form) {
        console.log(`resetForm called for form: ${form ? form.id : 'unknown form'}`);

        // Clear all error messages and small text displays for the form
        form.querySelectorAll('.error-message').forEach(error => error.textContent = '');
        form.querySelectorAll('[id$="SmallText"]').forEach(smallText => {
            smallText.style.display = 'none';
            smallText.style.color = 'var(--org-text-secondary)';
        });

        // Specific handling for studentInfoForm (this part should be working)
        if (form.id === 'studentInfoForm') {
            // Only clear specific editable inputs in studentInfoForm
            const editableInputIds = ['birthDate', 'gender', 'guardianName', 'guardianContact'];
            editableInputIds.forEach(id => {
                const inputElement = document.getElementById(id);
                if (inputElement) {
                    inputElement.value = '';
                }
            });

            // Revert hidden editable inputs back to display spans
            const displayInputPairs = [
                ['birthDateDisplay', 'birthDate'],
                ['genderDisplay', 'gender'],
                ['guardianNameDisplay', 'guardianName'],
                ['guardianContactDisplay', 'guardianContact'],
            ];
            displayInputPairs.forEach(([displayId, inputId]) => {
                const displayElement = document.getElementById(displayId);
                const inputElement = document.getElementById(inputId);
                if (displayElement && inputElement) {
                    displayElement.style.display = 'block';
                    inputElement.style.display = 'none';
                    // Reset display text if the original value was empty
                    if (inputElement.value === '') {
                        displayElement.textContent = '';
                    }
                }
            });

        } else if (form.id === 'securityForm') { // Only reset security form inputs directly
            // Default reset for all other forms (Profile Picture, Security, Registration Form)
            form.querySelectorAll('input, select').forEach(input => {
                if (input.type === 'file') {
                    // We're not explicitly clearing file inputs for profile picture or registration form
                    // via a 'clear' button anymore, so this branch won't be hit for them from `resetForm`.
                    // But it's fine to leave this general file input clearing logic.
                    input.value = '';
                    if (form.id === 'profilePictureForm') { // This log will still appear if resetForm is called for profilePictureForm for OTHER reasons (e.g., after successful submission)
                        console.log(`--- ProfilePictureForm: Cleared file input: ${input.id}`);
                    }
                } else if (input.type !== 'button') {
                    input.value = ''; // Clear other non-button inputs
                }
            });

            // --- Additional handling for profilePictureForm's visual state after clearing ---
            if (form.id === 'profilePictureForm') {
                const profilePicturePreview = form.querySelector('.profile-picture-preview');
                // The file input itself is cleared by the general loop above.
                // If you have a default profile picture or want to reset the image preview
                // to something specific, add that logic here.
                // Example:
                // if (profilePicturePreview) {
                //      profilePicturePreview.src = '/static/images/default_profile_placeholder.png'; // Your default image path
                // }
                console.log('--- ProfilePictureForm: resetForm specific logic complete.');
            }

            // Special handling for elements with display/input toggles in other forms
            if (form.id === 'registrationFormOnly') {
                const registrationFormDisplay = document.getElementById('registrationFormDisplay');
                const registrationFormOnlyUpload = document.getElementById('registrationFormOnlyUpload');
                if (registrationFormDisplay && registrationFormOnlyUpload) {
                    registrationFormDisplay.textContent = ''; // Clear the displayed file name
                    registrationFormDisplay.style.display = 'block';
                    registrationFormOnlyUpload.style.display = 'block'; // Make file input visible if it was hidden
                }
            }
        }
        // No else block here, as profilePictureForm and registrationFormOnly
        // will no longer have "Clear" button functionality calling resetForm on them.
    }


    // Function to handle form submissions
    function handleFormSubmit(event, formId, successCallback, errorCallback) {
        event.preventDefault(); // Prevent default form submission
        const form = document.getElementById(formId);
        if (!form) return;

        let hasErrors = false;
        // Clear all existing errors and small text before re-validating
        form.querySelectorAll('.error-message').forEach(error => error.textContent = '');
        form.querySelectorAll('[id$="SmallText"]').forEach(smallText => {
            smallText.style.display = 'none';
            smallText.style.color = 'var(--org-text-secondary)';
        });

        // Specific form validation logic
        if (formId === 'studentInfoForm') {
            const birthDateInput = document.getElementById('birthDate');
            const genderInput = document.getElementById('gender');
            const guardianNameInput = document.getElementById('guardianName');
            const guardianContactInput = document.getElementById('guardianContact');

            // Birth Date Validation with updated minimum age
            const today = new Date();
            const minAgeDate = new Date(today.getFullYear() - 16, today.getMonth(), today.getDate());

            // Check if birthDateInput is currently displayed or has a value (if hidden and pre-filled)
            if (!validateInput(birthDateInput, [
                { check: val => !val, message: 'Please enter your birth date.' }, // Always required
                { check: val => new Date(val) > today, message: 'Birth date cannot be in the future.' },
                { check: val => new Date(val) > minAgeDate, message: 'Student must be at least 16 years old.' }
            ])) hasErrors = true;

            // Check if genderInput is currently displayed or has a value (if hidden and pre-filled)
            if (!validateInput(genderInput, [
                { check: val => !val, message: 'Please select your gender.' } // Always required
            ])) hasErrors = true;

            // Check if guardianNameInput is currently displayed or has a value (if hidden and pre-filled)
            if (!validateInput(guardianNameInput, [
                { check: val => !val.trim(), message: 'Please enter your guardian name.' } // Always required
            ])) hasErrors = true;

            // Check if guardianContactInput is currently displayed or has a value (if hidden and pre-filled)
            if (!validateInput(guardianContactInput, [
                { check: val => !val.trim(), message: 'Please enter your guardian contact.' }, // Always required
                { check: val => !/^\d{10,15}$/.test(val), message: 'Invalid contact number format.' }
            ])) hasErrors = true;

        } else if (formId === 'profilePictureForm') {
            const profilePictureInput = document.getElementById('profilePicture');
            if (!validateInput(profilePictureInput, [
                { check: (val, input) => input.files.length === 0, message: 'Please select a profile picture.' },
                { check: (val, input) => input.files[0] && input.files[0].size > 2 * 1024 * 1024, message: 'File size must be less than 2MB.' },
                { check: (val, input) => input.files[0] && !['image/jpeg', 'image/png', 'image/gif'].includes(input.files[0].type), message: 'Only JPG, PNG, GIF formats are allowed.' }
            ])) hasErrors = true;
        } else if (formId === 'securityForm') {
            const currentPasswordInput = document.getElementById('currentPassword');
            const newPasswordInput = document.getElementById('newPassword');
            const confirmPasswordInput = document.getElementById('confirmPassword');

            if (!validateInput(currentPasswordInput, [{ check: val => !val, message: 'Please enter your current password.' }])) hasErrors = true;

            // Only validate new password if it's not empty (user intends to change it)
            if (newPasswordInput.value) {
                if (!validateInput(newPasswordInput, [
                    { check: val => val.length < 8, message: 'New password must be at least 8 characters long.' },
                    { check: val => !/[A-Z]/.test(val), message: 'New password must contain at least one capital letter.' },
                    { check: val => !/[0-9]/.test(val), message: 'New password must contain at least one number.' },
                    { check: val => !/[!@#$%^&*(),.?":{}|<>]/.test(val), message: 'New password must contain at least one special character.' }
                ])) hasErrors = true;

                if (!validateInput(confirmPasswordInput, [
                    { check: val => !val, message: 'Confirm password is required.' },
                    { check: val => val !== newPasswordInput.value, message: 'Passwords do not match.' }
                ])) hasErrors = true;
            } else {
                // If new password is empty, clear any existing new/confirm password errors
                clearError('newPassword');
                clearError('confirmPassword');
            }

        } else if (formId === 'registrationFormOnly') {
            const registrationFormInput = document.getElementById('registrationFormOnlyUpload');
            if (!validateInput(registrationFormInput, [
                { check: (val, input) => input.files.length === 0, message: 'Please upload your registration form.' },
                { check: (val, input) => input.files[0] && input.files[0].size > 5 * 1024 * 1024, message: 'File size must be less than 5MB.' },
                { check: (val, input) => input.files[0] && !['application/pdf'].includes(input.files[0].type), message: 'Only PDF files are allowed.' }
            ])) hasErrors = true;
        }

        if (!hasErrors) {
            let fetchUrl = '';
            if (formId === 'securityForm') {
                fetchUrl = '/api/auth/change-password';
            } else {
                fetchUrl = '/api/profile/update/';
            }

            fetch(fetchUrl, { method: 'POST', body: new FormData(form) })
                .then(response => {
                    console.log("Fetch Response:", response);
                    if (!response.ok) {
                        return response.json().then(errorData => {
                            console.error("Fetch Error Data:", errorData);
                            if (formId === 'securityForm' && errorData.detail) {
                                if (Array.isArray(errorData.detail)) {
                                    errorData.detail.forEach(err => {
                                        const fieldName = err.loc[1];
                                        const errorMessage = err.msg;
                                        if (fieldName === 'current_password') {
                                            showError('currentPassword', errorMessage);
                                        } else if (fieldName === 'new_password') {
                                            showError('newPassword', errorMessage);
                                        } else if (fieldName === 'confirm_password') {
                                            showError('confirmPassword', errorMessage);
                                            // Handle the specific case where FastAPI returns a general 'detail' error for password mismatch
                                            if (errorData.detail === 'Passwords do not match.') {
                                                showError('confirmPassword', 'Passwords do not match.');
                                            }
                                        } else {
                                            alert(errorMessage);
                                        }
                                    });
                                } else if (typeof errorData.detail === 'string') {
                                    alert(errorData.detail);
                                } else {
                                    alert("An unexpected error occurred during password change.");
                                }
                            }
                            throw new Error("Validation errors or other server errors occurred.");
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    console.log("Fetch Success Data:", data);
                    successCallback(data, form);
                })
                .catch(error => {
                    console.error("Fetch Error:", error);
                    if (formId !== 'securityForm' || !error.message.includes("Validation errors or other server errors occurred.")) {
                        errorCallback(error);
                    }
                });
        }
    }

    // Success callbacks for form submissions
    function handleStudentInfoSuccess(data, form) {
        alert('Profile information updated successfully!');
        resetForm(form);
        if (data && data.user) updateStudentInfoDisplay(data.user);
    }

    function handleProfilePictureSuccess(data, form) {
        alert('Profile picture updated successfully!');
        // No resetForm(form) call here for ProfilePictureForm, as we're not clearing its inputs.
        const profilePicturePreview = document.querySelector('.profile-picture-preview');
        if (profilePicturePreview && data.user.profile_picture) profilePicturePreview.src = data.user.profile_picture;
    }

    function handleSecuritySuccess(data, form) {
        alert('Security settings updated successfully!');
        resetForm(form);
    }

    function handleRegistrationFormOnlySuccess(data, form) {
        alert('Registration form updated successfully!');
        const registrationFormDisplayElement = document.getElementById('registrationFormDisplay');
        // No need to get registrationFormInput here as we're not resetting its value in JS.

        if (registrationFormDisplayElement && data.user && data.user.registration_form) {
            const pathParts = data.user.registration_form.split('/');
            registrationFormDisplayElement.textContent = pathParts[pathParts.length - 1];
        } else if (registrationFormDisplayElement) {
            registrationFormDisplayElement.textContent = '';
        }

        // No resetForm(form) call here for RegistrationFormOnly, as we're not clearing its inputs.

        if (data.user && data.user.verification_status) {
            setRegistrationStatus(data.user.verification_status);
        }
    }

    // Generic error handler for fetch operations
    function handleError(error) {
        alert(error.message);
    }

    // Configuration for fields that have display/input pairs for updating
    const fieldConfigs = [
        { id: 'studentNumber', displayId: 'studentNumberDisplay', prop: 'student_number' },
        { id: 'firstName', displayId: 'firstNameDisplay', prop: 'first_name' },
        { id: 'lastName', displayId: 'lastNameDisplay', prop: 'last_name' },
        { id: 'email', displayId: 'emailDisplay', prop: 'email' },
        { id: 'birthDate', displayId: 'birthDateDisplay', prop: 'birthdate', isDate: true },
        { id: 'gender', displayId: 'genderDisplay', prop: 'sex' },
        { id: 'address', displayId: 'addressDisplay', prop: 'address' },
        { id: 'yearLevel', displayId: 'yearLevelDisplay', prop: 'year_level' },
        { id: 'section', displayId: 'sectionDisplay', prop: 'section' },
        { id: 'guardianName', displayId: 'guardianNameDisplay', prop: 'guardian_name' },
        { id: 'guardianContact', displayId: 'guardianContactDisplay', prop: 'guardian_contact' },
    ];

    // Function to update the displayed student information after a successful update
    function updateStudentInfoDisplay(userData) {
        fieldConfigs.forEach(config => {
            const inputValue = userData[config.prop] || '';
            const displayElement = document.getElementById(config.displayId);
            const inputElement = document.getElementById(config.id);

            if (displayElement) {
                // Ensure date formatting is consistent with makeFieldEditable blur event
                displayElement.textContent = config.isDate && inputValue ? new Date(inputValue).toLocaleDateString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit' }) : inputValue;
            }
            if (inputElement) {
                inputElement.value = inputValue;
            }
        });
        if (userData.verification_status) {
            setRegistrationStatus(userData.verification_status);
        }
    }

    // Get edit button elements
    const editBirthDateBtn = document.getElementById('editBirthDate');
    const editGenderBtn = document.getElementById('editGender');
    const editGuardianNameBtn = document.getElementById('editGuardianName');
    const editGuardianContactBtn = document.getElementById('editGuardianContact');

    // Add event listeners for edit buttons
    if (editBirthDateBtn) editBirthDateBtn.addEventListener('click', () => makeFieldEditable('birthDateDisplay', 'birthDate'));
    if (editGenderBtn) editGenderBtn.addEventListener('click', () => makeFieldEditable('genderDisplay', 'gender'));
    if (editGuardianNameBtn) editGuardianNameBtn.addEventListener('click', () => makeFieldEditable('guardianNameDisplay', 'guardianName'));
    if (editGuardianContactBtn) editGuardianContactBtn.addEventListener('click', () => makeFieldEditable('guardianContactDisplay', 'guardianContact'));

    // Add event listeners for form submissions
    if (studentInfoForm) studentInfoForm.addEventListener('submit', (event) => handleFormSubmit(event, 'studentInfoForm', handleStudentInfoSuccess, handleError));
    if (profilePictureForm) profilePictureForm.addEventListener('submit', (event) => handleFormSubmit(event, 'profilePictureForm', handleProfilePictureSuccess, handleError));
    if (securityForm) securityForm.addEventListener('submit', (event) => handleFormSubmit(event, 'securityForm', handleSecuritySuccess, handleError));
    if (registrationFormOnly) registrationFormOnly.addEventListener('submit', (event) => handleFormSubmit(event, 'registrationFormOnly', handleRegistrationFormOnlySuccess, handleError));

    // Add event listeners for clear buttons
    if (clearStudentInfoFormBtn) clearStudentInfoFormBtn.addEventListener('click', () => {
        console.log('Clearing studentInfoForm...');
        resetForm(studentInfoForm);
    });

    // REMOVED event listeners for clearProfilePictureBtn and clearRegistrationFormOnlyBtn
    // This means their 'clear' functionality in JS will no longer execute.
    // Ensure you also REMOVE these buttons from your HTML.

    if (clearSecurityFormBtn) clearSecurityFormBtn.addEventListener('click', () => {
        console.log('Clearing securityForm...');
        resetForm(securityForm);
    });
});