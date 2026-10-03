"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { useDraft } from "@/lib/draft/context";
import { STEPS } from "@/lib/draft/steps";

/**
 * `/builder` opens the step the draft was last on (F §4.7 "Navigation"), or
 * Review & send when that step is not in the bar: a draft from a newer
 * release after a rollback (printed bulletin PR 2b-2 plan, Step R).
 */
export default function BuilderIndexPage() {
  const { draft } = useDraft();
  const router = useRouter();
  const target = STEPS.find((step) => step.id === draft.last_step)?.href ?? "/builder/review";

  useEffect(() => {
    router.replace(target);
  }, [router, target]);

  return <Skeleton className="h-40 w-full" />;
}
