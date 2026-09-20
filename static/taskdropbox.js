"use strict";

const RICH_TEXT_TAGS = new Map([
  ["P", "p"], ["DIV", "p"], ["BR", "br"], ["STRONG", "strong"],
  ["B", "strong"], ["EM", "em"], ["I", "em"], ["UL", "ul"],
  ["OL", "ol"], ["LI", "li"],
]);
const RICH_TEXT_BLOCKED_TAGS = new Set([
  "SCRIPT", "STYLE", "TEMPLATE", "IFRAME", "OBJECT", "EMBED",
]);

function safeEditorFragment(value) {
  const template = document.createElement("template");
  template.innerHTML = value;
  const fragment = document.createDocumentFragment();

  const copySafeNodes = (source, destination) => {
    source.childNodes.forEach((node) => {
      if (node.nodeType === Node.TEXT_NODE) {
        destination.append(document.createTextNode(node.textContent));
        return;
      }
      if (node.nodeType !== Node.ELEMENT_NODE) {
        return;
      }
      if (RICH_TEXT_BLOCKED_TAGS.has(node.tagName)) {
        return;
      }
      const safeTag = RICH_TEXT_TAGS.get(node.tagName);
      if (!safeTag) {
        copySafeNodes(node, destination);
        return;
      }
      const cleanElement = document.createElement(safeTag);
      copySafeNodes(node, cleanElement);
      destination.append(cleanElement);
    });
  };

  copySafeNodes(template.content, fragment);
  return fragment;
}

function enhanceRichTextArea(source) {
  const form = source.form;
  if (!form) {
    return;
  }
  const shell = document.createElement("div");
  shell.className = "rich-editor";

  const toolbar = document.createElement("div");
  toolbar.className = "rich-editor-toolbar";
  toolbar.setAttribute("role", "toolbar");

  const editor = document.createElement("div");
  editor.className = "rich-editor-content rich-content";
  editor.id = `${source.id}_editor`;
  editor.contentEditable = "true";
  editor.setAttribute("role", "textbox");
  editor.setAttribute("aria-multiline", "true");
  const label = document.querySelector(`label[for='${source.id}']`);
  if (label) {
    editor.setAttribute("aria-label", label.textContent.trim());
    label.htmlFor = editor.id;
  }
  editor.append(safeEditorFragment(source.value));
  editor.addEventListener("paste", (event) => {
    event.preventDefault();
    const richValue = event.clipboardData.getData("text/html");
    if (richValue) {
      const holder = document.createElement("div");
      holder.append(safeEditorFragment(richValue));
      document.execCommand("insertHTML", false, holder.innerHTML);
      return;
    }
    document.execCommand("insertText", false, event.clipboardData.getData("text/plain"));
  });
  editor.addEventListener("drop", (event) => {
    event.preventDefault();
    document.execCommand("insertText", false, event.dataTransfer.getData("text/plain"));
  });

  const controls = [
    ["bold", "B", source.dataset.boldLabel],
    ["italic", "I", source.dataset.italicLabel],
    ["insertUnorderedList", "• List", source.dataset.bulletListLabel],
    ["insertOrderedList", "1. List", source.dataset.numberedListLabel],
  ];
  controls.forEach(([command, visibleLabel, accessibleLabel]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `rich-editor-control rich-editor-${command}`;
    button.textContent = visibleLabel;
    button.title = accessibleLabel;
    button.setAttribute("aria-label", accessibleLabel);
    button.addEventListener("mousedown", (event) => event.preventDefault());
    button.addEventListener("click", () => {
      editor.focus();
      document.execCommand(command, false);
    });
    toolbar.append(button);
  });

  shell.append(toolbar, editor);
  source.before(shell);
  source.hidden = true;
  source.required = false;

  const format = document.createElement("input");
  format.type = "hidden";
  format.name = `${source.name}_format`;
  format.value = "html";
  source.after(format);
  form.addEventListener("submit", () => {
    source.value = editor.innerHTML;
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-language-switcher]").forEach((form) => {
    const select = form.querySelector("select[name='language']");
    if (!select) {
      return;
    }
    form.classList.add("is-enhanced");
    select.addEventListener("change", () => form.requestSubmit());
  });

  document.querySelectorAll("textarea[data-rich-text]").forEach(enhanceRichTextArea);

  const printButton = document.querySelector("[data-print-page]");
  if (printButton) {
    printButton.addEventListener("click", () => window.print());
  }
});
