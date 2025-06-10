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