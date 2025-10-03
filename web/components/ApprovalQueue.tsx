'use client';

import { approveStep, fetchApprovals } from '@/lib/client';
import { useEffect, useState } from 'react';

interface Props {
  onApproved: () => Promise<void>;
}

export default function ApprovalQueue({ onApproved }: Props) {
  const [pending, setPending] = useState<{ step_id: string; status: string }[]>([]);

  const refresh = async () => {
    setPending(await fetchApprovals());
  };

  useEffect(() => {
    refresh();
  }, []);

  if (pending.length === 0) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm text-sm text-slate-600">
        No approvals pending.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm space-y-3">
      <h2 className="text-lg font-semibold">Approval Queue</h2>
      {pending.map((item) => (
        <div key={item.step_id} className="flex items-center justify-between rounded border border-slate-100 p-3">
          <div>
            <p className="text-sm font-medium">{item.step_id}</p>
            <p className="text-xs text-slate-500">{item.status}</p>
          </div>
          <button
            className="rounded bg-emerald-600 px-3 py-1 text-sm text-white"
            onClick={async () => {
              await approveStep(item.step_id);
              await refresh();
              await onApproved();
            }}
          >
            Approve
          </button>
        </div>
      ))}
    </div>
  );
}
