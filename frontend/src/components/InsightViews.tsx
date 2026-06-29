import type { ReactNode } from 'react';
import MarkdownContent from './MarkdownContent';
import { parseWeeklyPlanSections } from '../utils/weeklyPlanParser';

export interface DeadlineTask {
  id?: string;
  title: string;
  deadline: string;
  priority?: string;
  status?: string;
}

export interface DeadlineSummaryData {
  overdue?: DeadlineTask[];
  upcoming?: DeadlineTask[];
  completed?: DeadlineTask[];
}

type InsightVariant = 'dashboard' | 'compact';

interface VariantProps {
  variant?: InsightVariant;
}

function panelClass(variant: InsightVariant): string {
  return variant === 'dashboard' ? 'insight-panel insight-panel--dashboard' : 'insight-panel insight-panel--compact';
}

function gridClass(variant: InsightVariant): string {
  return variant === 'dashboard' ? 'insight-grid' : 'insight-grid insight-grid--compact';
}

function SectionCard({
  title,
  titleClassName,
  children,
  variant,
}: {
  title: string;
  titleClassName?: string;
  children: ReactNode;
  variant: InsightVariant;
}) {
  if (variant === 'dashboard') {
    return (
      <div className={`schedule-day-card ${titleClassName || ''}`}>
        <h4 className={`schedule-day-title ${titleClassName || ''}`}>{title}</h4>
        <div className="schedule-item-list">{children}</div>
      </div>
    );
  }

  return (
    <div className="insight-section">
      <div className={`insight-section-title ${titleClassName || ''}`}>{title}</div>
      {children}
    </div>
  );
}

function ItemRow({
  children,
  itemClassName,
  variant,
}: {
  children: ReactNode;
  itemClassName?: string;
  variant: InsightVariant;
}) {
  if (variant === 'dashboard') {
    return <div className={`schedule-task-title ${itemClassName || ''}`}>{children}</div>;
  }
  return <div className={`insight-item ${itemClassName || ''}`}>{children}</div>;
}

export function ScheduleInsightView({
  schedule,
  variant = 'dashboard',
  overdueTitles,
}: {
  schedule: Record<string, string[]>;
  overdueTitles?: Set<string>;
} & VariantProps) {
  const entries = Object.entries(schedule);
  if (entries.length === 0) return null;

  const itemClass = (day: string, item: string) => {
    if (day === 'Completed') return 'completed-item';
    if (overdueTitles?.has(item)) return 'overdue-item';
    return '';
  };

  if (variant === 'dashboard') {
    return (
      <div className={gridClass(variant)}>
        {entries.map(([day, items]) => (
          <SectionCard
            key={day}
            title={day}
            titleClassName={day === 'Completed' ? 'completed-day' : ''}
            variant={variant}
          >
            {items.map((item, i) => (
              <ItemRow
                key={i}
                variant={variant}
                itemClassName={itemClass(day, item)}
              >
                {item}
              </ItemRow>
            ))}
          </SectionCard>
        ))}
      </div>
    );
  }

  return (
    <div className={panelClass(variant)}>
      {entries.map(([day, items]) => (
        <SectionCard key={day} title={day} variant={variant}>
          {items.map((item, i) => (
            <ItemRow key={i} variant={variant}>
              {item}
            </ItemRow>
          ))}
        </SectionCard>
      ))}
    </div>
  );
}

export function DeadlineSummaryView({
  data,
  variant = 'dashboard',
}: {
  data: DeadlineSummaryData;
} & VariantProps) {
  const overdue = data.overdue || [];
  const upcoming = data.upcoming || [];
  const completed = data.completed || [];
  const hasAny = overdue.length > 0 || upcoming.length > 0 || completed.length > 0;

  if (!hasAny) {
    return (
      <div className="insight-empty">No tasks with deadlines found.</div>
    );
  }

  const groups = [
    { key: 'overdue', title: 'Overdue', tasks: overdue, titleClass: 'overdue-section', itemClass: 'overdue-item' },
    { key: 'upcoming', title: 'Upcoming (Next 3 Days)', tasks: upcoming, titleClass: 'upcoming-section', itemClass: 'upcoming-item' },
    { key: 'completed', title: 'Completed with Deadlines', tasks: completed, titleClass: 'completed-section', itemClass: 'completed-item' },
  ].filter((g) => g.tasks.length > 0);

  if (variant === 'dashboard') {
    return (
      <div className={gridClass(variant)}>
        {groups.map((group) => (
          <SectionCard
            key={group.key}
            title={group.title}
            titleClassName={group.titleClass}
            variant={variant}
          >
            {group.tasks.map((t, i) => (
              <ItemRow key={t.id || i} variant={variant} itemClassName={group.itemClass}>
                <strong>{t.title}</strong>
                <span className="insight-item-meta"> — Due: {t.deadline}</span>
              </ItemRow>
            ))}
          </SectionCard>
        ))}
      </div>
    );
  }

  return (
    <div className={panelClass(variant)}>
      {groups.map((group) => (
        <SectionCard
          key={group.key}
          title={group.title}
          titleClassName={group.titleClass}
          variant={variant}
        >
          {group.tasks.map((t, i) => (
            <ItemRow key={t.id || i} variant={variant} itemClassName={group.itemClass}>
              {t.title} — {t.deadline}
            </ItemRow>
          ))}
        </SectionCard>
      ))}
    </div>
  );
}

export function WeeklyPlanView({
  plan,
  variant = 'dashboard',
}: {
  plan: string;
} & VariantProps) {
  if (variant === 'dashboard') {
    return (
      <div className="weekly-plan-scroll">
        <MarkdownContent text={plan} />
      </div>
    );
  }

  const sections = parseWeeklyPlanSections(plan);

  if (sections.length === 0) {
    return (
      <div className="chat-artifact">
        {plan.split('\n').map((line, idx) => (
          <p key={idx} className="chat-artifact-item">
            {line || '\u00A0'}
          </p>
        ))}
      </div>
    );
  }

  return (
    <div className="chat-artifact">
      {sections.map((section) => (
        <div key={section.title} className="chat-artifact-section">
          <strong>{section.title}</strong>
          {section.items.map((item, i) => (
            <div key={i} className="chat-artifact-item">
              {item}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
