"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Sparkles } from "lucide-react";
import Link from "next/link";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { FileUpload } from "@/components/features/FileUpload";
import { AnalysisLoader } from "@/components/features/AnalysisLoader";
import { ResultsPanel } from "@/components/features/ResultsPanel";
import { Button } from "@/components/ui/Button";
import { uploadPDF, analyzeFile } from "@/lib/api";
import styles from "./page.module.css";

/**
 * Analysis Page - Upload and analyze research papers
 */
export default function AnalyzePage() {
  const [state, setState] = useState("upload"); // 'upload' | 'analyzing' | 'results' | 'error'
  const [file, setFile] = useState(null);
  const [fileId, setFileId] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const handleFileSelect = async (selectedFile) => {
    setFile(selectedFile);
    setError(null);
    setIsUploading(true);
    setUploadProgress(0);

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      // Upload the file
      const uploadResult = await uploadPDF(selectedFile);

      clearInterval(progressInterval);
      setUploadProgress(100);
      setFileId(uploadResult.file_id);
      setIsUploading(false);
    } catch (err) {
      setIsUploading(false);
      setError(err.message || "Failed to upload file");
      setUploadProgress(0);
    }
  };

  const handleStartAnalysis = async () => {
    if (!fileId) return;

    setState("analyzing");
    setError(null);

    try {
      const analysisResults = await analyzeFile(fileId);
      setResults(analysisResults);
      setState("results");
    } catch (err) {
      setError(err.message || "Analysis failed");
      setState("error");
    }
  };

  const handleReset = () => {
    setState("upload");
    setFile(null);
    setFileId(null);
    setUploadProgress(0);
    setResults(null);
    setError(null);
  };

  return (
    <div className={styles.page}>
      <Navbar />

      <main className={styles.main}>
        <div className={styles.container}>
          {/* Header */}
          <motion.div
            className={styles.header}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Link href="/" className={styles.backLink}>
              <ArrowLeft size={18} />
              <span>Back to Home</span>
            </Link>

            <div className={styles.headerContent}>
              <div className={styles.badge}>
                <Sparkles size={14} />
                <span>AI Analysis</span>
              </div>
              <h1 className={styles.title}>Analyze Your Paper</h1>
              <p className={styles.subtitle}>
                Upload your research paper and get comprehensive feedback from
                our AI agents.
              </p>
            </div>
          </motion.div>

          {/* Content */}
          <div className={styles.content}>
            <AnimatePresence mode="wait">
              {state === "upload" && (
                <motion.div
                  key="upload"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.4 }}
                  className={styles.uploadSection}
                >
                  <FileUpload
                    onFileSelect={handleFileSelect}
                    isUploading={isUploading}
                    uploadProgress={uploadProgress}
                  />

                  {fileId && !isUploading && (
                    <motion.div
                      className={styles.startAnalysis}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.3 }}
                    >
                      <Button
                        variant="primary"
                        size="lg"
                        icon={<Sparkles size={20} />}
                        onClick={handleStartAnalysis}
                      >
                        Start Analysis
                      </Button>
                      <p className={styles.hint}>
                        This will analyze grammar, structure, citations, and
                        consistency.
                      </p>
                    </motion.div>
                  )}

                  {error && (
                    <motion.div
                      className={styles.error}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                    >
                      {error}
                    </motion.div>
                  )}
                </motion.div>
              )}

              {state === "analyzing" && (
                <motion.div
                  key="analyzing"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.4 }}
                >
                  <AnalysisLoader isAnalyzing />
                </motion.div>
              )}

              {state === "results" && (
                <motion.div
                  key="results"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.4 }}
                  className={styles.resultsSection}
                >
                  <ResultsPanel results={results} fileId={fileId} />

                  <div className={styles.actions}>
                    <Button variant="secondary" onClick={handleReset}>
                      Analyze Another Paper
                    </Button>
                  </div>
                </motion.div>
              )}

              {state === "error" && (
                <motion.div
                  key="error"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className={styles.errorSection}
                >
                  <div className={styles.errorContent}>
                    <h2>Analysis Failed</h2>
                    <p>{error}</p>
                    <Button variant="primary" onClick={handleReset}>
                      Try Again
                    </Button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
