'use client'

import { useEffect, useState } from 'react'
import type { QuoteRow, SparkRow } from '@/lib/api'
import {
  addCustomSymbol,
  deleteCustomSymbol,
  getCustomSymbols,
  getQuotes,
  getSparks,
} from '@/lib/api'
import StatusBanner from '@/components/StatusBanner'
import WatchlistTable from '@/components/WatchlistTable'

const WATCHLIST = ['COMI', 'HRHO', 'ABUK', 'TMGH', 'SWDY', 'EAST', 'ETEL', 'AMOC']

export default function Home() {
  const [rows, setRows] = useState<QuoteRow[]>([])
  const [sparks, setSparks] = useState<Record<string, number[]>>({})
  const [offline, setOffline] = useState(false)
  const [customs, setCustoms] = useState<string[]>([])
  const [input, setInput] = useState('')
  const [msg, setMsg] = useState('')

  useEffect(() => {
    let alive = true
    const load = async () => {
      const list = Array.from(new Set([...WATCHLIST, ...customs]))
      const [cRes, qRes, sRes] = await Promise.allSettled([
        getCustomSymbols(),
        getQuotes(list.join(',')),
        getSparks(list),
      ])
      if (cRes.status === 'fulfilled') {
        const syms = cRes.value.symbols ?? []
        const merge = (prev: string[]) => {
          const next = Array.from(new Set([...prev, ...syms]))
          return next.join(',') === prev.join(',') ? prev : next
        }
        if (alive) setCustoms(merge)
      }
      if (qRes.status === 'fulfilled') {
        if (!alive) return
        setRows((qRes.value.rows ?? []) as QuoteRow[])
        setOffline(false)
      } else if (alive) {
        setOffline(true)
      }
      if (sRes.status === 'fulfilled') {
        const map: Record<string, number[]> = {}
        for (const r of (sRes.value.rows ?? []) as SparkRow[]) map[r.ticker] = r.spark ?? []
        if (alive) setSparks(map)
      } else if (alive) {
        setOffline(true)
      }
    }
    load()
    const t = setInterval(load, 20000)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [customs])

  const handleAdd = async () => {
    const sym = input.trim().toUpperCase()
    if (!sym) {
      setMsg('Enter a ticker first.')
      return
    }
    try {
      const res = await addCustomSymbol(sym)
      setMsg(res.message ?? 'Could not add symbol.')
      if (res.added) {
        setInput('')
        setCustoms((prev) => (prev.includes(sym) ? prev : [...prev, sym]))
      }
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Could not add symbol.')
    }
  }

  const handleRemove = async (sym: string) => {
    try {
      await deleteCustomSymbol(sym)
      setCustoms((prev) => prev.filter((s) => s !== sym))
      setMsg('')
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Could not remove symbol.')
    }
  }

  return (
    <main className="wrap">
      <h1>EGX Watchlist</h1>
      <StatusBanner />
      {offline && <div className="off">Backend not reachable on /api</div>}
      <WatchlistTable rows={rows} sparks={sparks} />
      <section className="addsym">
        <h2>➕ Add stock</h2>
        <div>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void handleAdd()
            }}
            placeholder="Add a ticker, e.g. HELIO"
          />
          <button onClick={() => void handleAdd()}>Add</button>
        </div>
        {msg ? <div className="hint">{msg}</div> : null}
        {customs.length > 0 ? (
          <div className="chips">
            {customs.map((s) => (
              <span className="chip" key={s}>
                {s}
                <button aria-label={'Remove ' + s} onClick={() => void handleRemove(s)}>
                  ×
                </button>
              </span>
            ))}
          </div>
        ) : null}
      </section>
    </main>
  )
}
