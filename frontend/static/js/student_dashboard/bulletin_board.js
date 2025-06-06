document.addEventListener('DOMContentLoaded', function() {
    const heartButtons = document.querySelectorAll('.heart-button');

    heartButtons.forEach(button => {
        button.addEventListener('click', function() {
            const postId = this.dataset.postId;
            const heartCountSpan = this.querySelector('.heart-count');
            const isHeartedInitially = this.classList.contains('hearted');
            const action = isHeartedInitially ? 'unheart' : 'heart';

            let currentCount = parseInt(heartCountSpan.textContent);
            if (action === 'heart') {
                this.classList.add('hearted');
                heartCountSpan.textContent = currentCount + 1;
            } else {
                this.classList.remove('hearted');
                heartCountSpan.textContent = Math.max(0, currentCount - 1);
            }

            fetch(`/bulletin/heart/${postId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `action=${action}`,
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // *** CRUCIAL FIXES START HERE ***
                heartCountSpan.textContent = data.heart_count;

                if (data.is_hearted_by_user) {
                    this.classList.add('hearted');
                } else {
                    this.classList.remove('hearted');
                }
                // *** CRUCIAL FIXES END HERE ***
            })
            .catch(error => {
                console.error('Error hearting post:', error);
                if (action === 'heart') {
                    this.classList.remove('hearted');
                    heartCountSpan.textContent = currentCount;
                } else {
                    this.classList.add('hearted');
                    heartCountSpan.textContent = currentCount;
                }
            });
        });
    });
});