export interface Citation {
  index: number
  source: string
  page?: number
  source_type: 'pdf' | 'confluence' | 'slack' | 'text' | 'html'
  score: number
  preview: string
}

export interface SearchResponse {
  query: string
  answer: string
  citations: Citation[]
  chunks_retrieved: number
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  isStreaming?: boolean
  chunksRetrieved?: number
  timestamp: Date
}

export interface IngestResponse {
  source: string
  chunks_created: number
  message: string
}

export type ChunkStrategy = 'recursive' | 'token' | 'semantic'
