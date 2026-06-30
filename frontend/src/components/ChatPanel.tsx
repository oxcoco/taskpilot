import { useCallback, useEffect, useRef, useState } from 'react';
import MarkdownContent from './MarkdownContent';

const API_BASE = 'http://127.0.0.1:5000/api';

export interface PendingAction {
  id: string;
  action_name: string;
  summary: string;
  details: Record<string, unknown>;
  destructive: boolean;
}

export interface ChatArtifact {
  type: string;
  data: Record<string, unknown>;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  approval?: PendingAction | null;
  artifacts?: ChatArtifact | null;
}

interface DeadlineTask {
  id?: string;
  title: string;
  deadline: string;
}

interface ChatPanelProps {
  onTasksChanged?: () => void;
}

function renderDeadlineSummaryMarkdown(data: {
  overdue?: DeadlineTask[];
  upcoming?: DeadlineTask[];
  completed?: DeadlineTask[];
}) {
  const sections: string[] = [];

  const appendSection = (title: string, tasks: DeadlineTask[] | undefined) => {
    if (!tasks || tasks.length === 0) return;
    sections.push(`## ${title}`);
    for (const task of tasks) {
      sections.push(`- **${task.title}** — Due: ${task.deadline}`);
    }
  };

  appendSection('Overdue', data.overdue);
  appendSection('Upcoming', data.upcoming);
  appendSection('Completed', data.completed);

  return sections.join('\n');
}

function renderScheduleMarkdown(schedule: Record<string, string[]>) {
  return Object.entries(schedule)
    .map(([day, items]) => {
      const lines = [`## ${day}`];
      for (const item of items) {
        lines.push(`- ${item}`);
      }
      return lines.join('\n');
    })
    .join('\n\n');
}

function ArtifactRenderer({ artifact }: { artifact: ChatArtifact }) {
  if (artifact.type === 'deadline_summary') {
    const data = artifact.data as {
      overdue?: DeadlineTask[];
      upcoming?: DeadlineTask[];
      completed?: DeadlineTask[];
    };
    const markdown = renderDeadlineSummaryMarkdown(data);
    return markdown ? <MarkdownContent text={markdown} className="chat-markdown" /> : null;
  }

  if (artifact.type === 'weekly_plan') {
    const plan = (artifact.data as { plan?: string }).plan || '';
    return <MarkdownContent text={plan} className="chat-markdown" />;
  }

  if (artifact.type === 'schedule') {
    const schedule =
      (artifact.data as { schedule?: Record<string, string[]> }).schedule ||
      (artifact.data as Record<string, string[]>);
    const markdown = renderScheduleMarkdown(schedule);
    return markdown ? <MarkdownContent text={markdown} className="chat-markdown" /> : null;
  }

  if (artifact.type === 'task_list') {
    const tasks = (artifact.data as { tasks?: { title: string; status: string }[] }).tasks || [];
    return (
      <div className="chat-artifact">
        {tasks.map((t, i) => (
          <div key={i} className="chat-artifact-item">
            {t.title} [{t.status}]
          </div>
        ))}
      </div>
    );
  }

  return null;
}

function ApprovalCard({
  pending,
  onApprove,
  onReject,
  loading,
}: {
  pending: PendingAction;
  onApprove: () => void;
  onReject: () => void;
  loading: boolean;
}) {
  return (
    <div className={`approval-card ${pending.destructive ? 'destructive' : ''}`}>
      <div className="approval-card-title">Confirm action</div>
      <div className="approval-card-summary">{pending.summary}</div>
      {pending.destructive && (
        <div className="approval-card-warning">This action cannot be undone.</div>
      )}
      <div className="approval-card-actions">
        <button className="btn btn-secondary" onClick={onReject} disabled={loading}>
          Reject
        </button>
        <button className="btn btn-primary" onClick={onApprove} disabled={loading}>
          Approve
        </button>
      </div>
    </div>
  );
}

export default function ChatPanel({ onTasksChanged }: ChatPanelProps) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: 'Hi! I can help you manage tasks, check deadlines, and build schedules. What would you like to do?',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(() =>
    sessionStorage.getItem('taskpilot_chat_session')
  );
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, open]);

  const appendAssistant = useCallback(
    (content: string, approval?: PendingAction | null, artifacts?: ChatArtifact | null) => {
      setMessages((prev) => [...prev, { role: 'assistant', content, approval, artifacts }]);
    },
    []
  );

  const handleResponse = useCallback(
    (data: {
      session_id: string;
      message: string;
      approval_required?: boolean;
      pending_action?: PendingAction | null;
      artifacts?: ChatArtifact | null;
    }) => {
      setSessionId(data.session_id);
      sessionStorage.setItem('taskpilot_chat_session', data.session_id);
      appendAssistant(
        data.message,
        data.approval_required ? data.pending_action : null,
        data.artifacts
      );
      if (!data.approval_required && data.artifacts) {
        onTasksChanged?.();
      }
    },
    [appendAssistant, onTasksChanged]
  );

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: sessionId }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || 'Chat request failed');
      }
      const data = await res.json();
      handleResponse(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      appendAssistant(`Sorry, something went wrong: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  const handleApproval = async (pending: PendingAction, approved: boolean) => {
    if (!sessionId || loading) return;
    setLoading(true);
    try {
      const endpoint = approved ? 'approve' : 'reject';
      const res = await fetch(`${API_BASE}/chat/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          pending_action_id: pending.id,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || 'Approval request failed');
      }
      const data = await res.json();
      setMessages((prev) =>
        prev.map((m) => (m.approval?.id === pending.id ? { ...m, approval: null } : m))
      );
      appendAssistant(data.message, null, data.artifacts);
      if (approved) {
        onTasksChanged?.();
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      appendAssistant(`Sorry, something went wrong: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button
        type="button"
        className="chat-fab"
        onClick={() => setOpen((o) => !o)}
        aria-label="Open chat assistant"
      >
        {open ? '✕' : '💬'}
      </button>

      {open && (
        <div className="chat-panel">
          <div className="chat-panel-header">
            <span>TaskPilot Assistant</span>
            <button type="button" className="chat-close-btn" onClick={() => setOpen(false)}>
              ✕
            </button>
          </div>

          <div className="chat-messages">
            {messages.map((msg, idx) => (
              <div key={idx} className={`chat-message ${msg.role}`}>
                {msg.content ? (
                  <div className="chat-bubble">
                    {msg.role === 'assistant' ? (
                      <MarkdownContent text={msg.content} className="chat-markdown" />
                    ) : (
                      msg.content
                    )}
                  </div>
                ) : null}
                {msg.artifacts && <ArtifactRenderer artifact={msg.artifacts} />}
                {msg.approval && (
                  <ApprovalCard
                    pending={msg.approval}
                    loading={loading}
                    onApprove={() => handleApproval(msg.approval!, true)}
                    onReject={() => handleApproval(msg.approval!, false)}
                  />
                )}
              </div>
            ))}
            {loading && (
              <div className="chat-message assistant">
                <div className="chat-bubble chat-typing">Thinking…</div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form className="chat-input-form" onSubmit={sendMessage}>
            <input
              type="text"
              className="chat-input"
              placeholder="Ask about tasks, deadlines, schedules…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
            />
            <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()}>
              Send
            </button>
          </form>
        </div>
      )}
    </>
  );
}
