declare module 'react-mermaid2' {
  import type { FC } from 'react';

  export interface MermaidProps {
    chart: string;
    config?: Record<string, unknown>;
    name?: string;
  }

  const Mermaid: FC<MermaidProps>;
  export default Mermaid;
}
