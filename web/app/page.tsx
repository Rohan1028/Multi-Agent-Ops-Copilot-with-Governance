import ApprovalQueue from '@/components/ApprovalQueue';
import MetricsCard from '@/components/MetricsCard';
import RunsTable from '@/components/RunsTable';
import TaskForm from '@/components/TaskForm';
import { getLatestRuns, submitTask } from '@/lib/client';
import { Metrics } from '@/lib/types';
import { useEffect, useState } from 'react';

export default function HomePage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    const latest = await getLatestRuns();
    setRuns(latest);
    if (latest.length > 0) {
      setMetrics(latest[0].metrics);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-semibold">Multi-Agent Ops Copilot</h1>
      <TaskForm
        onSubmit={async (payload) => {
          setLoading(true);
          try {
            await submitTask(payload);
            await refresh();
          } finally {
            setLoading(false);
          }
        }}
        loading={loading}
      />
      <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <MetricsCard title="Success %" value={metrics ? metrics.success_rate * 100 : 0} suffix="%" />
        <MetricsCard title="Hallucination %" value={metrics ? metrics.hallucination_rate * 100 : 0} suffix="%" />
        <MetricsCard title="p95 Latency" value={metrics ? metrics.p95_latency_ms : 0} suffix="ms" />
      </section>
      <RunsTable runs={runs} />
      <ApprovalQueue onApproved={refresh} />
    </div>
  );
}
