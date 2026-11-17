document.addEventListener("click", function (event) {
  const confirmLink = event.target.closest("[data-confirm]");
  if (confirmLink && !window.confirm(confirmLink.dataset.confirm)) {
    event.preventDefault();
    return;
  }
  const toggle = event.target.closest("[data-toggle-password]");
  if (toggle) {
    const field = document.getElementById(toggle.dataset.togglePassword);
    if (field) {
      const show = field.type === "password";
      field.type = show ? "text" : "password";
      toggle.textContent = show ? "Hide" : "Show";
    }
  }
});
