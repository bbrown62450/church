"use client";

import { StepPlaceholder } from "@/components/builder/step-placeholder";
import { StillNeeded } from "@/components/builder/still-needed";

/** Step: Review & send. Slice 5a replaces the placeholder; "Still needed" lists shipped steps' gaps. */
export default function ReviewStepPage() {
  return (
    <>
      <StepPlaceholder step="review" />
      <StillNeeded />
    </>
  );
}
