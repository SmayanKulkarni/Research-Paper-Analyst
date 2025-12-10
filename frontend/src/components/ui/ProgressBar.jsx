'use client';

import { motion } from 'framer-motion';
import styles from './ProgressBar.module.css';
import { cn } from '@/lib/utils';

/**
 * Animated progress bar with gradient fill
 */
export function ProgressBar({
    value = 0,
    max = 100,
    showLabel = false,
    size = 'md',
    className,
}) {
    const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

    const sizes = {
        sm: styles.sm,
        md: styles.md,
        lg: styles.lg,
    };

    return (
        <div className={cn(styles.container, className)}>
            <div className={cn(styles.track, sizes[size])}>
                <motion.div
                    className={styles.fill}
                    initial={{ width: 0 }}
                    animate={{ width: `${percentage}%` }}
                    transition={{ duration: 0.6, ease: 'easeOut' }}
                />
                <div className={styles.shimmer} />
            </div>
            {showLabel && (
                <span className={styles.label}>{Math.round(percentage)}%</span>
            )}
        </div>
    );
}

export default ProgressBar;
