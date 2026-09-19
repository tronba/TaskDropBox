"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const printButton = document.querySelector("[data-print-page]");
  if (printButton) {
    printButton.addEventListener("click", () => window.print());
  }
});
