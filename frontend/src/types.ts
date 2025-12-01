/** API Types matching backend Pydantic models */

export interface QuoteResult {
  text: string;
  highlight: string | null;
  episode_number: number;
  episode_title: string;
  guest: string;
  youtube_id: string | null;
  timestamp: string | null;
  score: number;
  chunk_id: string;
}

export interface SearchResponse {
  query: string;
  results: QuoteResult[];
  total_results: number;
  search_time_ms: number;
}

export interface SearchRequest {
  query: string;
  top_k?: number;
  episode_filter?: number[];
  guest_filter?: string;
}

export interface HealthResponse {
  status: string;
  pinecone_connected: boolean;
  cohere_connected: boolean;
}
