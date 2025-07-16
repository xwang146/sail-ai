// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { env } from "~/env";

export function resolveServiceURL(path: string) {
  let BASE_URL = env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/";
  if (!BASE_URL.endsWith("/")) {
    BASE_URL += "/";
  }
  
  const finalURL = new URL(path, BASE_URL).toString();
  
  // Add production logging
  if (typeof window !== 'undefined') {
    console.log('[resolveServiceURL] Environment variables:', {
      NEXT_PUBLIC_API_URL: env.NEXT_PUBLIC_API_URL,
      process_env_NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL
    });
    console.log('[resolveServiceURL] Resolved URL:', {
      inputPath: path,
      baseURL: BASE_URL,
      finalURL: finalURL
    });
  }
  
  return finalURL;
}
