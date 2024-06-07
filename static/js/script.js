document.addEventListener('DOMContentLoaded', () => {
  const selectedWords = [];
  const selectedWordsContainer = document.getElementById('selected-words');
  const saveWordsBtn = document.getElementById('save-words-btn');
  const selectPageForm = document.getElementById('select-page-form');

  document.querySelectorAll('.btn-select').forEach(button => {
    button.addEventListener('click', () => {
      const tu = button.getAttribute('data-tu');
      const phienam = button.getAttribute('data-phienam');
      const nghia = button.getAttribute('data-nghia');
      const ma_tu_vung = button.getAttribute('data-ma_tu_vung');

      if (selectedWords.length < 10) {
        selectedWords.push({ tu, phienam, nghia, ma_tu_vung });
        renderSelectedWords();
      } else {
        alert('Bạn chỉ có thể chọn tối đa 10 từ.');
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
    selectPageForm.style.display = selectedWords.length > 0 ? 'block' : 'none';
  }

  // Xử lý khi người dùng chọn lưu vào trang đã có
  selectPageForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const existingPageId = document.getElementById('existing-page').value;

    if (!existingPageId) {
      alert('Vui lòng chọn một trang để lưu từ vựng.');
      return;
    }

    try {
      const response = await fetch('/save_words_to_existing_page', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ existing_page_id: existingPageId, words: selectedWords })
      });
      const data = await response.json();
      if (data.status === 'success') {
        alert('Lưu từ thành công!');
        window.location.reload();
      } else {
        alert(`Lỗi: ${data.message}`);
      }
    } catch (error) {
      console.error('Lỗi khi lưu từ:', error);
      alert('Đã xảy ra lỗi khi lưu từ. Vui lòng thử lại.');
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

