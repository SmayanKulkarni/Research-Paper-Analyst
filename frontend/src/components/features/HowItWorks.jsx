'use client';

import { motion } from 'framer-motion';
import { Upload, FileText, Cpu, Download } from 'lucide-react';
import styles from './HowItWorks.module.css';

const steps = [
    {
        icon: <Upload size={32} />,
        number: '01',
        title: 'Upload Your PDF',
        description: 'Drag and drop or click to upload your research paper in PDF format.',
    },
    {
        icon: <Cpu size={32} />,
        number: '02',
        title: 'AI Analysis',
        description: 'Our AI agents analyze grammar, structure, citations, and consistency.',
    },
    {
        icon: <FileText size={32} />,
        number: '03',
        title: 'Review Results',
        description: 'Get detailed feedback organized by category with actionable suggestions.',
    },
    {
        icon: <Download size={32} />,
        number: '04',
        title: 'Download Report',
        description: 'Export a comprehensive PDF report with all findings and recommendations.',
    },
];

/**
 * How it works section with step-by-step guide
 */
export function HowItWorks() {
    return (
        <section className={styles.section}>
            <div className={styles.container}>
                {/* Header */}
                <motion.div
                    className={styles.header}
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6 }}
                >
                    <span className={styles.label}>How It Works</span>
                    <h2 className={styles.title}>
                        Simple, Fast, Effective
                    </h2>
                    <p className={styles.subtitle}>
                        Get your paper analyzed in minutes with our streamlined process.
                    </p>
                </motion.div>

                {/* Steps */}
                <div className={styles.steps}>
                    {steps.map((step, index) => (
                        <motion.div
                            key={index}
                            className={styles.step}
                            initial={{ opacity: 0, y: 30 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.5, delay: index * 0.15 }}
                        >
                            {/* Connector Line */}
                            {index < steps.length - 1 && (
                                <div className={styles.connector} />
                            )}

                            <div className={styles.stepIcon}>
                                {step.icon}
                                <span className={styles.stepNumber}>{step.number}</span>
                            </div>

                            <h3 className={styles.stepTitle}>{step.title}</h3>
                            <p className={styles.stepDescription}>{step.description}</p>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    );
}

export default HowItWorks;
