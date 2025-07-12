// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { motion } from "framer-motion";

import { cn } from "~/lib/utils";

export function Welcome({ className }: { className?: string }) {
  return (
    <div className="-mt-24">
    <motion.div
      className={cn("flex flex-col max-w-3xl mx-auto", className)}
      style={{ transition: "all 0.2s ease-out" }}
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
    >
      <h3 className="mb-2 text-center text-3xl font-medium">
        👋 老板你好！我是飞猫出海AI助手
      </h3>
      <div className="text-muted-foreground px-4 text-center text-lg">
        很高兴能为您服务！我是基于前沿AI技术的出海战略规划助手，让我来帮你探索海外市场的无限可能吧！
      </div>
    </motion.div>
    </div>
  );
}
