'use client';

import React from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import * as Accordion from '@radix-ui/react-accordion';
import { motion } from 'framer-motion';
import {
    CheckCircle2,
    FileText,
    Quote,
    Calculator,
    Shield,
    Image as ImageIcon,
    Download,
    ChevronDown,
    AlertCircle
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { getReportUrl } from '@/lib/api';
import styles from './ResultsPanel.module.css';

// Map backend keys to frontend tabs
const TABS = [
    { id: 'language_quality', label: 'Grammar', icon: <CheckCircle2 size={16} /> },
    { id: 'structure', label: 'Structure', icon: <FileText size={16} /> },
    { id: 'citations', label: 'Citations', icon: <Quote size={16} /> },
    { id: 'math_review', label: 'Math', icon: <Calculator size={16} /> },
    { id: 'plagiarism', label: 'Plagiarism', icon: <Shield size={16} /> },
    { id: 'vision', label: 'Figures', icon: <ImageIcon size={16} /> },
];

export function ResultsPanel({ results, fileId }) {
    const handleDownload = () => {
        if (fileId) window.open(getReportUrl(fileId), '_blank');
    };

    if (!results) return null;

    // Filter tabs to only show those with content
    const availableTabs = TABS.filter(tab => {
        const content = results[tab.id];
        if (!content || content === null) return false;
        // Check if string contains failure message
        if (typeof content === 'string' && content.toLowerCase().includes('analysis failed')) return false;
        return true;
    });

    // Default to first available tab
    const defaultTab = availableTabs.length > 0 ? availableTabs[0].id : 'language_quality';

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <div>
                    <h2 className={styles.title}>Analysis Report</h2>
                    <p className={styles.subtitle}>AI-generated insights for your paper</p>
                </div>
                <Button
                    variant="primary"
                    size="sm"
                    icon={<Download size={16} />}
                    onClick={handleDownload}
                    disabled={!fileId}
                >
                    Download PDF
                </Button>
            </div>

            <Tabs.Root defaultValue={defaultTab} className={styles.tabsRoot}>
                <Tabs.List className={styles.tabsList}>
                    {availableTabs.map((tab) => (
                        <Tabs.Trigger
                            key={tab.id}
                            value={tab.id}
                            className={styles.tabsTrigger}
                        >
                            {tab.icon}
                            <span>{tab.label}</span>
                        </Tabs.Trigger>
                    ))}
                </Tabs.List>

                {availableTabs.map((tab) => (
                    <Tabs.Content key={tab.id} value={tab.id} className={styles.tabsContent}>
                        <TabContent content={results[tab.id]} type={tab.id} />
                    </Tabs.Content>
                ))}
            </Tabs.Root>
        </div>
    );
}

function TabContent({ content, type }) {
    if (!content || content === null || content.includes?.('No analysis available') || content.includes?.('Analysis failed')) {
        return (
            <div className={styles.emptyState}>
                <AlertCircle size={24} />
                <p>No data available for this section.</p>
            </div>
        );
    }

    // Vision content is JSON, handle separately
    if (type === 'vision' && typeof content === 'object') {
        return (
            <pre className={styles.jsonContent}>
                {JSON.stringify(content, null, 2)}
            </pre>
        );
    }

    // Clean up LLM artifacts from the response
    let cleanContent = String(content);

    // Remove common LLM thinking artifacts
    cleanContent = cleanContent.replace(/^(I now can give a great answer\.?\n?)/i, '');
    cleanContent = cleanContent.replace(/^(Thought:.*?\n)/i, '');
    cleanContent = cleanContent.replace(/^(I now know the final answer\.?\n?)/i, '');

    // Parse markdown-like structure
    const sections = parseContent(cleanContent);

    if (sections.length === 0) {
        return (
            <div className={styles.plainContent}>
                {cleanContent.split('\n').map((line, i) => (
                    <p key={i} className={styles.paragraph}>{line}</p>
                ))}
            </div>
        );
    }

    return (
        <Accordion.Root type="multiple" defaultValue={['item-0']} className={styles.accordionRoot}>
            {sections.map((section, idx) => (
                <Accordion.Item key={idx} value={`item-${idx}`} className={styles.accordionItem}>
                    <Accordion.Header className={styles.accordionHeader}>
                        <Accordion.Trigger className={styles.accordionTrigger}>
                            <span>{section.title}</span>
                            <ChevronDown className={styles.accordionChevron} size={16} />
                        </Accordion.Trigger>
                    </Accordion.Header>
                    <Accordion.Content className={styles.accordionContent}>
                        <div className={styles.accordionBody}>
                            {section.body.map((line, i) => (
                                <p key={i} className={getLineClass(line, styles)}>
                                    {formatLine(line)}
                                </p>
                            ))}
                        </div>
                    </Accordion.Content>
                </Accordion.Item>
            ))}
        </Accordion.Root>
    );
}

// Helper to determine line styling
function getLineClass(line, styles) {
    if (line.startsWith('•') || line.startsWith('-') || line.startsWith('*')) {
        return styles.bullet;
    }
    if (line.match(/^\d+\./)) {
        return styles.numbered;
    }
    // Highlight similarity scores, ratings, and important metrics
    if (line.includes('Similarity:') || line.includes('Originality Rating:') ||
        line.includes('Highest Similarity:') || line.includes('Score:') ||
        line.includes('Severity:') || line.includes('Papers Compared:') ||
        line.includes('Papers Found:')) {
        return styles.highlight;
    }
    // Highlight quotes/passages  
    if (line.includes('"') && line.includes('match')) {
        return styles.quote;
    }
    return styles.paragraph;
}

// Helper to format special characters in lines
function formatLine(line) {
    // Bold text between ** markers - render as styled
    let formatted = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italics between * markers
    formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Return as HTML if formatted
    if (formatted.includes('<strong>') || formatted.includes('<em>')) {
        return <span dangerouslySetInnerHTML={{ __html: formatted }} />;
    }
    return line;
}

// Helper to parse the text content into sections
function parseContent(text) {
    if (typeof text !== 'string') return [];

    const lines = text.split('\n');
    const sections = [];
    let currentSection = { title: 'Overview', body: [] };

    lines.forEach(line => {
        const trimmed = line.trim();
        if (!trimmed) return;

        // Check for markdown headers (## or ###)
        if (trimmed.startsWith('##') || trimmed.startsWith('###')) {
            if (currentSection.body.length > 0 || sections.length === 0) {
                if (currentSection.body.length > 0) {
                    sections.push(currentSection);
                }
            }
            currentSection = {
                title: trimmed.replace(/^#+\s*/, '').replace(/\*\*/g, ''),
                body: []
            };
        } else if (trimmed.startsWith('**') && trimmed.endsWith('**') && !trimmed.includes(':')) {
            // Bold headers like **Grammar & Syntax Review**
            if (currentSection.body.length > 0) {
                sections.push(currentSection);
            }
            currentSection = {
                title: trimmed.replace(/\*\*/g, ''),
                body: []
            };
        } else {
            currentSection.body.push(trimmed);
        }
    });

    if (currentSection.body.length > 0) {
        sections.push(currentSection);
    }

    return sections;
}

export default ResultsPanel;
