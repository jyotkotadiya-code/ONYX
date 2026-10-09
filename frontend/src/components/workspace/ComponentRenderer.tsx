import React from 'react';
import { ShieldAlert } from 'lucide-react';
import { AllowedComponentType, ComponentItem } from '../../types/structured';
import { TextBlock } from '../ai/TextBlock';
import { DataTable } from '../ai/DataTable';
import { ChartRenderer } from '../ai/ChartRenderer';
import { StatCard } from '../ai/StatCard';
import { ListRenderer } from '../ai/ListRenderer';
import { Timeline } from '../ai/Timeline';
import { Comparison } from '../ai/Comparison';
import { CodeBlock } from '../ai/CodeBlock';
import { SourceCard } from '../ai/SourceCard';

/**
 * Strict Component Allowlist Registry.
 * Never allows dynamic imports or execution of LLM-specified code/scripts.
 */
export const componentRegistry: Record<AllowedComponentType, React.FC<any>> = {
  text: TextBlock,
  table: DataTable,
  chart: ChartRenderer,
  stat: StatCard,
  list: ListRenderer,
  timeline: Timeline,
  comparison: Comparison,
  code: CodeBlock,
  source: SourceCard,
};

interface ComponentRendererProps {
  component: ComponentItem;
  onSelectSource?: (docId: string, chunkId?: string, page?: number) => void;
  onMutateCommand?: (command: string) => void;
}

export const ComponentRenderer: React.FC<ComponentRendererProps> = ({
  component,
  onSelectSource,
  onMutateCommand,
}) => {
  const cType = String(component?.type || '').toLowerCase() as AllowedComponentType;
  const TargetComponent = componentRegistry[cType];

  if (!TargetComponent) {
    return (
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-700 dark:text-amber-300 flex items-center gap-2">
        <ShieldAlert className="w-4 h-4 shrink-0" />
        <span>
          Blocked unapproved UI component type: <code className="font-mono">{String(component?.type)}</code>
        </span>
      </div>
    );
  }

  if (cType === 'source') {
    const sourcesList = Array.isArray(component.data?.sources) ? component.data.sources : [];
    return <SourceCard sources={sourcesList} onSelectSource={onSelectSource} />;
  }

  if (cType === 'table') {
    return (
      <DataTable
        id={component.id}
        title={component.title}
        data={component.data}
        onConvertToChart={
          onMutateCommand
            ? (compId) => onMutateCommand(`Change ${compId} to a bar chart`)
            : undefined
        }
      />
    );
  }

  return <TargetComponent id={component.id} title={component.title} data={component.data} />;
};
