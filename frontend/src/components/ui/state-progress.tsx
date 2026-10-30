import { cn, STATE_LABELS, STATE_ORDER, TERMINAL_STATES } from "@/lib/utils";
import { CheckCircle2, Circle, XCircle, Clock } from "lucide-react";

interface StateProgressProps {
  currentState: string;
  compact?: boolean;
}

export function StateProgress({ currentState, compact = false }: StateProgressProps) {
  const isTerminal = TERMINAL_STATES.has(currentState);
  const currentIdx = STATE_ORDER.indexOf(currentState);

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        <span className={cn(
          "text-xs font-medium px-2 py-0.5 rounded",
          isTerminal && currentState === "CLOSED"
            ? "bg-profit/10 text-profit"
            : isTerminal
            ? "bg-loss/10 text-loss"
            : currentState === "SIGNAL_READY" || currentState === "POSITION_OPEN"
            ? "bg-accent/10 text-accent"
            : "bg-surface-2 text-text-secondary"
        )}>
          {STATE_LABELS[currentState] ?? currentState}
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <p className="text-xs text-text-secondary uppercase tracking-wide font-medium mb-2">
        Setup Progress
      </p>
      <ol className="space-y-1">
        {STATE_ORDER.map((state, idx) => {
          const isDone    = currentIdx > idx;
          const isActive  = currentIdx === idx && !isTerminal;
          const isPending = currentIdx < idx;
          return (
            <li key={state} className="flex items-center gap-2 text-xs">
              {isDone ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-profit shrink-0" aria-hidden />
              ) : isActive ? (
                <Clock className="w-3.5 h-3.5 text-accent shrink-0 animate-pulse" aria-hidden />
              ) : (
                <Circle className="w-3.5 h-3.5 text-border shrink-0" aria-hidden />
              )}
              <span className={cn(
                isDone   ? "text-text-secondary" :
                isActive ? "text-text-primary font-medium" :
                           "text-border"
              )}>
                {STATE_LABELS[state] ?? state}
              </span>
            </li>
          );
        })}
        {isTerminal && (
          <li className="flex items-center gap-2 text-xs">
            {currentState === "CLOSED" ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-profit shrink-0" aria-hidden />
            ) : (
              <XCircle className="w-3.5 h-3.5 text-loss shrink-0" aria-hidden />
            )}
            <span className={currentState === "CLOSED" ? "text-profit font-medium" : "text-loss font-medium"}>
              {STATE_LABELS[currentState] ?? currentState}
            </span>
          </li>
        )}
      </ol>
    </div>
  );
}
