import { useState, useRef, useEffect, useCallback } from 'react'
import { Upload, Send, FileText, Link, Zap, Database, Search, ChevronDown, X, AlertCircle } from 'lucide-react'
import { Message, Citation, ChunkStrategy } from './types'
import { searchStream, ingestFile, ingestUrl } from './utils/api'

// ── CITATION PANEL ────────────────────────────────────────────────────────────

function CitationPanel({ citations, onClose }: { citations: Citation[]; onClose: () => void }) {
  const sourceIcons: Record<string, string> = { pdf: '📄', confluence: '📘', slack: '💬', text: '📝', html: '🌐' }
  return (
    <div className="fixed right-0 top-0 h-full w-80 bg-[#0d1117] border-l border-[#1e2530] z-50 flex flex-col shadow-2xl">
      <div className="flex items-center justify-between p-4 border-b border-[#1e2530]">
        <span className="font-mono text-xs tracking-widest uppercase text-[#00e5ff]">Sources ({citations.length})</span>
        <button onClick={onClose} className="text-[#64748b] hover:text-white transition-colors"><X size={16} /></button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {citations.map((c) => (
          <div key={c.index} className="bg-[#111620] border border-[#1e2530] rounded p-3 hover:border-[#00e5ff33] transition-colors">
            <div className="flex items-start gap-2 mb-2">
              <span className="text-lg leading-none">{sourceIcons[c.source_type] || '📄'}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-[#f59e0b] bg-[#f59e0b12] border border-[#f59e0b25] px-1.5 py-0.5 rounded">[{c.index}]</span>
                  <span className="font-mono text-[10px] text-[#64748b] uppercase tracking-wider">{c.source_type}</span>
                  {c.page && <span className="font-mono text-[10px] text-[#64748b]">p.{c.page}</span>}
                </div>
                <p className="text-xs text-[#94a3b8] mt-1 truncate">{c.source}</p>
              </div>
            </div>
            <p className="text-xs text-[#64748b] leading-relaxed line-clamp-3">{c.preview}</p>
            <div className="mt-2 flex items-center gap-1">
              <div className="flex-1 h-1 bg-[#1e2530] rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-[#00e5ff] to-[#7c3aed] rounded-full" style={{ width: `${Math.min(c.score * 100, 100)}%` }} />
              </div>
              <span className="font-mono text-[10px] text-[#64748b]">{(c.score * 100).toFixed(0)}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── MESSAGE BUBBLE ────────────────────────────────────────────────────────────

function MessageBubble({ msg, onCiteClick }: { msg: Message; onCiteClick: (citations: Citation[]) => void }) {
  const renderContent = (text: string) => {
    const parts = text.split(/(\[Source \d+\])/g)
    return parts.map((part, i) => {
      const match = part.match(/\[Source (\d+)\]/)
      if (match) {
        return <span key={i} className="citation-badge" onClick={() => msg.citations && onCiteClick(msg.citations)}>{part}</span>
      }
      return <span key={i}>{part}</span>
    })
  }

  if (msg.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] bg-[#00e5ff12] border border-[#00e5ff25] rounded px-4 py-3 text-sm text-[#e2e8f0]">
          {msg.content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-3">
      <div className="w-7 h-7 rounded bg-gradient-to-br from-[#00e5ff] to-[#7c3aed] flex items-center justify-center flex-shrink-0 mt-1">
        <Zap size={12} className="text-black" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-mono text-[10px] text-[#00e5ff] tracking-wider uppercase">RAG Engine</span>
          {msg.chunksRetrieved !== undefined && (
            <span className="font-mono text-[10px] text-[#64748b]">{msg.chunksRetrieved} chunks retrieved</span>
          )}
        </div>
        <div className={`text-sm text-[#94a3b8] leading-relaxed ${msg.isStreaming ? 'streaming-cursor' : ''}`}>
          {renderContent(msg.content)}
        </div>
        {msg.citations && msg.citations.length > 0 && !msg.isStreaming && (
          <button
            onClick={() => onCiteClick(msg.citations!)}
            className="mt-2 flex items-center gap-1.5 font-mono text-[10px] text-[#64748b] hover:text-[#f59e0b] transition-colors"
          >
            <FileText size={10} />
            {msg.citations.length} source{msg.citations.length > 1 ? 's' : ''}
          </button>
        )}
      </div>
    </div>
  )
}

// ── INGEST PANEL ──────────────────────────────────────────────────────────────

function IngestPanel() {
  const [strategy, setStrategy] = useState<ChunkStrategy>('recursive')
  const [urlInput, setUrlInput] = useState('')
  const [status, setStatus] = useState<{ type: 'success' | 'error'; msg: string } | null>(null)
  const [loading, setLoading] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setLoading(true)
    setStatus(null)
    try {
      const res = await ingestFile(file, strategy)
      setStatus({ type: 'success', msg: `✓ ${res.chunks_created} chunks ingested from "${file.name}"` })
    } catch (err: any) {
      setStatus({ type: 'error', msg: `✗ ${err.message}` })
    } finally {
      setLoading(false)
    }
  }

  const handleUrl = async () => {
    if (!urlInput.trim()) return
    setLoading(true)
    setStatus(null)
    try {
      const res = await ingestUrl(urlInput, strategy)
      setStatus({ type: 'success', msg: `✓ ${res.chunks_created} chunks ingested from URL` })
      setUrlInput('')
    } catch (err: any) {
      setStatus({ type: 'error', msg: `✗ ${err.message}` })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-4 space-y-4">
      <div>
        <label className="font-mono text-[10px] tracking-widest uppercase text-[#64748b] block mb-1.5">Chunk Strategy</label>
        <div className="flex gap-2">
          {(['recursive', 'token', 'semantic'] as ChunkStrategy[]).map((s) => (
            <button
              key={s}
              onClick={() => setStrategy(s)}
              className={`font-mono text-[10px] tracking-wider uppercase px-2.5 py-1 rounded border transition-all ${
                strategy === s ? 'border-[#00e5ff] text-[#00e5ff] bg-[#00e5ff0a]' : 'border-[#1e2530] text-[#64748b] hover:border-[#64748b]'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="font-mono text-[10px] tracking-widest uppercase text-[#64748b] block mb-1.5">Upload File</label>
        <input ref={fileRef} type="file" accept=".pdf,.txt,.md,.html,.json" onChange={handleFile} className="hidden" />
        <button
          onClick={() => fileRef.current?.click()}
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 border border-dashed border-[#1e2530] hover:border-[#00e5ff33] rounded p-4 text-[#64748b] hover:text-[#00e5ff] transition-all"
        >
          <Upload size={14} />
          <span className="font-mono text-xs">PDF, TXT, MD, HTML, JSON</span>
        </button>
      </div>

      <div>
        <label className="font-mono text-[10px] tracking-widest uppercase text-[#64748b] block mb-1.5">Ingest URL</label>
        <div className="flex gap-2">
          <input
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleUrl()}
            placeholder="https://docs.example.com/page"
            className="flex-1 bg-[#0d1117] border border-[#1e2530] rounded px-3 py-2 font-mono text-xs text-[#e2e8f0] placeholder-[#64748b] outline-none focus:border-[#00e5ff] transition-colors"
          />
          <button
            onClick={handleUrl}
            disabled={loading || !urlInput.trim()}
            className="bg-[#00e5ff] text-black font-mono text-xs font-medium px-3 rounded hover:bg-white transition-colors disabled:opacity-40"
          >
            <Link size={12} />
          </button>
        </div>
      </div>

      {status && (
        <div className={`font-mono text-xs p-2.5 rounded border ${
          status.type === 'success' ? 'text-[#10b981] bg-[#10b98110] border-[#10b98125]' : 'text-red-400 bg-red-400/10 border-red-400/25'
        }`}>
          {loading && <span className="inline-block w-2 h-2 bg-current rounded-full animate-pulse mr-2" />}
          {status.msg}
        </div>
      )}
    </div>
  )
}

// ── MAIN APP ──────────────────────────────────────────────────────────────────

export default function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '0',
      role: 'assistant',
      content: 'RAG Knowledge Search Engine ready. Ingest your documents, then ask anything — I\'ll retrieve relevant chunks, re-rank them, and generate a cited answer.',
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [activeCitations, setActiveCitations] = useState<Citation[] | null>(null)
  const [sidebarTab, setSidebarTab] = useState<'ingest' | 'info'>('ingest')
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const sendMessage = useCallback(async () => {
    const query = input.trim()
    if (!query || loading) return
    setInput('')
    setLoading(true)

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: query, timestamp: new Date() }
    const assistantId = (Date.now() + 1).toString()
    const assistantMsg: Message = { id: assistantId, role: 'assistant', content: '', isStreaming: true, timestamp: new Date() }

    setMessages((prev) => [...prev, userMsg, assistantMsg])

    try {
      let citations: Citation[] = []
      let fullText = ''

      for await (const event of searchStream(query)) {
        if (event.type === 'citations') {
          citations = event.data
          setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, citations, chunksRetrieved: event.data.length } : m))
        } else if (event.type === 'token') {
          fullText += event.data
          const snap = fullText
          setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, content: snap } : m))
        } else if (event.type === 'done') {
          break
        }
      }
      setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, isStreaming: false } : m))
    } catch (err: any) {
      setMessages((prev) => prev.map((m) =>
        m.id === assistantId ? { ...m, content: `Error: ${err.message}`, isStreaming: false } : m
      ))
    } finally {
      setLoading(false)
    }
  }, [input, loading])

  const EXAMPLE_QUERIES = [
    'How does hybrid retrieval work?',
    'What chunking strategy is best for PDFs?',
    'Explain cross-encoder re-ranking',
    'How are citations generated?',
  ]

  return (
    <div className="flex h-screen overflow-hidden">

      {/* ── SIDEBAR ── */}
      <aside className="w-72 flex-shrink-0 bg-[#0d1117] border-r border-[#1e2530] flex flex-col">
        <div className="p-4 border-b border-[#1e2530]">
          <div className="font-display text-2xl tracking-wider text-white">RAG ENGINE</div>
          <div className="font-mono text-[10px] text-[#00e5ff] tracking-widest mt-0.5">ENTERPRISE KNOWLEDGE SEARCH</div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-px bg-[#1e2530] border-b border-[#1e2530]">
          {[['10K+', 'Docs'], ['80%', 'Faster'], ['Hybrid', 'Search'], ['Cited', 'Answers']].map(([v, l]) => (
            <div key={l} className="bg-[#0d1117] p-3 text-center">
              <div className="font-display text-lg text-[#00e5ff] leading-none">{v}</div>
              <div className="font-mono text-[9px] text-[#64748b] tracking-wider uppercase mt-0.5">{l}</div>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div className="flex border-b border-[#1e2530]">
          {(['ingest', 'info'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setSidebarTab(tab)}
              className={`flex-1 font-mono text-[10px] tracking-widest uppercase py-2.5 transition-colors ${
                sidebarTab === tab ? 'text-[#00e5ff] border-b border-[#00e5ff]' : 'text-[#64748b] hover:text-[#94a3b8]'
              }`}
            >
              {tab === 'ingest' ? <><Upload size={9} className="inline mr-1" />Ingest</> : <><Database size={9} className="inline mr-1" />Info</>}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto">
          {sidebarTab === 'ingest' ? (
            <IngestPanel />
          ) : (
            <div className="p-4 space-y-3">
              {[
                ['Stack', 'FastAPI · LangChain · ChromaDB'],
                ['LLM', 'GPT-4o / Llama 3'],
                ['Embeddings', 'text-embedding-3-small'],
                ['Retrieval', 'Vector + BM25 hybrid'],
                ['Re-ranker', 'ms-marco cross-encoder'],
                ['Streaming', 'Server-Sent Events'],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between items-start gap-2">
                  <span className="font-mono text-[10px] tracking-wider text-[#64748b] uppercase flex-shrink-0">{k}</span>
                  <span className="font-mono text-[10px] text-[#94a3b8] text-right">{v}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="p-4 border-t border-[#1e2530]">
          <a href="https://github.com/sid-cha/rag-engine" target="_blank"
            className="flex items-center justify-center gap-2 w-full border border-[#1e2530] hover:border-[#00e5ff33] rounded p-2.5 font-mono text-[10px] text-[#64748b] hover:text-[#00e5ff] transition-all">
            View on GitHub ↗
          </a>
        </div>
      </aside>

      {/* ── MAIN CHAT ── */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-3 border-b border-[#1e2530] bg-[#080a0f]">
          <div className="flex items-center gap-2">
            <Search size={14} className="text-[#00e5ff]" />
            <span className="font-mono text-xs tracking-wider text-[#94a3b8]">Semantic Search · Hybrid Retrieval · Real-time Responses</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse" />
            <span className="font-mono text-[10px] text-[#64748b]">READY</span>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} msg={msg} onCiteClick={setActiveCitations} />
          ))}
          <div ref={chatEndRef} />
        </div>

        {/* Example queries */}
        {messages.length <= 1 && (
          <div className="px-6 pb-3 flex flex-wrap gap-2">
            {EXAMPLE_QUERIES.map((q) => (
              <button
                key={q}
                onClick={() => { setInput(q) }}
                className="font-mono text-[10px] text-[#64748b] border border-[#1e2530] hover:border-[#00e5ff33] hover:text-[#00e5ff] px-3 py-1.5 rounded transition-all"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div className="px-6 pb-6">
          <div className="flex gap-3 bg-[#111620] border border-[#1e2530] rounded p-1.5 focus-within:border-[#00e5ff33] transition-colors">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
              placeholder="Ask anything about your documents..."
              className="flex-1 bg-transparent font-mono text-sm text-[#e2e8f0] placeholder-[#64748b] outline-none px-3 py-2"
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="bg-[#00e5ff] text-black font-mono text-xs font-medium px-4 py-2 rounded hover:bg-white transition-colors disabled:opacity-40 flex items-center gap-1.5"
            >
              {loading ? <span className="w-3 h-3 border border-black border-t-transparent rounded-full animate-spin" /> : <Send size={12} />}
              {loading ? 'Searching' : 'Ask'}
            </button>
          </div>
          <p className="font-mono text-[9px] text-[#64748b] mt-1.5 px-3">↵ to send · Sources cited inline · Powered by GPT-4o + ChromaDB</p>
        </div>
      </main>

      {/* Citations Panel */}
      {activeCitations && <CitationPanel citations={activeCitations} onClose={() => setActiveCitations(null)} />}
    </div>
  )
}
