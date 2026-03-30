'use client'

import { useRef, type ReactNode } from 'react'
import { motion, useInView } from 'motion/react'

interface Props {
  children: ReactNode
  className?: string
  delay?: number
  y?: number
}

export function ScrollReveal({
  children,
  className = '',
  delay = 0,
  y = 40,
}: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })

  return (
    <motion.div
      ref={ref}
      className={className}
      initial={{ opacity: 0, y }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{
        duration: 0.8,
        delay,
        ease: [0.21, 0.47, 0.32, 0.98],
      }}
    >
      {children}
    </motion.div>
  )
}
