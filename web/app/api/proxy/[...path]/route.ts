import { NextRequest } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

export async function GET(request: NextRequest, { params }: { params: { path: string[] } }) {
  const url = `${API_BASE}/${params.path.join('/')}`;
  const response = await fetch(url, { headers: { 'Content-Type': 'application/json' } });
  return new Response(await response.text(), { status: response.status });
}

export async function POST(request: NextRequest, { params }: { params: { path: string[] } }) {
  const url = `${API_BASE}/${params.path.join('/')}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5_000);
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: await request.text(),
      signal: controller.signal,
    });
    return new Response(await response.text(), { status: response.status });
  } catch (error) {
    return new Response('Upstream timeout', { status: 504 });
  } finally {
    clearTimeout(timeout);
  }
}
