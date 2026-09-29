"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { useDraft } from "@/lib/draft/context";

/** `/builder` opens the step the draft was last on (F §4.7 "Navigation"). */
export default function BuilderIndexPage() {
  const { draft } = useDraft();
  const router = useRouter();
  const target = `/builder/${draft.last_step}`;

  useEffect(() => {
    router.replace(target);
  }, [router, target]);

  return <Skeleton className="h-40 w-full" />;
}
