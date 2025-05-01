document.addEventListener('DOMContentLoaded', () => {
    // --- Student Info Form ---
    const studentInfoForm = document.getElementById('studentInfoForm');
    const clearStudentInfoFormBtn = document.getElementById('clearStudentInfoForm');
    const registrationStatusDisplay = document.getElementById('registrationStatus');

    // --- Profile Picture Form ---
    const profilePictureForm = document.getElementById('profilePictureForm');
    const clearProfilePictureBtn = document.getElementById('clearProfilePictureBtn');

    // --- Security Form ---
    const securityForm = document.getElementById('securityForm');
    const clearSecurityFormBtn = document.getElementById('clearSecurityFormBtn');


    // Initial Registration Status
    function setRegistrationStatus(status) {
        if (status === 'Verified') {
            registrationStatusDisplay.textContent = 'Verified';
            registrationStatusDisplay.className = 'verified';
        } else {
            registrationStatusDisplay.textContent = 'Not Verified';
            registrationStatusDisplay.className = 'unverified';
        }
    }

    //set initial registration status.
    const initialStatus = "{{ user.verification_status }}"; // This is server-side templating.  Keep this.
    setRegistrationStatus(initialStatus);

    // Function to make fields editable
    function makeFieldEditable(displayElementId, inputElementId) {
        const displayElement = document.getElementById(displayElementId);
        const inputElement = document.getElementById(inputElementId);

        if (displayElement && inputElement) {
            displayElement.style.display = 'none';
            inputElement.style.display = 'block';
            inputElement.focus();

            // Hide input and show display on blur
            inputElement.addEventListener('blur', () => {
                displayElement.textContent = inputElement.value;
                displayElement.style.display = 'block';
                inputElement.style.display = 'none';
            });
        }
    }

    // Event listeners to make fields editable
    const editBirthDateBtn = document.getElementById('editBirthDate');
    const editGenderBtn = document.getElementById('editGender');
    const editGuardianNameBtn = document.getElementById('editGuardianName');
    const editGuardianContactBtn = document.getElementById('editGuardianContact');
    const editRegistrationFormBtn = document.getElementById('editRegistrationForm');

    if (editBirthDateBtn) {
        editBirthDateBtn.addEventListener('click', () => makeFieldEditable('birthDateDisplay', 'birthDate'));
    }
    if (editGenderBtn) {
        editGenderBtn.addEventListener('click', () => makeFieldEditable('genderDisplay', 'gender'));
    }
    if (editGuardianNameBtn) {
        editGuardianNameBtn.addEventListener('click', () => makeFieldEditable('guardianNameDisplay', 'guardianName'));
    }
    if (editGuardianContactBtn) {
        editGuardianContactBtn.addEventListener('click', () => makeFieldEditable('guardianContactDisplay', 'guardianContact'));
    }
    if (editRegistrationFormBtn) {
        editRegistrationFormBtn.addEventListener('click', () => makeFieldEditable('registrationFormDisplay', 'registrationFormUpload'));
    }

    // Function to display error messages
    function showError(inputElementId, message) {
        const errorElement = document.getElementById(inputElementId + 'Error');
        if (errorElement) {
            errorElement.textContent = message;
        }
    }

    // Function to clear error messages
    function clearError(inputElementId) {
        const errorElement = document.getElementById(inputElementId + 'Error');
        if (errorElement) {
            errorElement.textContent = '';
        }
    }

    // Function to reset forms
    function resetForm(form) {
        const inputs = form.querySelectorAll('input, select');
        inputs.forEach(input => {
            if (input.type === 'file') {
                input.value = '';
            } else if (input.type !== 'button') {
                input.value = '';
            }
        });
        const errorMessages = form.querySelectorAll('.error-message');
        errorMessages.forEach(error => {
            error.textContent = '';
        });

        // Special handling for showing display elements and hiding inputs
        const displayInputPairs = [
            ['birthDateDisplay', 'birthDate'],
            ['genderDisplay', 'gender'],
            ['guardianNameDisplay', 'guardianName'],
            ['guardianContactDisplay', 'guardianContact'],
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
        // Reset file inputs
        const fileInputs = form.querySelectorAll('input[type="file"]');
        fileInputs.forEach(fileInput => {
            fileInput.value = ''; // Clear the selected file
        });
    }

    // --- Form Submission Handlers ---
    function handleFormSubmit(event, formId, successCallback, errorCallback) {
        event.preventDefault();
        const form = document.getElementById(formId);
        if (!form) return;

        let hasErrors = false;
        const formData = new FormData(form);
        console.log(`Form ID: ${formId}`);

        // --- Validation ---
        if (formId === 'studentInfoForm') {
            const birthDateInput = document.getElementById('birthDate');
            const genderInput = document.getElementById('gender');
            const guardianNameInput = document.getElementById('guardianName');
            const guardianContactInput = document.getElementById('guardianContact');
            const registrationFormInput = document.getElementById('registrationFormUpload');

            if (!birthDateInput.value) {
                showError('birthDate', 'Please enter your birth date.');
                hasErrors = true;
            } else {
                clearError('birthDate');
            }
            if (!genderInput.value) {
                showError('gender', 'Please select your gender.');
                hasErrors = true;
            } else {
                clearError('gender');
            }
            if (!guardianNameInput.value) {
                showError('guardianName', 'Please enter your guardian name.');
                hasErrors = true;
            } else {
                clearError('guardianName');
            }
            if (!guardianContactInput.value) {
                showError('guardianContact', 'Please enter your guardian contact.');
                hasErrors = true;
            } else {
                clearError('guardianContact');
            }
            if (registrationFormInput.files.length === 0) {
                showError('registrationForm', 'Please upload your registration form.');
                hasErrors = true;
            } else {
                clearError('registrationForm');
            }
        } else if (formId === 'profilePictureForm') {
            const profilePictureInput = document.getElementById('profilePicture');
            //  Check if a file is selected.
            if (profilePictureInput.files.length === 0) {
                showError('profilePicture', 'Please select a profile picture.');
                hasErrors = true;
            }
            else if (profilePictureInput.files[0].size > 2 * 1024 * 1024) { // 2MB limit
                showError('profilePicture', 'File size must be less than 2MB.');
                hasErrors = true;
            } else {
                clearError('profilePicture');
            }
        } else if (formId === 'securityForm') {
            const currentPasswordInput = document.getElementById('currentPassword');
            const newPasswordInput = document.getElementById('newPassword');
            const confirmPasswordInput = document.getElementById('confirmPassword');

            if (!currentPasswordInput.value) {
                showError('currentPassword', 'Please enter your current password.');
                hasErrors = true;
            } else {
                clearError('currentPassword');
            }
            if (newPasswordInput.value && newPasswordInput.value.length < 8) {
                showError('newPassword', 'New password must be at least 8 characters long.');
                hasErrors = true;
            } else {
                clearError('newPassword');
            }
            if (newPasswordInput.value && confirmPasswordInput.value !== newPasswordInput.value) {
                showError('confirmPassword', 'Passwords do not match.');
                hasErrors = true;
            } else {
                clearError('confirmPassword');
            }
        }

        if (!hasErrors) {
            // Important:  Check formId before making the fetch call
            fetch('/api/profile/update/', {
                method: 'POST',
                body: formData,
            })
                .then(response => {
                    console.log("Fetch Response:", response);
                    if (!response.ok) {
                        return response.json().then(errorData => {
                            console.error("Fetch Error Data:", errorData);
                            throw new Error(errorData.detail || `Failed to update ${formId.slice(0, -4).toLowerCase()}`);
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
                    errorCallback(error);
                });
        }
    }

    // --- Success Callbacks ---
    function handleStudentInfoSuccess(data, form) {
        alert('Profile information updated successfully!');
        resetForm(form);
        // Update displayed values
        const formData = new FormData(form);
        if (document.getElementById('birthDateDisplay')) {
            document.getElementById('birthDateDisplay').textContent = formData.get('birthDate');
        }
        if (document.getElementById('genderDisplay')) {
            document.getElementById('genderDisplay').textContent = formData.get('gender');
        }
        if (document.getElementById('guardianNameDisplay')) {
            document.getElementById('guardianNameDisplay').textContent = formData.get('guardianName');
        }
        if (document.getElementById('guardianContactDisplay')) {
            document.getElementById('guardianContactDisplay').textContent = formData.get('guardianContact');
        }
        if (document.getElementById('registrationFormDisplay')) {
            const registrationFormInput = document.getElementById('registrationFormUpload');
            const fileName = registrationFormInput.files[0] ? registrationFormInput.files[0].name : '';
            document.getElementById('registrationFormDisplay').textContent = fileName;
        }
    }

    function handleProfilePictureSuccess(data, form) {
        alert('Profile picture updated successfully!');
        resetForm(form);
        const profilePicturePreview = document.querySelector('.profile-picture-preview');
        if (profilePicturePreview && data.user.profile_picture) {
            profilePicturePreview.src = data.user.profile_picture;
        }
    }

    function handleSecuritySuccess(data, form) {
        alert('Security settings updated successfully!');
        resetForm(form);
    }

    // --- Error Callback ---
    function handleError(error) {
        alert(error.message);
    }

    // --- Event Listeners for form submissions ---
    if (studentInfoForm) {
        studentInfoForm.addEventListener('submit', (event) => handleFormSubmit(event, 'studentInfoForm', handleStudentInfoSuccess, handleError));
    }
    if (profilePictureForm) {
        profilePictureForm.addEventListener('submit', (event) => handleFormSubmit(event, 'profilePictureForm', handleProfilePictureSuccess, handleError));
    }
    if (securityForm) {
        securityForm.addEventListener('submit', (event) => handleFormSubmit(event, 'securityForm', handleSecuritySuccess, handleError));
    }

    // --- Clear Form Buttons ---
    if (clearStudentInfoFormBtn) {
        clearStudentInfoFormBtn.addEventListener('click', () => {
            resetForm(studentInfoForm);
        });
    }
    if (clearProfilePictureBtn) {
        clearProfilePictureBtn.addEventListener('click', () => {
            resetForm(profilePictureForm);
        });
    }
    if (clearSecurityFormBtn) {
        clearSecurityFormBtn.addEventListener('click', () => {
            resetForm(securityForm);
        });
    }
});
