// =============================================================================
// loading.tsx — Next.js App Router route-level loading UI
//
// Replaces the generic spinner with the Cortex branded loader.
// Shown automatically during route transitions and page hydration.
// =============================================================================

import { PageLoader } from '@/components/shared/BrandedLoader';

export default function Loading() {
  return <PageLoader />;
}
