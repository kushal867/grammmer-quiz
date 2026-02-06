/* static/quiz/js/quiz.js */
let score = 0;
let currentStreak = 0;
let maxStreak = 0;
let totalQuestions = 0;
let correctAnswers = 0;
let currentQuestionId = null;
let isBookmarked = false;
let quizStartTime = Date.now();
const letters = ["क", "ख", "ग", "घ"];
const letterToNumber = {"क": 1, "ख": 2, "ग": 3, "घ": 4};

// CSRF Helper
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Initialize stats
document.addEventListener('DOMContentLoaded', () => {
    updateStats();
    newQuestion();
    
    // Auto-refresh stats every 5 seconds
    setInterval(updateStats, 5000);

    // Bookmark button listener
    document.getElementById('bookmarkBtn').addEventListener('click', toggleBookmark);
    document.getElementById('rateBtn').addEventListener('click', rateQuestion);
});

function newQuestion() {
    const resultEl = document.getElementById("result");
    const explanationEl = document.getElementById("explanation");
    const questionTextEl = document.getElementById("questionText");
    const optionsEl = document.getElementById("options");
    const domainEl = document.getElementById("domain");
    const difficultyEl = document.getElementById("difficulty");
    const loadingOverlay = document.getElementById("loadingOverlay");
    const bookmarkBtn = document.getElementById('bookmarkBtn');

    if(resultEl) resultEl.innerHTML = "";
    if(explanationEl) explanationEl.style.display = "none";
    if(loadingOverlay) loadingOverlay.style.display = "flex";
    if(optionsEl) optionsEl.innerHTML = "";
    if(domainEl) domainEl.textContent = "विषय: लोड हुँदैछ...";
    if(difficultyEl) {
        difficultyEl.textContent = "सजिलो";
        difficultyEl.className = "difficulty easy";
    }
    if(bookmarkBtn) bookmarkBtn.classList.remove('active');

    fetch("/quiz/api/new/")
        .then((r) => r.json())
        .then((data) => {
            if (data.success) {
                currentQuestionId = data.question_id;
                displayQuestion(data);
                updateStats();
            } else {
                showError("प्रश्न लोड गर्न असफल");
            }
        })
        .catch((err) => {
            showError("सर्भरमा समस्या छ। कृपया पछि प्रयास गर्नुहोस्।");
        })
        .finally(() => {
            if(loadingOverlay) loadingOverlay.style.display = "none";
        });
}

function displayQuestion(data) {
    document.getElementById("questionText").textContent = data.question;
    document.getElementById("domain").textContent = `विषय: ${data.domain} - ${data.topic}`;

    // Set difficulty styling
    const difficultyElem = document.getElementById("difficulty");
    difficultyElem.textContent = data.difficulty;
    difficultyElem.className = `difficulty ${
        data.difficulty === "सजिलो"
        ? "easy"
        : data.difficulty === "मध्यम"
        ? "medium"
        : "hard"
    }`;

    const container = document.getElementById("options");
    container.innerHTML = "";

    letters.forEach((letter) => {
        if (data.options[letter]) {
            const div = document.createElement("div");
            div.className = "opt";
            div.innerHTML = `
                <span class="opt-letter">${letter}</span>
                <span>${data.options[letter]}</span>
            `;
            div.onclick = () => checkAnswer(letter, div);
            container.appendChild(div);
        }
    });
}

