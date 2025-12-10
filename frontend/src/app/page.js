"use client";

import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Hero } from "@/components/features/Hero";
import { Features } from "@/components/features/Features";
import { HowItWorks } from "@/components/features/HowItWorks";
import styles from "./page.module.css";

/**
 * Landing Page - Home page for Research Paper Analyst
 */
export default function Home() {
  return (
    <div className={styles.page}>
      <Navbar />
      <main className={styles.main}>
        <Hero />
        <Features />
        <HowItWorks />
      </main>
      <Footer />
    </div>
  );
}
