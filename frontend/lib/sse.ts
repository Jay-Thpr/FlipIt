import { supabase } from './supabase';
import { API_BASE_URL } from '../constants/config';

export interface SSEEvent {
  event: string;
  data: any;
  id?: string;
}

export type SSECallback = (event: SSEEvent) => void;
export type SSEErrorCallback = (error: Error) => void;

/**
 * Connect to an SSE stream for a given run.
 * Returns an abort function to close the connection.
 */
export function connectToRunStream(
  runId: string,
  onEvent: SSECallback,
  onError?: SSEErrorCallback,
  onComplete?: () => void,
): () => void {
  const controller = new AbortController();
  let stopped = false;

  async function start() {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const headers: Record<string, string> = {
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
      };
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`;
      }

      const url = `${API_BASE_URL}/runs/${runId}/stream`;
      const response = await fetch(url, {
        headers,
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`SSE connection failed: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body reader available');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (!stopped) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEvent = 'message';
        let currentData = '';

        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            currentData = line.slice(5).trim();
          } else if (line === '' && currentData) {
            // Empty line = end of event
            try {
              const parsed = JSON.parse(currentData);
              onEvent({ event: currentEvent, data: parsed });

              // Check for terminal events
              if (currentEvent === 'pipeline_complete' || currentEvent === 'pipeline_failed') {
                onComplete?.();
                return;
              }
            } catch {
              onEvent({ event: currentEvent, data: currentData });
            }
            currentEvent = 'message';
            currentData = '';
          }
        }
      }
      // Stream ended without a terminal event (e.g., server closed connection during pause)
      if (!stopped) {
        onComplete?.();
      }
    } catch (err: any) {
      if (err.name === 'AbortError' || stopped) return;
      onError?.(err instanceof Error ? err : new Error(String(err)));
    }
  }

  start();

  return () => {
    stopped = true;
    controller.abort();
  };
}
