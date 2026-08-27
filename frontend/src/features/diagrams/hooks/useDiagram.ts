// =============================================================================
// useDiagram — Hook for fetching layered diagram data
// =============================================================================

'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  getDiagramSystem,
  getDiagramModule,
  getDiagramClass,
  type DiagramData,
} from '@/lib/api/diagrams.api';

export interface DiagramNavState {
  level: 'system' | 'module' | 'class';
  module?: string;
  className?: string;
}

export function useDiagram(jobId: string | null) {
  const [data, setData] = useState<DiagramData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nav, setNav] = useState<DiagramNavState>({ level: 'system' });

  const fetchDiagram = useCallback(
    async (navState: DiagramNavState) => {
      if (!jobId) return;
      setIsLoading(true);
      setError(null);
      try {
        let result: DiagramData;
        if (navState.level === 'module' && navState.module) {
          result = await getDiagramModule(jobId, navState.module);
        } else if (navState.level === 'class' && navState.className) {
          result = await getDiagramClass(jobId, navState.className);
        } else {
          result = await getDiagramSystem(jobId);
        }
        setData(result);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Failed to load diagram';
        setError(message);
      } finally {
        setIsLoading(false);
      }
    },
    [jobId]
  );

  // Initial fetch
  useEffect(() => {
    fetchDiagram(nav);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  // Navigation: drill into a module
  const drillToModule = useCallback(
    (moduleName: string) => {
      const newNav: DiagramNavState = { level: 'module', module: moduleName };
      setNav(newNav);
      fetchDiagram(newNav);
    },
    [fetchDiagram]
  );

  // Navigation: drill into a class
  const drillToClass = useCallback(
    (className: string) => {
      const newNav: DiagramNavState = { level: 'class', className };
      setNav(newNav);
      fetchDiagram(newNav);
    },
    [fetchDiagram]
  );

  // Navigation: go back to system view
  const goToSystem = useCallback(() => {
    const newNav: DiagramNavState = { level: 'system' };
    setNav(newNav);
    fetchDiagram(newNav);
  }, [fetchDiagram]);

  // Navigation: go back to module view (from class)
  const goToModule = useCallback(
    (moduleName: string) => {
      const newNav: DiagramNavState = { level: 'module', module: moduleName };
      setNav(newNav);
      fetchDiagram(newNav);
    },
    [fetchDiagram]
  );

  return {
    data,
    isLoading,
    error,
    nav,
    drillToModule,
    drillToClass,
    goToSystem,
    goToModule,
  };
}
