import type { Metadata } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import './globals.css'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Phoring — Financial Instability Early Warning',
  description:
    'AI early-warning and scenario intelligence for financial instability and geopolitical risk. Source-grounded risk scenarios, confidence-scored reports, and alerts.',
  openGraph: {
    title: 'Phoring — Financial Instability Early Warning',
    description: 'Detect early signs of financial instability from geopolitical, policy, and market signals. Source-cited scenarios with confidence scoring.',
    type: 'website',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  )
}
