// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { motion } from "framer-motion";

import { cn } from "~/lib/utils";

export function Welcome({ className }: { className?: string }) {
  return (
    <motion.div
      className={cn("flex flex-col", className)}
      style={{ transition: "all 0.2s ease-out" }}
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
    >
      <h3 className="mb-2 text-center text-3xl font-medium">
        👋 你好，我是飞猫出海AI助手
      </h3>
      <div className="text-muted-foreground px-4 text-center text-lg">
        很高兴遇见你！我是基于前沿AI技术的深度研究助手，让我帮你一起探索海外市场的无限可能吧！”
      </div>
    </motion.div>
  );
}
