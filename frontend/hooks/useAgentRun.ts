import { useState, useEffect, useRef, useCallback } from 'react';
import {
  startSellRun,
  startBuyRun,
  getLatestRun,
  submitSellCorrection,
  submitListingDecision,
  AgentRunResult,
} from '../lib/api';
import { connectToRunStream, SSEEvent } from '../lib/sse';

// ─── Types ──────────���───────────────────────────────────────────────────────

export interface AgentStep {
  name: string;
  status: 'running' | 'completed' | 'error';
  summary?: string;
}

export interface VisionResult {
  brand: string;
  item_name: string;
  detected_item: string;
  model: string | null;
  condition: string;
  confidence: number;
  search_query: string;
  clean_photo_url?: string;
}

export interface PricingResult {
  recommended_price: number;
  profit_margin: number;
  median_price: number;
  trend?: string;
  velocity?: string;
  sample_size?: number;
}

export interface CorrectedItem {
  brand: string;
  item_name: string;
  model: string;
  condition: string;
  search_query: string;
}

export interface UseAgentRunReturn {
  run: AgentRunResult | null;
  runLoading: boolean;
  runError: string | null;
  agentSteps: AgentStep[];
  visionResult: VisionResult | null;
  pricingResult: PricingResult | null;
  needsVisionCorrection: boolean;
  needsListingReview: boolean;
  startSellPipeline: (itemId: string, imageUrls: string[], notes: string) => Promise<void>;
  startBuyPipeline: (itemId: string, query: string, budget: number) => Promise<void>;
  submitCorrection: (runId: string, correctedItem: CorrectedItem) => Promise<void>;
  submitDecision: (sessionId: string, decision: 'confirm_submit' | 'revise' | 'abort', instructions?: string) => Promise<void>;
  fetchLatestRun: (itemId: string) => Promise<void>;
  stopStream: () => void;
  resetRun: () => void;
}

// ─── Hook ───────────────────────────────────────────────────────────────────

