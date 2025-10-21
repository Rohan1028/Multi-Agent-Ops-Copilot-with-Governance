'use client';

import { useState } from 'react';
import { TaskPayload } from '@/lib/types';

interface Props {
  onSubmit: (payload: TaskPayload) => Promise<void>;
  loading: boolean;
}

const riskLevels = ['low', 'medium', 'high'] as const;

export default function TaskForm({ onSubmit, loading }: Props) {
  const [form, setForm] = useState<TaskPayload>({
    title: '',
    description: '',
    risk_level: 'medium',
    desired_outcome: '',
  });

  const handleChange = (key: keyof TaskPayload, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <form
      className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm space-y-4"
      onSubmit={async (event) => {
        event.preventDefault();
        await onSubmit(form);
        setForm({ title: '', description: '', risk_level: 'medium', desired_outcome: '' });
      }}
    >
      <div>
        <label className="block text-sm font-medium">Title</label>
        <input
          className="mt-1 w-full rounded border border-slate-300 p-2"
          value={form.title}
          onChange={(event) => handleChange('title', event.target.value)}
          required
        />
      </div>
      <div>
        <label className="block text-sm font-medium">Description</label>
        <textarea
          className="mt-1 w-full rounded border border-slate-300 p-2"
          rows={3}
          value={form.description}
          onChange={(event) => handleChange('description', event.target.value)}
          required
        />
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label className="block text-sm font-medium">Desired Outcome</label>
          <input
            className="mt-1 w-full rounded border border-slate-300 p-2"
            value={form.desired_outcome}
            onChange={(event) => handleChange('desired_outcome', event.target.value)}
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Risk Level</label>
          <select
            className="mt-1 w-full rounded border border-slate-300 p-2"
            value={form.risk_level}
            onChange={(event) => handleChange('risk_level', event.target.value)}
          >
            {riskLevels.map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </select>
        </div>
      </div>
      <button
        type="submit"
        className="rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-50"
        disabled={loading}
      >
        {loading ? 'Running...' : 'Run Task'}
      </button>
    </form>
  );
}
