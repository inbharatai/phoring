import { Nav } from './components/Nav'
import { Hero } from './components/Hero'
import { WhatPhoring } from './components/WhatPhoring'
import { PipelineFlow } from './components/PipelineFlow'
import { BeyondForecast } from './components/BeyondForecast'
import { ReportAgent } from './components/ReportAgent'
import { Architecture } from './components/Architecture'
import { UseCases } from './components/UseCases'
import { Differentiator } from './components/Differentiator'
import { TrustMethodology } from './components/TrustMethodology'
import { CloudNative } from './components/CloudNative'
import { SimulationWorkbench } from './components/SimulationWorkbench'
import { FinalCTA } from './components/FinalCTA'
import { Footer } from './components/Footer'

export default function Page() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <WhatPhoring />
        <PipelineFlow />
        <BeyondForecast />
        <ReportAgent />
        <Architecture />
        <UseCases />
        <Differentiator />
        <TrustMethodology />
        <CloudNative />
        <SimulationWorkbench />
        <FinalCTA />
      </main>
      <Footer />
    </>
  )
}