'use client';

import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import styles from './Button.module.css';

export function Button({
    children,
    variant = 'primary', // primary, secondary, ghost, outline
    size = 'md', // sm, md, lg
    disabled = false,
    loading = false,
    icon,
    iconPosition = 'left',
    className = '',
    onClick,
    type = 'button',
    ...props
}) {
    return (
        <motion.button
            type={type}
            className={`${styles.btn} ${styles[variant]} ${styles[size]} ${className}`}
            disabled={disabled || loading}
            onClick={onClick}
            whileTap={{ scale: 0.98 }}
            transition={{ duration: 0.1 }}
            {...props}
        >
            {loading && <Loader2 size={16} className={styles.spinner} />}

            {!loading && icon && iconPosition === 'left' && (
                <span className={styles.icon}>{icon}</span>
            )}

            <span>{children}</span>

            {!loading && icon && iconPosition === 'right' && (
                <span className={styles.icon}>{icon}</span>
            )}
        </motion.button>
    );
}

export default Button;
