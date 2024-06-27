document.addEventListener("DOMContentLoaded", () => {
    const selectedWords = [];
    const selectedWordsContainer = document.getElementById("selected-words");
    const saveWordsBtn = document.getElementById("save-words-btn");
    const selectPageForm = document.getElementById("select-page-form");
    const existingPageSelect = document.getElementById("existing-page");

    // Function to load vocabulary pages
    async function loadVocabularyPages() {
        try {
            const response = await fetch("/api/get_vocabulary_pages");
            const data = await response.json();
            if (data.status === "success") {
                data.pages.forEach((page) => {
                    const option = document.createElement("option");
                    option.value = page.page_id;
                    option.textContent = page.page_name;
                    existingPageSelect.appendChild(option);
                });
            } else {
                alert(`Error: ${data.message}`);
            }
        } catch (error) {
            console.error("Error loading vocabulary pages:", error);
        }
    }

    // Ensure loadVocabularyPages is called only once
    if (existingPageSelect.options.length === 1) {  // Check if the default option is the only option present
        loadVocabularyPages();
    }

    function renderSelectedWords() {
        selectedWordsContainer.innerHTML = "";
        selectedWords.forEach((word) => {
            const div = document.createElement("div");
            div.textContent = `${word.word} - ${word.pronunciation} - ${word.meaning}`;
            selectedWordsContainer.appendChild(div);
        });
        saveWordsBtn.disabled = selectedWords.length === 0;
        selectPageForm.style.display = selectedWords.length > 0 ? "block" : "none";
    }

    // Add event listeners to word selection buttons
    document.querySelectorAll(".btn-select").forEach((button) => {
        button.addEventListener("click", () => {
            const word = {
                word: button.getAttribute("data-word"),
                pronunciation: button.getAttribute("data-pronunciation"),
                meaning: button.getAttribute("data-meaning"),
                word_id: button.getAttribute("data-word_id"),
            };

            if (selectedWords.some((selectedWord) => selectedWord.word_id === word.word_id)) {
                alert("This word is already selected.");
                return;
            }

            if (selectedWords.length < 10) {
                selectedWords.push(word);
                renderSelectedWords();
            } else {
                alert("You can only choose up to 10 words.");
            }
        });
    });

    // Handle form submission to save to an existing vocabulary page
    selectPageForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const existingPageId = existingPageSelect.value;
        if (!existingPageId) {
            alert("Please select a page to save vocabulary.");
            return;
        }

        try {
            const response = await fetch("/save_words_to_existing_page", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    existing_page_id: existingPageId,
                    words: selectedWords,
                }),
            });
            const data = await response.json();
            if (data.status === "success") {
                alert("Words saved successfully!");
                window.location.reload();
            } else {
                alert(`Error: ${data.message}`);
            }
        } catch (error) {
            console.error("Error when saving words:", error);
            alert("An error occurred while saving the words. Please try again.");
        }
    });
});
