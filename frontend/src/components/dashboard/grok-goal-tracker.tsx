"use client";

import { Target, Sparkles } from "lucide-react";

interface GrokGoalTrackerProps {
  currentMultiplier?: number;
  targetMultiplier?: number;
  currentEquity?: number;
  nextTargetEquity?: number;
}

export function GrokGoalTracker({
  currentMultiplier = 5.24,
  targetMultiplier = 10,
  currentEquity = 1048.47,
  nextTargetEquity = 1600.0,
}: GrokGoalTrackerProps) {
  const remainingUsd = Math.max(0, nextTargetEquity - currentEquity);

  const steps = [
    { label: "2x", val: 2 },
    { label: "3x", val: 3 },
    { label: "5x", val: 5 },
    { label: "8x", val: 8 },
    { label: "12x", val: 12 },
    { label: "17x", val: 17 },
  ];

  // Calculate percentage along the milestones (0 to 17x)
  const maxVal = 17;
  const progressPct = Math.min(100, Math.max(0, (currentMultiplier / maxVal) * 100));

  return (
    <div className="bg-[#0D131C] border border-[#243043] rounded-card p-5 shadow-[0_0_40px_rgba(0,0,0,0.4)] space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1B2535] pb-3">
        <h3 className="text-base font-extrabold text-white tracking-tight flex items-center gap-2">
          Goal: {targetMultiplier}x
        </h3>
        <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#121821] text-text-secondary border border-[#243043] font-mono">
          next 8x · <span className="text-emerald-400">${remainingUsd.toFixed(0)} to go</span>
        </span>
      </div>

      {/* Modern Stepper Timeline (matching Image 2) */}
      <div className="pt-6 pb-2 px-3 relative">
        {/* Current Multiplier Bubble Pill above active position */}
        <div
          style={{ left: `${Math.min(92, Math.max(8, progressPct))}%` }}
          className="absolute -top-1 -translate-x-1/2 bg-black border border-emerald-500 text-emerald-400 font-extrabold text-[11px] font-mono px-2 py-0.5 rounded-full shadow-[0_0_15px_rgba(16,185,129,0.5)] z-20"
        >
          {currentMultiplier}x
        </div>

        {/* Gray Track */}
        <div className="w-full h-1.5 bg-[#1B2535] rounded-full relative">
          {/* Active Glowing Green Fill */}
          <div
            style={{ width: `${progressPct}%` }}
            className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full shadow-[0_0_10px_rgba(16,185,129,0.8)]"
          />
        </div>

        {/* Milestone Node Circles */}
        <div className="flex justify-between items-center -mt-2.5 relative z-10">
          {steps.map((s) => {
            const passed = currentMultiplier >= s.val;
            const isNext = s.val === 8;
            return (
              <div key={s.label} className="flex flex-col items-center gap-1.5">
                <div
                  className={`w-4 h-4 rounded-full border-2 transition-all flex items-center justify-center ${
                    passed
                      ? "bg-emerald-500 border-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.6)]"
                      : isNext
                      ? "bg-[#0D131C] border-blue-400 shadow-[0_0_6px_rgba(96,165,250,0.6)]"
                      : "bg-[#0D131C] border-[#2A374A]"
                  }`}
                >
                  {passed && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                </div>
                <span
                  className={`text-[11px] font-mono ${
                    passed ? "text-emerald-400 font-bold" : "text-text-secondary"
                  }`}
                >
                  {s.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
