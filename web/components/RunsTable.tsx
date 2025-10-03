'use client';

import { RunResponse } from '@/lib/types';

interface Props {
  runs: RunResponse[];
}

export default function RunsTable({ runs }: Props) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-100">
          <tr>
            <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide">Task</th>
            <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide">Steps</th>
            <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide">Success</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {runs.map((run) => (
            <tr key={run.task.id}>
              <td className="px-4 py-2 text-sm font-medium">{run.task.title}</td>
              <td className="px-4 py-2 text-sm">{run.plan.length}</td>
              <td className="px-4 py-2 text-sm">
                {Math.round(run.metrics.success_rate * 100)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
