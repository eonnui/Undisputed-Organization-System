document.addEventListener('DOMContentLoaded', function() {
    const contactForm = document.getElementById('contactForm');
    const securityForm = document.getElementById('securityForm');
    const profilePictureForm = document.getElementById('profilePictureForm');
    const studentInfoForm = document.getElementById('studentInfoForm');


    // Initial student data (from signup)
    const initialStudentData = {
        student_number: '2023-10001',
        first_name: 'John',
        last_name: 'Doe',
        email: 'john.doe@example.com',
    };

    //display initial student data
    document.getElementById('studentNumberDisplay').textContent = initialStudentData.student_number;
    document.getElementById('firstNameDisplay').textContent = initialStudentData.first_name;
    document.getElementById('lastNameDisplay').textContent = initialStudentData.last_name;
    document.getElementById('studentEmailDisplay').textContent = initialStudentData.email;



    studentInfoForm.addEventListener('submit', function(event) {
        event.preventDefault();
        if (validateStudentInfoForm()) {
            const formData = new FormData(studentInfoForm);
            const studentData = Object.fromEntries(formData.entries());

            // Combine initial data with updated data
            const updatedStudentData = {
                ...initialStudentData, //keep initial data
                birth_date: studentData.birthDate,
                gender: studentData.gender,
                address: studentData.address,
                year_level: studentData.yearLevel,
                section: studentData.section,
                guardian_name: studentData.guardianName,
                guardian_contact: studentData.guardianContact
            };

            // Simulate sending data to the server
            console.log('Updated Student Data:', updatedStudentData);
            alert('Student information updated (simulated)!');
            // Update display
            document.getElementById('studentNumberDisplay').textContent = updatedStudentData.student_number ? updatedStudentData.student_number : '';
            document.getElementById('firstNameDisplay').textContent = updatedStudentData.first_name ? updatedStudentData.first_name : '';
            document.getElementById('lastNameDisplay').textContent = updatedStudentData.last_name ? updatedStudentData.last_name : '';
            document.getElementById('studentEmailDisplay').textContent = updatedStudentData.email ? updatedStudentData.email : '';
            document.getElementById('birthDateDisplay').textContent = updatedStudentData.birth_date ? updatedStudentData.birth_date : '';
            document.getElementById('genderDisplay').textContent = updatedStudentData.gender ? updatedStudentData.gender : '';
            document.getElementById('addressDisplay').textContent = updatedStudentData.address ? updatedStudentData.address : '';
            document.getElementById('yearLevelDisplay').textContent = updatedStudentData.year_level ? updatedStudentData.year_level : '';
            document.getElementById('sectionDisplay').textContent = updatedStudentData.section ? updatedStudentData.section : '';
            document.getElementById('guardianNameDisplay').textContent = updatedStudentData.guardian_name ? updatedStudentData.guardian_name : '';
            document.getElementById('guardianContactDisplay').textContent = updatedStudentData.guardian_contact ? updatedStudentData.guardian_contact : '';

            // Hide all input fields after submit
            hideAllInputs();

        }
    });



    contactForm.addEventListener('submit', function(event) {
        event.preventDefault();
        if (validateContactForm()) {
            alert('Contact details updated (simulated)');
            // Add your fetch/ajax request here
        }
    });

    securityForm.addEventListener('submit', function(event) {
        event.preventDefault();
        if (validateSecurityForm()) {
            alert('Security settings updated (simulated)');
            // Add your fetch/ajax request here
        }
    });

    profilePictureForm.addEventListener('submit', function(event) {
        event.preventDefault();
        if (validateProfilePictureForm()) {
            alert('Profile picture updated (simulated)');
            // Add your fetch/ajax request here (remember to handle file uploads)
        }
    });

    // Event listeners for edit icons
    document.getElementById('editStudentNumber').addEventListener('click', () => {
        toggleInput('studentNumberDisplay', 'studentNumber');
    });
    document.getElementById('editFirstName').addEventListener('click', () => {
        toggleInput('firstNameDisplay', 'firstName');
    });
    document.getElementById('editLastName').addEventListener('click', () => {
        toggleInput('lastNameDisplay', 'lastName');
    });
    document.getElementById('editEmail').addEventListener('click', () => {
        toggleInput('studentEmailDisplay', 'email');
    });
    document.getElementById('editBirthDate').addEventListener('click', () => {
        toggleInput('birthDateDisplay', 'birthDate');
    });
    document.getElementById('editGender').addEventListener('click', () => {
        toggleInput('genderDisplay', 'gender');
    });
    document.getElementById('editAddress').addEventListener('click', () => {
        toggleInput('addressDisplay', 'address');
    });
    document.getElementById('editYearLevel').addEventListener('click', () => {
        toggleInput('yearLevelDisplay', 'yearLevel');
    });
    document.getElementById('editSection').addEventListener('click', () => {
        toggleInput('sectionDisplay', 'section');
    });
    document.getElementById('editGuardianName').addEventListener('click', () => {
        toggleInput('guardianNameDisplay', 'guardianName');
    });
    document.getElementById('editGuardianContact').addEventListener('click', () => {
        toggleInput('guardianContactDisplay', 'guardianContact');
    });
    document.getElementById('editRegistrationForm').addEventListener('click', () => {
        toggleInput('registrationFormDisplay', 'registrationFormUpload');
    });
});



