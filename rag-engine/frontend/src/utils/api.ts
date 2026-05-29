import { Citation, IngestResponse, SearchResponse } from '../types'

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

// ── SEARCH ────────────────────────────────────────────────────────────────────

export async function searchQuery(query: string, topK = 5): Promise<SearchResponse> {
  const res = await fetch(`${BASE_URL}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: topK }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function* searchStream(
  query: string,
  topK = 5,
): AsyncGenerator<{ type: 'citations'; data: Citation[] } | { type: 'token'; data: string } | { type: 'done' }> {
  const res = await fetch(`${BASE_URL}/search/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: topK, stream: true }),
  })

  if (!res.ok) throw new Error(await res.text())

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (line.startsWith('event: citations')) continue
      if (line.startsWith('data: ')) {
        const data = line.slice(6)
        if (data === '[DONE]') {
          yield { type: 'done' }
          return
        }
        try {
          const parsed = JSON.parse(data)
          if (Array.isArray(parsed)) {
            yield { type: 'citations', data: parsed as Citation[] }
          } else {
            yield { type: 'token', data }
          }
        } catch {
          yield { type: 'token', data }
        }
      }
    }
  }
}

// ── INGEST ────────────────────────────────────────────────────────────────────

export async function ingestFile(
  file: File,
  strategy = 'recursive',
): Promise<IngestResponse> {
  const form = new FormData()
  form.append('file', file)
  form.append('chunk_strategy', strategy)
  const res = await fetch(`${BASE_URL}/ingest/upload`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function ingestUrl(
  url: string,
  strategy = 'recursive',
): Promise<IngestResponse> {
  const params = new URLSearchParams({ url, chunk_strategy: strategy })
  const res = await fetch(`${BASE_URL}/ingest/url?${params}`, { method: 'POST' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
