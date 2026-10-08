"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Skeleton } from "@/components/ui/skeleton";

/** The old address of Bulletin settings: it opens Settings → Bulletin (slice 6a-3a; owner's 6a-3 answer 3). */
export default function OldBulletinSettingsRoute() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/settings/bulletin");
  }, [router]);

  return <Skeleton aria-busy="true" className="h-40 w-full" />;
}
