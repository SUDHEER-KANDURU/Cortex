// App-level route loading — shown by Next.js App Router during any page transition
import { PageLoader } from '@/components/shared/BrandedLoader';

export default function Loading() {
  return <PageLoader />;
}
