import { RunResponse, TaskPayload } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

export async function submitTask(payload: TaskPayload): Promise<RunResponse> {
  const response = await fetch(`${API_BASE}/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error('Task submission failed');
  }
  return response.json();
}

export async function getLatestRuns(): Promise<RunResponse[]> {
  const response = await fetch(`${API_BASE}/runs/latest`);
  if (!response.ok) {
    return [];
  }
  return response.json();
}

export async function fetchApprovals(): Promise<{ step_id: string; status: string }[]> {
  const response = await fetch(`${API_BASE}/approvals/pending`);
  if (!response.ok) {
    return [];
  }
  return response.json();
}

export async function approveStep(stepId: string): Promise<void> {
  await fetch(`${API_BASE}/approvals/${stepId}:approve`, {
    method: 'POST',
  });
}
