import React from "react";
import { htmlToMarkdown, markdownToHtml } from "./markdown-parser";

export { markdownToHtml, htmlToMarkdown };

export function setCaretToEnd(el: HTMLElement): void {
  const sel = window.getSelection();
  const range = document.createRange();
  range.selectNodeContents(el);
  range.collapse(false);
  sel?.removeAllRanges();
  sel?.addRange(range);
}

export function tryHandleMarkdownShortcut(
  e: React.KeyboardEvent<HTMLDivElement>,
  editor: HTMLDivElement,
  onTransform: () => void,
): boolean {
  if (e.key === " ") {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return false;
    const range = sel.getRangeAt(0);
    const node = range.startContainer;

    if (node && node.nodeType === Node.TEXT_NODE) {
      let blockNode: Node | null = node;
      while (
        blockNode &&
        blockNode !== editor &&
        !["H1", "H2", "H3", "H4", "LI", "P", "DIV"].includes((blockNode as HTMLElement).tagName || "")
      ) {
        blockNode = blockNode.parentNode;
      }

      const tag = (blockNode as HTMLElement)?.tagName || "";
      if (["H1", "H2", "H3", "H4"].includes(tag)) {
        return false;
      }

      const textBeforeCaret = node.textContent?.slice(0, range.startOffset) || "";
      const textAfterCaret = node.textContent?.slice(range.startOffset) || "";

      // Multi-hash patterns: e.g. "# #", "## #", "## ##", "### #"
      const multiHashMatch = textBeforeCaret.match(/^(#{1,4})\s+(#.*)$/);
      if (multiHashMatch) {
        e.preventDefault();
        onTransform();
        const level = multiHashMatch[1].length;
        const remainingHashes = multiHashMatch[2];
        node.textContent = `${remainingHashes} ${textAfterCaret}`;
        document.execCommand("formatBlock", false, `h${level}`);
        return true;
      }

      // Heading shortcuts: #, ##, ###, ####
      const headingMatch = textBeforeCaret.match(/^(#{1,4})$/);
      if (headingMatch) {
        e.preventDefault();
        onTransform();
        node.textContent = textAfterCaret;
        document.execCommand("formatBlock", false, `h${headingMatch[1].length}`);
        return true;
      }

      // Bullet lists: - or *
      if (textBeforeCaret === "-" || textBeforeCaret === "*") {
        e.preventDefault();
        onTransform();
        node.textContent = textAfterCaret;
        document.execCommand("insertUnorderedList");
        return true;
      }

      // Numbered list: 1.
      if (textBeforeCaret === "1.") {
        e.preventDefault();
        onTransform();
        node.textContent = textAfterCaret;
        document.execCommand("insertOrderedList");
        return true;
      }
    }
  }

  if (e.key === "Enter") {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return false;
    const range = sel.getRangeAt(0);
    const node = range.startContainer;
    if (node && node.nodeType === Node.TEXT_NODE) {
      const text = (node.textContent || "").trim();
      if (text === "---" || text === "***") {
        e.preventDefault();
        node.textContent = "";
        document.execCommand("insertHorizontalRule");
        return true;
      }
    }
  }

  if (e.key === "Backspace") {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return false;
    const range = sel.getRangeAt(0);

    if (range.startOffset === 0) {
      let blockNode: Node | null = range.startContainer;
      while (
        blockNode &&
        blockNode !== editor &&
        !["H1", "H2", "H3", "H4", "LI"].includes((blockNode as HTMLElement).tagName || "")
      ) {
        blockNode = blockNode.parentNode;
      }

      if (blockNode && blockNode !== editor) {
        const tag = (blockNode as HTMLElement).tagName;
        if (["H1", "H2", "H3", "H4"].includes(tag)) {
          e.preventDefault();
          document.execCommand("formatBlock", false, "p");
          return true;
        }
        if (tag === "LI" && (blockNode.textContent || "").trim() === "") {
          e.preventDefault();
          document.execCommand("insertUnorderedList");
          return true;
        }
      }
    }
  }

  return false;
}

export function extractMarkdownFromSelection(
  selection: Selection,
  editor: HTMLElement,
): string | null {
  if (!selection || selection.rangeCount === 0 || selection.isCollapsed) return null;
  const range = selection.getRangeAt(0);

  let startBlock: HTMLElement | null = range.startContainer as HTMLElement;
  while (
    startBlock &&
    startBlock !== editor &&
    !["H1", "H2", "H3", "H4", "LI", "P", "DIV"].includes(startBlock.tagName || "")
  ) {
    startBlock = startBlock.parentElement;
  }

  let endBlock: HTMLElement | null = range.endContainer as HTMLElement;
  while (
    endBlock &&
    endBlock !== editor &&
    !["H1", "H2", "H3", "H4", "LI", "P", "DIV"].includes(endBlock.tagName || "")
  ) {
    endBlock = endBlock.parentElement;
  }

  if (startBlock && startBlock === endBlock && startBlock !== editor) {
    const tag = startBlock.tagName.toLowerCase();
    const selectedText = selection.toString();

    let prefix = "";
    if (tag === "h1") prefix = "# ";
    else if (tag === "h2") prefix = "## ";
    else if (tag === "h3") prefix = "### ";
    else if (tag === "h4") prefix = "#### ";
    else if (tag === "li") {
      const parent = startBlock.parentElement?.tagName.toLowerCase();
      if (parent === "ol") {
        const idx = Array.from(startBlock.parentElement?.children || []).indexOf(startBlock) + 1;
        prefix = `${idx}. `;
      } else {
        prefix = "- ";
      }
    }

    if (prefix) {
      return `${prefix}${selectedText}`;
    }
  }

  const clonedSelection = range.cloneContents();
  const container = document.createElement("div");
  container.appendChild(clonedSelection);
  return htmlToMarkdown(container) || null;
}
