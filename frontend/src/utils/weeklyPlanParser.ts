export interface PlanSection {
  title: string;
  items: string[];
}

function stripMarkdownBold(text: string): string {
  return text.replace(/\*\*(.*?)\*\*/g, '$1').trim();
}

/** Split a weekly plan markdown string into day/section cards with bullet items. */
export function parseWeeklyPlanSections(plan: string): PlanSection[] {
  const sections: PlanSection[] = [];
  let current: PlanSection | null = null;
  let miscItems: string[] = [];

  for (const rawLine of plan.split('\n')) {
    const line = rawLine.trim();
    if (!line) continue;

    if (line.startsWith('## ') || line.startsWith('### ')) {
      if (current && current.items.length > 0) {
        sections.push(current);
      }
      current = { title: line.replace(/^#+\s*/, ''), items: [] };
      continue;
    }

    if (line.startsWith('- ') || line.startsWith('* ')) {
      const item = stripMarkdownBold(line.slice(2));
      if (current) {
        current.items.push(item);
      } else {
        miscItems.push(item);
      }
      continue;
    }

    if (!line.startsWith('# ') && current && !line.startsWith('-')) {
      current.items.push(stripMarkdownBold(line));
    }
  }

  if (current && current.items.length > 0) {
    sections.push(current);
  }

  if (miscItems.length > 0) {
    sections.push({ title: 'Other', items: miscItems });
  }

  return sections;
}
