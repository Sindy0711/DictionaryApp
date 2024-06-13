document.addEventListener("DOMContentLoaded", () => {
  const selectedWords = [];
  const selectedWordsContainer = document.getElementById("selected-words");
  const saveWordsBtn = document.getElementById("save-words-btn");
  const selectPageForm = document.getElementById("select-page-form");
  const existingPageSelect = document.getElementById("existing-page");

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

  loadVocabularyPages();

  document.querySelectorAll(".btn-select").forEach((button) => {
    button.addEventListener("click", () => {
      const word = {
        word: button.getAttribute("data-word"),
        pronunciation: button.getAttribute("data-pronunciation"),
        meaning: button.getAttribute("data-meaning"),
        word_id: button.getAttribute("data-word_id"),
      };

      if (selectedWords.length < 10) {
        selectedWords.push(word);
        renderSelectedWords();
      } else {
        alert("You can only choose up to 10 words.");
      }
    });
  });

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

  selectPageForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const existingPageId = document.getElementById("existing-page").value;

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
        alert("Word saved successfully!");
        window.location.reload();
      } else {
        alert(`Error: ${data.message}`);
      }
    } catch (error) {
      console.error("Error when saving word:", error);
      alert("An error occurred while saving the word. Please try again.");
    }
  });
});

//tạo trang mới
document.addEventListener('DOMContentLoaded', () => {
  const createPageForm = document.getElementById('create-page-form');

  createPageForm.addEventListener('submit', async (event) => {
      event.preventDefault();

      const pageName = document.getElementById('page-name').value.trim();
      const pageDescription = document.getElementById('page-description').value.trim();

      if (!pageName) {
          alert('Tên trang là bắt buộc');
          return;
      }

      try {
          const response = await fetch('/create_vocabulary_page', {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/json'
              },
              body: JSON.stringify({
                  page_name: pageName,
                  page_description: pageDescription
              })
          });

          const data = await response.json();
          if (data.status === 'success') {
              alert('Tạo trang thành công!');
              window.location.reload();
          } else {
              alert(`Lỗi: ${data.message}`);
          }
      } catch (error) {
          console.error('Lỗi khi tạo trang:', error);
          alert('Đã xảy ra lỗi khi tạo trang. Vui lòng thử lại.');
      }
  });
});
document.getElementById("create-page-btn").addEventListener("click", function() {
  var form = document.getElementById("create-page-form");
  if (form.style.display === "none") {
      form.style.display = "block";
  } else {
      form.style.display = "none";
  }
});
