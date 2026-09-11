"use client";

import React, { useRef, useEffect, useCallback } from "react";
import {
  markdownToHtml,
  htmlToMarkdown,
  setCaretToEnd,
  tryHandleMarkdownShortcut,
  extractMarkdownFromSelection,
} from "@/lib/markdown-editor";

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
  const [isEmpty, setIsEmpty] = useState(!jobDesc.trim());
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
    setIsEmpty(!previousMd.trim());
    onChange(previousMd);
    setCaretToEnd(editorRef.current);
  }, [onChange]);

  const handleRedo = useCallback(() => {
    if (redoStackRef.current.length === 0 || !editorRef.current) return;
    const currentMd = htmlToMarkdown(editorRef.current);
    const nextMd = redoStackRef.current.pop()!;
    undoStackRef.current.push(currentMd);

    lastReportedMd.current = nextMd;
    editorRef.current.innerHTML = markdownToHtml(nextMd);
    setIsEmpty(!nextMd.trim());
    onChange(nextMd);
    setCaretToEnd(editorRef.current);
  }, [onChange]);

  // Sync external markdown changes into editor HTML only when not focused
  useEffect(() => {
    if (!editorRef.current) return;
    const isFocused = document.activeElement === editorRef.current;
    if (!editorRef.current.innerHTML && jobDesc) {
      editorRef.current.innerHTML = markdownToHtml(jobDesc);
      setIsEmpty(!jobDesc.trim());
      lastReportedMd.current = jobDesc;
    } else if (jobDesc !== lastReportedMd.current) {
      lastReportedMd.current = jobDesc;
      if (!isFocused) {
        editorRef.current.innerHTML = markdownToHtml(jobDesc);
        setIsEmpty(!jobDesc.trim());
      }
    }
  }, [jobDesc]);

  const handleInput = useCallback(() => {
    if (!editorRef.current) return;
    const text = editorRef.current.innerText.replace(/\u200B/g, "").trim();
    if (!text) {
      editorRef.current.innerHTML = "";
      setIsEmpty(true);
    } else {
      setIsEmpty(false);
    }

    const md = htmlToMarkdown(editorRef.current);
    lastReportedMd.current = md;
    onChange(md);

    if (typingTimerRef.current) clearTimeout(typingTimerRef.current);
    typingTimerRef.current = setTimeout(() => {
      pushHistory(textBeforeTypingRef.current);
      textBeforeTypingRef.current = md;
    }, 450);
  }, [onChange, pushHistory]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    // Undo / Redo
    if ((e.ctrlKey || e.metaKey) && (e.key === "z" || e.key === "Z")) {
      e.preventDefault();
      if (e.shiftKey) handleRedo();
      else handleUndo();
      return;
    }

    if ((e.ctrlKey || e.metaKey) && (e.key === "y" || e.key === "Y")) {
      e.preventDefault();
      handleRedo();
      return;
    }

    // Ctrl+Enter to generate
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      onEnterGenerate();
      return;
    }

    if ([" ", "Enter", "Backspace"].includes(e.key) && editorRef.current) {
      textBeforeTypingRef.current = htmlToMarkdown(editorRef.current);
    }

    // Markdown shortcut expansion
    if (editorRef.current) {
      const handled = tryHandleMarkdownShortcut(e, editorRef.current, () => {
        if (editorRef.current) pushHistory(htmlToMarkdown(editorRef.current));
      });
      if (handled) {
        handleInput();
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
    const isSelectAll = Boolean(
      sel &&
      sel.rangeCount > 0 &&
      !sel.isCollapsed &&
      editorRef.current &&
      sel.toString().trim().length >= (editorRef.current.innerText.trim().length - 2)
    );

    if (isEditorEmpty || isSelectAll) {
      if (editorRef.current) {
        editorRef.current.innerHTML = html;
        setCaretToEnd(editorRef.current);
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
    if (!selection || !editorRef.current) return;
    const md = extractMarkdownFromSelection(selection, editorRef.current);
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
          <p className="text-xs jd-error-msg">
            Job description too long (max {maxChars.toLocaleString()} characters)
          </p>
        )}
        {jdTrimLen > 0 && jdTrimLen < 10 && (
          <p className="text-xs jd-error-msg">
            Job description too short (min 10 characters)
          </p>
        )}
      </div>
    </div>
  );
}
