export interface ResumeEntry {
  title?: string;
  meta?: string;
  subtitle?: string;
  subMeta?: string;
  bullets: string[];
  textLines: string[];
}

export interface ResumeSection {
  title: string;
  entries: ResumeEntry[];
}

export interface ParsedResume {
  name: string;
  contact: string[];
  sections: ResumeSection[];
}

const SECTION_RE = /^(?:#+\s*)?(skills|technical skills|projects|selected projects|experience|work experience|employment|education|summary|professional summary|objective|certifications?|awards?|publications?|languages?)(?:\s*:)?$/i;

const DATE_OR_LOC_RE = /\b(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}|\d{4}\s*[-–—to]\s*(?:Present|Current|\d{4})|Graduation|Expected|\b\d{4}\b)|^[A-Z][a-zA-Z\s.\-]+,\s*[A-Z]{2}\b/i;

export function parseResumeText(rawText: string): ParsedResume {
  if (!rawText || !rawText.trim()) {
    return { name: "", contact: [], sections: [] };
  }

  // 1. Normalize literal \n or escaped newlines
  const text = rawText
    .replace(/\\r\\n/g, "\n")
    .replace(/\\n/g, "\n")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(/[\u0000-\u001F\u007F-\u009F\uE000-\uF8FF]/g, "")
    .replace(/[§ï]/g, "");

  const lines = text.split("\n");
  let name = "";
  const contact: string[] = [];
  const sections: ResumeSection[] = [];

  let currentSection: ResumeSection | null = null;
  let currentEntry: ResumeEntry | null = null;
  let i = 0;

  // 2. Extract Candidate Name (first line)
  while (i < lines.length && !lines[i].trim()) i++;
  if (i < lines.length) {
    name = lines[i].trim().replace(/^#+\s*/, "").replace(/\*\*/g, "");
    i++;
  }

  // 3. Extract Contact bar (next non-empty line with phone, email, or pipe/dash)
  while (i < lines.length && !lines[i].trim()) i++;
  if (i < lines.length) {
    const line = lines[i].trim();
    if (line.includes("@") || line.includes("|") || line.includes("—") || line.includes("–") || line.includes("+") || /portfolio|github|linkedin/i.test(line)) {
      const parts = line.split(/[|—–•·]/).map((p) => p.replace(/^[\s#~]+|[\s#~]+$/g, "").trim()).filter(Boolean);
      contact.push(...parts);
      i++;
    }
  }

  const pushEntry = () => {
    if (!currentSection || !currentEntry) return;
    if (currentEntry.title || currentEntry.bullets.length > 0 || currentEntry.textLines.length > 0) {
      currentSection.entries.push(currentEntry);
    }
    currentEntry = null;
  };

  const pushSection = () => {
    pushEntry();
    if (currentSection && (currentSection.entries.length > 0 || currentSection.title)) {
      sections.push(currentSection);
    }
    currentSection = null;
  };

  // 4. Parse Sections
  for (; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    // Check Section Header (## Section or UPPERCASE Section)
    const isMdSec = /^##\s+([^#]+)$/.test(line);
    const isNamedSec = SECTION_RE.test(line);

    if (isMdSec || (isNamedSec && !line.startsWith("-") && !line.startsWith("•"))) {
      pushSection();
      const title = line.replace(/^#+\s*/, "").replace(/:$/, "").trim();
      currentSection = { title, entries: [] };
      continue;
    }

    if (!currentSection) {
      currentSection = { title: "Summary", entries: [] };
    }

    // Check Bullet
    const bulletMatch = /^[-*•–▪]\s*(.*)/.exec(line);
    if (bulletMatch) {
      if (!currentEntry) currentEntry = { bullets: [], textLines: [] };
      currentEntry.bullets.push(bulletMatch[1].trim());
      continue;
    }

    // Check Markdown Subheader (### ...)
    const isMdSub = /^###\s+(.*)/.exec(line);
    if (isMdSub) {
      pushEntry();
      currentEntry = { title: isMdSub[1].trim(), bullets: [], textLines: [] };
      continue;
    }

    // Structured Entry lines (Education / Experience / Projects)
    const secLower = currentSection.title.toLowerCase();
    if (secLower.includes("education") || secLower.includes("experience") || secLower.includes("project")) {
      if (!currentEntry) {
        currentEntry = { title: line, bullets: [], textLines: [] };
        continue;
      }

      if (!currentEntry.meta && DATE_OR_LOC_RE.test(line)) {
        currentEntry.meta = line;
        continue;
      }

      if (!currentEntry.subtitle && !DATE_OR_LOC_RE.test(line)) {
        currentEntry.subtitle = line;
        continue;
      }

      if (!currentEntry.subMeta && DATE_OR_LOC_RE.test(line)) {
        currentEntry.subMeta = line;
        continue;
      }

      // If already complete, start next entry
      if (currentEntry.meta && (currentEntry.subtitle || currentEntry.bullets.length > 0)) {
        pushEntry();
        currentEntry = { title: line, bullets: [], textLines: [] };
        continue;
      }
    }

    // Default text line
    if (!currentEntry) currentEntry = { bullets: [], textLines: [] };
    currentEntry.textLines.push(line);
  }

  pushSection();
  return { name, contact, sections };
}
