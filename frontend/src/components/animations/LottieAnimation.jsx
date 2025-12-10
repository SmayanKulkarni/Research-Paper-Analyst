'use client';

import Lottie from 'lottie-react';
import { motion } from 'framer-motion';
import styles from './LottieAnimation.module.css';
import { cn } from '@/lib/utils';

/**
 * Wrapper component for Lottie animations
 */
export function LottieAnimation({
    animationData,
    loop = true,
    autoplay = true,
    className,
    size = 'md',
    ...props
}) {
    const sizes = {
        sm: styles.sm,
        md: styles.md,
        lg: styles.lg,
        xl: styles.xl,
        full: styles.full,
    };

    return (
        <motion.div
            className={cn(styles.container, sizes[size], className)}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
        >
            <Lottie
                animationData={animationData}
                loop={loop}
                autoplay={autoplay}
                {...props}
            />
        </motion.div>
    );
}

export default LottieAnimation;
