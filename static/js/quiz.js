
document.addEventListener("DOMContentLoaded", function () {
  var countdownElement = document.getElementById("countdown");
  var countdownSeconds = 30;

  var timer = setInterval(function () {
    countdownElement.textContent = countdownSeconds + "s";
    debugger;

    countdownSeconds--;

    if (countdownSeconds < 0) {
      clearInterval(timer);
      document.getElementById("submit-button").setAttribute("disabled", "disabled");
      setTimeout(function () {
        window.location.reload();
      }, 1000);
    }
  }, 1000);

  window.selectChoice = function (choice) {
    document.getElementById("user_choice").value = choice;
    var buttons = document.querySelectorAll(".btn-multiple-choice");
    buttons.forEach(function (button) {
      button.classList.remove("btn-selected");
    });
    var escapedChoice = CSS.escape(choice);
    document
      .querySelector(`button[value="${escapedChoice}"]`)
      .classList.add("btn-selected");
  };
});