/* static/assistant/js/writer.js */

// Text history management
let textHistory = [];
let historyIndex = -1;
let lastTransformedText = '';

document.addEventListener('DOMContentLoaded', () => {
    // Add initial state to history
    addToHistory('');
    
    // Initialize word count
    updateWordCount();
    
    // Attach event listeners
    const textInput = document.getElementById('textInput');
    if(textInput) {
        textInput.addEventListener('input', () => {
            updateWordCount();
            // Optional: Debounce history addition here if intended to save every keystroke, 
            // but for now we follow original logic which might rely on manual changes or specific trigger points
            // Original code didn't auto-save to history on input, only on load? 
            // Wait, original code had: addToHistory('') on load. 
            // And didn't seem to have auto-add on input? 
            // Let's add debounced history saving for better UX
        });
        
        textInput.addEventListener("keydown", (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === "Enter") submitText();
        });
    }

    // Keyboard shortcuts for undo/redo
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
            e.preventDefault();
            undo();
        }
        if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
            e.preventDefault();
            redo();
        }
    });

    // Capture input for history when user stops typing (simple debounce)
    let timeout = null;
    if(textInput) {
        textInput.addEventListener('input', () => {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                const currentVal = textInput.value;
                if(currentVal !== textHistory[historyIndex]) {
                    addToHistory(currentVal);
                }
            }, 1000);
        });
    }
});

function submitText() {
    const text = document.getElementById("textInput").value.trim();
    const task = document.getElementById("taskSelect").value;
    const output = document.getElementById("output");
    const btn = document.getElementById("main-btn");
    const overlay = document.getElementById("loadingOverlay");
    const loadingBar = document.getElementById("loadingBar");

    if (!text) {
        output.innerHTML = `<em style="color:#fb923c; opacity:0.9;">Please enter some text first</em>`;
        return;
    }

    // Show overlay
    if(overlay) {
        overlay.style.display = 'flex';
        loadingBar.style.width = '10%';
        let progress = 10;
        const interval = setInterval(() => {
            if(progress < 90) {
                progress += Math.random() * 5;
                loadingBar.style.width = progress + '%';
            }
        }, 800);
        window.currentLoadingInterval = interval;
    }

    output.innerHTML = `<span style="color:var(--primary); font-weight:600;"><i class="fas fa-brain" style="margin-right:8px;"></i>Kushal is thinking deeply...</span>`;
    btn.disabled = true;
    btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i><span>Working...</span>`;

    const apiUrl = window.IMPROVE_API_URL || "/assistant/api/improve/";

    fetch(apiUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({ text, task }),
    })
    .then((r) => r.json())
    .then((data) => {
        if (data.result) {
            window.lastTransformedText = data.result;
            output.innerHTML = `
            <div style="position:relative;">
            ${data.result.replace(/\n/g, "<br>")}
            </div>`;
            const exportBtn = document.getElementById('exportBtn');
            if(exportBtn) exportBtn.disabled = false;
            
            // If in comparison mode, update views
            if(document.getElementById('compareWrapper').style.display === 'grid') {
                document.getElementById('compareEnhanced').innerText = data.result;
            }
        } else {
            output.textContent = "Error: " + (data.error || "Please try again");
        }
    })
    .catch((err) => {
        console.error(err);
        output.textContent = "Network error - check if Ollama is running";
    })
    .finally(() => {
        btn.disabled = false;
        btn.innerHTML = `<i class="fas fa-wand-magic-sparkles"></i><span>Transform Text</span>`;
        if(overlay) {
            loadingBar.style.width = '100%';
            setTimeout(() => {
                overlay.style.display = 'none';
                clearInterval(window.currentLoadingInterval);
            }, 500);
        }
    });
}

function copy(btn) {
    const text =
        btn.parentNode.firstChild.textContent ||
        btn.parentNode.innerText.replace("Copy", "").trim();
    navigator.clipboard.writeText(text);
    const icon = btn.innerHTML;
    btn.innerHTML = `<i class="fas fa-check"></i> Copied!`;
    setTimeout(() => (btn.innerHTML = icon), 2000);
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === name + "=") {
                cookieValue = decodeURIComponent(
                    cookie.substring(name.length + 1)
                );
                break;
            }
        }
    }
    return cookieValue;
}

function updateWordCount() {
    const text = document.getElementById('textInput').value;
    const charCount = text.length;
    const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;
    
    document.getElementById('charCount').textContent = charCount;
    document.getElementById('wordCount').textContent = wordCount;
}

function addToHistory(text) {
    // Remove any history after current index
    textHistory = textHistory.slice(0, historyIndex + 1);
    textHistory.push(text);
    historyIndex = textHistory.length - 1;
    updateHistoryButtons();
}

function undo() {
    if (historyIndex > 0) {
        historyIndex--;
        document.getElementById('textInput').value = textHistory[historyIndex];
        updateWordCount();
        updateHistoryButtons();
    }
}

function redo() {
    if (historyIndex < textHistory.length - 1) {
        historyIndex++;
        document.getElementById('textInput').value = textHistory[historyIndex];
        updateWordCount();
        updateHistoryButtons();
    }
}

function updateHistoryButtons() {
    const undoBtn = document.getElementById('undoBtn');
    const redoBtn = document.getElementById('redoBtn');
    
    if(undoBtn) undoBtn.disabled = historyIndex <= 0;
    if(redoBtn) redoBtn.disabled = historyIndex >= textHistory.length - 1;
}

function clearHistory() {
    if(confirm('Are you sure you want to clear your writing history?')) {
        textHistory = [''];
        historyIndex = 0;
        document.getElementById('textInput').value = '';
        updateWordCount();
        updateHistoryButtons();
        // Also clear output
        document.getElementById('output').innerHTML = '<span class="placeholder">Your transformed text will appear here instantly...</span>';
    }
}

function exportText() {
    const text = lastTransformedText || document.getElementById('output').innerText;
    if (!text || text.includes('Your transformed text will appear here')) {
        alert('No text to export. Please transform some text first.');
        return;
    }

    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `kushal-writer-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
