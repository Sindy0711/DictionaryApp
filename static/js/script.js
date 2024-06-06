// static/js/script.js
document.addEventListener('DOMContentLoaded', () => {
  const selectedWords = [];
  const selectedWordsContainer = document.getElementById('selected-words');
  const saveWordsBtn = document.getElementById('save-words-btn');
  const createPageForm = document.getElementById('create-page-form');

  document.querySelectorAll('.btn-select').forEach(button => {
    button.addEventListener('click', () => {
      const tu = button.getAttribute('data-tu');
      const phienam = button.getAttribute('data-phienam');
      const nghia = button.getAttribute('data-nghia');

      if (selectedWords.length < 10) {
        selectedWords.push({ tu, phienam, nghia });
        renderSelectedWords();
      } else {
        alert('You can select up to 10 words only.');
      }
    });
  });

  function renderSelectedWords() {
    selectedWordsContainer.innerHTML = '';
    selectedWords.forEach(word => {
      const div = document.createElement('div');
      div.textContent = `${word.tu} - ${word.phienam} - ${word.nghia}`;
      selectedWordsContainer.appendChild(div);
    });
    saveWordsBtn.disabled = selectedWords.length === 0;
    createPageForm.style.display = selectedWords.length > 0 ? 'block' : 'none';
  }

  createPageForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const pageName = document.getElementById('page-name').value.trim();
    const pageDescription = document.getElementById('page-description').value.trim();

    if (!pageName) {
      alert('Page name is required');
      return;
    }

    try {
      const response = await fetch('/create_vocabulary_page', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ page_name: pageName, page_description: pageDescription, words: selectedWords })
      });
      const data = await response.json();
      if (data.status === 'success') {
        alert('Page created successfully!');
        window.location.reload();
      } else {
        alert(`Error: ${data.message}`);
      }
    } catch (error) {
      console.error('Error creating page:', error);
      alert('An error occurred while creating the page. Please try again.');
    }
  });
});
