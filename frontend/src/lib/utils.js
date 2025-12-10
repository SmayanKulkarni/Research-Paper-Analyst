/**
 * Utility functions for the Research Paper Analyst frontend
 */

/**
 * Format file size in human-readable format
 * @param {number} bytes - Size in bytes
 * @returns {string}
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return "0 Bytes";

  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

/**
 * Truncate text with ellipsis
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string}
 */
export function truncateText(text, maxLength = 100) {
  if (!text || text.length <= maxLength) return text;
  return text.slice(0, maxLength).trim() + "...";
}

/**
 * Sleep for a given duration
 * @param {number} ms - Duration in milliseconds
 * @returns {Promise<void>}
 */
export function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Classnames utility - combines class names
 * @param  {...any} classes - Class names to combine
 * @returns {string}
 */
export function cn(...classes) {
  return classes.filter(Boolean).join(" ");
}

/**
 * Parse markdown-like text to extract key sections
 * @param {string} text - Raw text from analysis
 * @returns {object}
 */
export function parseAnalysisText(text) {
  if (!text) return { content: "", sections: [] };

  const lines = text.split("\n");
  const sections = [];
  let currentSection = null;

  for (const line of lines) {
    // Check for headers
    if (line.startsWith("###")) {
      if (currentSection) sections.push(currentSection);
      currentSection = { title: line.replace(/^#+\s*/, ""), content: [] };
    } else if (line.startsWith("##")) {
      if (currentSection) sections.push(currentSection);
      currentSection = { title: line.replace(/^#+\s*/, ""), content: [] };
    } else if (currentSection) {
      currentSection.content.push(line);
    }
  }

  if (currentSection) sections.push(currentSection);

  return {
    content: text,
    sections: sections.map((s) => ({
      ...s,
      content: s.content.join("\n").trim(),
    })),
  };
}

/**
 * Generate a unique ID
 * @returns {string}
 */
export function generateId() {
  return Math.random().toString(36).substring(2, 9);
}

/**
 * Debounce function
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in ms
 * @returns {Function}
 */
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}
