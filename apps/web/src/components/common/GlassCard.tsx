import React from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';
import { cn } from '../../utils/cn';

interface GlassCardProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode;
  className?: string;
  glow?: 'brand' | 'cyan' | 'purple' | 'none';
  interactive?: boolean;
}

export function GlassCard({
  children,
  className,
  glow = 'none',
  interactive = false,
  ...props
}: GlassCardProps) {
  const glowStyles = {
    brand: 'hover:shadow-glow-primary hover:border-brand-500/40',
    cyan: 'hover:shadow-glow-cyan hover:border-cyber-cyan/40',
    purple: 'hover:shadow-glow-purple hover:border-cyber-purple/40',
    none: '',
  };

  return (
    <motion.div
      className={cn(
        'glass-card rounded-2xl p-6 transition-all duration-300',
        interactive && 'cursor-pointer hover:-translate-y-1',
        glowStyles[glow],
        className
      )}
      {...props}
    >
      {children}
    </motion.div>
  );
}
