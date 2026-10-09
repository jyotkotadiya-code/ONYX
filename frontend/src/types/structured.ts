export type AllowedComponentType =
  | 'text'
  | 'table'
  | 'chart'
  | 'stat'
  | 'list'
  | 'timeline'
  | 'comparison'
  | 'code'
  | 'source';

export type AllowedResponseType = 'text' | 'single' | 'composite';

export interface SourceItem {
  document_id?: string | null;
  filename: string;
  page?: number | null;
  chunk_id?: string | null;
  table?: string | null;
  row_id?: string | null;
  locator?: string | null;
}

export interface ComponentItem {
  id: string;
  type: AllowedComponentType;
  title?: string | null;
  data: Record<string, any>;
}

export interface ResponsePlan {
  intent: string;
  requires_calculation: boolean;
  requires_table: boolean;
  requires_chart: boolean;
  requires_stat: boolean;
  requires_timeline: boolean;
  requires_comparison: boolean;
  selected_components: AllowedComponentType[];
}

export interface StructuredResponse {
  schema_version: string;
  version: number;
  title: string;
  intent: string;
  response_type: AllowedResponseType;
  plan?: ResponsePlan | null;
  components: ComponentItem[];
  sources: SourceItem[];
  confidence?: number | null;
  history_versions?: Array<Record<string, any>>;
}
