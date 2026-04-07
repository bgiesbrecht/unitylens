import { ChevronRight } from 'lucide-react';

export interface BreadcrumbItem {
  label: string;
  onClick?: () => void;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
}

export function Breadcrumb({ items }: BreadcrumbProps) {
  return (
    <nav className="breadcrumb">
      {items.map((item, i) => {
        const isLast = i === items.length - 1;
        return (
          <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            {i > 0 && <ChevronRight size={12} className="breadcrumb-separator" />}
            {isLast ? (
              <span className="breadcrumb-current">{item.label}</span>
            ) : (
              <span className="breadcrumb-item" onClick={item.onClick}>
                {item.label}
              </span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
