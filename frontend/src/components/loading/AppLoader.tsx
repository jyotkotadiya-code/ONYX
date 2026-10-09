import React from 'react';
import { OnyxLogo } from '../system/OnyxLogo';
import { PrivacyIndicator } from '../system/PrivacyIndicator';
import { BootStatus } from './BootStatus';
import { ErrorState } from './ErrorState';
import { ServiceStatusItem } from './ServiceStatus';

export type AppBootPhase =
  | 'BOOT'
  | 'AUTHENTICATING'
  | 'LOADING_WORKSPACE'
  | 'CHECKING_SERVICES'
  | 'READY'
  | 'DEGRADED'
  | 'ERROR';

interface AppLoaderProps {
  phase: AppBootPhase;
  services: ServiceStatusItem[];
  offlineMode?: boolean;
  verifiedPrivate?: boolean;
  technicalDetails?: string;
  onRetry: () => void;
  isRetrying?: boolean;
}

/**
 * Full-screen calm application boot / initialization screen.
 * Driven by real service health checks (Authentication, Metadata DB, Vector DB, Embeddings, Local Llama, OCR).
 */
export const AppLoader: React.FC<AppLoaderProps> = ({
  phase,
  services,
  offlineMode = true,
  verifiedPrivate = true,
  technicalDetails,
  onRetry,
  isRetrying = false,
}) => {
  const subheading =
    phase === 'AUTHENTICATING'
      ? 'Verifying workspace session...'
      : phase === 'LOADING_WORKSPACE'
      ? 'Preparing workspace environment...'
      : phase === 'CHECKING_SERVICES'
      ? 'Checking local AI and vector services...'
      : phase === 'READY' || phase === 'DEGRADED'
      ? 'Workspace ready'
      : 'Initializing local AI...';

  return (
    <div className="min-h-screen flex flex-col items-center justify-between bg-zinc-50 dark:bg-[#0b0c0e] text-zinc-900 dark:text-zinc-100 p-6 select-none">
      <div />

      <div className="w-full max-w-sm flex flex-col items-center space-y-6">
        <OnyxLogo size="lg" animated />

        {phase === 'ERROR' ? (
          <ErrorState
            title="Backend unavailable"
            message="Make sure the local RAG server is running and try again."
            services={services}
            technicalDetails={technicalDetails}
            onRetry={onRetry}
            isRetrying={isRetrying}
          />
        ) : (
          <BootStatus
            heading="Preparing workspace"
            subheading={subheading}
            services={services}
            isReady={phase === 'READY' || phase === 'DEGRADED'}
          />
        )}
      </div>

      <div className="pb-2">
        <PrivacyIndicator offlineMode={offlineMode} verifiedPrivate={verifiedPrivate} />
      </div>
    </div>
  );
};
