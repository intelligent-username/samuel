"use client";

import React, { useRef, useEffect, useCallback } from "react";

interface JobDescriptionInputProps {
  jobDesc: string;
  onChange: (text: string) => void;
  onEnterGenerate: () => void;
  overLimit: boolean;
  nearLimit: boolean;
  wordCount: number;
  jdLen: number;
  jdTrimLen: number;
  charsRemaining: number;
  maxChars: number;
}

function markdownToHtml(md: string): string {
  if (!md) return "";
  const lines = md.split("\n");
  let html = "";
  let inUl = false;
  let inOl = false;

  const formatInline = (text: string) => {
    let s = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    s = s.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/__(.*?)__/g, "<strong>$1</strong>");
    s = s.replace(/\*(.*?)\*/g, "<em>$1</em>");
    s = s.replace(/_(.*?)_/g, "<em>$1</em>");
    s = s.replace(/`(.*?)`/g, "<code>$1</code>");
    return s;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Horizontal rule: ---, ***, ___
    if (/^(\s*[-*_]\s*){3,}$/.test(line)) {
      if (inUl) { html += "</ul>"; inUl = false; }
      if (inOl) { html += "</ol>"; inOl = false; }
      html += "<hr>";
      continue;
    }

    // Heading 4: #### ...
    if (/^####\s*(.*)/.test(line)) {
      if (inUl) { html += "</ul>"; inUl = false; }
      if (inOl) { html += "</ol>"; inOl = false; }
      const content = line.replace(/^####\s*/, "");
      html += `<h4>${content ? formatInline(content) : "<br>"}</h4>`;
      continue;
    }

    // Heading 3: ### ...
    if (/^###\s*(.*)/.test(line)) {
      if (inUl) { html += "</ul>"; inUl = false; }
      if (inOl) { html += "</ol>"; inOl = false; }
      const content = line.replace(/^###\s*/, "");
      html += `<h3>${content ? formatInline(content) : "<br>"}</h3>`;
      continue;
    }

    // Heading 2: ## ...
    if (/^##\s*(.*)/.test(line)) {
      if (inUl) { html += "</ul>"; inUl = false; }
      if (inOl) { html += "</ol>"; inOl = false; }
      const content = line.replace(/^##\s*/, "");
      html += `<h2>${content ? formatInline(content) : "<br>"}</h2>`;
      continue;
    }

    // Heading 1: # ...
    if (/^#\s*(.*)/.test(line)) {
      if (inUl) { html += "</ul>"; inUl = false; }
      if (inOl) { html += "</ol>"; inOl = false; }
      const content = line.replace(/^#\s*/, "");
      html += `<h1>${content ? formatInline(content) : "<br>"}</h1>`;
      continue;
    }

    // Bullet list: - or *
    if (/^(\s*)[-*]\s+(.*)/.test(line)) {
      if (inOl) { html += "</ol>"; inOl = false; }
      if (!inUl) { html += "<ul>"; inUl = true; }
      html += `<li>${formatInline(line.replace(/^(\s*)[-*]\s+/, ""))}</li>`;
      continue;
    }

    // Numbered list: 1.
    if (/^(\s*)\d+\.\s+(.*)/.test(line)) {
      if (inUl) { html += "</ul>"; inUl = false; }
      if (!inOl) { html += "<ol>"; inOl = true; }
      html += `<li>${formatInline(line.replace(/^(\s*)\d+\.\s+/, ""))}</li>`;
      continue;
    }

    // Normal line
    if (inUl) { html += "</ul>"; inUl = false; }
    if (inOl) { html += "</ol>"; inOl = false; }

    if (!line.trim()) {
      html += "<p><br></p>";
    } else {
      html += `<p>${formatInline(line)}</p>`;
    }
  }

  if (inUl) html += "</ul>";
  if (inOl) html += "</ol>";

  return html;
}

function htmlToMarkdown(root: HTMLElement): string {
  function walk(node: Node): string {
    if (node.nodeType === Node.TEXT_NODE) {
      return node.textContent || "";
    }
    if (node.nodeType !== Node.ELEMENT_NODE) {
      return "";
    }

    const el = node as HTMLElement;
    const tag = el.tagName.toLowerCase();

    let children = "";
    for (let i = 0; i < el.childNodes.length; i++) {
      children += walk(el.childNodes[i]);
    }

    switch (tag) {
      case "h1":
        return `# ${children.trim()}\n\n`;
      case "h2":
        return `## ${children.trim()}\n\n`;
      case "h3":
        return `### ${children.trim()}\n\n`;
      case "h4":
        return `#### ${children.trim()}\n\n`;
      case "p":
      case "div":
        return children.trim() ? `${children.trim()}\n\n` : "\n";
      case "li": {
        const parent = el.parentElement?.tagName.toLowerCase();
        if (parent === "ol") {
          const idx = Array.from(el.parentElement?.children || []).indexOf(el) + 1;
          return `${idx}. ${children.trim()}\n`;
        }
        return `- ${children.trim()}\n`;
      }
      case "ul":
      case "ol":
        return `${children.trim()}\n\n`;
      case "hr":
        return `---\n\n`;
      case "strong":
      case "b":
        return `**${children}**`;
      case "em":
      case "i":
        return `*${children}*`;
      case "code":
        return `\`${children}\``;
      case "br":
        return "\n";
      default:
        return children;
    }
  }

  return walk(root).replace(/\n{3,}/g, "\n\n").trim();
}

export default function JobDescriptionInput({
  jobDesc,
  onChange,
  onEnterGenerate,
  overLimit,
  nearLimit,
  wordCount,
  jdLen,
  jdTrimLen,
  charsRemaining,
  maxChars,
}: JobDescriptionInputProps) {
  const editorRef = useRef<HTMLDivElement>(null);
  const lastReportedMd = useRef<string>(jobDesc);
  const undoStackRef = useRef<string[]>([]);
  const redoStackRef = useRef<string[]>([]);
  const typingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const textBeforeTypingRef = useRef<string>(jobDesc);

  const pushHistory = useCallback((text: string) => {
    if (!text && undoStackRef.current.length === 0) return;
    const last = undoStackRef.current[undoStackRef.current.length - 1];
    if (last !== text) {
      undoStackRef.current.push(text);
      if (undoStackRef.current.length > 60) {
        undoStackRef.current.shift();
      }
    }
    redoStackRef.current = [];
  }, []);

  const handleUndo = useCallback(() => {
    if (undoStackRef.current.length === 0 || !editorRef.current) return;
    const currentMd = htmlToMarkdown(editorRef.current);
    const previousMd = undoStackRef.current.pop()!;
    redoStackRef.current.push(currentMd);

    lastReportedMd.current = previousMd;
    editorRef.current.innerHTML = markdownToHtml(previousMd);
    onChange(previousMd);

    // Place caret at end
    const sel = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(editorRef.current);
    range.collapse(false);
    sel?.removeAllRanges();
    sel?.addRange(range);
  }, [onChange]);

  const handleRedo = useCallback(() => {
    if (redoStackRef.current.length === 0 || !editorRef.current) return;
    const currentMd = htmlToMarkdown(editorRef.current);
    const nextMd = redoStackRef.current.pop()!;
    undoStackRef.current.push(currentMd);

    lastReportedMd.current = nextMd;
    editorRef.current.innerHTML = markdownToHtml(nextMd);
    onChange(nextMd);

    // Place caret at end
    const sel = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(editorRef.current);
    range.collapse(false);
    sel?.removeAllRanges();
    sel?.addRange(range);
  }, [onChange]);

  // Sync external markdown changes into editor HTML
  useEffect(() => {
    if (editorRef.current && jobDesc !== lastReportedMd.current) {
      lastReportedMd.current = jobDesc;
      editorRef.current.innerHTML = markdownToHtml(jobDesc);
    }
  }, [jobDesc]);

  // Initial populate
  useEffect(() => {
    if (editorRef.current && !editorRef.current.innerHTML && jobDesc) {
      editorRef.current.innerHTML = markdownToHtml(jobDesc);
    }
  }, []);

  const handleInput = useCallback(() => {
    if (!editorRef.current) return;
    const md = htmlToMarkdown(editorRef.current);
    lastReportedMd.current = md;
    onChange(md);

    // Debounced history record while typing
    if (typingTimerRef.current) clearTimeout(typingTimerRef.current);
    typingTimerRef.current = setTimeout(() => {
      pushHistory(textBeforeTypingRef.current);
      textBeforeTypingRef.current = md;
    }, 450);
  }, [onChange, pushHistory]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    // Ctrl+Z (Undo) and Ctrl+Shift+Z / Ctrl+Y (Redo)
    if ((e.ctrlKey || e.metaKey) && (e.key === "z" || e.key === "Z")) {
      e.preventDefault();
      if (e.shiftKey) {
        handleRedo();
      } else {
        handleUndo();
      }
      return;
    }

    if ((e.ctrlKey || e.metaKey) && (e.key === "y" || e.key === "Y")) {
      e.preventDefault();
      handleRedo();
      return;
    }

    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      onEnterGenerate();
      return;
    }

    // Capture text state before structural changes
    if ([" ", "Enter", "Backspace"].includes(e.key) && editorRef.current) {
      const currentMd = htmlToMarkdown(editorRef.current);
      textBeforeTypingRef.current = currentMd;
    }

    // Markdown shortcut expansion on Space
    if (e.key === " ") {
      const sel = window.getSelection();
      if (!sel || sel.rangeCount === 0) return;
      const range = sel.getRangeAt(0);
      const node = range.startContainer;

      if (node && node.nodeType === Node.TEXT_NODE) {
        // Check if already inside a heading
        let blockNode: Node | null = node;
        while (
          blockNode &&
          blockNode !== editorRef.current &&
          !["H1", "H2", "H3", "H4", "LI", "P", "DIV"].includes((blockNode as HTMLElement).tagName || "")
        ) {
          blockNode = blockNode.parentNode;
        }

        const tag = (blockNode as HTMLElement)?.tagName || "";
        const isHeading = ["H1", "H2", "H3", "H4"].includes(tag);

        // If already inside a heading, do NOT convert or delete subsequent hashes
        if (isHeading) {
          return;
        }

        const textBeforeCaret = node.textContent?.slice(0, range.startOffset) || "";
        const textAfterCaret = node.textContent?.slice(range.startOffset) || "";

        // Multi-hash patterns: e.g. "# #", "## #", "## ##", "### #"
        const multiHashMatch = textBeforeCaret.match(/^(#{1,4})\s+(#.*)$/);
        if (multiHashMatch) {
          e.preventDefault();
          if (editorRef.current) pushHistory(htmlToMarkdown(editorRef.current));
          const level = multiHashMatch[1].length;
          const remainingHashes = multiHashMatch[2];
          node.textContent = `${remainingHashes} ${textAfterCaret}`;
          document.execCommand("formatBlock", false, `h${level}`);
          handleInput();
          return;
        }

        if (textBeforeCaret === "#") {
          e.preventDefault();
          if (editorRef.current) pushHistory(htmlToMarkdown(editorRef.current));
          node.textContent = textAfterCaret;
          document.execCommand("formatBlock", false, "h1");
          handleInput();
          return;
        } else if (textBeforeCaret === "##") {
          e.preventDefault();
          if (editorRef.current) pushHistory(htmlToMarkdown(editorRef.current));
          node.textContent = textAfterCaret;
          document.execCommand("formatBlock", false, "h2");
          handleInput();
          return;
        } else if (textBeforeCaret === "###") {
          e.preventDefault();
          if (editorRef.current) pushHistory(htmlToMarkdown(editorRef.current));
          node.textContent = textAfterCaret;
          document.execCommand("formatBlock", false, "h3");
          handleInput();
          return;
        } else if (textBeforeCaret === "####") {
          e.preventDefault();
          if (editorRef.current) pushHistory(htmlToMarkdown(editorRef.current));
          node.textContent = textAfterCaret;
          document.execCommand("formatBlock", false, "h4");
          handleInput();
          return;
        } else if (textBeforeCaret === "-" || textBeforeCaret === "*") {
          e.preventDefault();
          if (editorRef.current) pushHistory(htmlToMarkdown(editorRef.current));
          node.textContent = textAfterCaret;
          document.execCommand("insertUnorderedList");
          handleInput();
          return;
        } else if (textBeforeCaret === "1.") {
          e.preventDefault();
          if (editorRef.current) pushHistory(htmlToMarkdown(editorRef.current));
          node.textContent = textAfterCaret;
          document.execCommand("insertOrderedList");
          handleInput();
          return;
        }
      }
    }

    // Divider shortcut expansion on Enter
    if (e.key === "Enter") {
      const sel = window.getSelection();
      if (!sel || sel.rangeCount === 0) return;
      const range = sel.getRangeAt(0);
      const node = range.startContainer;
      if (node && node.nodeType === Node.TEXT_NODE) {
        const text = (node.textContent || "").trim();
        if (text === "---" || text === "***") {
          e.preventDefault();
          node.textContent = "";
          document.execCommand("insertHorizontalRule");
          handleInput();
          return;
        }
      }
    }

    // Demote heading or list on Backspace at start of line
    if (e.key === "Backspace") {
      const sel = window.getSelection();
      if (!sel || sel.rangeCount === 0) return;
      const range = sel.getRangeAt(0);

      if (range.startOffset === 0) {
        let blockNode: Node | null = range.startContainer;
        while (
          blockNode &&
          blockNode !== editorRef.current &&
          !["H1", "H2", "H3", "H4", "LI"].includes((blockNode as HTMLElement).tagName || "")
        ) {
          blockNode = blockNode.parentNode;
        }

        if (blockNode && blockNode !== editorRef.current) {
          const tag = (blockNode as HTMLElement).tagName;
          if (["H1", "H2", "H3", "H4"].includes(tag)) {
            e.preventDefault();
            document.execCommand("formatBlock", false, "p");
            handleInput();
            return;
          }
          if (tag === "LI" && (blockNode.textContent || "").trim() === "") {
            e.preventDefault();
            document.execCommand("insertUnorderedList");
            handleInput();
            return;
          }
        }
      }
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLDivElement>) => {
    e.preventDefault();
    const plainText = e.clipboardData.getData("text/plain");
    if (!plainText) return;

    if (editorRef.current) {
      pushHistory(htmlToMarkdown(editorRef.current));
    }

    const html = markdownToHtml(plainText);
    const sel = window.getSelection();

    const isEditorEmpty = !editorRef.current?.innerText.trim();
    const isSelectAll =
      Boolean(
        sel &&
        sel.rangeCount > 0 &&
        !sel.isCollapsed &&
        editorRef.current &&
        sel.toString().trim().length >= (editorRef.current.innerText.trim().length - 2)
      );

    if (isEditorEmpty || isSelectAll) {
      if (editorRef.current) {
        editorRef.current.innerHTML = html;
        const range = document.createRange();
        range.selectNodeContents(editorRef.current);
        range.collapse(false);
        sel?.removeAllRanges();
        sel?.addRange(range);
      }
    } else if (sel && sel.rangeCount > 0) {
      const range = sel.getRangeAt(0);
      range.deleteContents();

      const temp = document.createElement("div");
      temp.innerHTML = html;

      const frag = document.createDocumentFragment();
      let node: Node | null;
      let lastNode: Node | null = null;
      while ((node = temp.firstChild)) {
        lastNode = frag.appendChild(node);
      }

      range.insertNode(frag);

      if (lastNode) {
        const newRange = document.createRange();
        newRange.setStartAfter(lastNode);
        newRange.collapse(true);
        sel.removeAllRanges();
        sel.addRange(newRange);
      }
    }

    handleInput();
  };

  const handleCopy = (e: React.ClipboardEvent<HTMLDivElement>) => {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0 || selection.isCollapsed) return;

    const range = selection.getRangeAt(0);

    // Check if selection is within a single block
    let startBlock: HTMLElement | null = range.startContainer as HTMLElement;
    while (
      startBlock &&
      startBlock !== editorRef.current &&
      !["H1", "H2", "H3", "H4", "LI", "P", "DIV"].includes(startBlock.tagName || "")
    ) {
      startBlock = startBlock.parentElement;
    }

    let endBlock: HTMLElement | null = range.endContainer as HTMLElement;
    while (
      endBlock &&
      endBlock !== editorRef.current &&
      !["H1", "H2", "H3", "H4", "LI", "P", "DIV"].includes(endBlock.tagName || "")
    ) {
      endBlock = endBlock.parentElement;
    }

    if (startBlock && startBlock === endBlock && startBlock !== editorRef.current) {
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
        e.preventDefault();
        e.clipboardData.setData("text/plain", `${prefix}${selectedText}`);
        return;
      }
    }

    // Multi-block selection
    const clonedSelection = range.cloneContents();
    const container = document.createElement("div");
    container.appendChild(clonedSelection);
    const md = htmlToMarkdown(container);
    if (md) {
      e.preventDefault();
      e.clipboardData.setData("text/plain", md);
    }
  };

  const handleCut = (e: React.ClipboardEvent<HTMLDivElement>) => {
    if (editorRef.current) {
      pushHistory(htmlToMarkdown(editorRef.current));
    }
    handleCopy(e);
    document.execCommand("delete");
    handleInput();
  };

  return (
    <div
      className="nm-card"
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        padding: "1.5rem",
        minHeight: "560px",
      }}
    >
      <h3 style={{ margin: "0 0 0.85rem", fontSize: "1rem", fontWeight: 700 }}>
        Job Description
      </h3>

      <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
        <div
          ref={editorRef}
          contentEditable
          suppressContentEditableWarning
          onInput={handleInput}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          onCopy={handleCopy}
          onCut={handleCut}
          className="textarea custom-scrollbar jd-rich-editor"
          data-placeholder="Paste the target job description here (Markdown supported: # headings, - bullets, --- dividers)..."
          style={{
            flex: 1,
            height: "440px",
            minHeight: "440px",
            maxHeight: "440px",
            fontSize: "0.875rem",
            lineHeight: "1.65",
            overflowY: "auto",
            padding: "1rem 1.4rem",
            wordBreak: "break-word",
            boxSizing: "border-box",
            background: "var(--color-background)",
            border: "1px solid var(--color-border)",
            borderRadius: "8px",
            color: "var(--color-foreground)",
            outline: "none",
            cursor: "text",
          }}
        />

        <p
          className="text-xs text-muted"
          style={{
            marginTop: "0.6rem",
            fontFamily: "monospace",
            color:
              overLimit || nearLimit
                ? "var(--color-destructive)"
                : "var(--color-muted-fg)",
            fontWeight: nearLimit ? 600 : 400,
            flexShrink: 0,
          }}
        >
          {wordCount} words · {jdLen.toLocaleString()} / {maxChars.toLocaleString()} chars
          {nearLimit && !overLimit && ` · ${charsRemaining} remaining`}
          {overLimit && ` · over by ${Math.abs(charsRemaining)}`}
        </p>
        {overLimit && (
          <p
            className="text-xs"
            style={{ color: "var(--color-destructive)", marginTop: "0.25rem", flexShrink: 0 }}
          >
            Job description too long (max {maxChars.toLocaleString()} characters)
          </p>
        )}
        {jdTrimLen > 0 && jdTrimLen < 10 && (
          <p
            className="text-xs"
            style={{ color: "var(--color-destructive)", marginTop: "0.25rem", flexShrink: 0 }}
          >
            Job description too short (min 10 characters)
          </p>
        )}
      </div>
    </div>
  );
}
