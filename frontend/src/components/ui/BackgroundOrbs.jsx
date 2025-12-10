'use client';

import { motion } from 'framer-motion';
import styles from './BackgroundOrbs.module.css';

export function BackgroundOrbs() {
    return (
        <div className={styles.container}>
            <motion.div
                className={`${styles.orb} ${styles.orb1}`}
                animate={{
                    x: [0, 100, 0],
                    y: [0, -50, 0],
                    scale: [1, 1.2, 1],
                }}
                transition={{
                    duration: 20,
                    repeat: Infinity,
                    ease: "easeInOut"
                }}
            />
            <motion.div
                className={`${styles.orb} ${styles.orb2}`}
                animate={{
                    x: [0, -70, 0],
                    y: [0, 100, 0],
                    scale: [1, 1.5, 1],
                }}
                transition={{
                    duration: 25,
                    repeat: Infinity,
                    ease: "easeInOut",
                    delay: 2
                }}
            />
        </div>
    );
}

export default BackgroundOrbs;
