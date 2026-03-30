import { Nav } from './components/Nav'
import { Hero } from './components/Hero'
import { WhatPhoring } from './components/WhatPhoring'
import { PipelineFlow } from './components/PipelineFlow'
import { UseCases } from './components/UseCases'
import { Differentiator } from './components/Differentiator'
import { TrustMethodology } from './components/TrustMethodology'
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
        <UseCases />
        <Differentiator />
        <TrustMethodology />
        <SimulationWorkbench />
        <FinalCTA />
      </main>
      <Footer />
    </>
  )
}
