'use client';
import { useEffect } from 'react';

export default function KeepAlive() {
  useEffect(() => {
    // Wake up Render backend on app load
    const rawAPI = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const cleanAPI = rawAPI.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');
    fetch(`${cleanAPI}/health`).catch(() => {});
    
    // Keep alive every 10 minutes
    const interval = setInterval(() => {
      fetch(`${cleanAPI}/health`).catch(() => {});
    }, 10 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, []);
  
  return null;
}
