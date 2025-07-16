// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useEffect, useRef, useState } from "react";

import { env } from "~/env";

import type { DeerFlowConfig } from "../config";
import { useReplay } from "../replay";

import { fetchReplayTitle } from "./chat";
import { resolveServiceURL } from "./resolve-service-url";

export function useReplayMetadata() {
  const { isReplay } = useReplay();
  const [title, setTitle] = useState<string | null>(null);
  const isLoading = useRef(false);
  const [error, setError] = useState<boolean>(false);
  useEffect(() => {
    if (!isReplay) {
      return;
    }
    if (title || isLoading.current) {
      return;
    }
    isLoading.current = true;
    fetchReplayTitle()
      .then((title) => {
        setError(false);
        setTitle(title ?? null);
        if (title) {
          document.title = `${title} - DeerFlow`;
        }
      })
      .catch(() => {
        setError(true);
        setTitle("Error: the replay is not available.");
        document.title = "DeerFlow";
      })
      .finally(() => {
        isLoading.current = false;
      });
  }, [isLoading, isReplay, title]);
  return { title, isLoading, hasError: error };
}

export function useConfig(): {
  config: DeerFlowConfig | null;
  loading: boolean;
} {
  const [loading, setLoading] = useState(true);
  const [config, setConfig] = useState<DeerFlowConfig | null>(null);

  useEffect(() => {
    // Add production logging
    if (typeof window !== 'undefined') {
      console.log('[useConfig] Environment check:', {
        NEXT_PUBLIC_STATIC_WEBSITE_ONLY: env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY,
        NEXT_PUBLIC_API_URL: env.NEXT_PUBLIC_API_URL,
        process_env_NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL
      });
    }

    if (env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY) {
      console.log('[useConfig] Static website mode enabled, skipping config fetch');
      setLoading(false);
      return;
    }

    const configURL = resolveServiceURL("config");
    console.log('[useConfig] Fetching config from:', configURL);

    fetch(configURL)
      .then((res) => {
        console.log('[useConfig] Config fetch response status:', res.status);
        return res.json();
      })
      .then((config) => {
        console.log('[useConfig] Config loaded successfully:', config);
        setConfig(config);
        setLoading(false);
      })
      .catch((err) => {
        console.error("[useConfig] Failed to fetch config", err);
        setConfig(null);
        setLoading(false);
      });
  }, []);

  return { config, loading };
}
