import type { Metadata, Viewport } from 'next'
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
  metadataBase: new URL('https://phoring.in'),
  title: 'Phoring — Multi-Agent Decision Intelligence & Scenario Forecasting',
  description:
    'Turn documents into knowledge graphs, parallel Twitter and Reddit simulations, and evidence-linked forecast reports with agent interviews, confidence scoring and optional multi-model validation.',
  keywords: [
    'decision intelligence',
    'scenario simulation',
    'multi-agent simulation',
    'knowledge graph',
    'OASIS',
    'social simulation',
    'forecast reports',
    'evidence-linked AI',
    'agentic reporting',
  ],
  alternates: {
    canonical: '/',
  },
  openGraph: {
    title: 'Phoring — Multi-Agent Decision Intelligence & Scenario Forecasting',
    description:
      'Turn documents into knowledge graphs, parallel Twitter and Reddit simulations, and evidence-linked forecast reports with agent interviews, confidence scoring and optional multi-model validation.',
    type: 'website',
    url: 'https://phoring.in',
    siteName: 'Phoring',
    images: [{ url: '/phoring_logo.png', width: 1200, height: 630, alt: 'Phoring — decision intelligence' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Phoring — Multi-Agent Decision Intelligence & Scenario Forecasting',
    description:
      'Turn documents into knowledge graphs, parallel Twitter and Reddit simulations, and evidence-linked forecast reports.',
    images: ['/phoring_logo.png'],
  },
  icons: {
    icon: '/icon.png',
    apple: '/icon.png',
  },
  authors: [{ name: 'Reeturaj Goswami', url: 'https://github.com/inbharatai/phoring' }],
}

export const viewport: Viewport = {
  themeColor: '#050507',
}

const structuredData = {
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: 'Phoring',
  applicationCategory: 'Decision Intelligence',
  operatingSystem: 'Web',
  description:
    'Open-source decision-intelligence and social-simulation system. Ingest documents, build a Zep knowledge graph, run parallel Twitter and Reddit simulations, and generate evidence-linked forecasts with agent interviews, confidence scoring and optional multi-model validation.',
  url: 'https://phoring.in',
  codeRepository: 'https://github.com/inbharatai/phoring',
  license: 'https://github.com/inbharatai/phoring/blob/main/LICENSE',
  offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' },
  author: { '@type': 'Person', name: 'Reeturaj Goswami', url: 'https://github.com/inbharatai/phoring' },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="font-sans antialiased">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
        />
        {children}
      </body>
    </html>
  )
}
