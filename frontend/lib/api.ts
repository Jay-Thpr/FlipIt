import { supabase } from './supabase';
import { API_BASE_URL } from '../constants/config';

async function getAuthHeaders(): Promise<Record<string, string>> {
  const { data: { session } } = await supabase.auth.getSession();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`;
  }
  return headers;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: { ...headers, ...options?.headers },
  });
  if (!res.ok) {
    const errorText = await res.text().catch(() => 'Unknown error');
    throw new Error(`API ${res.status}: ${errorText}`);
  }
  return res.json();
}

// --- Types ---

export interface RunStartResponse {
  session_id: string;
  run_id?: string;
  stream_url: string;
  result_url: string;
  run_url?: string;
}

export interface SellListingReviewState {
  state: string;
  step: string;
  platform: string;
  latest_decision: 'confirm_submit' | 'revise' | 'abort' | null;
  revision_instructions: string | null;
  revision_count: number;
  paused_at: string | null;
  deadline_at: string | null;
}

export interface AgentRunResult {
  session_id: string;
  run_id: string;
  item_id: string | null;
  pipeline: 'sell' | 'buy';
  status: 'queued' | 'running' | 'paused' | 'completed' | 'failed';
  phase: string;
  created_at: string;
  updated_at: string;
  request: any;
  result: any;
  error: string | null;
  events: any[];
  next_action: { type: string; payload: any };
  progress: { step: string | null; event_type: string | null } | null;
  result_source: string | null;
  sell_listing_review: SellListingReviewState | null;
  sell_summary?: {
    detected_item: string | null;
    brand: string | null;
    confidence: number | null;
    recommended_price: number | null;
    listing_title: string | null;
    listing_price: number | null;
    listing_status: string | null;
    ready_for_confirmation: boolean;
  };
}

export interface AgentInfo {
  name: string;
  slug: string;
  port: number;
}

export interface FetchAgentInfo extends AgentInfo {
  agentverse_address: string | null;
  description: string;
}

// --- Endpoints ---

/** Start a sell pipeline run for an item */
export async function startSellRun(itemId: string, input: { image_urls?: string[]; notes?: string }) {
  return apiFetch<RunStartResponse>(`/items/${itemId}/sell/run`, {
    method: 'POST',
    body: JSON.stringify({ input }),
  });
}

/** Start a buy pipeline run for an item */
export async function startBuyRun(itemId: string, input: { query: string; budget?: number }) {
  return apiFetch<RunStartResponse>(`/items/${itemId}/buy/run`, {
    method: 'POST',
    body: JSON.stringify({ input }),
  });
}

/** Get the current state of a run */
export async function getRunResult(runId: string) {
  return apiFetch<AgentRunResult>(`/runs/${runId}`);
}

/** Get the latest run for an item */
export async function getLatestRun(itemId: string) {
  return apiFetch<AgentRunResult>(`/items/${itemId}/runs/latest`);
}

/** Submit a vision correction for a paused sell run */
export async function submitSellCorrection(runId: string, correctedItem: {
  brand: string;
  item_name: string;
  model: string;
  condition: string;
  search_query: string;
}) {
  return apiFetch<{ status: string }>(`/runs/${runId}/sell/correct`, {
    method: 'POST',
    body: JSON.stringify({ corrected_item: correctedItem }),
  });
}

/** Submit a listing decision for a paused sell run */
export async function submitListingDecision(runId: string, decision: 'confirm_submit' | 'revise' | 'abort', revisionInstructions?: string) {
  return apiFetch<{ status: string }>(`/runs/${runId}/sell/listing-decision`, {
    method: 'POST',
    body: JSON.stringify({
      decision,
      ...(revisionInstructions ? { revision_instructions: revisionInstructions } : {}),
    }),
  });
}

/** Get the list of backend agents */
export async function getAgents() {
  return apiFetch<{ agents: AgentInfo[] }>('/agents');
}

/** Get the list of Fetch.ai agents */
export async function getFetchAgents() {
  return apiFetch<{ agents: FetchAgentInfo[] }>('/fetch-agents');
}

/** Get backend config (master agent address) */
export async function getConfig() {
  return apiFetch<{ resale_copilot_agent_address: string }>('/config');
}

/** Get backend health */
export async function getHealth() {
  return apiFetch<{ status: string; agent_execution_mode: string; agent_count: string }>('/health');
}

/** Build the SSE stream URL for a run */
export function getStreamUrl(runId: string): string {
  return `${API_BASE_URL}/runs/${runId}/stream`;
}

/** AI-powered item analysis and professional photo generation */
export interface AnalyzeItemRequest {
  photo_url: string;
  item_id: string;
  generate_photos: boolean;
  photo_count?: number;
}

export interface AnalyzeItemResponse {
  name: string;
  description: string;
  condition: string;
  generated_photo_urls: string[];
}

export async function analyzeItem(request: AnalyzeItemRequest) {
  return apiFetch<AnalyzeItemResponse>('/ai/analyze-item', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}
