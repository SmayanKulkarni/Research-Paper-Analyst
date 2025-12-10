/**
 * API Client for Research Paper Analyst Backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Upload a PDF file for analysis
 * @param {File} file - The PDF file to upload
 * @returns {Promise<{file_id: string, filename: string}>}
 */
export async function uploadPDF(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/api/uploads/`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to upload PDF");
  }

  return response.json();
}

/**
 * Run full analysis on an uploaded PDF
 * @param {string} fileId - The file ID from upload
 * @returns {Promise<AnalysisResult>}
 */
export async function analyzeFile(fileId) {
  const response = await fetch(`${API_BASE}/api/analyze/?file_id=${fileId}`, {
    method: "POST",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Analysis failed");
  }

  return response.json();
}

/**
 * Get the URL for downloading the PDF report
 * @param {string} fileId - The file ID
 * @returns {string}
 */
export function getReportUrl(fileId) {
  return `${API_BASE}/api/report/${fileId}`;
}

/**
 * Generate a new PDF report
 * @param {string} fileId - The file ID
 * @returns {Promise<{success: boolean, pdf_path: string, message: string}>}
 */
export async function generateReport(fileId) {
  const response = await fetch(`${API_BASE}/api/report/generate/${fileId}`, {
    method: "POST",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to generate report");
  }

  return response.json();
}

/**
 * Check if the backend is healthy
 * @returns {Promise<boolean>}
 */
export async function healthCheck() {
  try {
    const response = await fetch(`${API_BASE}/`);
    return response.ok;
  } catch {
    return false;
  }
}

export const api = {
  uploadPDF,
  analyzeFile,
  getReportUrl,
  generateReport,
  healthCheck,
};

export default api;
