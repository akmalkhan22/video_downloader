
const downloadForm = document.getElementById('downloadForm');
const spinner = document.getElementById('loader');
const errorMessage = document.getElementById('errorMessage');

// Function to get CSRF token from cookies
function getCSRFToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
            return value;
        }
    }
    return null;
}

// Handle form submission
downloadForm.addEventListener('submit', async function (event) {
    event.preventDefault();
     spinner.classList.remove('d-none'); // Show spinner
    errorMessage.classList.add('d-none'); // Hide error message

    const videoUrl = document.getElementById('videoUrl').value;
    const videoQuality = document.getElementById('videoQuality').value;
    const csrfToken = getCSRFToken();

    try {
        const response = await fetch('/download/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken,
            },
            body: new URLSearchParams({ video_url: videoUrl, video_quality: videoQuality }),
        });

        if (response.ok) {
            // Trigger automatic download
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = response.headers.get('Content-Disposition').split('filename=')[1];
            document.body.appendChild(link);
            link.click();
            link.remove();
        } else {
            const data = await response.json();
            errorMessage.textContent = data.error || 'An error occurred.';
            errorMessage.classList.remove('d-none');
        }
    } catch (error) {
        console.error(error);
        errorMessage.textContent = 'An unexpected error occurred.';
        errorMessage.classList.remove('d-none');
    } finally {
     spinner.classList.add('d-none'); // Hide spinner
    }
});
