"use client";

import { useEffect, useState } from "react";

import { resolveServiceURL } from "~/core/api/resolve-service-url";
import { env } from "~/env";

export default function DebugPage() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div>Loading...</div>;
  }

  const testURLs = [
    "config",
    "chat/stream",
    "rag/resources",
    "prompt/enhance"
  ];

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Environment Debug Information</h1>
      
      <div className="space-y-6">
        <div className="bg-gray-100 p-4 rounded">
          <h2 className="text-lg font-semibold mb-2">Environment Variables</h2>
          <pre className="text-sm">
            {JSON.stringify({
              NODE_ENV: process.env.NODE_ENV,
              NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
              NEXT_PUBLIC_STATIC_WEBSITE_ONLY: process.env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY,
            }, null, 2)}
          </pre>
        </div>

        <div className="bg-gray-100 p-4 rounded">
          <h2 className="text-lg font-semibold mb-2">Processed Environment Variables (from env.js)</h2>
          <pre className="text-sm">
            {JSON.stringify({
              NODE_ENV: env.NODE_ENV,
              NEXT_PUBLIC_API_URL: env.NEXT_PUBLIC_API_URL,
              NEXT_PUBLIC_STATIC_WEBSITE_ONLY: env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY,
            }, null, 2)}
          </pre>
        </div>

        <div className="bg-gray-100 p-4 rounded">
          <h2 className="text-lg font-semibold mb-2">Resolved URLs</h2>
          <div className="space-y-2">
            {testURLs.map((path) => (
              <div key={path} className="text-sm">
                <strong>{path}:</strong> {resolveServiceURL(path)}
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-100 p-4 rounded">
          <h2 className="text-lg font-semibold mb-2">Browser Information</h2>
          <pre className="text-sm">
            {JSON.stringify({
              userAgent: navigator.userAgent,
              location: window.location.href,
              origin: window.location.origin,
            }, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
} 