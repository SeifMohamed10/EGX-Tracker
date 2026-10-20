'use client'

import { useEffect, useState } from 'react'
import type { StatusRow } from '@/lib/api'
import { getStatus } from '@/lib/api'

export default function StatusBanner() {
  const [status, setStatus] = useState<StatusRow | null>(null)

  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const s = await getStatus()
        if (!alive) return
        setStatus(s)
      } catch {
        if (!alive) return
        setStatus(null)
      }
    }
    load()
    const t = setInterval(load, 15000)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [])

  const open = !!status?.is_open
  return (
    <div className={open ? 'banner open' : 'banner closed'}>
      {open ? 'OPEN' : 'CLOSED'}
      <span className="state">{status?.is_open === undefined ? ' connecting…' : (status?.state ?? '')}</span>
    </div>
  )
}
