document.addEventListener('DOMContentLoaded', () => {
    const eventTags = document.querySelectorAll('.event-tag');

    eventTags.forEach(tag => {
        const imageOnHover = tag.querySelector('.image-on-hover');
        if (imageOnHover) {
            imageOnHover.style.display = 'none';

            tag.addEventListener('mouseenter', () => {
                imageOnHover.style.display = 'block';
                imageOnHover.style.position = 'absolute';
                imageOnHover.style.zIndex = '10';
                imageOnHover.style.maxWidth = '200px';
                imageOnHover.style.height = 'auto';
                imageOnHover.style.border = '1px solid #ccc';
                imageOnHover.style.borderRadius = '8px';
                imageOnHover.style.boxShadow = '0 4px 8px rgba(0,0,0,0.2)';
            });

            tag.addEventListener('mouseleave', () => {
                imageOnHover.style.display = 'none';
            });
        }
    });
});
