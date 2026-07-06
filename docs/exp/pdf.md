# Expectations

These are the standard expectations of the backend for different aspects of the project.

## 1. Resume PDF Page Dimensions & Editor Guidelines

Resumes have standard page dimensions based on the following job application regions:

|    Standard   | Dimensions (Points) | Dimensions (Inches) |  Dimensions (mm) |         Region        |
| ------------- | ------------------- | ------------------- | ---------------- | --------------------- |
| **US Letter** |    `612 x 792 pt`   |      8.5" x 11"     | 215.9 x 279.4 mm | United States, Canada |
|    **A4**     |    `595 x 842 pt`   |    8.27" x 11.69"   |   210 x 297 mm   |     Rest of World     |

> The system will accept pages with alternative sizes but will give a warning.

---

## 2. Editor Layout Behavior

The stream-editor (`b.py`) dynamically reads document properties to ensure replacement edits fit target constraints perfectly:

* **Visible Boundaries (`CropBox` / `page.rect`)**: Used as the hard boundary for rendering text. The editor checks height limits (`page.rect.height`) to prevent bottom-of-the-page overflow.
* **Layout Geometry Protection**: Rather than using static margins, the editor analyzes the target paragraph's existing coordinates (`first_line_x`, `subsequent_x`, `y_first`, `y_last`) to anchor alignment and wrap text correctly.
* **Tab Stops**: Indentation formatting like tabs (`\t`) are dynamically parsed into relative offsets (36pt per tab) and added directly to the anchor offsets, ensuring robust alignment across any page size specification.

---

## 3. Common Sense

Rules that the backend will adhere to when producing PDFs but won't force the user to follow.

- Lines don't overflow off the page (wrap instead)
- Resumes are <= 2 pages long
- No page numbers
