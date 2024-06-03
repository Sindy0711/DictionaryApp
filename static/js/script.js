document.addEventListener("DOMContentLoaded", function() {
  // Script để xử lý các từ đã chọn
  const selectedWords = JSON.parse(sessionStorage.getItem('selectedWords')) || [];
  const selectedWordsDiv = document.getElementById('selected-words');
  const saveWordsBtn = document.getElementById('save-words-btn');

  document.querySelectorAll('.btn-select').forEach(button => {
    button.addEventListener('click', function() {
      const tu = this.getAttribute('data-tu');
      const phienam = this.getAttribute('data-phienam');
      const nghia = this.getAttribute('data-nghia');
      
      // Kiểm tra nếu từ đã tồn tại trong selectedWords
      if (selectedWords.length < 10 && !selectedWords.some(word => word.tu === tu)) {
        selectedWords.push({ tu, phienam, nghia });
        updateSelectedWords();
      } else if (selectedWords.some(word => word.tu === tu)) {
        alert("Từ này đã được chọn.");
      } else {
        alert("Bạn chỉ có thể chọn tối đa 10 từ.");
      }
    });
  });

  function updateSelectedWords() {
    selectedWordsDiv.innerHTML = '<ul>' + selectedWords.map(word => `<li>${word.tu} - ${word.phienam} - ${word.nghia}</li>`).join('') + '</ul>';
    saveWordsBtn.disabled = selectedWords.length === 0;
    sessionStorage.setItem('selectedWords', JSON.stringify(selectedWords));
    fetch('/save_selected_words', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(selectedWords),
    });
  }

  function loadSelectedWords() {
    updateSelectedWords();
  }

  loadSelectedWords();

  // Script để xử lý việc xóa từ
  document.querySelectorAll('.btn-delete').forEach(button => {
    button.addEventListener('click', function() {
      const wordId = this.getAttribute('data-id');
      fetch(`/delete_word/${wordId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      .then(response => response.json())
      .then(data => {
        if (data.status === 'success') {
          this.closest('tr').remove();
        } else {
          alert('Lỗi khi xóa từ.');
        }
      });
    });
  });
});
