// Colors matching Python web app
const COLORS = {
  darkBg: '#070C14',
  surface: '#0A1428',
  cyan: '#00C2FF',
  green: '#34D399',
  blue: '#60A5FA',
  red: '#F87171',
  text: '#E2E8F0',
  textSecondary: '#94A3B8',
  textMuted: '#64748B',
  border: 'rgba(0,200,255,0.1)',
};

// Mock API responses for testing without Python backend
export const mockData = {
  currentState: {
    label: 'pollinating',
    confidence: 0.87,
    probs: {
      pollinating: 0.87,
      pollinated: 0.12,
      not_pollinated: 0.01,
    },
    timestamp: new Date().toISOString(),
  },
  history: [
    {
      label: 'pollinating',
      confidence: 0.87,
      timestamp: new Date(Date.now() - 5000).toISOString(),
    },
    {
      label: 'pollinated',
      confidence: 0.92,
      timestamp: new Date(Date.now() - 10000).toISOString(),
    },
    {
      label: 'not_pollinated',
      confidence: 0.95,
      timestamp: new Date(Date.now() - 15000).toISOString(),
    },
  ],
  snapshots: [],
};

export default COLORS;
