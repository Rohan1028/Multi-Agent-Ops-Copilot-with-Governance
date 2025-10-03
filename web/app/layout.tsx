import './globals.css';
import type { ReactNode } from 'react';

export const metadata = {
  title: 'Ops Copilot Dashboard',
  description: 'Monitor governed multi-agent operations',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900">
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
