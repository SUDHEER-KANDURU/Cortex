import React from 'react';
import Link from 'next/link';

/**
 * Terms of Service content — reusable between modal and standalone page.
 */
export function TermsContent() {
  return (
    <div className="space-y-6 text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
      <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
        Last updated: August 27, 2026
      </p>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          1. Acceptance of Terms
        </h2>
        <p>
          By accessing or using Cortex (&quot;the Service&quot;), you agree to be bound by these Terms of Service.
          If you do not agree to these terms, please do not use the Service. These terms constitute a legally
          binding agreement between you and Cortex.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          2. Description of Service
        </h2>
        <p>
          Cortex is an Engineering Reasoning Engine that provides code analysis, understanding, and learning
          capabilities. The Service analyzes repositories, generates insights, and helps engineers understand
          codebases through AI-powered reasoning.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          3. User Accounts
        </h2>
        <p>
          To use certain features, you must create an account. You are responsible for maintaining the
          confidentiality of your login credentials and for all activities under your account. You agree to:
        </p>
        <ul className="list-disc pl-5 mt-2 space-y-1">
          <li>Provide accurate and complete registration information</li>
          <li>Keep your password secure and confidential</li>
          <li>Notify us immediately of any unauthorized access</li>
          <li>Accept responsibility for all activity under your account</li>
        </ul>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          4. Acceptable Use
        </h2>
        <p>You agree not to:</p>
        <ul className="list-disc pl-5 mt-2 space-y-1">
          <li>Use the Service for any unlawful purpose or in violation of any laws</li>
          <li>Upload or analyze code that you do not have the right to access</li>
          <li>Attempt to interfere with or disrupt the Service or its infrastructure</li>
          <li>Use automated means to access the Service beyond provided APIs</li>
          <li>Reverse engineer, decompile, or disassemble any part of the Service</li>
          <li>Share your account credentials with third parties</li>
        </ul>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          5. Intellectual Property
        </h2>
        <p>
          The Service and its original content, features, and functionality are owned by Cortex and are
          protected by copyright, trademark, and other intellectual property laws. You retain ownership
          of any code or content you submit for analysis.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          6. Data and Privacy
        </h2>
        <p>
          Your use of the Service is also governed by our{' '}
          <Link href="/privacy" className="font-medium underline" style={{ color: 'var(--text)' }}>
            Privacy Policy
          </Link>
          . By using the Service, you consent to the collection and use of information as described therein.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          7. Service Availability
        </h2>
        <p>
          We strive to maintain high availability but do not guarantee uninterrupted access. The Service
          may be temporarily unavailable for maintenance, updates, or circumstances beyond our control.
          We reserve the right to modify or discontinue the Service at any time with reasonable notice.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          8. Limitation of Liability
        </h2>
        <p>
          To the maximum extent permitted by law, Cortex shall not be liable for any indirect, incidental,
          special, consequential, or punitive damages resulting from your use of the Service. The Service
          is provided &quot;as is&quot; without warranties of any kind.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          9. Termination
        </h2>
        <p>
          We may suspend or terminate your access to the Service at any time for violation of these terms
          or for any reason with notice. Upon termination, your right to use the Service ceases immediately.
          You may also delete your account at any time.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          10. Changes to Terms
        </h2>
        <p>
          We reserve the right to update these terms at any time. We will notify users of material changes
          via email or through the Service. Continued use after changes constitutes acceptance of the
          updated terms.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          11. Contact
        </h2>
        <p>
          If you have questions about these Terms of Service, please contact us at{' '}
          <span className="font-medium" style={{ color: 'var(--text)' }}>legal@cortex.dev</span>.
        </p>
      </section>
    </div>
  );
}
