/**
 * QuizGen.AI - PDF Upload and AJAX Progress Logic
 */

document.addEventListener('DOMContentLoaded', function() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const fileInfo = document.getElementById('file-info');
    const submitBtn = document.getElementById('submit-btn');
    const form = document.getElementById('pdf-upload-form');
    
    const formContainer = document.getElementById('upload-form-container');
    const loadingContainer = document.getElementById('upload-loading-container');
    const loadingStatus = document.getElementById('loading-status');
    const loadingSubtext = document.getElementById('loading-subtext');
    const progressBar = document.getElementById('loading-progress-bar');
    const progressText = document.getElementById('loading-percentage');

    let selectedFile = null;

    // Trigger click on file input when clicking dropzone
    dropzone.addEventListener('click', () => fileInput.click());

    // Drag-and-drop event handlers
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dragover');
        }, false);
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    function handleFileSelect(file) {
        if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
            showToast('Invalid file format. Only PDF files are supported.', 'danger');
            return;
        }

        // Check size limit: 1 GB
        if (file.size > 1024 * 1024 * 1024) {
            showToast('File size exceeds the 1GB limit.', 'danger');
            return;
        }

        selectedFile = file;
        fileInfo.textContent = `${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} MB)`;
        fileInfo.classList.remove('d-none');
        submitBtn.disabled = false;
        
        // Visual indicator that file is loaded
        dropzone.querySelector('i').className = 'fa-solid fa-circle-check text-success display-4 mb-3';
    }

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        if (!selectedFile) return;

        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('difficulty', document.getElementById('difficulty').value);
        formData.append('num_questions', document.getElementById('num_questions').value);

        // Transition to loading view
        formContainer.classList.add('d-none');
        loadingContainer.classList.remove('d-none');

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/upload', true);
        
        // Attach CSRF Token
        const csrfToken = getCsrfToken();
        if (csrfToken) {
            xhr.setRequestHeader('X-CSRFToken', csrfToken);
        }

        // Monitor upload percentage
        xhr.upload.onprogress = function(event) {
            if (event.lengthComputable) {
                const percent = Math.round((event.loaded / event.total) * 100);
                // Cap upload display at 95% because server-side PDF parsing and AI quiz generation takes time
                const displayPercent = Math.round(percent * 0.5); 
                updateProgress(displayPercent, 'Uploading Document...');
            }
        };

        xhr.onload = function() {
            if (xhr.status === 200) {
                updateProgress(100, 'Quiz Ready!');
                try {
                    const response = JSON.parse(xhr.responseText);
                    if (response.success && response.redirect_url) {
                        setTimeout(() => {
                            window.location.href = response.redirect_url;
                        }, 800);
                    } else {
                        revertToForm(response.error || 'Failed to generate quiz.');
                    }
                } catch (err) {
                    revertToForm('Invalid server response.');
                }
            } else {
                try {
                    const response = JSON.parse(xhr.responseText);
                    revertToForm(response.error || 'Server error occurred during processing.');
                } catch(e) {
                    revertToForm('An unexpected server error occurred.');
                }
            }
        };

        xhr.onerror = function() {
            revertToForm('Network error occurred. Please verify connectivity.');
        };

        // Simulated phases for server parsing to keep user updated
        let phase = 0;
        const fakeProgressInterval = setInterval(() => {
            if (xhr.readyState === 4) {
                clearInterval(fakeProgressInterval);
                return;
            }
            
            // Advance synthetic progress bar for server processing tasks
            phase++;
            if (phase < 5) {
                updateProgress(50 + (phase * 10), 'Extracting text and tables...');
            } else if (phase < 9) {
                updateProgress(90 + (phase - 4), 'Google Gemini AI is creating quiz questions...');
            }
        }, 3000);

        xhr.send(formData);
    });

    function updateProgress(percent, statusText) {
        progressBar.style.width = `${percent}%`;
        progressBar.setAttribute('aria-valuenow', percent);
        progressText.textContent = `${percent}%`;
        loadingStatus.textContent = statusText;
        
        if (percent < 50) {
            loadingSubtext.textContent = 'Transferring document data securely to server...';
        } else if (percent >= 50 && percent < 90) {
            loadingSubtext.textContent = 'Running structural parser and extracting elements...';
        } else if (percent >= 90 && percent < 100) {
            loadingSubtext.textContent = 'Formulating multiple choice alternatives and answer keys...';
        } else {
            loadingSubtext.textContent = 'Initializing test workspace. Redirecting now...';
        }
    }

    function revertToForm(errorMessage) {
        showToast(errorMessage, 'danger');
        
        // Reset controls
        formContainer.classList.remove('d-none');
        loadingContainer.classList.add('d-none');
        
        progressBar.style.width = '0%';
        progressBar.setAttribute('aria-valuenow', 0);
        progressText.textContent = '0%';
        
        // Reset checkmark in dropzone
        dropzone.querySelector('i').className = 'fa-solid fa-file-pdf upload-icon';
        selectedFile = null;
        fileInfo.classList.add('d-none');
        submitBtn.disabled = true;
        fileInput.value = '';
    }
});
