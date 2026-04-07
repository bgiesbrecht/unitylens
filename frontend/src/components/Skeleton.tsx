interface SkeletonProps {
  variant?: 'text' | 'text-lg' | 'card' | 'row';
  count?: number;
  width?: string;
}

export function Skeleton({ variant = 'text', count = 1, width }: SkeletonProps) {
  const className = {
    text: 'skeleton skeleton-text',
    'text-lg': 'skeleton skeleton-text-lg',
    card: 'skeleton skeleton-card',
    row: 'skeleton skeleton-row',
  }[variant];

  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={className}
          style={width ? { width } : undefined}
        />
      ))}
    </>
  );
}

export function CardSkeleton() {
  return (
    <div className="card" style={{ padding: 24 }}>
      <Skeleton variant="text-lg" />
      <Skeleton variant="text" width="60%" />
      <div style={{ height: 12 }} />
      <Skeleton variant="text" width="80%" />
      <Skeleton variant="text" width="40%" />
    </div>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div>
      <Skeleton variant="row" count={rows} />
    </div>
  );
}
