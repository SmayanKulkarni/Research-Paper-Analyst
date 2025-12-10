'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, Menu, X } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import styles from './Navbar.module.css';

export function Navbar() {
    const [scrolled, setScrolled] = useState(false);
    const [mobileOpen, setMobileOpen] = useState(false);

    useEffect(() => {
        const handleScroll = () => setScrolled(window.scrollY > 20);
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <header className={`${styles.header} ${scrolled ? styles.scrolled : ''}`}>
            <div className={styles.container}>
                <Link href="/" className={styles.logo}>
                    <div className={styles.logoIcon}>
                        <FileText size={20} />
                    </div>
                    <span className={styles.logoText}>PaperAnalyst</span>
                </Link>

                <nav className={styles.desktopNav}>
                    <Link href="/" className={styles.navLink}>Home</Link>
                    <Link href="#features" className={styles.navLink}>Features</Link>
                    <Link href="/analyze">
                        <Button size="sm" variant="primary">Launch App</Button>
                    </Link>
                </nav>

                <button className={styles.mobileToggle} onClick={() => setMobileOpen(!mobileOpen)}>
                    {mobileOpen ? <X size={24} /> : <Menu size={24} />}
                </button>

                <AnimatePresence>
                    {mobileOpen && (
                        <motion.div
                            initial={{ opacity: 0, y: -20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            className={styles.mobileNav}
                        >
                            <Link href="/" onClick={() => setMobileOpen(false)} className={styles.mobileLink}>Home</Link>
                            <Link href="#features" onClick={() => setMobileOpen(false)} className={styles.mobileLink}>Features</Link>
                            <Link href="/analyze" onClick={() => setMobileOpen(false)}>
                                <Button className={styles.mobileBtn}>Launch App</Button>
                            </Link>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </header>
    );
}

export default Navbar;
