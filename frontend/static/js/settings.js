document.addEventListener('DOMContentLoaded', () => {
    // Form Elements
    const studentInfoForm = document.getElementById('studentInfoForm');
    const clearStudentInfoFormBtn = document.getElementById('clearStudentInfoForm');
    const registrationStatusDisplay = document.getElementById('registrationStatus');
    const profilePictureForm = document.getElementById('profilePictureForm');
    const clearProfilePictureBtn = document.getElementById('clearProfilePictureBtn');
    const securityForm = document.getElementById('securityForm');
    const clearSecurityFormBtn = document.getElementById('clearSecurityFormBtn');
    const registrationFormOnly = document.getElementById('registrationFormOnly');
    const clearRegistrationFormOnlyBtn = document.getElementById('clearRegistrationFormOnly');

    // Initial Registration Status
    function setRegistrationStatus(status) {
        registrationStatusDisplay.textContent = status === 'Verified' ? 'Verified' : 'Not Verified';
        registrationStatusDisplay.className = status === 'Verified' ? 'verified' : 'unverified';
    }

    // Editable Field Logic
    function makeFieldEditable(displayElementId, inputElementId) {
        const displayElement = document.getElementById(displayElementId);
        const inputElement = document.getElementById(inputElementId);

        if (displayElement && inputElement) {
            displayElement.style.display = 'none';
            inputElement.style.display = 'block';
            inputElement.focus();

            inputElement.addEventListener('blur', () => {
                displayElement.textContent = (inputElement.type === 'date' && inputElement.value) ? new Date(inputElement.value).toLocaleDateString() : inputElement.value;
                displayElement.style.display = 'block';
                inputElement.style.display = 'none';
            });
        }
    }

    // Error Handling
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

    function clearError(inputElementId) {
        const errorElement = document.getElementById(inputElementId + 'Error');
        const smallTextElement = document.getElementById(inputElementId + 'SmallText'); 

        if (errorElement) {
            errorElement.textContent = '';
        }
        if (smallTextElement) { 
            smallTextElement.style.display = 'none';
            smallTextElement.style.color = 'var(--org-text-secondary)'; 
        }
    }

    // Form Reset Logic
    function resetForm(form) {
        form.querySelectorAll('input, select').forEach(input => {
            if (input.type === 'file') input.value = '';
            else if (input.type !== 'button') input.value = '';
        });
        form.querySelectorAll('.error-message').forEach(error => error.textContent = '');

        const displayInputPairs = [
            ['birthDateDisplay', 'birthDate'], ['genderDisplay', 'gender'],
            ['guardianNameDisplay', 'guardianName'], ['guardianContactDisplay', 'guardianContact'],
            ['registrationFormDisplay', 'registrationFormUpload'],
        ];

        displayInputPairs.forEach(([displayId, inputId]) => {
            const displayElement = document.getElementById(displayId);
            const inputElement = document.getElementById(inputId);
            if (displayElement && inputElement) {
                displayElement.style.display = 'block';
                inputElement.style.display = 'none';
            }
        });
        form.querySelectorAll('input[type="file"]').forEach(fileInput => fileInput.value = '');
    }

    // Form Submission Handlers
    function handleFormSubmit(event, formId, successCallback, errorCallback) {
        event.preventDefault();
        const form = document.getElementById(formId);
        if (!form) return;

        let hasErrors = false;
        const formData = new FormData(form);
        console.log(`Form ID: ${formId}`);

        // Validation
        if (formId === 'studentInfoForm') {
            const birthDateInput = document.getElementById('birthDate');
            const genderInput = document.getElementById('gender');
            const guardianNameInput = document.getElementById('guardianName');
            const guardianContactInput = document.getElementById('guardianContact');

            if (!birthDateInput.value) { showError('birthDate', 'Please enter your birth date.'); hasErrors = true; } else { clearError('birthDate'); }
            if (!genderInput.value) { showError('gender', 'Please select your gender.'); hasErrors = true; } else { clearError('gender'); }
            if (!guardianNameInput.value) { showError('guardianName', 'Please enter your guardian name.'); hasErrors = true; } else { clearError('guardianName'); }
            if (!guardianContactInput.value) { showError('guardianContact', 'Please enter your guardian contact.'); hasErrors = true; } else { clearError('guardianContact'); }
        } else if (formId === 'profilePictureForm') {
            const profilePictureInput = document.getElementById('profilePicture');
            if (profilePictureInput.files.length === 0) { showError('profilePicture', 'Please select a profile picture.'); hasErrors = true; }
            else if (profilePictureInput.files[0].size > 2 * 1024 * 1024) { showError('profilePicture', 'File size must be less than 2MB.'); hasErrors = true; }
            else { clearError('profilePicture'); }
        } else if (formId === 'securityForm') {
            const currentPasswordInput = document.getElementById('currentPassword');
            const newPasswordInput = document.getElementById('newPassword');
            const confirmPasswordInput = document.getElementById('confirmPassword');

            if (!currentPasswordInput.value) { showError('currentPassword', 'Please enter your current password.'); hasErrors = true; } else { clearError('currentPassword'); }
            if (newPasswordInput.value && newPasswordInput.value.length < 8) { showError('newPassword', 'New password must be at least 8 characters long.'); hasErrors = true; } else { clearError('newPassword'); }
            if (newPasswordInput.value && confirmPasswordInput.value !== newPasswordInput.value) { showError('confirmPassword', 'Passwords do not match.'); hasErrors = true; } else { clearError('confirmPassword'); }
        } else if (formId === 'registrationFormOnly') {
            const registrationFormInput = document.getElementById('registrationFormOnlyUpload');
            if (registrationFormInput.files.length === 0) { showError('registrationFormOnly', 'Please upload your registration form.'); hasErrors = true; } else { clearError('registrationFormOnly'); }
        }

        if (!hasErrors) {
            fetch('/api/profile/update/', { method: 'POST', body: formData })
                .then(response => {
                    console.log("Fetch Response:", response);
                    if (!response.ok) return response.json().then(errorData => {
                        console.error("Fetch Error Data:", errorData);
                        throw new Error(errorData.detail || `Failed to update ${formId.slice(0, -4).toLowerCase()}`);
                    });
                    return response.json();
                })
                .then(data => {
                    console.log("Fetch Success Data:", data);
                    successCallback(data, form);
                })
                .catch(error => {
                    console.error("Fetch Error:", error);
                    errorCallback(error);
                });
        }
    }

    // Success Callbacks
    function handleStudentInfoSuccess(data, form) {
        alert('Profile information updated successfully!');
        resetForm(form);
        if (data && data.user) updateStudentInfoDisplay(data.user);
    }

    function handleProfilePictureSuccess(data, form) {
        alert('Profile picture updated successfully!');
        resetForm(form);
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
        const registrationFormInput = document.getElementById('registrationFormOnlyUpload');
        const fileName = registrationFormInput.files[0] ? registrationFormInput.files[0].name : '';

        if (registrationFormDisplayElement && fileName) registrationFormDisplayElement.textContent = fileName;

        resetForm(form);

        if (data.user.verification_status) setRegistrationStatus(data.user.verification_status);

        updateStudentInfoDisplay(data.user);
    }

    // Error Callback
    function handleError(error) {
        alert(error.message);
    }

    // Update Display and Input Fields
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

    function updateStudentInfoDisplay(userData) {
        fieldConfigs.forEach(config => {
            const inputValue = userData[config.prop] || '';
            const displayElement = document.getElementById(config.displayId);
            const inputElement = document.getElementById(config.id);

            if (displayElement) {
                displayElement.textContent = config.isDate && inputValue ? new Date(inputValue).toLocaleDateString() : inputValue;
            }
            if (inputElement) {
                inputElement.value = inputValue;
            }
        });
    }

    // Event Listeners for editable fields
    const editBirthDateBtn = document.getElementById('editBirthDate');
    const editGenderBtn = document.getElementById('editGender');
    const editGuardianNameBtn = document.getElementById('editGuardianName');
    const editGuardianContactBtn = document.getElementById('editGuardianContact');
    const editRegistrationFormBtn = document.getElementById('editRegistrationForm');

    if (editBirthDateBtn) editBirthDateBtn.addEventListener('click', () => makeFieldEditable('birthDateDisplay', 'birthDate'));
    if (editGenderBtn) editGenderBtn.addEventListener('click', () => makeFieldEditable('genderDisplay', 'gender'));
    if (editGuardianNameBtn) editGuardianNameBtn.addEventListener('click', () => makeFieldEditable('guardianNameDisplay', 'guardianName'));
    if (editGuardianContactBtn) editGuardianContactBtn.addEventListener('click', () => makeFieldEditable('guardianContactDisplay', 'guardianContact'));
    if (editRegistrationFormBtn) editRegistrationFormBtn.addEventListener('click', () => makeFieldEditable('registrationFormDisplay', 'registrationFormUpload'));

    // Event Listeners for form submissions
    if (studentInfoForm) studentInfoForm.addEventListener('submit', (event) => handleFormSubmit(event, 'studentInfoForm', handleStudentInfoSuccess, handleError));
    if (profilePictureForm) profilePictureForm.addEventListener('submit', (event) => handleFormSubmit(event, 'profilePictureForm', handleProfilePictureSuccess, handleError));
    if (securityForm) securityForm.addEventListener('submit', (event) => handleFormSubmit(event, 'securityForm', handleSecuritySuccess, handleError));
    if (registrationFormOnly) registrationFormOnly.addEventListener('submit', (event) => handleFormSubmit(event, 'registrationFormOnly', handleRegistrationFormOnlySuccess, handleError));

    // Clear Form Buttons
    if (clearStudentInfoFormBtn) clearStudentInfoFormBtn.addEventListener('click', () => resetForm(studentInfoForm));
    if (clearProfilePictureBtn) clearProfilePictureBtn.addEventListener('click', () => resetForm(profilePictureForm));
    if (clearSecurityFormBtn) clearSecurityFormBtn.addEventListener('click', () => resetForm(securityForm));
    if (clearRegistrationFormOnlyBtn) clearRegistrationFormOnlyBtn.addEventListener('click', () => resetForm(registrationFormOnly));
    
});
