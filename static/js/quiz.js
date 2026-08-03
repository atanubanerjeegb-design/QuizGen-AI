/**
 * QuizGen.AI - Interactive Quiz Taker Module
 */

document.addEventListener('DOMContentLoaded', function() {
    const workspace = document.getElementById('quiz-workspace');
    if (!workspace) return; // Exit if not on quiz taker page
    
    const quizId = workspace.getAttribute('data-quiz-id');
    const questionPanels = document.querySelectorAll('.question-panel');
    const navButtons = document.querySelectorAll('.nav-grid-btn');
    const totalQuestions = questionPanels.length;
    
    // UI Elements
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const skipBtn = document.getElementById('skip-btn');
    const flagBtn = document.getElementById('flag-btn');
    const submitBtn = document.getElementById('submit-quiz-btn');
    const progressRatio = document.getElementById('progress-ratio');
    const progressBar = document.getElementById('quiz-progress-bar');
    const timeDisplay = document.getElementById('time-display');
    const timerBox = document.getElementById('timer-box');

    // Quiz State
    let currentIndex = 0;
    const answers = {};  // Maps Question ID (string) to Option ('A', 'B', 'C', 'D')
    const flagged = {};  // Maps Question ID (string) to Boolean
    
    // Timer Configuration (2 minutes per question)
    let timeRemaining = totalQuestions * 120; 
    let timerInterval = null;

    // Initialize Quiz Taker
    initQuiz();

    function initQuiz() {
        showQuestion(0);
        startTimer();
        setupEventListeners();
        updateProgress();
    }

    function showQuestion(index) {
        if (index < 0 || index >= totalQuestions) return;
        
        // Hide previous active panel
        questionPanels[currentIndex].classList.add('d-none');
        navButtons[currentIndex].classList.remove('active');
        
        // Update index
        currentIndex = index;
        
        // Show current panel
        questionPanels[currentIndex].classList.remove('d-none');
        navButtons[currentIndex].classList.add('active');
        
        // Update button states
        prevBtn.disabled = (currentIndex === 0);
        
        if (currentIndex === totalQuestions - 1) {
            nextBtn.innerHTML = 'Finish Quiz <i class="fa-solid fa-check ms-1"></i>';
            nextBtn.classList.replace('btn-glow-cyan', 'btn-outline-danger');
        } else {
            nextBtn.innerHTML = 'Next <i class="fa-solid fa-chevron-right ms-1"></i>';
            nextBtn.classList.replace('btn-outline-danger', 'btn-glow-cyan');
        }

        // Update Flag button visual state for current question
        const qId = questionPanels[currentIndex].getAttribute('data-question-id');
        if (flagged[qId]) {
            flagBtn.classList.replace('btn-glass-primary', 'btn-warning');
            flagBtn.innerHTML = '<i class="fa-solid fa-flag me-1"></i> Flagged';
        } else {
            flagBtn.classList.replace('btn-warning', 'btn-glass-primary');
            flagBtn.innerHTML = '<i class="fa-regular fa-flag me-1"></i> Flag';
        }
        updateProgress();
    }

    function setupEventListeners() {
        // Option Buttons selection
        questionPanels.forEach((panel, panelIdx) => {
            const qId = panel.getAttribute('data-question-id');
            const options = panel.querySelectorAll('.option-btn');
            
            options.forEach(btn => {
                btn.addEventListener('click', function() {
                    // Remove selected class from sibling buttons in this panel
                    options.forEach(o => o.classList.remove('selected'));
                    
                    // Add selected class to clicked button
                    btn.classList.add('selected');
                    
                    // Record answer in state
                    const selectedVal = btn.getAttribute('data-option');
                    answers[qId] = selectedVal;
                    
                    // Update navigation sidebar state
                    const navBtn = document.getElementById(`nav-btn-${panelIdx}`);
                    if (navBtn) {
                        navBtn.classList.add('answered');
                    }
                    
                    updateProgress();
                });
            });
        });

        // Navigation controls
        prevBtn.addEventListener('click', () => showQuestion(currentIndex - 1));
        
        nextBtn.addEventListener('click', () => {
            if (currentIndex === totalQuestions - 1) {
                confirmAndSubmit();
            } else {
                showQuestion(currentIndex + 1);
            }
        });
        
        skipBtn.addEventListener('click', () => {
            if (currentIndex < totalQuestions - 1) {
                showQuestion(currentIndex + 1);
            }
        });

        // Flag toggle
        flagBtn.addEventListener('click', () => {
            const qId = questionPanels[currentIndex].getAttribute('data-question-id');
            const navBtn = document.getElementById(`nav-btn-${currentIndex}`);
            
            flagged[qId] = !flagged[qId];
            
            if (flagged[qId]) {
                flagBtn.classList.replace('btn-glass-primary', 'btn-warning');
                flagBtn.innerHTML = '<i class="fa-solid fa-flag me-1"></i> Flagged';
                if (navBtn) navBtn.classList.add('flagged');
            } else {
                flagBtn.classList.replace('btn-warning', 'btn-glass-primary');
                flagBtn.innerHTML = '<i class="fa-regular fa-flag me-1"></i> Flag';
                if (navBtn) navBtn.classList.remove('flagged');
            }
        });

        // Review sidebar button links
        navButtons.forEach(btn => {
            btn.addEventListener('click', function() {
                const targetIdx = parseInt(btn.getAttribute('data-index'));
                showQuestion(targetIdx);
            });
        });

        // Manual submit button
        submitBtn.addEventListener('click', confirmAndSubmit);
    }

    function updateProgress() {
        const answeredCount = Object.keys(answers).length;
        const percent = Math.round((answeredCount / totalQuestions) * 100);
        
        progressBar.style.width = `${percent}%`;
        progressBar.setAttribute('aria-valuenow', percent);
        progressRatio.textContent = `${answeredCount}/${totalQuestions} Answered`;
        
        const qNumDisplay = document.getElementById('question-number-display');
        if (qNumDisplay) {
            qNumDisplay.textContent = `Question ${currentIndex + 1} of ${totalQuestions}`;
        }
        
        const remainingDisplay = document.getElementById('remaining-display');
        if (remainingDisplay) {
            remainingDisplay.textContent = `${totalQuestions - answeredCount} Remaining`;
        }
    }

    function startTimer() {
        updateTimerDisplay();
        
        timerInterval = setInterval(() => {
            timeRemaining--;
            updateTimerDisplay();
            
            if (timeRemaining <= 60) {
                timerBox.classList.add('timer-pulsing');
            }
            
            if (timeRemaining <= 0) {
                clearInterval(timerInterval);
                autoSubmitQuiz();
            }
        }, 1000);
    }

    function updateTimerDisplay() {
        const mins = Math.floor(timeRemaining / 60);
        const secs = timeRemaining % 60;
        const timeStr = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        timeDisplay.textContent = timeStr;
        
        const timeLeftDisplay = document.getElementById('time-left-display');
        if (timeLeftDisplay) {
            timeLeftDisplay.textContent = `Time left: ${timeStr}`;
        }
    }

    function confirmAndSubmit() {
        const answeredCount = Object.keys(answers).length;
        let confirmMsg = 'Are you sure you want to submit your answers?';
        
        if (answeredCount < totalQuestions) {
            confirmMsg = `You have only answered ${answeredCount} out of ${totalQuestions} questions. Are you sure you want to submit?`;
        }
        
        if (confirm(confirmMsg)) {
            submitQuizData(false);
        }
    }

    function autoSubmitQuiz() {
        showToast('Time has expired! Submitting your answers automatically.', 'warning');
        setTimeout(() => {
            submitQuizData(true);
        }, 1500);
    }

    function submitQuizData(isAutoSubmit = false) {
        clearInterval(timerInterval);
        
        // Disable submission triggers to prevent duplicate posts
        submitBtn.disabled = true;
        nextBtn.disabled = true;
        prevBtn.disabled = true;
        
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Submitting...';

        const timeSpent = (totalQuestions * 120) - timeRemaining;
        const payload = {
            answers: answers,
            time_spent: timeSpent
        };

        fetch(`/quiz/${quizId}/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Server returned an error status.');
            }
            return response.json();
        })
        .then(data => {
            if (data.success && data.redirect_url) {
                window.location.href = data.redirect_url;
            } else {
                alert(data.error || 'Failed to submit quiz. Please try again.');
                enableControls();
            }
        })
        .catch(err => {
            console.error('Quiz submit error:', err);
            alert('A network connection error occurred while submitting. Try submitting again.');
            enableControls();
        });
    }

    function enableControls() {
        submitBtn.disabled = false;
        nextBtn.disabled = false;
        prevBtn.disabled = (currentIndex === 0);
        submitBtn.innerHTML = '<i class="fa-solid fa-paper-plane me-2"></i> Submit Quiz';
        startTimer(); // Restart timer if submission failed
    }
});
