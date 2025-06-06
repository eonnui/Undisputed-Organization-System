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