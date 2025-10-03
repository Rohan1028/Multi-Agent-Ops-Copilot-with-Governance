interface Props {
  title: string;
  value: number;
  suffix?: string;
}

export default function MetricsCard({ title, value, suffix = '' }: Props) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mt-2 text-2xl font-semibold">
        {value.toFixed(2)} {suffix}
      </p>
    </div>
  );
}
