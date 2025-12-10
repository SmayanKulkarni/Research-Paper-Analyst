'use client';

import { motion, useMotionTemplate, useMotionValue } from 'framer-motion';
import styles from './Card.module.css';

export function Card({
    children,
    variant = 'default',
    className = '',
    spotlight = false,
    ...props
}) {
    const mouseX = useMotionValue(0);
    const mouseY = useMotionValue(0);

    function handleMouseMove({ currentTarget, clientX, clientY }) {
        const { left, top } = currentTarget.getBoundingClientRect();
        mouseX.set(clientX - left);
        mouseY.set(clientY - top);
    }

    return (
        <div
            className={`${styles.card} ${styles[variant]} ${className} ${spotlight ? styles.spotlightContainer : ''}`}
            onMouseMove={spotlight ? handleMouseMove : undefined}
            {...props}
        >
            {spotlight && (
                <motion.div
                    className={styles.spotlightOverlay}
                    style={{
                        background: useMotionTemplate`
              radial-gradient(
                500px circle at ${mouseX}px ${mouseY}px,
                rgba(59, 130, 246, 0.25),
                transparent 80%
              )
            `,
                    }}
                />
            )}
            <div className={styles.contentWrapper}>
                {children}
            </div>
        </div>
    );
}

export function CardHeader({ children, className = '' }) {
    return <div className={`${styles.header} ${className}`}>{children}</div>;
}

export function CardTitle({ children, className = '' }) {
    return <h3 className={`${styles.title} ${className}`}>{children}</h3>;
}

export function CardDescription({ children, className = '' }) {
    return <p className={`${styles.description} ${className}`}>{children}</p>;
}

export function CardContent({ children, className = '' }) {
    return <div className={`${styles.content} ${className}`}>{children}</div>;
}

export function CardFooter({ children, className = '' }) {
    return <div className={`${styles.footer} ${className}`}>{children}</div>;
}

export default Card;
