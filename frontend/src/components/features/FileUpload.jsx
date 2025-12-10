'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import { UploadCloud, FileText, X, Check, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { formatFileSize } from '@/lib/utils';
import styles from './FileUpload.module.css';

export function FileUpload({ onFileSelect, isUploading = false, uploadProgress = 0 }) {
    const [file, setFile] = useState(null);
    const [error, setError] = useState(null);

    const onDrop = useCallback((acceptedFiles, rejectedFiles) => {
        setError(null);
        if (rejectedFiles.length > 0) {
            setError('Please upload a valid PDF file under 50MB.');
            return;
        }
        if (acceptedFiles.length > 0) {
            const selectedFile = acceptedFiles[0];
            setFile(selectedFile);
            onFileSelect?.(selectedFile);
        }
    }, [onFileSelect]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { 'application/pdf': ['.pdf'] },
        maxFiles: 1,
        maxSize: 50 * 1024 * 1024,
        disabled: isUploading,
    });

    const removeFile = (e) => {
        e.stopPropagation();
        setFile(null);
        setError(null);
    };

    return (
        <div className={styles.container}>
            <AnimatePresence mode="wait">
                {!file ? (
                    <motion.div
                        key="dropzone"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className={`${styles.dropzone} ${isDragActive ? styles.active : ''} ${error ? styles.error : ''}`}
                        {...getRootProps()}
                    >
                        <input {...getInputProps()} />

                        <div className={styles.iconWrapper}>
                            <UploadCloud size={32} strokeWidth={1.5} />
                        </div>

                        <div className={styles.textWrapper}>
                            <p className={styles.primaryText}>
                                <span className={styles.highlight}>Click to upload</span> or drag and drop
                            </p>
                            <p className={styles.secondaryText}>PDF (max. 50MB)</p>
                        </div>

                        {error && (
                            <div className={styles.errorMessage}>
                                <AlertCircle size={14} />
                                <span>{error}</span>
                            </div>
                        )}
                    </motion.div>
                ) : (
                    <motion.div
                        key="preview"
                        initial={{ opacity: 0, scale: 0.98 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.98 }}
                        className={styles.fileCard}
                    >
                        <div className={styles.fileIcon}>
                            <FileText size={24} strokeWidth={1.5} />
                        </div>

                        <div className={styles.fileInfo}>
                            <p className={styles.fileName}>{file.name}</p>
                            <p className={styles.fileSize}>{formatFileSize(file.size)}</p>
                        </div>

                        {isUploading ? (
                            <div className={styles.uploadStatus}>
                                <div className={styles.spinner} />
                            </div>
                        ) : (
                            <button onClick={removeFile} className={styles.removeBtn}>
                                <X size={18} />
                            </button>
                        )}

                        {isUploading && (
                            <div className={styles.progressBar}>
                                <motion.div
                                    className={styles.progressFill}
                                    initial={{ width: 0 }}
                                    animate={{ width: `${uploadProgress}%` }}
                                />
                            </div>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

export default FileUpload;