export function useAgentRun(): UseAgentRunReturn {
  const [run, setRun] = useState<AgentRunResult | null>(null);
  const [runLoading, setRunLoading] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>([]);
  const [visionResult, setVisionResult] = useState<VisionResult | null>(null);
  const [pricingResult, setPricingResult] = useState<PricingResult | null>(null);
  const [needsVisionCorrection, setNeedsVisionCorrection] = useState(false);
  const [needsListingReview, setNeedsListingReview] = useState(false);
  const stopStreamRef = useRef<(() => void) | null>(null);
  const itemIdRef = useRef<string | null>(null);

  useEffect(() => {
    return () => { stopStreamRef.current?.(); };
  }, []);

  function handleSSEEvent(event: SSEEvent) {
    const agentName = event.data?.agent_name || event.data?.step;

    if (event.event === 'agent_started') {
      setAgentSteps(prev => [...prev, { name: agentName, status: 'running' }]);
    } else if (event.event === 'agent_completed') {
      setAgentSteps(prev => prev.map(s =>
        s.name === agentName ? { ...s, status: 'completed', summary: event.data.summary } : s
      ));
    } else if (event.event === 'agent_error') {
      setAgentSteps(prev => prev.map(s =>
        s.name === agentName ? { ...s, status: 'error', summary: event.data.error } : s
      ));
    } else if (event.event === 'vision_result') {
      setVisionResult({
        brand: event.data.brand ?? '',
        item_name: event.data.item_name ?? event.data.detected_item ?? '',
        detected_item: event.data.detected_item ?? event.data.item_name ?? '',
        model: event.data.model ?? null,
        condition: event.data.condition ?? 'Good',
        confidence: event.data.confidence ?? 0,
        search_query: event.data.search_query ?? '',
        clean_photo_url: event.data.clean_photo_url,
      });
    } else if (event.event === 'vision_low_confidence') {
      setNeedsVisionCorrection(true);
      setRunLoading(false);
      if (itemIdRef.current) {
        getLatestRun(itemIdRef.current).then(setRun).catch(() => {});
      }
    } else if (event.event === 'pricing_result') {
      setPricingResult({
        recommended_price: event.data.recommended_price ?? event.data.recommended_list_price ?? 0,
        profit_margin: event.data.profit_margin ?? 0,
        median_price: event.data.median_price ?? 0,
        trend: event.data.trend,
        velocity: event.data.velocity,
        sample_size: event.data.sample_size,
      });
    } else if (event.event === 'pipeline_complete') {
      if (itemIdRef.current) {
        getLatestRun(itemIdRef.current).then(setRun).catch(() => {});
      }
    } else if (event.event === 'pipeline_failed') {
      setRunError(event.data.error || 'Pipeline failed');
    } else if (event.event === 'listing_review_required') {
      setNeedsListingReview(true);
      setRunLoading(false);
      if (itemIdRef.current) {
        getLatestRun(itemIdRef.current).then(setRun).catch(() => {});
      }
    }
  }

  async function connectStream(runId: string) {
    stopStreamRef.current?.();
    stopStreamRef.current = connectToRunStream(
      runId,
      handleSSEEvent,
      (err) => { setRunError(err.message); },
      () => { setRunLoading(false); },
    );
  }

  const startSellPipeline = useCallback(async (itemId: string, imageUrls: string[], notes: string) => {
    itemIdRef.current = itemId;
    setRunLoading(true);
    setRunError(null);
    setAgentSteps([]);
    setVisionResult(null);
    setPricingResult(null);
    setNeedsVisionCorrection(false);
    setNeedsListingReview(false);
    try {
      const response = await startSellRun(itemId, { image_urls: imageUrls, notes });
      const runId = response.run_id || response.session_id;
      connectStream(runId);
    } catch (err: any) {
      setRunError(err.message);
      setRunLoading(false);
    }
  }, []);

  const startBuyPipeline = useCallback(async (itemId: string, query: string, budget: number) => {
    itemIdRef.current = itemId;
    setRunLoading(true);
    setRunError(null);
    setAgentSteps([]);
    setVisionResult(null);
    setPricingResult(null);
    setNeedsVisionCorrection(false);
    setNeedsListingReview(false);
    try {
      const response = await startBuyRun(itemId, { query, budget });
      const runId = response.run_id || response.session_id;
      connectStream(runId);
    } catch (err: any) {
      setRunError(err.message);
      setRunLoading(false);
    }
  }, []);

  const submitCorrectionFn = useCallback(async (runId: string, correctedItem: CorrectedItem) => {
    try {
      await submitSellCorrection(runId, correctedItem);
      setNeedsVisionCorrection(false);
      setVisionResult(null);
      setPricingResult(null);
      setRunLoading(true);
    } catch (err: any) {
      setRunError(err.message);
    }
  }, []);

  const submitDecisionFn = useCallback(async (
    sessionId: string,
    decision: 'confirm_submit' | 'revise' | 'abort',
    instructions?: string,
  ) => {
    try {
      await submitListingDecision(sessionId, decision, instructions);
      setNeedsListingReview(false);
      if (decision !== 'abort' && itemIdRef.current) {
        getLatestRun(itemIdRef.current).then(setRun).catch(() => {});
      }
    } catch (err: any) {
      setRunError(err.message);
    }
  }, []);

  const fetchLatestRun = useCallback(async (itemId: string) => {
    itemIdRef.current = itemId;
    try {
      const result = await getLatestRun(itemId);
      setRun(result);

      // Derive paused-state flags from the fetched run so the UI is
      // reachable even when the user navigated away and came back.
      if (result.phase === 'awaiting_user_correction') {
        setNeedsVisionCorrection(true);
        // Populate visionResult from the run's next_action suggestion
        // so the correction form can pre-fill.
        const suggestion = result.next_action?.payload?.suggestion;
        if (suggestion) {
          setVisionResult({
            brand: suggestion.brand ?? '',
            item_name: suggestion.item_name ?? suggestion.detected_item ?? '',
            detected_item: suggestion.detected_item ?? '',
            model: suggestion.model ?? null,
            condition: suggestion.condition ?? 'Good',
            confidence: suggestion.confidence ?? 0,
            search_query: suggestion.search_query ?? '',
            clean_photo_url: suggestion.clean_photo_url,
          });
        }
      } else if (result.phase === 'awaiting_listing_review') {
        setNeedsListingReview(true);
      }
    } catch {
      // No run exists yet — that's fine
    }
  }, []);

  const stopStream = useCallback(() => {
    stopStreamRef.current?.();
    stopStreamRef.current = null;
  }, []);

  const resetRun = useCallback(() => {
    stopStream();
    setRun(null);
    setRunLoading(false);
    setRunError(null);
    setAgentSteps([]);
    setVisionResult(null);
    setPricingResult(null);
    setNeedsVisionCorrection(false);
    setNeedsListingReview(false);
    itemIdRef.current = null;
  }, [stopStream]);

  return {
    run,
    runLoading,
    runError,
    agentSteps,
    visionResult,
    pricingResult,
    needsVisionCorrection,
    needsListingReview,
    startSellPipeline,
    startBuyPipeline,
    submitCorrection: submitCorrectionFn,
    submitDecision: submitDecisionFn,
    fetchLatestRun,
    stopStream,
    resetRun,
  };
}
