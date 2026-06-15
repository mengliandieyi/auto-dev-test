export type JobEvent = {
  job_id?: string;
  event: string;
  command?: string;
  project?: string;
  exit_code?: number;
  message?: string;
};

const PREFIX = '[job-event] ';

export function parseJobEvents(log: string): JobEvent[] {
  const events: JobEvent[] = [];
  for (const line of (log || '').split('\n')) {
    if (!line.startsWith(PREFIX)) continue;
    try {
      events.push(JSON.parse(line.slice(PREFIX.length)) as JobEvent);
    } catch {
      /* ignore malformed lines */
    }
  }
  return events;
}

export function jobEventLabel(ev: JobEvent): string {
  switch (ev.event) {
    case 'start':
      return `开始 ${ev.command || '任务'}${ev.project ? ` · ${ev.project}` : ''}`;
    case 'finish':
      return ev.exit_code === 0 ? '完成' : `结束（退出码 ${ev.exit_code ?? '?'}）`;
    case 'error':
      return `错误：${ev.message || '未知'}`;
    default:
      return ev.event;
  }
}

export function stripJobEventsFromLog(log: string): string {
  return (log || '')
    .split('\n')
    .filter((line) => !line.startsWith(PREFIX))
    .join('\n')
    .trimEnd();
}
