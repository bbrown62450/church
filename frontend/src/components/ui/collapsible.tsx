"use client"

// Rebuilt from the upstream shadcn source (slice 2c plan clarification 4,
// as slice 2b's owner answer A): shadcn-ui/ui@db2db460
// apps/v4/registry/bases/base/ui/collapsible.tsx with
// apps/v4/registry/styles/style-nova.css, through the shadcn 4.21.0 CLI's own
// style transform and Prettier's Tailwind class order. The only change from
// that output is this comment. Replace it with the file
// `npx shadcn@latest add collapsible` generates when the registry is reachable.

import { Collapsible as CollapsiblePrimitive } from "@base-ui/react/collapsible"

function Collapsible({ ...props }: CollapsiblePrimitive.Root.Props) {
  return <CollapsiblePrimitive.Root data-slot="collapsible" {...props} />
}

function CollapsibleTrigger({ ...props }: CollapsiblePrimitive.Trigger.Props) {
  return (
    <CollapsiblePrimitive.Trigger data-slot="collapsible-trigger" {...props} />
  )
}

function CollapsibleContent({ ...props }: CollapsiblePrimitive.Panel.Props) {
  return (
    <CollapsiblePrimitive.Panel data-slot="collapsible-content" {...props} />
  )
}

export { Collapsible, CollapsibleTrigger, CollapsibleContent }
