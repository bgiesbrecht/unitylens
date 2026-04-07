interface StatusBadgeProps {
  status: string;
  label?: string;
}

const STATUS_LABELS: Record<string, string> = {
  connected: 'Connected',
  error: 'Error',
  crawling: 'Crawling',
  unknown: 'Unknown',
};

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const normalized = status?.toLowerCase() || 'unknown';
  const displayLabel = label || STATUS_LABELS[normalized] || status;

  return (
    <span className={`status-badge ${normalized}`}>
      <span className="status-badge-dot" />
      {displayLabel}
    </span>
  );
}
