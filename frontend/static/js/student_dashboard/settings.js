console.log("----- settings.js script loaded! -----");

document.addEventListener("DOMContentLoaded", () => {
  console.log("DOMContentLoaded event fired! Initializing script...");

  const studentInfoForm = document.getElementById("studentInfoForm");
  const profilePictureForm = document.getElementById("profilePictureForm");
  const securityForm = document.getElementById("securityForm");
  const registrationFormOnly = document.getElementById("registrationFormOnly");

  const clearStudentInfoFormBtn = document.getElementById(
    "clearStudentInfoForm"
  );

  const clearSecurityFormBtn = document.getElementById("clearSecurityForm");

  const registrationStatusDisplay =
    document.getElementById("registrationStatus");

  function setRegistrationStatus(status) {
    if (registrationStatusDisplay) {
      registrationStatusDisplay.textContent =
        status === "Verified" ? "Verified" : "Not Verified";
      registrationStatusDisplay.className =
        status === "Verified" ? "verified" : "unverified";
    }
  }

  function makeFieldEditable(displayElementId, inputElementId) {
    const displayElement = document.getElementById(displayElementId);
    const inputElement = document.getElementById(inputElementId);

    // Corrected: Extract the base name and then apply proper casing for the edit icon ID
    // Example: "birthDateDisplay" -> "birthDate" -> "editBirthDate"
    const baseName = displayElementId.replace("Display", "");
    const editIconId = "edit" + baseName.charAt(0).toUpperCase() + baseName.slice(1); // Capitalize first letter of baseName
    const editIcon = document.getElementById(editIconId);

    // Check if all necessary elements are found before proceeding
    if (!displayElement) {
      console.error(`Error: Display element with ID '${displayElementId}' not found.`);
      return;
    }
    if (!inputElement) {
      console.error(`Error: Input element with ID '${inputElementId}' not found.`);
      return;
    }
    if (!editIcon) {
      // This is the error you were seeing!
      console.error(`Error: Edit icon element with ID '${editIconId}' not found.`);
      return;
    }

    // --- Rest of your makeFieldEditable function (from previous solution) ---
    // Hide the display element and show the input element
    displayElement.classList.add("hidden");
    inputElement.classList.remove("hidden");
    inputElement.focus();

    // Optionally hide the edit icon while in edit mode
    editIcon.classList.add("hidden");

    // Add a blur event listener to revert back when the input loses focus
    function handleBlur() {
      let displayValue = inputElement.value;

      // Handle date formatting if applicable
      if (inputElement.type === "date" && inputElement.value) {
        try {
          displayValue = new Date(inputElement.value).toLocaleDateString(
            "en-US",
            { year: "numeric", month: "2-digit", day: "2-digit" }
          );
        } catch (e) {
          displayValue = inputElement.value;
        }
      } else if (inputElement.tagName === "SELECT") {
          displayValue = inputElement.options[inputElement.selectedIndex].textContent;
          if (displayValue === "Select Gender" || displayValue.trim() === "") {
              displayValue = "--";
          }
      } else if (displayValue.trim() === "") {
          displayValue = "--";
      }

      displayElement.textContent = displayValue;

      displayElement.classList.remove("hidden");
      inputElement.classList.add("hidden");
      editIcon.classList.remove("hidden");

      inputElement.removeEventListener("blur", handleBlur);
    }

    inputElement.addEventListener("blur", handleBlur);
  }

  function showError(inputElementId, message) {
    const errorElement = document.getElementById(inputElementId + "Error");
    const smallTextElement = document.getElementById(
      inputElementId + "SmallText"
    );

    if (errorElement) {
      errorElement.textContent = message;
    }
    if (smallTextElement) {
      smallTextElement.style.display = "block";
      smallTextElement.style.color = "red";
    }
  }

  function clearError(inputElementId) {
    const errorElement = document.getElementById(inputElementId + "Error");
    const smallTextElement = document.getElementById(
      inputElementId + "SmallText"
    );

    if (errorElement) {
      errorElement.textContent = "";
    }
    if (smallTextElement) {
      smallTextElement.style.display = "none";
      smallTextElement.style.color = "var(--org-text-secondary)";
    }
  }

  function validateInput(inputElement, validationRules) {
    let isValid = true;
    clearError(inputElement.id);

    for (const rule of validationRules) {
      if (rule.check(inputElement.value, inputElement)) {
        showError(inputElement.id, rule.message);
        isValid = false;
        break;
      }
    }
    return isValid;
  }

  function resetForm(form) {
    console.log(
      `resetForm called for form: ${form ? form.id : "unknown form"}`
    );

    form
      .querySelectorAll(".error-message")
      .forEach((error) => (error.textContent = ""));
    form.querySelectorAll('[id$="SmallText"]').forEach((smallText) => {
      smallText.style.display = "none";
      smallText.style.color = "var(--org-text-secondary)";
    });

    if (form.id === "studentInfoForm") {
      const editableInputIds = [
        "birthDate",
        "gender",
        "guardianName",
        "guardianContact",
      ];
      editableInputIds.forEach((id) => {
        const inputElement = document.getElementById(id);
        if (inputElement) {
          inputElement.value = "";
        }
      });

      const displayInputPairs = [
        ["birthDateDisplay", "birthDate"],
        ["genderDisplay", "gender"],
        ["guardianNameDisplay", "guardianName"],
        ["guardianContactDisplay", "guardianContact"],
      ];
      displayInputPairs.forEach(([displayId, inputId]) => {
        const displayElement = document.getElementById(displayId);
        const inputElement = document.getElementById(inputId);
        if (displayElement && inputElement) {
          displayElement.style.display = "block";
          inputElement.style.display = "none";

          if (inputElement.value === "") {
            displayElement.textContent = "";
          }
        }
      });
    } else if (form.id === "securityForm") {
      form.querySelectorAll("input, select").forEach((input) => {
        if (input.type === "file") {
          input.value = "";
          if (form.id === "profilePictureForm") {
            console.log(
              `--- ProfilePictureForm: Cleared file input: ${input.id}`
            );
          }
        } else if (input.type !== "button") {
          input.value = "";
        }
      });

      if (form.id === "profilePictureForm") {
        const profilePicturePreview = form.querySelector(
          ".profile-picture-preview"
        );

        console.log(
          "--- ProfilePictureForm: resetForm specific logic complete."
        );
      }

      if (form.id === "registrationFormOnly") {
        const registrationFormDisplay = document.getElementById(
          "registrationFormDisplay"
        );
        const registrationFormOnlyUpload = document.getElementById(
          "registrationFormOnlyUpload"
        );
        if (registrationFormDisplay && registrationFormOnlyUpload) {
          registrationFormDisplay.textContent = "";
          registrationFormDisplay.style.display = "block";
          registrationFormOnlyUpload.style.display = "block";
        }
      }
    }
  }

  function handleFormSubmit(event, formId, successCallback, errorCallback) {
    event.preventDefault();
    const form = document.getElementById(formId);
    if (!form) return;

    let hasErrors = false;

    form
      .querySelectorAll(".error-message")
      .forEach((error) => (error.textContent = ""));
    form.querySelectorAll('[id$="SmallText"]').forEach((smallText) => {
      smallText.style.display = "none";
      smallText.style.color = "var(--org-text-secondary)";
    });

    if (formId === "studentInfoForm") {
      const birthDateInput = document.getElementById("birthDate");
      const genderInput = document.getElementById("gender");
      const guardianNameInput = document.getElementById("guardianName");
      const guardianContactInput = document.getElementById("guardianContact");

      const today = new Date();
      const minAgeDate = new Date(
        today.getFullYear() - 16,
        today.getMonth(),
        today.getDate()
      );

      if (
        !validateInput(birthDateInput, [
          { check: (val) => !val, message: "Please enter your birth date." },
          {
            check: (val) => new Date(val) > today,
            message: "Birth date cannot be in the future.",
          },
          {
            check: (val) => new Date(val) > minAgeDate,
            message: "Student must be at least 16 years old.",
          },
        ])
      )
        hasErrors = true;

      if (
        !validateInput(genderInput, [
          { check: (val) => !val, message: "Please select your gender." },
        ])
      )
        hasErrors = true;

      if (
        !validateInput(guardianNameInput, [
          {
            check: (val) => !val.trim(),
            message: "Please enter your guardian name.",
          },
        ])
      )
        hasErrors = true;

      if (
        !validateInput(guardianContactInput, [
          {
            check: (val) => !val.trim(),
            message: "Please enter your guardian contact.",
          },
          {
            check: (val) => !/^\d{10,15}$/.test(val),
            message: "Invalid contact number format.",
          },
        ])
      )
        hasErrors = true;
    } else if (formId === "profilePictureForm") {
      const profilePictureInput = document.getElementById("profilePicture");
      if (
        !validateInput(profilePictureInput, [
          {
            check: (val, input) => input.files.length === 0,
            message: "Please select a profile picture.",
          },
          {
            check: (val, input) =>
              input.files[0] && input.files[0].size > 2 * 1024 * 1024,
            message: "File size must be less than 2MB.",
          },
          {
            check: (val, input) =>
              input.files[0] &&
              !["image/jpeg", "image/png", "image/gif"].includes(
                input.files[0].type
              ),
            message: "Only JPG, PNG, GIF formats are allowed.",
          },
        ])
      )
        hasErrors = true;
    } else if (formId === "securityForm") {
      const currentPasswordInput = document.getElementById("currentPassword");
      const newPasswordInput = document.getElementById("newPassword");
      const confirmPasswordInput = document.getElementById("confirmPassword");

      if (
        !validateInput(currentPasswordInput, [
          {
            check: (val) => !val,
            message: "Please enter your current password.",
          },
        ])
      )
        hasErrors = true;

      if (newPasswordInput.value) {
        if (
          !validateInput(newPasswordInput, [
            {
              check: (val) => val.length < 8,
              message: "New password must be at least 8 characters long.",
            },
            {
              check: (val) => !/[A-Z]/.test(val),
              message: "New password must contain at least one capital letter.",
            },
            {
              check: (val) => !/[0-9]/.test(val),
              message: "New password must contain at least one number.",
            },
            {
              check: (val) => !/[!@#$%^&*(),.?":{}|<>]/.test(val),
              message:
                "New password must contain at least one special character.",
            },
          ])
        )
          hasErrors = true;

        if (
          !validateInput(confirmPasswordInput, [
            { check: (val) => !val, message: "Confirm password is required." },
            {
              check: (val) => val !== newPasswordInput.value,
              message: "Passwords do not match.",
            },
          ])
        )
          hasErrors = true;
      } else {
        clearError("newPassword");
        clearError("confirmPassword");
      }
    } else if (formId === "registrationFormOnly") {
      const registrationFormInput = document.getElementById(
        "registrationFormOnlyUpload"
      );
      if (
        !validateInput(registrationFormInput, [
          {
            check: (val, input) => input.files.length === 0,
            message: "Please upload your registration form.",
          },
          {
            check: (val, input) =>
              input.files[0] && input.files[0].size > 5 * 1024 * 1024,
            message: "File size must be less than 5MB.",
          },
          {
            check: (val, input) =>
              input.files[0] &&
              !["application/pdf"].includes(input.files[0].type),
            message: "Only PDF files are allowed.",
          },
        ])
      )
        hasErrors = true;
    }

    if (!hasErrors) {
      let fetchUrl = "";
      if (formId === "securityForm") {
        fetchUrl = "/api/auth/change-password";
      } else {
        fetchUrl = "/api/profile/update/";
      }

      fetch(fetchUrl, { method: "POST", body: new FormData(form) })
        .then((response) => {
          console.log("Fetch Response:", response);
          if (!response.ok) {
            return response.json().then((errorData) => {
              console.error("Fetch Error Data:", errorData);
              if (formId === "securityForm" && errorData.detail) {
                if (Array.isArray(errorData.detail)) {
                  errorData.detail.forEach((err) => {
                    const fieldName = err.loc[1];
                    const errorMessage = err.msg;
                    if (fieldName === "current_password") {
                      showError("currentPassword", errorMessage);
                    } else if (fieldName === "new_password") {
                      showError("newPassword", errorMessage);
                    } else if (fieldName === "confirm_password") {
                      showError("confirmPassword", errorMessage);

                      if (errorData.detail === "Passwords do not match.") {
                        showError("confirmPassword", "Passwords do not match.");
                      }
                    } else {
                      alert(errorMessage);
                    }
                  });
                } else if (typeof errorData.detail === "string") {
                  alert(errorData.detail);
                } else {
                  alert("An unexpected error occurred during password change.");
                }
              }
              throw new Error(
                "Validation errors or other server errors occurred."
              );
            });
          }
          return response.json();
        })
        .then((data) => {
          console.log("Fetch Success Data:", data);
          successCallback(data, form);
        })
        .catch((error) => {
          console.error("Fetch Error:", error);
          if (
            formId !== "securityForm" ||
            !error.message.includes(
              "Validation errors or other server errors occurred."
            )
          ) {
            errorCallback(error);
          }
        });
    }
  }

  function handleStudentInfoSuccess(data, form) {
    alert("Profile information updated successfully!");
    resetForm(form);
    if (data && data.user) updateStudentInfoDisplay(data.user);
  }

  function handleProfilePictureSuccess(data, form) {
    alert("Profile picture updated successfully!");

    const profilePicturePreview = document.querySelector(
      ".profile-picture-preview"
    );
    if (profilePicturePreview && data.user.profile_picture)
      profilePicturePreview.src = data.user.profile_picture;
  }

  function handleSecuritySuccess(data, form) {
    alert("Security settings updated successfully!");
    resetForm(form);
  }

  function handleRegistrationFormOnlySuccess(data, form) {
    alert("Registration form updated successfully!");
    const registrationFormDisplayElement = document.getElementById(
      "registrationFormDisplay"
    );

    if (
      registrationFormDisplayElement &&
      data.user &&
      data.user.registration_form
    ) {
      const pathParts = data.user.registration_form.split("/");
      registrationFormDisplayElement.textContent =
        pathParts[pathParts.length - 1];
    } else if (registrationFormDisplayElement) {
      registrationFormDisplayElement.textContent = "";
    }

    if (data.user && data.user.verification_status) {
      setRegistrationStatus(data.user.verification_status);
    }
  }

  function handleError(error) {
    alert(error.message);
  }

  const fieldConfigs = [
    {
      id: "studentNumber",
      displayId: "studentNumberDisplay",
      prop: "student_number",
    },
    { id: "firstName", displayId: "firstNameDisplay", prop: "first_name" },
    { id: "lastName", displayId: "lastNameDisplay", prop: "last_name" },
    { id: "email", displayId: "emailDisplay", prop: "email" },
    {
      id: "birthDate",
      displayId: "birthDateDisplay",
      prop: "birthdate",
      isDate: true,
    },
    { id: "gender", displayId: "genderDisplay", prop: "sex" },
    { id: "address", displayId: "addressDisplay", prop: "address" },
    { id: "yearLevel", displayId: "yearLevelDisplay", prop: "year_level" },
    { id: "section", displayId: "sectionDisplay", prop: "section" },
    {
      id: "guardianName",
      displayId: "guardianNameDisplay",
      prop: "guardian_name",
    },
    {
      id: "guardianContact",
      displayId: "guardianContactDisplay",
      prop: "guardian_contact",
    },
  ];

  function updateStudentInfoDisplay(userData) {
    fieldConfigs.forEach((config) => {
      const inputValue = userData[config.prop] || "";
      const displayElement = document.getElementById(config.displayId);
      const inputElement = document.getElementById(config.id);

      if (displayElement) {
        displayElement.textContent =
          config.isDate && inputValue
            ? new Date(inputValue).toLocaleDateString("en-US", {
                year: "numeric",
                month: "2-digit",
                day: "2-digit",
              })
            : inputValue;
      }
      if (inputElement) {
        inputElement.value = inputValue;
      }
    });
    if (userData.verification_status) {
      setRegistrationStatus(userData.verification_status);
    }
  }

  const editBirthDateBtn = document.getElementById("editBirthDate");
  const editGenderBtn = document.getElementById("editGender");
  const editGuardianNameBtn = document.getElementById("editGuardianName");
  const editGuardianContactBtn = document.getElementById("editGuardianContact");

  if (editBirthDateBtn)
    editBirthDateBtn.addEventListener("click", () =>
      makeFieldEditable("birthDateDisplay", "birthDate")
    );
  if (editGenderBtn)
    editGenderBtn.addEventListener("click", () =>
      makeFieldEditable("genderDisplay", "gender")
    );
  if (editGuardianNameBtn)
    editGuardianNameBtn.addEventListener("click", () =>
      makeFieldEditable("guardianNameDisplay", "guardianName")
    );
  if (editGuardianContactBtn)
    editGuardianContactBtn.addEventListener("click", () =>
      makeFieldEditable("guardianContactDisplay", "guardianContact")
    );

  if (studentInfoForm)
    studentInfoForm.addEventListener("submit", (event) =>
      handleFormSubmit(
        event,
        "studentInfoForm",
        handleStudentInfoSuccess,
        handleError
      )
    );
  if (profilePictureForm)
    profilePictureForm.addEventListener("submit", (event) =>
      handleFormSubmit(
        event,
        "profilePictureForm",
        handleProfilePictureSuccess,
        handleError
      )
    );
  if (securityForm)
    securityForm.addEventListener("submit", (event) =>
      handleFormSubmit(
        event,
        "securityForm",
        handleSecuritySuccess,
        handleError
      )
    );
  if (registrationFormOnly)
    registrationFormOnly.addEventListener("submit", (event) =>
      handleFormSubmit(
        event,
        "registrationFormOnly",
        handleRegistrationFormOnlySuccess,
        handleError
      )
    );

  if (clearStudentInfoFormBtn)
    clearStudentInfoFormBtn.addEventListener("click", () => {
      console.log("Clearing studentInfoForm...");
      resetForm(studentInfoForm);
    });

  if (clearSecurityFormBtn)
    clearSecurityFormBtn.addEventListener("click", () => {
      console.log("Clearing securityForm...");
      resetForm(securityForm);
    });
});
