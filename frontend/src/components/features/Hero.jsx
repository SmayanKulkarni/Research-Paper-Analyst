'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { ArrowRight, Sparkles, FileText, Zap } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import styles from './Hero.module.css';

export function Hero() {
    return (
        <section className={styles.hero}>
            <div className={styles.glow} />

            <div className={styles.container}>
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
                    className={styles.content}
                >
                    <div className={styles.badge}>
                        <Sparkles size={12} className={styles.badgeIcon} />
                        <span>AI-Powered Research Assistant</span>
                    </div>

                    <h1 className={styles.title}>
                        Analyze papers with <br />
                        <span className={styles.gradientText}>superhuman precision</span>
                    </h1>

                    <p className={styles.subtitle}>
                        Get instant feedback on grammar, structure, citations, and consistency.
                        Transform your research workflow with our multi-agent AI system.
                    </p>

                    <div className={styles.actions}>
                        <Link href="/analyze">
                            <Button size="lg" icon={<Zap size={18} />}>
                                Start Analysis
                            </Button>
                        </Link>
                        <Link href="#features">
                            <Button variant="secondary" size="lg" icon={<ArrowRight size={18} />} iconPosition="right">
                                How it works
                            </Button>
                        </Link>
                    </div>

                    <div className={styles.stats}>
                        <div className={styles.statItem}>
                            <strong>5+</strong> Agents
                        </div>
                        <div className={styles.statDivider} />
                        <div className={styles.statItem}>
                            <strong>100%</strong> Automated
                        </div>
                        <div className={styles.statDivider} />
                        <div className={styles.statItem}>
                            <strong>PDF</strong> Reports
                        </div>
                    </div>
                </motion.div>

                {/* Abstract Visual Representation */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
                    className={styles.visual}
                >
                    <div className={styles.cardStack}>
                        <div className={`${styles.card} ${styles.card1}`}>
                            <div className={styles.cardHeader}>
                                <div className={styles.skeletonLine} style={{ width: '40%' }} />
                                <div className={styles.skeletonCircle} />
                            </div>
                            <div className={styles.skeletonBody}>
                                <div className={styles.skeletonLine} />
                                <div className={styles.skeletonLine} style={{ width: '80%' }} />
                                <div className={styles.skeletonLine} style={{ width: '60%' }} />
                            </div>
                        </div>
                        <div className={`${styles.card} ${styles.card2}`} />
                        <div className={`${styles.card} ${styles.card3}`} />
                    </div>
                </motion.div>
            </div>
        </section>
    );
}

export default Hero;
