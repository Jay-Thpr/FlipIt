/**
 * Gemini Nano Banana - Photo Enhancement Pipeline
 *
 * 1. analyzeItemPhoto  → Gemini Vision identifies the item
 * 2. generateWhiteBackgroundPhoto → Gemini Image Generation produces a clean product photo
 */

const GEMINI_API_KEY = 'AIzaSyBVJMtygdqs4Rw_w552UH8WTR84PFfbUeI';
const VISION_MODEL = 'gemini-2.5-flash';
// Nano Banana 2 = gemini-3.1-flash-image-preview (1/100 RPM, 4/1K RPD — barely used)
const NANO_BANANA_MODEL = 'gemini-3.1-flash-image-preview';
const BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/models';

export interface ItemAnalysis {
  name: string;
  description: string;
  brand?: string;
  condition?: string;
}

/**
 * Step 1: Identify the item using Gemini Vision.
 * Returns structured metadata that can prefill the listing form.
 */
export async function analyzeItemPhoto(
  base64Image: string,
  mimeType: string = 'image/jpeg'
): Promise<ItemAnalysis> {
  const response = await fetch(
    `${BASE_URL}/${VISION_MODEL}:generateContent?key=${GEMINI_API_KEY}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [
          {
            parts: [
              {
                inline_data: {
                  mime_type: mimeType,
                  data: base64Image,
                },
              },
              {
                text: `You are an expert resale product analyst. Examine this photo and respond ONLY with valid JSON — no markdown, no explanation:
{
  "name": "<Brand + item type, e.g. Vintage Carhartt Detroit Jacket>",
  "description": "<2-sentence compelling resale listing description highlighting condition, key features, and demand>",
  "brand": "<brand name or empty string>",
  "condition": "<one of: New, Like New, Good, Fair, Poor>"
}`,
              },
            ],
          },
        ],
        generationConfig: { temperature: 0.1, maxOutputTokens: 300 },
      }),
    }
  );

  const data = await response.json();
  const raw = data?.candidates?.[0]?.content?.parts?.[0]?.text ?? '';

  try {
    const cleaned = raw
      .replace(/```json\n?/g, '')
      .replace(/```\n?/g, '')
      .trim();
    return JSON.parse(cleaned) as ItemAnalysis;
  } catch {
    // Graceful fallback — return whatever text we got as the name
    return {
      name: raw.slice(0, 80).trim() || 'Resale Item',
      description: '',
    };
  }
}

/**
 * Step 2: Generate a professional white-background product photo using Nano Banana.
 * Uses the nano-banana-pro-preview model (confirmed available via ListModels).
 * Returns a data-URI string (data:image/png;base64,...) or null on failure.
 */
export async function generateWhiteBackgroundPhoto(
  itemDescription: string,
  base64SourceImage: string,
  mimeType: string = 'image/jpeg'
): Promise<string | null> {
  const prompt =
    `Generate a professional e-commerce product photograph of: ${itemDescription}. ` +
    `The item must be perfectly isolated on a pure white background. ` +
    `Flat-lay or upright studio shot, soft diffused studio lighting, sharp focus, ` +
    `photorealistic, high resolution. No shadows, no text, no watermarks, no props.`;

  try {
    const response = await fetch(
      `${BASE_URL}/${NANO_BANANA_MODEL}:generateContent?key=${GEMINI_API_KEY}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [
            {
              parts: [
                {
                  inline_data: {
                    mime_type: mimeType,
                    data: base64SourceImage,
                  },
                },
                { text: prompt },
              ],
            },
          ],
          generationConfig: {
            responseModalities: ['IMAGE', 'TEXT'],
            temperature: 0.8,
          },
        }),
      }
    );

    const data = await response.json();
    const parts: any[] = data?.candidates?.[0]?.content?.parts ?? [];

    for (const part of parts) {
      if (part?.inline_data?.mime_type?.startsWith('image/')) {
        return `data:${part.inline_data.mime_type};base64,${part.inline_data.data}`;
      }
    }

    console.warn('[Nano Banana] No image in response:', JSON.stringify(data).slice(0, 400));
    return null;
  } catch (e) {
    console.error('[Nano Banana] Error:', e);
    return null;
  }
}
