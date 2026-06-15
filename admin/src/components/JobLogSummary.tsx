import { useMemo } from 'react';
import { Job } from '../api/client';
import { JobEvent, jobEventLabel, parseJobEvents, stripJobEventsFromLog } from '../utils/jobEvents';

type Props = {
  job: Pick<Job, 'log_tail' | 'failure_hint' | 'status' | 'events'>;
};

export function JobLogSummary({ job }: Props) {
  const events = useMemo(() => {
    if (job.events && job.events.length > 0) {
      return job.events as JobEvent[];
    }
    return parseJobEvents(job.log_tail || '');
  }, [job.events, job.log_tail]);
  const logText = useMemo(() => stripJobEventsFromLog(job.log_tail || ''), [job.log_tail]);

  return (
    <div className="job-log-detail">
      {events.length > 0 && (
        <ol className="job-event-timeline" data-testid="job-event-timeline">
          {events.map((ev, index) => (
            <li
              key={`${ev.event}-${index}`}
              className={`job-event-chip job-event-chip--${ev.event}`}
            >
              {jobEventLabel(ev)}
            </li>
          ))}
        </ol>
      )}
      <div className="log-box">{logText || job.log_tail || '…'}</div>
      {job.failure_hint && (
        <p className="job-failure-hint muted">{job.failure_hint}</p>
      )}
    </div>
  );
}
