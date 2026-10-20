import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'EGX Tracker',
  description: 'EGX live quotes, screener, news and backtests',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body>
        {children}
        <footer className="foot">
          <span>EGX Tracker</span>
          <span>Data for information only — not investment advice.</span>
        </footer>
      </body>
    </html>
  )
}
