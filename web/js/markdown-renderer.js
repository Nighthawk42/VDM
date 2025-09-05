// web/js/markdown-renderer.js

// Import the libraries directly from the CDN.
// This ensures they are loaded before this code runs.
import { marked } from "https://cdn.jsdelivr.net/npm/marked/lib/marked.esm.js";
import DOMPurify from "https://cdn.jsdelivr.net/npm/dompurify/dist/purify.es.js";

/**
 * Safely converts a string of Markdown text into sanitized HTML.
 * @param {string} markdownText The raw text to convert.
 * @returns {string} The sanitized HTML string, ready to be inserted into the DOM.
 */
export function renderMarkdown(markdownText) {
    if (typeof markdownText !== 'string' || !markdownText) {
        return "";
    }

    // 1. Convert the raw text from the server into HTML using marked.js
    const dirtyHtml = marked.parse(markdownText);
    
    // 2. Sanitize that HTML using DOMPurify to prevent XSS attacks.
    const cleanHtml = DOMPurify.sanitize(dirtyHtml);
    
    return cleanHtml;
}