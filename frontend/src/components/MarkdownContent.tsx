import type { ReactNode } from 'react';

interface MarkdownContentProps {
  text: string;
  className?: string;
}

function renderInline(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const boldRegex = /\*\*(.*?)\*\*/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let key = 0;

  while ((match = boldRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }
    parts.push(<strong key={key++}>{match[1]}</strong>);
    lastIndex = boldRegex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts.length > 0 ? parts : [text];
}

/** Lightweight markdown renderer for assistant text and weekly plans. */
export default function MarkdownContent({ text, className = '' }: MarkdownContentProps) {
  if (!text) return null;

  const lines = text.split('\n');
  const nodes: ReactNode[] = [];
  let listItems: ReactNode[] = [];
  let key = 0;

  const flushList = () => {
    if (listItems.length === 0) return;
    nodes.push(
      <ul key={key++} className="md-list">
        {listItems}
      </ul>
    );
    listItems = [];
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();

    if (!line.trim()) {
      flushList();
      nodes.push(<div key={key++} className="md-spacer" />);
      continue;
    }

    if (line.startsWith('### ')) {
      flushList();
      nodes.push(
        <h4 key={key++} className="md-h4">
          {renderInline(line.slice(4))}
        </h4>
      );
      continue;
    }

    if (line.startsWith('## ')) {
      flushList();
      nodes.push(
        <h3 key={key++} className="md-h3">
          {renderInline(line.slice(3))}
        </h3>
      );
      continue;
    }

    if (line.startsWith('# ')) {
      flushList();
      nodes.push(
        <h2 key={key++} className="md-h2">
          {renderInline(line.slice(2))}
        </h2>
      );
      continue;
    }

    if (line.startsWith('- ') || line.startsWith('* ')) {
      listItems.push(
        <li key={key++} className="md-li">
          {renderInline(line.slice(2))}
        </li>
      );
      continue;
    }

    flushList();
    nodes.push(
      <p key={key++} className="md-p">
        {renderInline(line)}
      </p>
    );
  }

  flushList();
  return <div className={`markdown-content ${className}`.trim()}>{nodes}</div>;
}
