// =============================================================================
// Home page — Immediately redirects to /dashboard
// =============================================================================

import { redirect } from 'next/navigation';

export default function HomePage() {
  redirect('/dashboard');
}
