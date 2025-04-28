document.addEventListener('DOMContentLoaded', () => {
    // --- Student Info Form ---
    const studentInfoForm = document.getElementById('studentInfoForm');
    const editStudentNumberBtn = document.getElementById('editStudentNumber');
    const editFirstNameBtn = document.getElementById('editFirstName');
    const editLastNameBtn = document.getElementById('editLastName');
    const editEmailBtn = document.getElementById('editEmail');
    const editBirthDateBtn = document.getElementById('editBirthDate');
    const editGenderBtn = document.getElementById('editGender');
    const editAddressBtn = document.getElementById('editAddress');
    const editYearLevelBtn = document.getElementById('editYearLevel');
    const editSectionBtn = document.getElementById('editSection');
    const editGuardianNameBtn = document.getElementById('editGuardianName');
    const editGuardianContactBtn = document.getElementById('editGuardianContact');
    const editRegistrationFormBtn = document.getElementById('editRegistrationForm');
    const clearStudentInfoFormBtn = document.getElementById('clearStudentInfoForm');

    function makeFieldEditable(displayElementId, inputElementId) {
        const displayElement = document.getElementById(displayElementId);
        const inputElement = document.getElementById(inputElementId);

        if (displayElement && inputElement) { // Check if elements exist
            displayElement.style.display = 'none';
            inputElement.style.display = 'block';
            inputElement.focus(); // Focus on the input when it appears.

            // Hide input and show display on blur
            inputElement.addEventListener('blur', () => {
                displayElement.style.display = 'block';
                inputElement.style.display = 'none';
            });
        }
    }

    if (editStudentNumberBtn) {
        editStudentNumberBtn.addEventListener('click', () => makeFieldEditable('studentNumberDisplay', 'studentNumber'));
    }
    if (editFirstNameBtn) {
        editFirstNameBtn.addEventListener('click', () => makeFieldEditable('firstNameDisplay', 'firstName'));
    }
    if (editLastNameBtn) {
        editLastNameBtn.addEventListener('click', () => makeFieldEditable('lastNameDisplay', 'lastName'));
    }
    if (editEmailBtn) {
        editEmailBtn.addEventListener('click', () => makeFieldEditable('studentEmailDisplay', 'email'));
    }


    if (editBirthDateBtn) {
        editBirthDateBtn.addEventListener('click', () => {
            const displayElement = document.getElementById('birthDateDisplay');
            const inputElement = document.getElementById('birthDate');
            if (displayElement && inputElement) {
                inputElement.type = 'date';
                displayElement.style.display = 'none';
                inputElement.style.display = 'block';
                inputElement.focus();

                inputElement.addEventListener('blur', () => {
                    displayElement.textContent = inputElement.value;
                    displayElement.style.display = 'block';
                    inputElement.style.display = 'none';
                    inputElement.type = 'text';
                });
            }
        });
    }

    if (editGenderBtn) {
        editGenderBtn.addEventListener('click', () => {
            const displayElement = document.getElementById('genderDisplay');
            const inputElement = document.getElementById('gender');
            if (displayElement && inputElement) {
                displayElement.style.display = 'none';
                inputElement.style.display = 'block';
                inputElement.focus();

                inputElement.addEventListener('blur', () => {
                    const selectedOption = inputElement.options[inputElement.selectedIndex];
                    displayElement.textContent = selectedOption.text;
                    displayElement.style.display = 'block';
                    inputElement.style.display = 'none';
                });
            }

        });
    }

    if (editAddressBtn) {
        editAddressBtn.addEventListener('click', () => makeFieldEditable('addressDisplay', 'address'));
    }

    if (editYearLevelBtn) {
        editYearLevelBtn.addEventListener('click', () => {
            const displayElement = document.getElementById('yearLevelDisplay');
            const inputElement = document.getElementById('yearLevel');
            if (displayElement && inputElement) {
                displayElement.style.display = 'none';
                inputElement.style.display = 'block';
                inputElement.focus();

                inputElement.addEventListener('blur', () => {
                    const selectedOption = inputElement.options[inputElement.selectedIndex];
                    displayElement.textContent = selectedOption.text;
                    displayElement.style.display = 'block';
                    inputElement.style.display = 'none';
                });
            }
        });
    }

    if (editSectionBtn) {
        editSectionBtn.addEventListener('click', () => makeFieldEditable('sectionDisplay', 'section'));
    }

    if (editGuardianNameBtn) {
        editGuardianNameBtn.addEventListener('click', () => makeFieldEditable('guardianNameDisplay', 'guardianName'));
    }

    if (editGuardianContactBtn) {
        editGuardianContactBtn.addEventListener('click', () => makeFieldEditable('guardianContactDisplay', 'guardianContact'));
    }

    if (editRegistrationFormBtn) {
        editRegistrationFormBtn.addEventListener('click', () => {
            const displayElement = document.getElementById('registrationFormDisplay');
            const inputElement = document.getElementById('registrationFormUpload');
            if (displayElement && inputElement) {
                displayElement.style.display = 'none';
                inputElement.style.display = 'block';
                inputElement.focus();

                inputElement.addEventListener('change', () => {
                    if (inputElement.files && inputElement.files[0]) {
                        displayElement.textContent = inputElement.files[0].name;
                    } else {
                        displayElement.textContent = '';
                    }
                    displayElement.style.display = 'block';
                    inputElement.style.display = 'none';
                });
            }
        });
    }


    studentInfoForm.addEventListener('submit', (event) => {
        event.preventDefault();

        let hasErrors = false;

        // Reset all error messages
        document.getElementById('birthDateError').textContent = '';
        document.getElementById('genderError').textContent = '';
        document.getElementById('addressError').textContent = '';
        document.getElementById('yearLevelError').textContent = '';
        document.getElementById('sectionError').textContent = '';
        document.getElementById('guardianNameError').textContent = '';
        document.getElementById('guardianContactError').textContent = '';
        document.getElementById('registrationFormError').textContent = '';


        const birthDateInput = document.getElementById('birthDate');
        const genderInput = document.getElementById('gender');
        const addressInput = document.getElementById('address');
        const yearLevelInput = document.getElementById('yearLevel');
        const sectionInput = document.getElementById('section');
        const guardianNameInput = document.getElementById('guardianName');
        const guardianContactInput = document.getElementById('guardianContact');
        const registrationFormInput = document.getElementById('registrationFormUpload');


        if (!birthDateInput.value) {
            document.getElementById('birthDateError').textContent = 'Please enter your birth date.';
            hasErrors = true;
        }

        if (!genderInput.value) {
            document.getElementById('genderError').textContent = 'Please select your gender.';
            hasErrors = true;
        }

        if (!addressInput.value) {
            document.getElementById('addressError').textContent = 'Please enter your address.';
            hasErrors = true;
        }
        if (!yearLevelInput.value) {
            document.getElementById('yearLevelError').textContent = 'Please select your year level.';
            hasErrors = true;
        }
        if (!sectionInput.value) {
            document.getElementById('sectionError').textContent = 'Please enter your section.';
            hasErrors = true;
        }
        if (!guardianNameInput.value) {
            document.getElementById('guardianNameError').textContent = 'Please enter your guardian name.';
            hasErrors = true;
        }
        if (!guardianContactInput.value) {
            document.getElementById('guardianContactError').textContent = 'Please enter your guardian contact.';
            hasErrors = true;
        }

        if (registrationFormInput.files.length === 0) {
            document.getElementById('registrationFormError').textContent = 'Please upload your registration form.';
            hasErrors = true;
        } else if (registrationFormInput.files[0].type !== 'application/pdf') {
            document.getElementById('registrationFormError').textContent = 'Invalid file format. Please upload a PDF.';
            hasErrors = true;
        }

        if (hasErrors) {
            return;
        }
        const formData = new FormData(studentInfoForm);

        fetch('/api/profile/update/', {
            method: 'POST',
            body: formData,
        })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(errorData => {
                        throw new Error(errorData.detail || 'Failed to update profile');
                    });
                }
                return response.json();
            })
            .then(data => {
                alert(data.message);
                 // Update the displayed values after successful submission
                document.getElementById('studentNumberDisplay').textContent = document.getElementById('studentNumber').value;
                document.getElementById('firstNameDisplay').textContent = document.getElementById('firstName').value;
                document.getElementById('lastNameDisplay').textContent = document.getElementById('lastName').value;
                document.getElementById('studentEmailDisplay').textContent = document.getElementById('email').value;
                document.getElementById('birthDateDisplay').textContent = document.getElementById('birthDate').value;
                document.getElementById('genderDisplay').textContent = document.getElementById('gender').options[document.getElementById('gender').selectedIndex].text;
                document.getElementById('addressDisplay').textContent = document.getElementById('address').value;
                document.getElementById('yearLevelDisplay').textContent = document.getElementById('yearLevel').options[document.getElementById('yearLevel').selectedIndex].text;
                document.getElementById('sectionDisplay').textContent = document.getElementById('section').value;
                document.getElementById('guardianNameDisplay').textContent = document.getElementById('guardianName').value;
                document.getElementById('guardianContactDisplay').textContent = document.getElementById('guardianContact').value;
                if (registrationFormInput.files && registrationFormInput.files[0]) {
                    document.getElementById('registrationFormDisplay').textContent = registrationFormInput.files[0].name;
                }

                // Hide the input fields after successful update
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

                //show the display labels
                document.getElementById('studentNumberDisplay').style.display = 'block';
                document.getElementById('firstNameDisplay').style.display = 'block';
                document.getElementById('lastNameDisplay').style.display = 'block';
                document.getElementById('studentEmailDisplay').style.display = 'block';
                document.getElementById('birthDateDisplay').style.display = 'block';
                document.getElementById('genderDisplay').style.display = 'block';
                document.getElementById('addressDisplay').style.display = 'block';
                document.getElementById('yearLevelDisplay').style.display = 'block';
                document.getElementById('sectionDisplay').style.display = 'block';
                document.getElementById('guardianNameDisplay').style.display = 'block';
                document.getElementById('guardianContactDisplay').style.display = 'block';
                document.getElementById('registrationFormDisplay').style.display = 'block';

            })
            .catch(error => {
                alert(error.message);
            });
    });

    if (clearStudentInfoFormBtn) {
        clearStudentInfoFormBtn.addEventListener('click', () => {
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


            document.getElementById('birthDateError').textContent = '';
            document.getElementById('genderError').textContent = '';
            document.getElementById('addressError').textContent = '';
            document.getElementById('yearLevelError').textContent = '';
            document.getElementById('sectionError').textContent = '';
            document.getElementById('guardianNameError').textContent = '';
            document.getElementById('guardianContactError').textContent = '';
            document.getElementById('registrationFormError').textContent = '';

            //reset the display labels
            document.getElementById('studentNumberDisplay').textContent = '2023-10001';
            document.getElementById('firstNameDisplay').textContent = 'John';
            document.getElementById('lastNameDisplay').textContent = 'Doe';
            document.getElementById('studentEmailDisplay').textContent = 'john.doe@example.com';
            document.getElementById('birthDateDisplay').textContent = '';
            document.getElementById('genderDisplay').textContent = '';
            document.getElementById('addressDisplay').textContent = '';
            document.getElementById('yearLevelDisplay').textContent = '';
            document.getElementById('sectionDisplay').textContent = '';
            document.getElementById('guardianNameDisplay').textContent = '';
            document.getElementById('guardianContactDisplay').textContent = '';
            document.getElementById('registrationFormDisplay').textContent = '';

            // Hide input fields and show display labels
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

            document.getElementById('studentNumberDisplay').style.display = 'block';
            document.getElementById('firstNameDisplay').style.display = 'block';
            document.getElementById('lastNameDisplay').style.display = 'block';
            document.getElementById('studentEmailDisplay').style.display = 'block';
            document.getElementById('birthDateDisplay').style.display = 'block';
            document.getElementById('genderDisplay').style.display = 'block';
            document.getElementById('addressDisplay').style.display = 'block';
            document.getElementById('yearLevelDisplay').style.display = 'block';
            document.getElementById('sectionDisplay').style.display = 'block';
            document.getElementById('guardianNameDisplay').style.display = 'block';
            document.getElementById('guardianContactDisplay').style.display = 'block';
            document.getElementById('registrationFormDisplay').style.display = 'block';

        });
    }


    // --- Profile Picture Form ---
    const profilePictureForm = document.getElementById('profilePictureForm');
    const clearProfilePictureBtn = document.getElementById('clearProfilePicture');


    profilePictureForm.addEventListener('submit', (event) => {
        event.preventDefault();

        const profilePictureInput = document.getElementById('profilePicture');
        const profilePictureError = document.getElementById('profilePictureError');
        profilePictureError.textContent = ''; // Clear previous error

        if (profilePictureInput.files.length === 0) {
            profilePictureError.textContent = 'Please select a profile picture.';
            return;
        }

        const file = profilePictureInput.files[0];
        if (!file.type.startsWith('image/')) {
            profilePictureError.textContent = 'Invalid file type. Please upload an image.';
            return;
        }

        // Simulate a successful upload
        // alert('Profile picture updated successfully!');
        // In a real application, you would send the file to the server using AJAX or fetch.
        const reader = new FileReader();
        reader.onload = function (e) {
            const profilePicturePreview = document.querySelector('.profile-picture-preview');
            profilePicturePreview.src = e.target.result;
        };
        reader.readAsDataURL(file);

        const formData = new FormData(profilePictureForm);

        fetch('/api/profile/update/', {
            method: 'POST',
            body: formData,
        })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(errorData => {
                        throw new Error(errorData.detail || 'Failed to update profile picture');
                    });
                }
                return response.json();
            })
            .then(data => {
                alert(data.message);
                profilePictureInput.value = '';

            })
            .catch(error => {
                alert(error.message);
            });

    });

    if (clearProfilePictureBtn) {
        clearProfilePictureBtn.addEventListener('click', () => {
            document.getElementById('profilePicture').value = '';
            document.getElementById('profilePictureError').textContent = '';
        });
    }


    // --- Security Form ---
    const securityForm = document.getElementById('securityForm');
    const clearSecurityFormBtn = document.getElementById('clearSecurityForm');

    securityForm.addEventListener('submit', (event) => {
        event.preventDefault();

        let hasErrors = false;
        const currentPasswordInput = document.getElementById('currentPassword');
        const newPasswordInput = document.getElementById('newPassword');
        const confirmPasswordInput = document.getElementById('confirmPassword');
        const currentPasswordError = document.getElementById('currentPasswordError');
        const newPasswordError = document.getElementById('newPasswordError');
        const confirmPasswordError = document.getElementById('confirmPasswordError');

        currentPasswordError.textContent = '';
        newPasswordError.textContent = '';
        confirmPasswordError.textContent = '';

        if (!currentPasswordInput.value) {
            currentPasswordError.textContent = 'Please enter your current password.';
            hasErrors = true;
        }

        if (newPasswordInput.value) {
            if (newPasswordInput.value.length < 8) {
                newPasswordError.textContent = 'New password must be at least 8 characters long.';
                hasErrors = true;
            }
            if (newPasswordInput.value !== confirmPasswordInput.value) {
                confirmPasswordError.textContent = 'Passwords do not match.';
                hasErrors = true;
            }
        } else if (confirmPasswordInput.value) {
            newPasswordError.textContent = 'Please enter a new password or leave both fields empty.';
            confirmPasswordError.textContent = 'Please confirm your new password.';
            hasErrors = true;
        }

        if (hasErrors) {
            return;
        }

        const formData = new FormData(securityForm);
        fetch('/api/profile/update/', {
            method: 'POST',
            body: formData,
        })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(errorData => {
                        throw new Error(errorData.detail || 'Failed to update security settings');
                    });
                }
                return response.json();
            })
            .then(data => {
                alert('Security settings updated successfully!');
                clearSecurityForm();
            })
            .catch(error => {
                alert(error.message);
            });



    });

    if (clearSecurityFormBtn) {
        clearSecurityFormBtn.addEventListener('click', () => {
            document.getElementById('currentPassword').value = '';
            document.getElementById('newPassword').value = '';
            document.getElementById('confirmPassword').value = '';

            document.getElementById('currentPasswordError').textContent = '';
            document.getElementById('newPasswordError').textContent = '';
            document.getElementById('confirmPasswordError').textContent = '';
        });
    }
});
