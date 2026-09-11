export function markdownToHtml(md: string): string {
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

    // Heading 1-4: # ..., ## ..., ### ..., #### ...
    const headingMatch = line.match(/^(#{1,4})\s*(.*)/);
    if (headingMatch) {
      if (inUl) { html += "</ul>"; inUl = false; }
      if (inOl) { html += "</ol>"; inOl = false; }
      const level = headingMatch[1].length;
      const content = headingMatch[2];
      html += `<h${level}>${content ? formatInline(content) : "<br>"}</h${level}>`;
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

    // Normal paragraph
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

export function htmlToMarkdown(root: HTMLElement): string {
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

  return walk(root).replace(/\n{3,}/g, "\n\n").replace(/^\n+/, "");
}
