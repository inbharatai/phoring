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
  title: 'Phoring — Predict Anything. Source-Cited Scenario Forecasts',
  description:
    'Phoring is a universal decision-intelligence engine. Upload documents, describe any scenario, and get a simulation-backed, source-cited forecast with confidence scoring and multi-AI consensus.',
  openGraph: {
    title: 'Phoring — Predict Anything. Source-Cited Scenario Forecasts',
    description: 'From documents to simulation-backed forecasts. Multi-agent simulation, knowledge graphs, and source-cited prediction reports — for any scenario you can describe.',
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
