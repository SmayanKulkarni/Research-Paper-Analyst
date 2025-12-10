'use client';

import { motion } from 'framer-motion';
import styles from './GlassPanel.module.css';
import { cn } from '@/lib/utils';

/**
 * Glassmorphism panel with animated gradient border
 */
export function GlassPanel({
    children,
    className,
    glow = false,
    ...props
}) {
    return (
        <motion.div
            className={cn(styles.panel, glow && styles.glow, className)}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
            {...props}
        >
            <div className={styles.inner}>
                {children}
            </div>
        </motion.div>
    );
}

export default GlassPanel;
