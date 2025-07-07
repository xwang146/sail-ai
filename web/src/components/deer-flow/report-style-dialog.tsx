// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useState } from "react";
import { Check, FileText, Newspaper, Users, GraduationCap } from "lucide-react";

import { Button } from "~/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "~/components/ui/dialog";
import { setReportStyle, useSettingsStore } from "~/core/store";
import { cn } from "~/lib/utils";

import { Tooltip } from "./tooltip";

const REPORT_STYLES = [
  {
    value: "academic" as const,
    label: "学术",
    description: "正式、客观、分析性强，术语精确",
    icon: GraduationCap,
  },
  {
    value: "popular_science" as const,
    label: "科普",
    description: "通俗易懂，适合大众",
    icon: FileText,
  },
  {
    value: "news" as const,
    label: "新闻",
    description: "事实、简明、公正的新闻风格",
    icon: Newspaper,
  },
  {
    value: "social_media" as const,
    label: "社交媒体",
    description: "简洁吸引眼球，易于分享",
    icon: Users,
  },
];

export function ReportStyleDialog() {
  const [open, setOpen] = useState(false);
  const currentStyle = useSettingsStore((state) => state.general.reportStyle);

  const handleStyleChange = (
    style: "academic" | "popular_science" | "news" | "social_media",
  ) => {
    setReportStyle(style);
    setOpen(false);
  };

  const currentStyleConfig =
    REPORT_STYLES.find((style) => style.value === currentStyle) ||
    REPORT_STYLES[0]!;
  const CurrentIcon = currentStyleConfig.icon;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Tooltip
        className="max-w-60"
        title={
          <div>
            <h3 className="mb-2 font-bold">
              写作风格：{currentStyleConfig.label}
            </h3>
            <p>
              请选择你的研究报告写作风格，不同风格适合不同场景和受众。
            </p>
          </div>
        }
      >
        <DialogTrigger asChild>
          <Button
            className="!border-brand !text-brand rounded-2xl"
            variant="outline"
          >
            <CurrentIcon className="h-4 w-4" /> {currentStyleConfig.label}
          </Button>
        </DialogTrigger>
      </Tooltip>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>选择写作风格</DialogTitle>
          <DialogDescription>
            请选择你的研究报告写作风格。每种风格适合不同的受众和用途。
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-3 py-4">
          {REPORT_STYLES.map((style) => {
            const Icon = style.icon;
            const isSelected = currentStyle === style.value;

            return (
              <button
                key={style.value}
                className={cn(
                  "hover:bg-accent flex items-start gap-3 rounded-lg border p-4 text-left transition-colors",
                  isSelected && "border-primary bg-accent",
                )}
                onClick={() => handleStyleChange(style.value)}
              >
                <Icon className="mt-0.5 h-5 w-5 shrink-0" />
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium">{style.label}</h4>
                    {isSelected && <Check className="text-primary h-4 w-4" />}
                  </div>
                  <p className="text-muted-foreground text-sm">
                    {style.description}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </DialogContent>
    </Dialog>
  );
}
