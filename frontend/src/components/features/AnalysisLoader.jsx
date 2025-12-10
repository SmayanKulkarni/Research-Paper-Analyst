'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import Lottie from 'lottie-react';
import { Check, Loader2 } from 'lucide-react';
import { loadingDotsAnimation } from '@/lib/animations';
import styles from './AnalysisLoader.module.css';
import * as Progress from '@radix-ui/react-progress';

const STEPS = [
    { id: 'upload', label: 'Uploading Document' },
    { id: 'parse', label: 'Extracting Content' },
    { id: 'proofreading', label: 'Analyzing Grammar' },
    { id: 'structure', label: 'Checking Structure' },
    { id: 'citations', label: 'Verifying Citations' },
    { id: 'consistency', label: 'Reviewing Consistency' },
    { id: 'report', label: 'Finalizing Report' },
];

export function AnalysisLoader({ isAnalyzing = false }) {
    const [progress, setProgress] = useState(0);
    const [currentStepIndex, setCurrentStepIndex] = useState(0);

    useEffect(() => {
        if (!isAnalyzing) return;

        const interval = setInterval(() => {
            setProgress((prev) => {
                if (prev >= 100) {
                    clearInterval(interval);
                    return 100;
                }
                return prev + 0.5; // Slow, smooth progress
            });
        }, 50);

        return () => clearInterval(interval);
    }, [isAnalyzing]);

    useEffect(() => {
        const stepDuration = 100 / STEPS.length;
        const newIndex = Math.min(
            Math.floor(progress / stepDuration),
            STEPS.length - 1
        );
        setCurrentStepIndex(newIndex);
    }, [progress]);

    return (
        <div className={styles.container}>
            <div className={styles.content}>
                <div className={styles.animationWrapper}>
                    <Lottie
                        animationData={loadingDotsAnimation}
                        loop
                        autoplay
                        className={styles.lottie}
                    />
                </div>

                <h2 className={styles.title}>Analyzing Paper</h2>
                <p className={styles.subtitle}>
                    {STEPS[currentStepIndex].label}...
                </p>

                <Progress.Root className={styles.progressRoot} value={progress}>
                    <Progress.Indicator
                        className={styles.progressIndicator}
                        style={{ transform: `translateX(-${100 - progress}%)` }}
                    />
                </Progress.Root>

                <div className={styles.stepsGrid}>
                    {STEPS.map((step, idx) => {
                        const isActive = idx === currentStepIndex;
                        const isCompleted = idx < currentStepIndex;

                        return (
                            <div
                                key={step.id}
                                className={`${styles.stepItem} ${isActive ? styles.active : ''} ${isCompleted ? styles.completed : ''}`}
                            >
                                <div className={styles.stepIcon}>
                                    {isCompleted ? (
                                        <Check size={12} strokeWidth={3} />
                                    ) : isActive ? (
                                        <Loader2 size={12} className={styles.spin} />
                                    ) : (
                                        <div className={styles.dot} />
                                    )}
                                </div>
                                <span className={styles.stepLabel}>{step.label}</span>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}

export default AnalysisLoader;
