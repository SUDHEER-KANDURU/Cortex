import React from 'react';

/**
 * Privacy Policy content — reusable between modal and standalone page.
 */
export function PrivacyContent() {
  return (
    <div className="space-y-6 text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
      <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
        Last updated: August 27, 2026
      </p>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          1. Introduction
        </h2>
        <p>
          At Cortex, we take your privacy seriously. This Privacy Policy explains how we collect, use,
          store, and protect your personal information when you use our Engineering Reasoning Engine service.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          2. Information We Collect
        </h2>
        <p className="mb-2">We collect the following types of information:</p>
        <h3 className="font-medium mt-3 mb-1" style={{ color: 'var(--text)' }}>Account Information</h3>
        <ul className="list-disc pl-5 space-y-1">
          <li>Full name</li>
          <li>Email address</li>
          <li>Organization name (optional)</li>
          <li>Job title or role (optional)</li>
          <li>Encrypted password</li>
        </ul>
        <h3 className="font-medium mt-3 mb-1" style={{ color: 'var(--text)' }}>Usage Data</h3>
        <ul className="list-disc pl-5 space-y-1">
          <li>Repositories submitted for analysis</li>
          <li>Feature usage patterns and interactions</li>
          <li>Chat session history with the AI assistant</li>
          <li>Browser type, device information, and IP address</li>
        </ul>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          3. How We Use Your Information
        </h2>
        <p>We use your information to:</p>
        <ul className="list-disc pl-5 mt-2 space-y-1">
          <li>Provide and maintain the Service</li>
          <li>Authenticate your identity and secure your account</li>
          <li>Analyze code repositories as requested by you</li>
          <li>Improve our AI models and service quality</li>
          <li>Send important service notifications and updates</li>
          <li>Respond to support requests and inquiries</li>
          <li>Detect and prevent fraud or abuse</li>
        </ul>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          4. Data Storage and Security
        </h2>
        <p>
          We implement industry-standard security measures to protect your data, including encryption
          in transit (TLS) and at rest, secure password hashing (bcrypt), and regular security audits.
          Your code is processed in isolated environments and is not shared with other users.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          5. Data Sharing
        </h2>
        <p>
          We do not sell your personal information. We may share data with:
        </p>
        <ul className="list-disc pl-5 mt-2 space-y-1">
          <li>Service providers who help us operate the platform (hosting, analytics)</li>
          <li>Law enforcement when required by law or to protect our rights</li>
          <li>Third parties with your explicit consent</li>
        </ul>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          6. Data Retention
        </h2>
        <p>
          We retain your account data for as long as your account is active. Analysis results and
          chat history are retained for 90 days after the last access. You may request deletion of
          your data at any time by contacting us or deleting your account.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          7. Your Rights
        </h2>
        <p>You have the right to:</p>
        <ul className="list-disc pl-5 mt-2 space-y-1">
          <li>Access your personal data</li>
          <li>Correct inaccurate information</li>
          <li>Request deletion of your data</li>
          <li>Export your data in a portable format</li>
          <li>Withdraw consent for data processing</li>
          <li>Object to automated decision-making</li>
        </ul>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          8. Cookies and Tracking
        </h2>
        <p>
          We use essential cookies for authentication and session management. We do not use
          third-party advertising cookies. Analytics cookies are optional and can be disabled
          in your account settings.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          9. Children&apos;s Privacy
        </h2>
        <p>
          The Service is not intended for users under 16 years of age. We do not knowingly collect
          personal information from children. If we become aware that we have collected data from a
          child, we will take steps to delete it promptly.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          10. Changes to This Policy
        </h2>
        <p>
          We may update this Privacy Policy from time to time. We will notify you of material changes
          via email or through the Service at least 30 days before they take effect.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-2" style={{ color: 'var(--text)' }}>
          11. Contact Us
        </h2>
        <p>
          For privacy-related questions or to exercise your rights, contact our Data Protection team at{' '}
          <span className="font-medium" style={{ color: 'var(--text)' }}>privacy@cortex.dev</span>.
        </p>
      </section>
    </div>
  );
}
