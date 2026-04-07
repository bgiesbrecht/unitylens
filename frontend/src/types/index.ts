export interface Source {
  name: string;
  type: 'databricks' | 'snowflake' | 'oracle' | string;
  status: 'connected' | 'error' | 'crawling' | 'unknown';
  last_crawled?: string;
  catalogs_count?: number;
  tables_count?: number;
  host?: string;
}

export interface Catalog {
  name: string;
  source: string;
  schemas_count?: number;
}

export interface Schema {
  name: string;
  source: string;
  catalog: string;
  tables_count?: number;
}

export interface Column {
  name: string;
  type: string;
  nullable: boolean;
  comment?: string;
  position?: number;
}

export interface Table {
  name: string;
  source: string;
  catalog: string;
  schema: string;
  type?: string;
  description?: string;
  owner?: string;
  columns?: Column[];
  created_at?: string;
  updated_at?: string;
}

export interface SearchResult {
  source: string;
  catalog: string;
  schema: string;
  table: string;
  description?: string;
  relevance?: number;
  match_reason?: string;
}

export interface DashboardStats {
  total_sources: number;
  total_catalogs: number;
  total_schemas: number;
  total_tables: number;
  total_columns: number;
  last_crawl?: string;
}

export interface HealthCheck {
  status: string;
  version?: string;
  database?: string;
}

export interface CrawlResult {
  status: string;
  message: string;
  source?: string;
}

export interface SourceStatus {
  name: string;
  status: string;
  message?: string;
  last_checked?: string;
}