function checkAnswer(choice, element) {
    // Prevent multiple clicks
    document.querySelectorAll(".opt").forEach((el) => {
        el.style.pointerEvents = "none";
    });

    fetch("/quiz/api/check/", {
        method: "POST",
        headers: { 
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie('csrftoken')
        },
        body: JSON.stringify({ choice: choice }),
    })
        .then((r) => r.json())
        .then((res) => {
            totalQuestions++;
            
            // Handle bookmark state from server
            if (res.is_bookmarked) {
                document.getElementById('bookmarkBtn').classList.add('active');
            }

            if (res.correct) {
                element.classList.add("correct");
                document.getElementById("result").innerHTML =
                    '<div style="color:#22c55e;"><i class="fas fa-check-circle"></i> सही जवाफ!</div>';
                score++;
                currentStreak++;
                correctAnswers++;
                maxStreak = Math.max(maxStreak, currentStreak);
            } else {
                element.classList.add("wrong");
                currentStreak = 0;

                const correctAns = res.correct_answer;
                document.getElementById("result").innerHTML = `
                    <div style="color:#ef4444;"><i class="fas fa-times-circle"></i> गलत!</div>
                    <div style="color:#f59e0b; margin-top:10px; font-size:2rem;">
                        सही जवाफ: <b>${correctAns}) ${res.correct_text}</b>
                    </div>
                `;

                // Highlight correct answer
                document.querySelectorAll(".opt").forEach((opt) => {
                    if (opt.querySelector(".opt-letter").textContent === correctAns) {
                        opt.classList.add("correct");
                    }
                });
            }

            // Always show explanation
            if (res.explanation) {
                const explEl = document.getElementById("explanation");
                const explTextEl = document.getElementById("explanationText");
                explTextEl.textContent = res.explanation;
                explEl.style.display = "block";
            }

            updateStats();
        })
        .catch((err) => {
            console.error(err);
            document.getElementById("result").innerHTML =
                '<div style="color:#ef4444;">जवाफ जाँच गर्न असफल</div>';
        });
}

function toggleBookmark() {
    if (!currentQuestionId) return;
    
    const btn = document.getElementById('bookmarkBtn');
    const isAdding = !btn.classList.contains('active');
    const url = isAdding ? "/quiz/api/bookmark/" : "/quiz/api/bookmark/remove/";
    
    fetch(url, {
        method: "POST",
        headers: { 
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie('csrftoken')
        },
        body: JSON.stringify({ question_id: currentQuestionId }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            btn.classList.toggle('active');
            // Visual feedback
            const icon = btn.querySelector('i');
            icon.classList.add('fa-beat');
            setTimeout(() => icon.classList.remove('fa-beat'), 500);
        } else if (data.error && data.error.includes('login')) {
            alert("कृपया बुकमार्क गर्न लगइन गर्नुहोस्।");
        }
    })
    .catch(err => console.error("Bookmark error:", err));
}

function rateQuestion() {
    if (!currentQuestionId) return;
    
    const rating = prompt("यस प्रश्नलाई ५ मा कति अंक दिनुहुन्छ? (1-5)", "5");
    if (!rating || rating < 1 || rating > 5) return;
    
    fetch("/quiz/api/rate-question/", {
        method: "POST",
        headers: { 
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie('csrftoken')
        },
        body: JSON.stringify({ 
            question_id: currentQuestionId,
            rating: parseInt(rating)
        }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            alert("प्रतिक्रियाको लागि धन्यवाद!");
            document.getElementById('rateBtn').classList.add('active');
        }
    })
    .catch(err => console.error("Rating error:", err));
}

function updateStats() {
    const scoreEl = document.getElementById("score");
    if(scoreEl) scoreEl.textContent = score;

    const streakDisplay = document.getElementById("streakDisplay");
    if(streakDisplay) streakDisplay.textContent = currentStreak;

    const totalQuestionsEl = document.getElementById("totalQuestions");
    if(totalQuestionsEl) totalQuestionsEl.textContent = totalQuestions;

    const currentStreakEl = document.getElementById("currentStreak");
    if(currentStreakEl) currentStreakEl.textContent = currentStreak;

    const maxStreakEl = document.getElementById("maxStreak");
    if(maxStreakEl) maxStreakEl.textContent = maxStreak;

    const accuracy = totalQuestions > 0
        ? Math.round((correctAnswers / totalQuestions) * 100)
        : 0;
    
    const accuracyEl = document.getElementById("accuracy");
    if(accuracyEl) accuracyEl.textContent = accuracy + "%";

    // Update progress bar
    const progressBar = document.getElementById("progressBar");
    if(progressBar) progressBar.style.width = accuracy + "%";
}