function clearContactForm() {
    document.getElementById('emailContact').value = '';
    document.getElementById('mobileContact').value = '';
    clearErrors('contactForm');
}

function clearSecurityForm() {
    document.getElementById('currentPassword').value = '';
    document.getElementById('newPassword').value = '';
    document.getElementById('confirmPassword').value = '';
    clearErrors('securityForm');
}

function clearStudentInfoForm() {
    document.getElementById('studentNumber').value = '2023-10001';
    document.getElementById('firstName').value = 'John';
    document.getElementById('lastName').value = 'Doe';
    document.getElementById('email').value = 'john.doe@example.com';
    document.getElementById('birthDate').value = '';
    document.getElementById('gender').value = '';
    document.getElementById('address').value = '';
    document.getElementById('yearLevel').value = '';
    document.getElementById('section').value = '';
    document.getElementById('guardianName').value = '';
    document.getElementById('guardianContact').value = '';
    document.getElementById('registrationFormUpload').value = '';
    clearErrors('studentInfoForm');
    hideAllInputs();
}

function clearErrors(formId) {
    const errors = document.querySelectorAll(`#${formId} .error-message`);
    errors.forEach(error => error.textContent = '');
}

function hideAllInputs() {
    document.getElementById('studentNumber').style.display = 'none';
    document.getElementById('firstName').style.display = 'none';
    document.getElementById('lastName').style.display = 'none';
    document.getElementById('email').style.display = 'none';
    document.getElementById('birthDate').style.display = 'none';
    document.getElementById('gender').style.display = 'none';
    document.getElementById('address').style.display = 'none';
    document.getElementById('yearLevel').style.display = 'none';
    document.getElementById('section').style.display = 'none';
    document.getElementById('guardianName').style.display = 'none';
    document.getElementById('guardianContact').style.display = 'none';
    document.getElementById('registrationFormUpload').style.display = 'none';

    document.getElementById('studentNumberDisplay').style.display = 'inline-block';
    document.getElementById('firstNameDisplay').style.display = 'inline-block';
    document.getElementById('lastNameDisplay').style.display = 'inline-block';
    document.getElementById('studentEmailDisplay').style.display = 'inline-block';
    document.getElementById('birthDateDisplay').style.display = 'inline-block';
    document.getElementById('genderDisplay').style.display = 'inline-block';
    document.getElementById('addressDisplay').style.display = 'inline-block';
    document.getElementById('yearLevelDisplay').style.display = 'inline-block';
    document.getElementById('sectionDisplay').style.display = 'inline-block';
    document.getElementById('guardianNameDisplay').style.display = 'inline-block';
    document.getElementById('guardianContactDisplay').style.display = 'inline-block';
    document.getElementById('registrationFormDisplay').style.display = 'inline-block';
}


