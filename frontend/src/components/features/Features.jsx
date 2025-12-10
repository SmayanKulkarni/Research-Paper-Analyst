'use client';

import { motion } from 'framer-motion';
import {
    CheckCircle,
    FileText,
    Search,
    GitCompare,
    Eye,
    BookOpen
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import styles from './Features.module.css';

const features = [
    {
        icon: <CheckCircle size={28} />,
        title: 'Grammar & Style',
        description: 'AI-powered proofreading that catches grammar errors, improves clarity, and refines your academic writing style.',
        color: 'primary',
    },
    {
        icon: <FileText size={28} />,
        title: 'Structure Analysis',
        description: 'Validate your paper follows proper academic structure (IMRAD) with detailed section-by-section feedback.',
        color: 'accent',
    },
    {
        icon: <Search size={28} />,
        title: 'Citation Check',
        description: 'Verify citation formatting and cross-reference claims with sources to ensure academic integrity.',
        color: 'primary',
    },
    {
        icon: <GitCompare size={28} />,
        title: 'Consistency Review',
        description: 'Detect contradictions, inconsistent terminology, and logical gaps throughout your paper.',
        color: 'accent',
    },
    {
        icon: <Eye size={28} />,
        title: 'Visual Analysis',
        description: 'Optional AI vision analysis of figures, charts, and images to verify quality and relevance.',
        color: 'primary',
    },
    {
        icon: <BookOpen size={28} />,
        title: 'PDF Report',
        description: 'Download a comprehensive PDF report with all findings, suggestions, and improvement recommendations.',
        color: 'accent',
    },
];

export function Features() {
    return (
        <section id="features" className={styles.section}>
            <div className={styles.container}>
                <motion.div
                    className={styles.header}
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6 }}
                >
                    <span className={styles.label}>Features</span>
                    <h2 className={styles.title}>
                        Comprehensive Paper Analysis
                    </h2>
                    <p className={styles.subtitle}>
                        Multiple AI agents work together to provide thorough,
                        multi-dimensional feedback on your research paper.
                    </p>
                </motion.div>

                <div className={styles.grid}>
                    {features.map((feature, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ delay: index * 0.1 }}
                        >
                            <Card variant="default" spotlight className={styles.card}>
                                <div className={`${styles.iconWrapper} ${styles[feature.color]}`}>
                                    {feature.icon}
                                </div>
                                <CardHeader>
                                    <CardTitle>{feature.title}</CardTitle>
                                    <CardDescription>{feature.description}</CardDescription>
                                </CardHeader>
                            </Card>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    );
}

export default Features;
