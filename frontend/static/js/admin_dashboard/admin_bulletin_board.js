/* JavaScript for toggling the create post form */
  const createPostInput = document.querySelector('.create-post-input');
  const createPostForm = document.querySelector('.create-post-form-fields');
  const backToBulletinLink = document.querySelector('.back-to-bulletin');

  if (createPostInput) {
    createPostInput.addEventListener('click', function () {
      this.style.display = 'none';
      createPostForm.style.display = 'block';
      backToBulletinLink.style.display = 'block';
    });
  }

  if (backToBulletinLink) {
    backToBulletinLink.addEventListener('click', function (event) {
      event.preventDefault();
      createPostInput.style.display = 'block';
      createPostForm.style.display = 'none';
      this.style.display = 'none';
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    function toggleEditMode(postId, showEdit) {
        const postCard = document.getElementById(`wiki-post-${postId}`);
        if (postCard) {
            const displayMode = postCard.querySelector('.wiki-post-display-mode');
            const editMode = postCard.querySelector('.wiki-post-edit-mode');

            if (showEdit) {
                if (displayMode) displayMode.style.display = 'none';
                if (editMode) editMode.style.display = 'block';
                postCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
            } else {
                if (displayMode) displayMode.style.display = 'block';
                if (editMode) editMode.style.display = 'none';
            }
        }
    }
  
    const urlParams = new URLSearchParams(window.location.search);
    const editPostId = urlParams.get('edit_wiki_post_id');

    if (editPostId) {
        toggleEditMode(editPostId, true);
    }

    document.querySelectorAll('.wiki-edit-button').forEach(button => {
        button.addEventListener('click', (event) => {
            const postId = event.target.dataset.postId;
            toggleEditMode(postId, true);
        });
    });

    document.querySelectorAll('.cancel-edit-button').forEach(button => {
        button.addEventListener('click', (event) => {
            const postId = event.target.dataset.postId;
            toggleEditMode(postId, false);
        });
    });
    
    document.querySelectorAll('.edit-wiki-post-form').forEach(form => {
        form.addEventListener('submit', async (event) => {
            event.preventDefault(); 
            const postId = form.dataset.postId || form.querySelector('input[name="post_id"]').value; 
            const formData = new FormData(form);

            try {
                const response = await fetch(form.action, { 
                    method: 'POST', 
                    body: formData
                });

                if (response.ok) {
                    alert('Post updated successfully!');
                    toggleEditMode(postId, false);                   
                } else {
                    const errorText = await response.text();
                    alert(`Failed to update post: ${errorText}`);
                }
            } catch (error) {
                console.error('Error submitting edit form:', error);
                alert('An error occurred during submission.');
            }
        });
    });
});
document.addEventListener('DOMContentLoaded', function() {
    const createPostInput = document.querySelector('.create-post-input');
    const createPostFormFields = document.querySelector('.create-post-form-fields');
    const backToBulletinLink = document.querySelector('.back-to-bulletin');

    if (createPostInput && createPostFormFields && backToBulletinLink) {
        createPostInput.addEventListener('click', function() {
            createPostInput.style.display = 'none';
            createPostFormFields.style.display = 'block';
            backToBulletinLink.style.display = 'block';
        });
    }

    const createWikiInput = document.querySelector('.create-wiki-input');
    const createWikiPostForm = document.querySelector('.create-wiki-post-form');
    const cancelCreateWikiButton = document.querySelector('.cancel-create-wiki-button');

    if (createWikiInput && createWikiPostForm && cancelCreateWikiButton) {
        createWikiInput.addEventListener('click', function() {
            createWikiInput.style.display = 'none';
            createWikiPostForm.style.display = 'flex';
            cancelCreateWikiButton.style.display = 'inline-block';
        });

        cancelCreateWikiButton.addEventListener('click', function() {
            createWikiInput.style.display = 'block';
            createWikiPostForm.style.display = 'none';
            cancelCreateWikiButton.style.display = 'none';
            createWikiPostForm.reset();
        });
    }

    const wikiEditButtons = document.querySelectorAll('.wiki-edit-button');
    const cancelEditButtons = document.querySelectorAll('.cancel-edit-button');

    wikiEditButtons.forEach(button => {
        button.addEventListener('click', function() {
            const postId = this.dataset.postId;
            const wikiPostCard = document.getElementById(`wiki-post-${postId}`);
            if (wikiPostCard) {
                const displayMode = wikiPostCard.querySelector('.wiki-post-display-mode');
                const editMode = wikiPostCard.querySelector('.wiki-post-edit-mode');

                if (displayMode && editMode) {
                    displayMode.style.display = 'none';
                    editMode.style.display = 'block';
                }
            }
        });
    });

    cancelEditButtons.forEach(button => {
        button.addEventListener('click', function() {
            const postId = this.dataset.postId;
            const wikiPostCard = document.getElementById(`wiki-post-${postId}`);
            if (wikiPostCard) {
                const displayMode = wikiPostCard.querySelector('.wiki-post-display-mode');
                const editMode = wikiPostCard.querySelector('.wiki-post-edit-mode');

                if (displayMode && editMode) {
                    displayMode.style.display = 'block';
                    editMode.style.display = 'none';
                }
            }
        });
    });
});
