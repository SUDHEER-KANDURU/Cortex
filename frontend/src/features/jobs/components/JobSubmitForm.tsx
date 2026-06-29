// =============================================================================
// JobSubmitForm — Form for submitting a new Cortex analysis job
// Validates GitHub URL, lets user select artifact type, calls onJobSubmitted.
// =============================================================================

'use client';

import React, { useState, useEffect } from 'react';
import { Send } from 'lucide-react';
import type { Job, ArtifactType } from '@/types';
import { ARTIFACT_TYPE_LABELS } from '@/features/jobs/jobs.types';
import { useSubmitJob } from '@/features/jobs/hooks/useSubmitJob';
import ErrorAlert from '@/components/shared/ErrorAlert';

export interface JobSubmitFormProps {
  /** Called with the new Job after a successful submission */
  onJobSubmitted: (job: Job) => void;
}

const ARTIFACT_TYPES: ArtifactType[] = [
  'folder_structure',
  'module_breakdown',
  'architecture_diagram',
  'database_schema',
  'api_spec',
  'learning_path',
  'interview_questions',
];

function isValidGitHubUrl(url: string): boolean {
  return url.startsWith('https://github.com/');
}

export default function JobSubmitForm({ onJobSubmitted }: JobSubmitFormProps) {
  const [repoUrl, setRepoUrl] = useState('');
  const [artifactType, setArtifactType] = useState<ArtifactType>('architecture_diagram');
  const [validationError, setValidationError] = useState<string | null>(null);

  const { submittedJob, isSubmitting, error: apiError, submitJob } = useSubmitJob();

  // Notify parent whenever a job is successfully submitted
  useEffect(() => {
    if (submittedJob) {
      onJobSubmitted(submittedJob);
      // Reset the form after a successful submission
      setRepoUrl('');
      setArtifactType('architecture_diagram');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [submittedJob]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setValidationError(null);

    const trimmedUrl = repoUrl.trim();
    if (!trimmedUrl) {
      setValidationError('Please enter a GitHub repository URL.');
      return;
    }
    if (!isValidGitHubUrl(trimmedUrl)) {
      setValidationError('URL must start with https://github.com/');
      return;
    }

    await submitJob({ repo_url: trimmedUrl, artifact_type: artifactType });
  };

  const displayError = validationError ?? apiError;

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-4"
      aria-label="Submit a new Cortex job"
      noValidate
    >
      <div className="flex flex-col gap-1.5">
        <label htmlFor="repo-url" className="text-sm font-medium text-gray-300">
          GitHub Repository URL
        </label>
        <input
          id="repo-url"
          type="url"
          placeholder="https://github.com/owner/repo"
          value={repoUrl}
          onChange={(e) => {
            setRepoUrl(e.target.value);
            setValidationError(null);
          }}
          disabled={isSubmitting}
          aria-describedby={displayError ? 'submit-error' : undefined}
          aria-invalid={!!validationError}
          className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 transition-colors focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500 disabled:opacity-50"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="artifact-type" className="text-sm font-medium text-gray-300">
          Artifact Type
        </label>
        <select
          id="artifact-type"
          value={artifactType}
          onChange={(e) => setArtifactType(e.target.value as ArtifactType)}
          disabled={isSubmitting}
          className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 transition-colors focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500 disabled:opacity-50"
        >
          {ARTIFACT_TYPES.map((type) => (
            <option key={type} value={type}>
              {ARTIFACT_TYPE_LABELS[type]}
            </option>
          ))}
        </select>
      </div>

      {displayError && (
        <ErrorAlert
          message={displayError}
          onDismiss={() => setValidationError(null)}
        />
      )}

      <button
        type="submit"
        disabled={isSubmitting || !repoUrl.trim()}
        className="flex items-center justify-center gap-2 rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-violet-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
        aria-busy={isSubmitting}
      >
        <Send className="h-4 w-4" aria-hidden="true" />
        {isSubmitting ? 'Submitting…' : 'Analyze Repository'}
      </button>
    </form>
  );
}
