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
                heartCountSpan.textContent = data.heart_count;

                if (data.is_hearted_by_user) {
                    this.classList.add('hearted');
                } else {
                    this.classList.remove('hearted');
                }
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

    function fetchRulesWiki() {
        const rulesWikiContainer = document.querySelector('.wiki-posts-list');
        rulesWikiContainer.innerHTML = '<p>Loading rules and wiki entries...</p>'; 

        fetch('/BulletinBoard')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.text(); 
            })
            .then(htmlString => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(htmlString, 'text/html');
                const newRulesWikiContent = doc.querySelector('.wiki-posts-list');

                if (newRulesWikiContent) {
                    rulesWikiContainer.innerHTML = newRulesWikiContent.innerHTML;
                } else {
                    rulesWikiContainer.innerHTML = '<p>Error: Could not load rules and wiki entries.</p>';
                }
            })
            .catch(error => {
                console.error('Error fetching rules and wiki:', error);
                rulesWikiContainer.innerHTML = '<p>Failed to load rules and wiki entries.</p>';
            });
    }
    
    fetchRulesWiki();
});