function resetQuiz() {
    if (confirm("के तपाईं क्विज रिसेट गर्न चाहनुहुन्छ? तपाईंको सबै डाटा हराउनेछ।")) {
        fetch("/quiz/api/reset/", { method: "POST" })
            .then((r) => r.json())
            .then((() => {
                score = 0;
                currentStreak = 0;
                maxStreak = 0;
                totalQuestions = 0;
                correctAnswers = 0;
                updateStats();
                newQuestion();
            }));
    }
}

function showError(message) {
    document.getElementById("questionText").innerHTML = 
        `<div style="color:#ef4444; font-size:1.6rem;"><i class="fas fa-exclamation-triangle"></i> ${message}</div>`;
}

function exportStats() {
    const accuracy = totalQuestions > 0 ? Math.round((correctAnswers / totalQuestions) * 100) : 0;
    const timeElapsed = Math.floor((Date.now() - quizStartTime) / 1000);
    const minutes = Math.floor(timeElapsed / 60);
    const seconds = timeElapsed % 60;
    
    const statsText = `
═══════════════════════════════════════
लोकसेवा क्विज मास्टर - Statistics Report
कुशल सापकोटा द्वारा निर्मित
═══════════════════════════════════════

Quiz Session Summary
-------------------
Date: ${new Date().toLocaleDateString('ne-NP')}
Time: ${new Date().toLocaleTimeString('ne-NP')}
Duration: ${minutes}m ${seconds}s

Performance Metrics
-------------------
Total Questions: ${totalQuestions}
Correct Answers: ${correctAnswers}
Wrong Answers: ${totalQuestions - correctAnswers}
Accuracy: ${accuracy}%
Current Score: ${score}

Streak Information
-------------------
Current Streak: ${currentStreak}
Maximum Streak: ${maxStreak}

═══════════════════════════════════════
Keep practicing! लोकसेवा जित्ने बाटो यहीँबाट सुरु हुन्छ
═══════════════════════════════════════
    `;
    
    // Create and download file
    const blob = new Blob([statsText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `quiz-stats-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function shareScore() {
    const accuracy = totalQuestions > 0 ? Math.round((correctAnswers / totalQuestions) * 100) : 0;
    const text = `मैले लोकसेवा क्विज मास्टरमा ${totalQuestions} मध्ये ${correctAnswers} प्रश्नको सही जवाफ दिएँ (${accuracy}% सटिकता)! तपाईं पनि आफ्नो लोकसेवा तयारी परीक्षण गर्नुहोस्। #Loksewa #Nepal #Quiz`;
    
    if (navigator.share) {
        navigator.share({
            title: 'लोकसेवा क्विज मास्टर',
            text: text,
            url: window.location.href
        }).catch(err => console.error("Sharing failed:", err));
    } else {
        // Fallback: Copy to clipboard
        navigator.clipboard.writeText(text + " " + window.location.href)
            .then(() => alert("स्कोर क्लिपबोर्डमा प्रतिलिपि गरियो!"))
            .catch(() => alert("साझा गर्न असफल।"));
    }
}


// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    const key = e.key.toLowerCase();
    
    // Number keys 1-4 for selecting options
    if (['1', '2', '3', '4'].includes(key)) {
        const optionIndex = parseInt(key) - 1;
        const options = document.querySelectorAll('.opt');
        if (options[optionIndex] && options[optionIndex].style.pointerEvents !== 'none') {
            options[optionIndex].click();
        }
    }
    
    // N for next question
    if (key === 'n') {
        const nextBtn = document.getElementById('nextBtn');
        if(nextBtn) nextBtn.click();
    }
    
    // R for reset
    if (key === 'r') {
        const resetBtn = document.getElementById('resetBtn');
        if(resetBtn) resetBtn.click();
    }
    
    // E for export
    if (key === 'e') {
        exportStats();
    }

    // B for bookmark
    if (key === 'b') {
        toggleBookmark();
    }
});
