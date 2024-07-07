document.addEventListener('DOMContentLoaded', function() {
    const meaningsContainer = document.querySelector('.matching-meanings');
    let draggedItem = null;
    let timeLeft = 60;
    const timerElement = document.getElementById('matching-timer');
    
    // Get page_id from URL
    const urlParams = new URLSearchParams(window.location.search);
    const pageId = urlParams.get('page_id');
    const startTime = new Date().toISOString();

    const timerInterval = setInterval(() => {
        timeLeft--;
        timerElement.textContent = `Time left: ${timeLeft}s`;
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            timerElement.textContent = 'Time is up!';
            checkAnswers();
        }
    }, 1000);

    document.querySelectorAll('.matching-meaning').forEach(item => {
        item.setAttribute('draggable', true);

        item.addEventListener('dragstart', function(e) {
            draggedItem = e.target;
            setTimeout(() => {
                e.target.style.display = 'none';
            }, 0);
        });

        item.addEventListener('dragend', function(e) {
            setTimeout(() => {
                if (draggedItem) {
                    draggedItem.style.display = 'block';
                    draggedItem = null;
                }
            }, 0);
        });
    });

    meaningsContainer.addEventListener('dragover', function(e) {
        e.preventDefault();
    });

    meaningsContainer.addEventListener('drop', function(e) {
        e.preventDefault();
        if (e.target.classList.contains('matching-meaning')) {
            meaningsContainer.insertBefore(draggedItem, e.target);
        } else {
            meaningsContainer.appendChild(draggedItem);
        }
    });

    document.getElementById('matching-checkAnswers').addEventListener('click', function() {
        clearInterval(timerInterval);
        checkAnswers();
    });

    function checkAnswers() {
        const results = [];
        document.querySelectorAll('.matching-word').forEach((wordElem, index) => {
            const wordId = parseInt(wordElem.dataset.id, 10);
            const meaningElem = document.querySelectorAll('.matching-meanings .matching-meaning')[index];
            if (meaningElem) {
                const meaning = meaningElem.dataset.meaning;
                results.push({ "word_id": wordId, "meaning": meaning });
            }
        });

        console.log("Results to be sent:", results);

        fetch('/check_matching_answers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ results, page_id: pageId })
        })
        .then(response => response.json())
        .then(data => {
            console.log("Response from server:", data);

            document.querySelectorAll('.matching-word').forEach((wordElem, index) => {
                const wordId = parseInt(wordElem.dataset.id, 10);
                const meaningElem = document.querySelectorAll('.matching-meanings .matching-meaning')[index];
                if (meaningElem) {
                    const correctMeaning = data.correct_answers[wordId];
                    if (correctMeaning === meaningElem.dataset.meaning) {
                        wordElem.classList.add('matching-correct');
                        wordElem.classList.remove('matching-incorrect');
                        meaningElem.classList.add('matching-correct');
                        meaningElem.classList.remove('matching-incorrect');
                    } else {
                        wordElem.classList.add('matching-incorrect');
                        wordElem.classList.remove('matching-correct');
                        meaningElem.classList.add('matching-incorrect');
                        meaningElem.classList.remove('matching-correct');
                    }
                }
            });

            fetch('/update_points_matching_game', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    correct_answers: data.correct_answers, 
                    page_id: pageId, 
                    time_left: timeLeft  // Gửi thời gian còn lại
                })
            })
            .then(response => response.json())
            .then(updateData => {
                console.log("Points update response:", updateData);
                document.querySelectorAll('.matching-meaning').forEach(item => {
                    item.setAttribute('draggable', false);
                });
                
                if (timeLeft >= 31 && timeLeft <= 60) {
                    alert("You earned 0.82 points for each correct word!");
                } else if (timeLeft >= 0 && timeLeft <= 30) {
                    alert("You have earned 0.75 points for each correct word!");
                }


                setTimeout(() => {
                    window.location.href = `/view_page/${pageId}`;
                }, 30000);
            })
            .catch(error => {
                console.error("Error updating points:", error);
                alert("An error occurred while updating points. Please try again.");
            });
        })
        .catch(error => {
            console.error("Error checking answers:", error);
            alert("An error occurred while checking answers. Please try again.");
        });
    }
});