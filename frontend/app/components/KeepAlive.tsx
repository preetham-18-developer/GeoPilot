'use client';
import { useEffect } from 'react';

export default function KeepAlive() {
  useEffect(() => {
    // Wake up Render backend on app load
    const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    fetch(`${API}/health`).catch(() => {});
    
    // Keep alive every 10 minutes
    const interval = setInterval(() => {
      fetch(`${API}/health`).catch(() => {});
    }, 10 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, []);
  
  return null;
}
