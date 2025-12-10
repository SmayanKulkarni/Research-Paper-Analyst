'use client';

import Link from 'next/link';
import { FileText, Github, Twitter, Linkedin } from 'lucide-react';
import styles from './Footer.module.css';

/**
 * Footer component with links and branding
 */
export function Footer() {
    const currentYear = new Date().getFullYear();

    return (
        <footer className={styles.footer}>
            <div className={styles.container}>
                <div className={styles.grid}>
                    {/* Brand Section */}
                    <div className={styles.brand}>
                        <Link href="/" className={styles.logo}>
                            <div className={styles.logoIcon}>
                                <FileText size={24} />
                            </div>
                            <span className={styles.logoText}>
                                Paper<span className="gradient-text">Analyst</span>
                            </span>
                        </Link>
                        <p className={styles.description}>
                            AI-powered research paper analysis tool. Get detailed feedback on grammar,
                            structure, citations, and more.
                        </p>
                    </div>

                    {/* Quick Links */}
                    <div className={styles.section}>
                        <h4 className={styles.sectionTitle}>Quick Links</h4>
                        <nav className={styles.links}>
                            <Link href="/" className={styles.link}>Home</Link>
                            <Link href="/analyze" className={styles.link}>Analyze Paper</Link>
                        </nav>
                    </div>

                    {/* Features */}
                    <div className={styles.section}>
                        <h4 className={styles.sectionTitle}>Features</h4>
                        <nav className={styles.links}>
                            <span className={styles.link}>Grammar Check</span>
                            <span className={styles.link}>Structure Analysis</span>
                            <span className={styles.link}>Citation Verification</span>
                            <span className={styles.link}>Consistency Review</span>
                        </nav>
                    </div>
                </div>

                {/* Bottom Bar */}
                <div className={styles.bottom}>
                    <p className={styles.copyright}>
                        © {currentYear} Research Paper Analyst. All rights reserved.
                    </p>
                    <div className={styles.social}>
                        <a href="#" className={styles.socialLink} aria-label="GitHub">
                            <Github size={20} />
                        </a>
                        <a href="#" className={styles.socialLink} aria-label="Twitter">
                            <Twitter size={20} />
                        </a>
                        <a href="#" className={styles.socialLink} aria-label="LinkedIn">
                            <Linkedin size={20} />
                        </a>
                    </div>
                </div>
            </div>
        </footer>
    );
}

export default Footer;
