/* eslint-disable @typescript-eslint/no-explicit-any */

interface DataTableColumn {
  key: string;
  header: string;
  render?: (row: any) => React.ReactNode;
  width?: string;
}

interface DataTableProps {
  columns: DataTableColumn[];
  data: any[];
  emptyMessage?: string;
  onRowClick?: (row: any) => void;
}

export function DataTable({
  columns,
  data,
  emptyMessage,
  onRowClick,
}: DataTableProps) {
  if (data.length === 0) {
    return (
      <div className="empty-state" style={{ padding: '32px 24px' }}>
        <p className="empty-state-desc">{emptyMessage || 'No data available'}</p>
      </div>
    );
  }

  return (
    <div className="data-table-wrapper">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} style={col.width ? { width: col.width } : undefined}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr
              key={i}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              style={onRowClick ? { cursor: 'pointer' } : undefined}
            >
              {columns.map((col) => (
                <td key={col.key}>
                  {col.render ? col.render(row) : String(row[col.key] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
