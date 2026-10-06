"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { SETTINGS_SECTIONS } from "@/components/settings/sections";

/** `/settings` opens the first section, Church (6a spec "Settings nav"). */
export default function SettingsHome() {
  const router = useRouter();

  useEffect(() => {
    router.replace(SETTINGS_SECTIONS[0].href);
  }, [router]);

  return <Skeleton aria-busy="true" className="h-40 w-full" />;
}
