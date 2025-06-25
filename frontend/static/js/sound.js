document.addEventListener('DOMContentLoaded', function() {
    const video = document.getElementById('background-video');
    const soundToggleButton = document.getElementById('soundToggle');
    const soundIcon = soundToggleButton.querySelector('i');

    // Get the initial muted state directly from the video element
    let isMuted = video.muted;

    // Set initial icon based on the video's muted state
    if (isMuted) {
        soundIcon.classList.remove('fa-volume-up');
        soundIcon.classList.add('fa-volume-xmark'); // Using fa-volume-xmark for muted state
    } else {
        soundIcon.classList.remove('fa-volume-xmark');
        soundIcon.classList.add('fa-volume-up');
    }

    soundToggleButton.addEventListener('click', function() {
        if (isMuted) {
            // Currently muted, so unmute
            video.muted = false;
            soundIcon.classList.remove('fa-volume-xmark'); // Remove mute icon
            soundIcon.classList.add('fa-volume-up');    // Add sound on icon
            isMuted = false;
        } else {
            // Currently unmuted, so mute
            video.muted = true;
            soundIcon.classList.remove('fa-volume-up'); // Remove sound on icon
            soundIcon.classList.add('fa-volume-xmark');   // Add mute icon
            isMuted = true;
        }
    });
});