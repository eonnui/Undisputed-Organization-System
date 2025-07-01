document.addEventListener('DOMContentLoaded', function() {
    const chatPopup = document.getElementById('chat-popup');
    const openChatBtn = document.getElementById('open-chat-button');
    const closeChatBtn = document.getElementById('close-chat');
    const chatInputField = document.getElementById('chat-input-field');
    const sendChatBtn = document.getElementById('send-chat-btn');
    const chatBody = document.getElementById('chat-body');

    // Function to open the chat pop-up
    openChatBtn.addEventListener('click', function() {
        chatPopup.classList.add('open');
        chatBody.scrollTop = chatBody.scrollHeight; // Scroll to bottom
    });

    // Function to close the chat pop-up
    closeChatBtn.addEventListener('click', function() {
        chatPopup.classList.remove('open');
    });

    // Function to send a message
    function sendMessage() {
        const message = chatInputField.value.trim();
        if (message === '') return;

        appendMessage('user', message);
        chatInputField.value = ''; // Clear input field

        const typingIndicator = appendMessage('ai', 'AI is thinking...'); // Add typing indicator

        const pageContent = document.body.outerHTML; // Capture the full HTML content of the body
        const pageData = window.lastFetchedJsonData || null; // Get the last fetched JSON data
        window.lastFetchedJsonData = null; // Clear the data after sending

        // Send message to backend
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message, page_content: pageContent, page_data: pageData }),
        })
        .then(response => response.json())
        .then(data => {
            chatBody.removeChild(typingIndicator); // Remove typing indicator
            appendMessage('ai', data.response);
        })
        .catch(error => {
            chatBody.removeChild(typingIndicator); // Remove typing indicator on error
            console.error('Error:', error);
            appendMessage('ai', 'Sorry, something went wrong.');
        });
    }

    // Function to append messages to the chat body
    function appendMessage(sender, text) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('chat-message', `${sender}-message`);
        messageElement.innerHTML = text.replace(/\n/g, '<br>');
        chatBody.appendChild(messageElement);
        chatBody.scrollTop = chatBody.scrollHeight; // Scroll to bottom
        return messageElement; // Return the created element
    }

    // Event listeners for sending messages
    sendChatBtn.addEventListener('click', sendMessage);
    chatInputField.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});
