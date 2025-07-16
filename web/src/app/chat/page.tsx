// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { GithubOutlined } from "@ant-design/icons";
import dynamic from "next/dynamic";
import Link from "next/link";
import { Suspense } from "react";
import { useEffect } from "react";

import { Button } from "~/components/ui/button";
import { resolveServiceURL } from "~/core/api/resolve-service-url";
import { env } from "~/env";

import { Logo } from "../../components/deer-flow/logo";
import { ThemeToggle } from "../../components/deer-flow/theme-toggle";
import { Tooltip } from "../../components/deer-flow/tooltip";
import { SettingsDialog } from "../settings/dialogs/settings-dialog";

const Main = dynamic(() => import("./main"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center">
      飞猫出海AI助手正在加载中...
    </div>
  ),
});

export default function HomePage() {
  useEffect(() => {
    // 在页面上显示环境信息
    console.log("=== 环境变量调试信息 ===");
    console.log("NEXT_PUBLIC_API_URL:", env.NEXT_PUBLIC_API_URL);
    console.log("process.env.NEXT_PUBLIC_API_URL:", process.env.NEXT_PUBLIC_API_URL);
    console.log("解析后的配置URL:", resolveServiceURL("config"));
    console.log("当前页面URL:", window.location.href);
    console.log("=== 调试信息结束 ===");
  }, []);

  return (
    <div className="flex h-screen w-screen justify-center overscroll-none">
      <header className="fixed top-0 left-0 flex h-12 w-full items-center justify-between px-4">
        {/* <Logo /> */}
        <div className="flex items-center">
          {/* <Tooltip title="Star DeerFlow on GitHub">
            <Button variant="ghost" size="icon" asChild>
              <Link
                href="https://github.com/bytedance/deer-flow"
                target="_blank"
              >
                <GithubOutlined />
              </Link>
            </Button>
          </Tooltip> */}
          {/* <Suspense>
            <SettingsDialog />
          </Suspense> */}
        </div>
        <div className="flex items-center">
          <ThemeToggle />
        </div>
      </header>
      <Main />
      
      {/* 调试信息面板 - 只在开发环境显示
      {
        <div className="fixed bottom-4 right-4 bg-black text-white p-4 rounded text-xs max-w-sm z-50">
          <div className="font-bold mb-2">调试信息</div>
          <div>API URL: {env.NEXT_PUBLIC_API_URL ?? '未设置'}</div>
          <div>解析URL: {resolveServiceURL("config")}</div>
          <div>环境: {process.env.NODE_ENV}</div>
        </div>
      } */}
    </div>
  );
}