function validateContactForm() {
    clearErrors('contactForm');
    let isValid = true;

    const emailInput = document.getElementById('emailContact');
    const mobileInput = document.getElementById('mobileContact');

    if (!emailInput.value.trim()) {
        document.getElementById('emailContactError').textContent = 'Email is required.';
        isValid = false;
    } else if (!isValidEmail(emailInput.value.trim())) {
        document.getElementById('emailContactError').textContent = 'Invalid email format.';
        isValid = false;
    }

    if (!mobileInput.value.trim()) {
        document.getElementById('mobileContactError').textContent = 'Mobile number is required.';
        isValid = false;
    } else if (!/^(09|\+639)\d{9}$/.test(mobileInput.value.trim())) {
        document.getElementById('mobileContactError').textContent = 'Invalid mobile number format (e.g., 09XXXXXXXXX or +639XXXXXXXXX).';
        isValid = false;
    }

    return isValid;
}

function validateSecurityForm() {
    clearErrors('securityForm');
    let isValid = true;

    const currentPasswordInput = document.getElementById('currentPassword');
    const newPasswordInput = document.getElementById('newPassword');
    const confirmPasswordInput = document.getElementById('confirmPassword');

    if (!currentPasswordInput.value.trim()) {
        document.getElementById('currentPasswordError').textContent = 'Current password is required.';
        isValid = false;
    }

    if (newPasswordInput.value.trim()) {
        if (newPasswordInput.value.trim().length < 8) {
            document.getElementById('newPasswordError').textContent = 'New password must be at least 8 characters long.';
            isValid = false;
        } else if (newPasswordInput.value.trim() !== confirmPasswordInput.value.trim()) {
            document.getElementById('confirmPasswordError').textContent = 'New passwords do not match.';
            isValid = false;
        }
    } else if (confirmPasswordInput.value.trim()) {
        document.getElementById('newPasswordError').textContent = 'Please enter a new password to confirm.';
        document.getElementById('confirmPasswordError').textContent = 'Please enter a new password to confirm.';
        isValid = false;
    }

    return isValid;
}

function validateProfilePictureForm() {
    const fileInput = document.getElementById('profilePicture');
    const errorDiv = document.getElementById('profilePictureError');
    errorDiv.textContent = '';

    if (fileInput.files.length > 0) {
        const file = fileInput.files[0];
        const allowedTypes = ['image/jpeg', 'image/png', 'image/gif'];

        if (!allowedTypes.includes(file.type)) {
            errorDiv.textContent = 'Invalid file type. Only JPG, PNG, and GIF are allowed.';
            return false;
        }
        // Optional: Add file size validation here
    }
    return true;
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function validateRegistrationForm() {
    const fileInput = document.getElementById('registrationFormUpload');
    const errorDiv = document.getElementById('registrationFormError');
    errorDiv.textContent = '';

    if (fileInput.files.length === 0) {
        errorDiv.textContent = 'Please upload the registration form.';
        return false;
    }

    const file = fileInput.files[0];
    const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];

    if (!allowedTypes.includes(file.type)) {
        errorDiv.textContent = 'Invalid file type. Only PDF, DOC, and DOCX are allowed.';
        return false;
    }
    return true;
}

function validateStudentInfoForm() {
    clearErrors('studentInfoForm');
    let isValid = true;

    const studentNumberInput = document.getElementById('studentNumber');
    const firstNameInput = document.getElementById('firstName');
    const lastNameInput = document.getElementById('lastName');
    const emailInput = document.getElementById('email');
    const birthDateInput = document.getElementById('birthDate');
    const genderInput = document.getElementById('gender');


    if (!birthDateInput.value.trim()) {
        document.getElementById('birthDateError').textContent = 'Birth Date is required.';
        isValid = false;
    }
    if (!genderInput.value.trim()) {
        document.getElementById('genderError').textContent = 'Gender is required.';
        isValid = false;
    }

    return isValid;
}

function toggleInput(displayId, inputId) {
    const displayElement = document.getElementById(displayId);
    const inputElement = document.getElementById(inputId);

    if (displayElement.style.display === 'none') {
        displayElement.style.display = 'inline-block';
        inputElement.style.display = 'none';
         inputElement.focus();
    } else {
        displayElement.style.display = 'none';
        inputElement.style.display = 'inline-block';
       
    }
}
