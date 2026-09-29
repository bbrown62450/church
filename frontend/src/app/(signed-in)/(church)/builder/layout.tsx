"use client";

import type { ReactNode } from "react";

import { BuilderShell } from "@/components/builder/builder-shell";

/** Every `/builder` route renders inside the shell (F §4.7). */
export default function BuilderLayout({ children }: { children: ReactNode }) {
  return <BuilderShell>{children}</BuilderShell>;
}
