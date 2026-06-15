/** 将后端 UTC 时间字符串格式化为本地时间。 */
export function formatUtcTime(value?: string): string {
  if (!value) return '—';
  const iso = value.replace(' UTC', 'Z').replace(' ', 'T');
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return value.replace(' UTC', '');
  }
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}
