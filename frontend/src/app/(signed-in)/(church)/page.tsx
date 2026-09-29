"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Skeleton } from "@/components/ui/skeleton";

/**
 * Home (`/`) opens the Service Builder (F §4.1; S "Routes and files"). The
 * `(signed-in)` layout has already followed any stored post-login path before
 * this page mounts.
 */
export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/builder");
  }, [router]);

  return (
    <main className="mx-auto grid w-full max-w-2xl gap-4 p-4" aria-busy="true">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-40 w-full" />
    </main>
  );
}
