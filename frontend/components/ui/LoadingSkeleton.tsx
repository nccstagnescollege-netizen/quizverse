import { cn } from '@/lib/utils';

interface LoadingSkeletonProps {
  className?: string;
  count?: number;
}

export function LoadingSkeleton({ className, count = 1 }: LoadingSkeletonProps) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          aria-hidden="true"
          className={cn(
            'animate-pulse rounded-xl bg-surface-elevated/70 border border-surface-border/50',
            className
          )}
        />
      ))}
    </>
  );
}
