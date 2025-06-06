document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', async (event) => {
                console.log('PAY button clicked and form submitted!');
                event.preventDefault(); // Prevent the default form submission

                // Get the form data.
                const formData = new FormData(form);

                // Use fetch to send the request
                const response = await fetch(form.action, {
                    method: form.method, // Get method from the form
                    body: formData,
                });

                const data = await response.json(); // Parse JSON response

                if (response.ok && data.redirectUrl) {
                    // Redirect the user to PayMaya
                    window.location.href = data.redirectUrl;
                } else {
                    // Handle errors (e.g., show a message to the user)
                    alert('Payment initiation failed. Please try again.');
                    console.error('Error initiating payment:', data);
                }
            });
        });
    });