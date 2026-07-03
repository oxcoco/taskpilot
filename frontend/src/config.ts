// Use the real backend URL in deployed builds, and fall back to the local Vite proxy in development.
// If the frontend feels slow, keep local dev on the Vite proxy and avoid pointing a local browser
// session at a remote backend unless you actually need to test deployment behavior.
const rawApiBase = import.meta.env.VITE_API_BASE_URL || '/api';

export const API_BASE = rawApiBase.replace(/\/$/, '');
export const API_BASE_LABEL = import.meta.env.VITE_API_BASE_URL
	? `Backend: ${API_BASE}`
	: 'Backend: local Vite proxy (/api)';

console.info(`[TaskPilot] API base: ${API_BASE_LABEL}`);
