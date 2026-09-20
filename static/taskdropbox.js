"use strict";

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-language-switcher]").forEach((form) => {
    const select = form.querySelector("select[name='language']");
    if (!select) {
      return;
    }
    form.classList.add("is-enhanced");
    select.addEventListener("change", () => form.requestSubmit());
  });

  const printButton = document.querySelector("[data-print-page]");
  if (printButton) {
    printButton.addEventListener("click", () => window.print());
  }
});
