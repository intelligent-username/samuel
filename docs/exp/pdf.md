# PDF handling

The backend reads and writes resume PDFs with PyMuPDF (`fitz`). WeasyPrint is a fallback only.

## 1. Page sizes

The app accepts US Letter and A4 pages. It warns when Skills or Projects headers are missing and falls back to full text.

## 2. Render path

Primary path is `rewrite_pdf_layout()` in `backend/app/services/pdf_extractor.py`. It edits the source PDF in place. It keeps fonts, icons, layout, and ruling lines. It blanks the Skills and Projects areas and writes new text with matched styles.

Fallback path is `render_resume_to_pdf()` in `backend/app/services/pdf_renderer.py`. It builds a plain PDF with WeasyPrint. It runs only when no source PDF bytes exist. See `backend/app/orchestrator.py:155-163,251-257`.

The preview endpoint `GET /generate/{id}/preview-html` returns styled HTML for the in-app viewer. The download endpoint defaults to inline display and uses attachment only with `?download=true` or `?download=1`.

## 3. Common sense

Rules the backend follows when writing PDFs:

- Lines wrap instead of running off the page
- Resumes stay at most 2 pages long
- No page numbers
