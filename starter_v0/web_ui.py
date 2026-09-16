from __future__ import annotations

import argparse
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from chat import run_model_tool_loop, safe_slug
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"
load_lab_env(ROOT)

PAGE = r"""<!doctype html>
<html lang="vi" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Northstar IT Helpdesk — Trợ lý Kỹ thuật Thông minh</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --font-main: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      --font-mono: 'JetBrains Mono', ui-monospace, monospace;
      --radius-sm: 8px;
      --radius-md: 14px;
      --radius-lg: 20px;
      --radius-full: 9999px;
      --transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }

    [data-theme="dark"] {
      --bg-base: #0a0e1a;
      --bg-gradient: radial-gradient(circle at 50% 0%, #171f38 0%, #0a0e1a 70%);
      --bg-surface: rgba(18, 24, 43, 0.75);
      --bg-surface-elevated: rgba(28, 37, 65, 0.8);
      --bg-card: #111827;
      --border: rgba(255, 255, 255, 0.08);
      --border-hover: rgba(99, 102, 241, 0.4);
      --text-primary: #f8fafc;
      --text-secondary: #94a3b8;
      --text-muted: #64748b;
      --accent-primary: #6366f1;
      --accent-hover: #4f46e5;
      --accent-gradient: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #d946ef 100%);
      --accent-glow: 0 0 25px rgba(99, 102, 241, 0.35);
      --user-msg-bg: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
      --user-msg-text: #ffffff;
      --agent-msg-bg: rgba(17, 24, 39, 0.75);
      --agent-msg-border: rgba(255, 255, 255, 0.07);
      --code-bg: #0d121f;
      --pre-bg: #090d16;
      --input-bg: rgba(15, 23, 42, 0.85);
      --card-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.5), 0 0 1px 1px rgba(255, 255, 255, 0.05);
      --trace-bg: rgba(13, 18, 30, 0.85);
      --scrollbar-thumb: #1e293b;
    }

    [data-theme="light"] {
      --bg-base: #f8fafc;
      --bg-gradient: radial-gradient(circle at 50% 0%, #e2e8f0 0%, #f8fafc 70%);
      --bg-surface: rgba(255, 255, 255, 0.85);
      --bg-surface-elevated: #ffffff;
      --bg-card: #ffffff;
      --border: rgba(0, 0, 0, 0.08);
      --border-hover: rgba(99, 102, 241, 0.3);
      --text-primary: #0f172a;
      --text-secondary: #475569;
      --text-muted: #94a3b8;
      --accent-primary: #4f46e5;
      --accent-hover: #4338ca;
      --accent-gradient: linear-gradient(135deg, #4f46e5 0%, #6366f1 50%, #8b5cf6 100%);
      --accent-glow: 0 0 20px rgba(79, 70, 229, 0.2);
      --user-msg-bg: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%);
      --user-msg-text: #ffffff;
      --agent-msg-bg: #ffffff;
      --agent-msg-border: rgba(0, 0, 0, 0.08);
      --code-bg: #f1f5f9;
      --pre-bg: #f8fafc;
      --input-bg: rgba(255, 255, 255, 0.95);
      --card-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.06), 0 0 1px 1px rgba(0, 0, 0, 0.04);
      --trace-bg: #f1f5f9;
      --scrollbar-thumb: #cbd5e1;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: var(--font-main);
      background: var(--bg-base);
      background-image: var(--bg-gradient);
      color: var(--text-primary);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      line-height: 1.6;
      transition: background 0.3s ease, color 0.3s ease;
    }

    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb); border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--accent-primary); }

    .app-container {
      max-width: 1040px;
      margin: 0 auto;
      width: 100%;
      display: flex;
      flex-direction: column;
      min-height: 100vh;
      padding: 0 20px;
    }

    header {
      position: sticky;
      top: 0;
      z-index: 50;
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border);
      padding: 14px 20px;
      margin: 0 -20px 20px -20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      text-decoration: none;
      color: inherit;
    }

    .brand-logo {
      width: 42px;
      height: 42px;
      border-radius: var(--radius-md);
      background: var(--accent-gradient);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: var(--accent-glow);
      color: white;
      flex-shrink: 0;
      transition: var(--transition);
    }
    .brand-logo:hover {
      transform: rotate(6deg) scale(1.05);
    }

    .brand-text h1 {
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      background: var(--accent-gradient);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      line-height: 1.2;
    }

    .brand-status {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.78rem;
      color: var(--text-secondary);
      font-weight: 500;
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 10px #10b981;
      display: inline-block;
      animation: pulse-dot 2s infinite;
    }

    @keyframes pulse-dot {
      0% { transform: scale(0.95); opacity: 0.8; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
      70% { transform: scale(1.1); opacity: 1; box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
      100% { transform: scale(0.95); opacity: 0.8; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    .header-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 4px 10px;
      border-radius: var(--radius-full);
      font-size: 0.75rem;
      font-weight: 600;
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border);
      color: var(--text-secondary);
      font-family: var(--font-mono);
      transition: var(--transition);
    }
    .badge:hover {
      border-color: var(--border-hover);
      color: var(--text-primary);
    }

    .badge.version {
      background: rgba(99, 102, 241, 0.12);
      border-color: rgba(99, 102, 241, 0.3);
      color: #818cf8;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .icon-btn {
      width: 38px;
      height: 38px;
      border-radius: var(--radius-md);
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border);
      color: var(--text-secondary);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: var(--transition);
      outline: none;
    }
    .icon-btn:hover {
      background: var(--bg-surface);
      color: var(--text-primary);
      border-color: var(--border-hover);
      transform: translateY(-1px);
    }

    /* Main Chat Stream */
    #chat {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 20px;
      padding-bottom: 24px;
    }

    /* Empty State Hero */
    .empty-hero {
      text-align: center;
      padding: 40px 20px;
      margin: auto 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      max-width: 680px;
      margin-inline: auto;
      animation: fadeIn 0.5s ease-out;
    }

    .hero-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      border-radius: var(--radius-full);
      background: rgba(99, 102, 241, 0.12);
      border: 1px solid rgba(99, 102, 241, 0.3);
      color: #818cf8;
      font-size: 0.85rem;
      font-weight: 600;
      margin-bottom: 16px;
    }

    .empty-hero h2 {
      font-size: 1.85rem;
      font-weight: 800;
      letter-spacing: -0.03em;
      margin-bottom: 10px;
      background: var(--accent-gradient);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .empty-hero p {
      color: var(--text-secondary);
      font-size: 0.98rem;
      max-width: 540px;
      margin-bottom: 28px;
    }

    .quick-chips-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 12px;
      width: 100%;
    }

    .quick-chip {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 14px 16px;
      text-align: left;
      cursor: pointer;
      display: flex;
      align-items: flex-start;
      gap: 12px;
      transition: var(--transition);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }
    .quick-chip:hover {
      border-color: var(--accent-primary);
      transform: translateY(-2px);
      box-shadow: var(--accent-glow);
      background: var(--bg-surface-elevated);
    }

    .chip-icon {
      width: 32px;
      height: 32px;
      border-radius: var(--radius-sm);
      background: rgba(99, 102, 241, 0.15);
      color: var(--accent-primary);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .chip-content strong {
      display: block;
      font-size: 0.88rem;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 2px;
    }
    .chip-content span {
      display: block;
      font-size: 0.78rem;
      color: var(--text-secondary);
    }

    /* Message Bubbles */
    .message-row {
      display: flex;
      gap: 14px;
      animation: messageIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      width: 100%;
    }

    @keyframes messageIn {
      from { opacity: 0; transform: translateY(12px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .message-row.user {
      flex-direction: row-reverse;
    }

    .avatar {
      width: 38px;
      height: 38px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      font-weight: 700;
      font-size: 0.85rem;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    .user .avatar {
      background: linear-gradient(135deg, #ec4899 0%, #8b5cf6 100%);
      color: #fff;
    }

    .agent .avatar {
      background: var(--accent-gradient);
      color: #fff;
      box-shadow: var(--accent-glow);
    }

    .error .avatar {
      background: #ef4444;
      color: #fff;
    }

    .message-bubble {
      max-width: 82%;
      border-radius: var(--radius-lg);
      padding: 16px 20px;
      position: relative;
      box-shadow: var(--card-shadow);
      font-size: 0.95rem;
      line-height: 1.65;
    }

    .user .message-bubble {
      background: var(--user-msg-bg);
      color: var(--user-msg-text);
      border-bottom-right-radius: 4px;
      font-weight: 500;
    }

    .agent .message-bubble {
      background: var(--agent-msg-bg);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid var(--agent-msg-border);
      border-bottom-left-radius: 4px;
      color: var(--text-primary);
    }

    .error .message-bubble {
      background: rgba(239, 68, 68, 0.12);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #fca5a5;
    }

    .msg-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
      font-size: 0.78rem;
      color: var(--text-secondary);
      font-weight: 600;
    }
    .user .msg-header {
      color: rgba(255, 255, 255, 0.8);
    }

    .msg-actions {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .copy-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      padding: 2px 6px;
      border-radius: var(--radius-sm);
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 0.72rem;
      transition: var(--transition);
    }
    .copy-btn:hover {
      color: var(--text-primary);
      background: rgba(255, 255, 255, 0.1);
    }

    .md-content { overflow-wrap: break-word; }
    .md-content p { margin-bottom: 10px; }
    .md-content p:last-child { margin-bottom: 0; }
    .md-content strong { color: #fff; font-weight: 700; }
    [data-theme="light"] .md-content strong { color: #0f172a; }
    .md-content em { font-style: italic; opacity: 0.9; }
    .md-content h2, .md-content h3, .md-content h4 {
      font-weight: 700;
      margin: 14px 0 6px 0;
      letter-spacing: -0.01em;
    }
    .md-content h2 { font-size: 1.25rem; color: #a5b4fc; }
    .md-content h3 { font-size: 1.1rem; color: #c7d2fe; }
    .md-content h4 { font-size: 1rem; color: #e0e7ff; }

    .md-ul, .md-ol {
      margin: 8px 0 12px 20px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .md-ul li::marker { color: var(--accent-primary); }

    .inline-code {
      font-family: var(--font-mono);
      background: var(--code-bg);
      color: #38bdf8;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.86em;
      border: 1px solid var(--border);
    }

    .code-block-wrapper {
      margin: 12px 0;
      border-radius: var(--radius-md);
      overflow: hidden;
      border: 1px solid var(--border);
      background: var(--pre-bg);
    }

    .code-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 6px 14px;
      background: rgba(0, 0, 0, 0.25);
      border-bottom: 1px solid var(--border);
      font-size: 0.72rem;
      font-family: var(--font-mono);
      color: var(--text-muted);
    }

    .code-header button {
      background: transparent;
      border: none;
      color: var(--text-secondary);
      font-size: 0.72rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 2px 6px;
      border-radius: 4px;
    }
    .code-header button:hover {
      color: #fff;
      background: rgba(255, 255, 255, 0.1);
    }

    .code-block {
      padding: 12px 16px;
      font-family: var(--font-mono);
      font-size: 0.85rem;
      overflow-x: auto;
      white-space: pre;
      color: #e2e8f0;
      line-height: 1.5;
    }

    .md-quote {
      border-left: 4px solid var(--accent-primary);
      padding: 8px 14px;
      margin: 10px 0;
      background: rgba(99, 102, 241, 0.08);
      border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
      color: var(--text-secondary);
      font-style: italic;
    }

    .table-responsive {
      width: 100%;
      overflow-x: auto;
      margin: 12px 0;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border);
    }

    .md-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.88rem;
      text-align: left;
    }

    .md-table th, .md-table td {
      padding: 10px 14px;
      border-bottom: 1px solid var(--border);
    }

    .md-table tr:last-child td { border-bottom: none; }
    .md-table tr:first-child {
      background: rgba(99, 102, 241, 0.12);
      font-weight: 600;
    }
    .md-table tr:nth-child(even) {
      background: rgba(255, 255, 255, 0.02);
    }

    /* Tool Trace Accordion */
    .trace-wrapper {
      margin-top: 14px;
      border-radius: var(--radius-md);
      border: 1px solid var(--border);
      background: var(--trace-bg);
      overflow: hidden;
      font-size: 0.85rem;
    }

    .trace-summary {
      padding: 10px 14px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: space-between;
      user-select: none;
      background: rgba(255, 255, 255, 0.02);
      transition: var(--transition);
      font-weight: 600;
      color: var(--text-secondary);
      list-style: none;
    }
    .trace-summary::-webkit-details-marker { display: none; }
    .trace-summary:hover {
      background: rgba(99, 102, 241, 0.1);
      color: var(--text-primary);
    }

    .trace-title {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .trace-chevron {
      transition: transform 0.2s ease;
    }
    details[open] .trace-chevron {
      transform: rotate(180deg);
    }

    .trace-content {
      padding: 14px;
      border-top: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .trace-round {
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      overflow: hidden;
      background: rgba(0, 0, 0, 0.2);
    }

    .trace-round-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 6px 12px;
      background: rgba(255, 255, 255, 0.03);
      border-bottom: 1px solid var(--border);
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--text-secondary);
    }

    .tool-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 2px 8px;
      border-radius: 4px;
      font-family: var(--font-mono);
      font-size: 0.75rem;
      font-weight: 600;
    }
    .tool-badge.kb { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .tool-badge.service { background: rgba(6, 182, 212, 0.15); color: #22d3ee; border: 1px solid rgba(6, 182, 212, 0.3); }
    .tool-badge.device { background: rgba(99, 102, 241, 0.15); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.3); }
    .tool-badge.user_info { background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }
    .tool-badge.ticket { background: rgba(244, 63, 94, 0.15); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.3); }
    .tool-badge.clarify { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .tool-badge.default { background: rgba(148, 163, 184, 0.15); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.3); }

    .json-code {
      font-family: var(--font-mono);
      font-size: 0.78rem;
      padding: 10px 12px;
      overflow-x: auto;
      white-space: pre-wrap;
      color: #94a3b8;
      max-height: 280px;
      overflow-y: auto;
    }

    /* Collapsible Metadata (intent, action, evidence_ids) */
    .metadata-wrapper {
      margin-top: 10px;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border);
      background: rgba(0, 0, 0, 0.14);
      overflow: hidden;
      font-size: 0.76rem;
    }

    .metadata-summary {
      padding: 6px 12px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: space-between;
      user-select: none;
      color: var(--text-muted);
      font-weight: 500;
      transition: var(--transition);
      list-style: none;
    }
    .metadata-summary::-webkit-details-marker { display: none; }
    .metadata-summary:hover {
      color: var(--text-secondary);
      background: rgba(255, 255, 255, 0.03);
    }

    .meta-title {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .meta-preview {
      font-family: var(--font-mono);
      font-size: 0.7rem;
      background: rgba(99, 102, 241, 0.12);
      color: #a5b4fc;
      padding: 1px 6px;
      border-radius: 4px;
    }

    .metadata-content {
      padding: 8px 12px;
      border-top: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      gap: 5px;
      font-family: var(--font-mono);
      font-size: 0.74rem;
      background: rgba(0, 0, 0, 0.2);
    }

    .meta-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .meta-label {
      color: var(--text-muted);
      min-width: 86px;
    }
    .meta-val {
      color: #38bdf8;
    }

    /* Typing Loader */
    .typing-indicator {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 14px 18px;
      background: var(--agent-msg-bg);
      border: 1px solid var(--agent-msg-border);
      border-radius: var(--radius-lg);
      border-bottom-left-radius: 4px;
      max-width: 340px;
      animation: fadeIn 0.3s ease;
    }

    .dots-wave {
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .dot-wave {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--accent-primary);
      animation: wave 1.3s infinite ease-in-out;
    }
    .dot-wave:nth-child(2) { animation-delay: 0.2s; }
    .dot-wave:nth-child(3) { animation-delay: 0.4s; }

    @keyframes wave {
      0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
      30% { transform: translateY(-6px); opacity: 1; }
    }

    .typing-text {
      font-size: 0.82rem;
      color: var(--text-secondary);
      font-weight: 500;
    }

    /* Floating Input Bar */
    .input-dock {
      position: sticky;
      bottom: 16px;
      z-index: 40;
      margin-top: auto;
      padding-top: 10px;
    }

    .input-card {
      background: var(--input-bg);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 10px 14px;
      box-shadow: var(--card-shadow), 0 20px 40px rgba(0, 0, 0, 0.25);
      transition: var(--transition);
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .input-card:focus-within {
      border-color: var(--accent-primary);
      box-shadow: var(--card-shadow), var(--accent-glow);
    }

    .input-row {
      display: flex;
      align-items: flex-end;
      gap: 10px;
    }

    textarea#message {
      flex: 1;
      background: transparent;
      border: none;
      outline: none;
      color: var(--text-primary);
      font-family: var(--font-main);
      font-size: 0.95rem;
      line-height: 1.5;
      resize: none;
      min-height: 48px;
      max-height: 180px;
      padding: 8px 4px;
      box-sizing: border-box;
    }
    textarea#message::placeholder {
      color: var(--text-muted);
    }

    .send-btn {
      width: 44px;
      height: 44px;
      border-radius: var(--radius-md);
      background: var(--accent-gradient);
      border: none;
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: var(--transition);
      box-shadow: var(--accent-glow);
      flex-shrink: 0;
      outline: none;
    }
    .send-btn:hover:not(:disabled) {
      transform: scale(1.05);
      filter: brightness(1.1);
    }
    .send-btn:active:not(:disabled) {
      transform: scale(0.96);
    }
    .send-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      filter: grayscale(0.5);
    }

    .input-hints {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.72rem;
      color: var(--text-muted);
      padding: 0 4px;
    }
    .shortcut-hint {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .kbd {
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 1px 5px;
      font-family: var(--font-mono);
      font-size: 0.68rem;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @media (max-width: 640px) {
      .header-meta { display: none; }
      .message-bubble { max-width: 90%; }
      .quick-chips-grid { grid-template-columns: 1fr; }
      .empty-hero h2 { font-size: 1.45rem; }
    }
  </style>
</head>
<body>
  <div class="app-container">
    <header>
      <div class="brand">
        <div class="brand-logo">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"></path>
          </svg>
        </div>
        <div class="brand-text">
          <h1>Northstar IT Helpdesk</h1>
          <div class="brand-status">
            <span class="status-dot"></span>
            <span>Hệ thống trực tuyến</span>
          </div>
        </div>
      </div>

      <div class="header-meta" id="headerMeta">
        <span class="badge version" id="metaVersion">v3_bonus</span>
        <span class="badge" id="metaProvider">openai</span>
        <span class="badge" id="metaModel">gpt-4.1-mini</span>
      </div>

      <div class="header-actions">
        <button type="button" class="icon-btn" id="clearBtn" title="Xóa lịch sử chat và làm mới">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
        <button type="button" class="icon-btn" id="themeBtn" title="Chuyển chế độ Sáng / Tối">
          <svg id="themeIcon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="5"></circle>
            <line x1="12" y1="1" x2="12" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="23"></line>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
            <line x1="1" y1="12" x2="3" y2="12"></line>
            <line x1="21" y1="12" x2="23" y2="12"></line>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
          </svg>
        </button>
      </div>
    </header>

    <main id="chat">
      <div class="empty-hero" id="emptyHero">
        <div class="hero-badge">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
          Trợ lý IT Thế hệ mới
        </div>
        <h2>Xin chào! Bạn cần hỗ trợ gì hôm nay?</h2>
        <p>Hệ thống tự động tra cứu sự cố hạ tầng, kiểm tra dịch vụ mạng, chẩn đoán thiết bị và giải đáp chính sách IT nội bộ.</p>

        <div class="quick-chips-grid">
          <div class="quick-chip" data-prompt="Kiểm tra trạng thái dịch vụ VPN production">
            <div class="chip-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>
            </div>
            <div class="chip-content">
              <strong>Kiểm tra dịch vụ VPN</strong>
              <span>Trạng thái môi trường production</span>
            </div>
          </div>

          <div class="quick-chip" data-prompt="Tra cứu trạng thái ticket LAB-1001">
            <div class="chip-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>
            </div>
            <div class="chip-content">
              <strong>Tra cứu Ticket LAB-1001</strong>
              <span>Kiểm tra tiến độ xử lý sự cố</span>
            </div>
          </div>

          <div class="quick-chip" data-prompt="Chẩn đoán kiểm tra thiết bị AST-9021">
            <div class="chip-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
            </div>
            <div class="chip-content">
              <strong>Chẩn đoán thiết bị AST-9021</strong>
              <span>Kiểm tra phần cứng, mạng và bảo mật</span>
            </div>
          </div>

          <div class="quick-chip" data-prompt="Tra cứu thông tin nhân viên EMP-1024">
            <div class="chip-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
            </div>
            <div class="chip-content">
              <strong>Hồ sơ nhân viên EMP-1024</strong>
              <span>Xem tài khoản và thiết bị được cấp</span>
            </div>
          </div>
        </div>
      </div>
    </main>

    <div class="input-dock">
      <form id="form" class="input-card">
        <div class="input-row">
          <textarea id="message" rows="1" required placeholder="Nhập câu hỏi hoặc yêu cầu hỗ trợ IT... (ví dụ: Kiểm tra VPN production)"></textarea>
          <button type="submit" class="send-btn" id="submitBtn" title="Gửi tin nhắn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </div>
        <div class="input-hints">
          <div class="shortcut-hint">
            <span class="kbd">↵ Enter</span> để gửi • <span class="kbd">Shift + ↵</span> xuống dòng
          </div>
          <div id="charCount">Northstar IT Assistant</div>
        </div>
      </form>
    </div>
  </div>

<script>
const chat = document.querySelector('#chat');
const form = document.querySelector('#form');
const input = document.querySelector('#message');
const submitBtn = document.querySelector('#submitBtn');
const emptyHero = document.querySelector('#emptyHero');
const clearBtn = document.querySelector('#clearBtn');
const themeBtn = document.querySelector('#themeBtn');
const history = [];
let sessionId = crypto.randomUUID();

// Theme management
function initTheme() {
  const saved = localStorage.getItem('northstar_theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  updateThemeIcon(saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('northstar_theme', next);
  updateThemeIcon(next);
}

function updateThemeIcon(theme) {
  const icon = document.querySelector('#themeIcon');
  if (theme === 'dark') {
    icon.innerHTML = `<circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>`;
  } else {
    icon.innerHTML = `<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>`;
  }
}

themeBtn.addEventListener('click', toggleTheme);
initTheme();

// Auto-expand textarea
input.addEventListener('input', () => {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 180) + 'px';
});

// Keyboard submission
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    submitMessage();
  }
});

// Quick prompt click handler
document.addEventListener('click', (e) => {
  const chip = e.target.closest('.quick-chip');
  if (chip) {
    const prompt = chip.getAttribute('data-prompt');
    if (prompt) {
      submitMessage(prompt);
    }
  }
});

// Clear conversation
clearBtn.addEventListener('click', () => {
  if (history.length === 0) return;
  if (confirm('Bạn có chắc muốn xóa lịch sử đoạn chat này và bắt đầu phiên mới?')) {
    history.length = 0;
    sessionId = crypto.randomUUID();
    chat.innerHTML = '';
    chat.appendChild(emptyHero);
    input.value = '';
    input.style.height = 'auto';
    input.focus();
  }
});

// Escape HTML utility
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Markdown parser
function renderMarkdown(text) {
  if (!text) return '(không có text)';
  let src = escapeHtml(text);

  // Extract code blocks
  const codeBlocks = [];
  src = src.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    const idx = codeBlocks.length;
    codeBlocks.push({ lang: lang || 'code', code: code.trim() });
    return `<!--CODEBLOCK_${idx}-->`;
  });

  // Inline code: `code`
  src = src.replace(/`([^`\n]+)`/g, '<code class="inline-code">$1</code>');

  // Headings
  src = src.replace(/^### (.*$)/gim, '<h4 class="md-h3">$1</h4>');
  src = src.replace(/^## (.*$)/gim, '<h3 class="md-h2">$1</h3>');
  src = src.replace(/^# (.*$)/gim, '<h2 class="md-h1">$1</h2>');

  // Bold & Italic
  src = src.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  src = src.replace(/\*(.*?)\*/g, '<em>$1</em>');

  // Blockquotes
  src = src.replace(/^>\s?(.*$)/gim, '<blockquote class="md-quote">$1</blockquote>');

  // Process tables and lines
  const lines = src.split('\n');
  const processed = [];
  let inTable = false;
  let tableHtml = '';
  let inUl = false;
  let inOl = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      if (inUl) { processed.push('</ul>'); inUl = false; }
      if (inOl) { processed.push('</ol>'); inOl = false; }
      if (!inTable) {
        inTable = true;
        tableHtml = '<div class="table-responsive"><table class="md-table"><tbody>';
      }
      if (/^\|[-:|\s]+\|$/.test(trimmed)) {
        continue;
      }
      const cells = trimmed.slice(1, -1).split('|').map(c => c.trim());
      tableHtml += '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>';
      continue;
    } else if (inTable) {
      tableHtml += '</tbody></table></div>';
      processed.push(tableHtml);
      inTable = false;
      tableHtml = '';
    }

    const ulMatch = line.match(/^[\s]*[-*]\s+(.*)$/);
    const olMatch = line.match(/^[\s]*\d+\.\s+(.*)$/);

    if (ulMatch) {
      if (!inUl) {
        if (inOl) { processed.push('</ol>'); inOl = false; }
        processed.push('<ul class="md-ul">');
        inUl = true;
      }
      processed.push(`<li>${ulMatch[1]}</li>`);
    } else if (olMatch) {
      if (!inOl) {
        if (inUl) { processed.push('</ul>'); inUl = false; }
        processed.push('<ol class="md-ol">');
        inOl = true;
      }
      processed.push(`<li>${olMatch[1]}</li>`);
    } else {
      if (inUl) { processed.push('</ul>'); inUl = false; }
      if (inOl) { processed.push('</ol>'); inOl = false; }

      if (trimmed.length > 0 && !trimmed.startsWith('<') && !trimmed.endsWith('>')) {
        processed.push(`<p class="md-p">${line}</p>`);
      } else {
        processed.push(line);
      }
    }
  }

  if (inTable) {
    tableHtml += '</tbody></table></div>';
    processed.push(tableHtml);
  }
  if (inUl) processed.push('</ul>');
  if (inOl) processed.push('</ol>');

  let finalHtml = processed.join('\n');

  // Restore code blocks
  finalHtml = finalHtml.replace(/<!--CODEBLOCK_(\d+)-->/g, (m, idx) => {
    const block = codeBlocks[Number(idx)];
    return `<div class="code-block-wrapper">
      <div class="code-header">
        <span class="code-lang">${block.lang}</span>
        <button type="button" class="copy-code-btn" onclick="copySnippet(this)">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          Sao chép
        </button>
      </div>
      <pre class="code-block"><code>${block.code}</code></pre>
    </div>`;
  });

  return finalHtml;
}

window.copySnippet = function(btn) {
  const code = btn.closest('.code-block-wrapper').querySelector('code').textContent;
  navigator.clipboard.writeText(code).then(() => {
    const originalText = btn.innerHTML;
    btn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg> Đã chép!`;
    setTimeout(() => { btn.innerHTML = originalText; }, 1800);
  });
};

window.copyMessageText = function(btn) {
  const bubble = btn.closest('.message-bubble');
  const text = bubble.querySelector('.md-content').innerText;
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.innerHTML;
    btn.innerHTML = `✓ Đã sao chép`;
    setTimeout(() => { btn.innerHTML = orig; }, 1800);
  });
};

function getToolBadgeClass(name) {
  if (!name) return 'default';
  if (name.includes('kb')) return 'kb';
  if (name.includes('service')) return 'service';
  if (name.includes('device')) return 'device';
  if (name.includes('user')) return 'user_info';
  if (name.includes('ticket')) return 'ticket';
  if (name.includes('clarify')) return 'clarify';
  return 'default';
}

function renderToolTrace(rounds) {
  if (!rounds || !Array.isArray(rounds) || rounds.length === 0) return '';
  
  let totalCalls = 0;
  const toolNames = new Set();

  rounds.forEach(r => {
    if (r.tool_calls) {
      totalCalls += r.tool_calls.length;
      r.tool_calls.forEach(c => toolNames.add(c.name));
    }
  });

  if (totalCalls === 0) return '';

  const badgesHtml = Array.from(toolNames).map(name => 
    `<span class="tool-badge ${getToolBadgeClass(name)}">${escapeHtml(name)}</span>`
  ).join(' ');

  let roundsHtml = '';
  rounds.forEach(r => {
    if ((r.tool_calls && r.tool_calls.length > 0) || (r.tool_results && r.tool_results.length > 0)) {
      roundsHtml += `<div class="trace-round">
        <div class="trace-round-header">
          <span>Vòng thực thi #${r.round}</span>
          <span>${(r.tool_calls || []).length} tool call(s)</span>
        </div>
        <div class="json-code">${escapeHtml(JSON.stringify({ tool_calls: r.tool_calls, tool_results: r.tool_results }, null, 2))}</div>
      </div>`;
    }
  });

  return `
    <details class="trace-wrapper">
      <summary class="trace-summary">
        <div class="trace-title">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
          <span>Thực thi công cụ (${totalCalls})</span>
          ${badgesHtml}
        </div>
        <div class="trace-chevron">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
        </div>
      </summary>
      <div class="trace-content">
        ${roundsHtml}
      </div>
    </details>
  `;
}

function getTimeString() {
  const now = new Date();
  return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function block(css, title, body, trace = null, metadata = null) {
  if (emptyHero && emptyHero.parentElement) {
    emptyHero.remove();
  }

  const row = document.createElement('div');
  row.className = `message-row ${css}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  if (css === 'user') {
    avatar.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>`;
  } else if (css === 'agent') {
    avatar.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>`;
  } else {
    avatar.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
  }

  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';

  const header = document.createElement('div');
  header.className = 'msg-header';
  header.innerHTML = `
    <span>${escapeHtml(title)} • ${getTimeString()}</span>
    <div class="msg-actions">
      ${css === 'agent' ? `<button type="button" class="copy-btn" onclick="copyMessageText(this)" title="Sao chép câu trả lời">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
        Sao chép
      </button>` : ''}
    </div>
  `;

  const content = document.createElement('div');
  content.className = 'md-content';
  content.innerHTML = renderMarkdown(body);

  bubble.appendChild(header);
  bubble.appendChild(content);

  // Collapsible metadata: intent, action, evidence_ids (hidden by default)
  if (metadata && (metadata.intent || metadata.action || (metadata.evidence_ids && metadata.evidence_ids.length > 0))) {
    const metaWrap = document.createElement('details');
    metaWrap.className = 'metadata-wrapper';
    
    let previewTag = metadata.intent ? metadata.intent : 'metadata';
    metaWrap.innerHTML = `
      <summary class="metadata-summary">
        <div class="meta-title">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
          <span>Thông tin phân loại</span>
          <span class="meta-preview">${escapeHtml(previewTag)}</span>
        </div>
        <div class="trace-chevron">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
        </div>
      </summary>
      <div class="metadata-content">
        ${metadata.intent ? `<div class="meta-row"><span class="meta-label">intent:</span><span class="meta-val">${escapeHtml(metadata.intent)}</span></div>` : ''}
        ${metadata.action ? `<div class="meta-row"><span class="meta-label">action:</span><span class="meta-val">${escapeHtml(metadata.action)}</span></div>` : ''}
        ${metadata.evidence_ids && metadata.evidence_ids.length ? `<div class="meta-row"><span class="meta-label">evidence_ids:</span><span>${escapeHtml(JSON.stringify(metadata.evidence_ids))}</span></div>` : ''}
      </div>
    `;
    bubble.appendChild(metaWrap);
  }

  if (trace) {
    const traceHtml = renderToolTrace(trace);
    if (traceHtml) {
      const traceContainer = document.createElement('div');
      traceContainer.innerHTML = traceHtml;
      bubble.appendChild(traceContainer.firstElementChild);
    }
  }

  row.appendChild(avatar);
  row.appendChild(bubble);
  chat.appendChild(row);

  window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
}

function extractAssistantReply(rawText) {
  if (!rawText || typeof rawText !== 'string') {
    return { displayText: rawText || '', metadata: null };
  }

  let text = rawText.trim();

  // Strip markdown code fences if wrapped in ```json ... ```
  if (text.startsWith('```')) {
    const match = text.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i);
    if (match) {
      text = match[1].trim();
    }
  }

  // Try parsing JSON directly
  try {
    const parsed = JSON.parse(text);
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      if (parsed.reply !== undefined || parsed.intent !== undefined || parsed.action !== undefined || parsed.evidence_ids !== undefined) {
        const metadata = {
          intent: parsed.intent,
          action: parsed.action,
          evidence_ids: parsed.evidence_ids
        };
        const displayText = parsed.reply !== undefined ? String(parsed.reply) : '(không có nội dung phản hồi)';
        return { displayText, metadata };
      }
    }
  } catch (e) {
    // Check if JSON object substring with "reply" exists inside the text
    const jsonMatch = text.match(/\{[\s\S]*"reply"\s*:[\s\S]*\}/);
    if (jsonMatch) {
      try {
        const parsed = JSON.parse(jsonMatch[0]);
        if (parsed && typeof parsed === 'object' && parsed.reply !== undefined) {
          const metadata = {
            intent: parsed.intent,
            action: parsed.action,
            evidence_ids: parsed.evidence_ids
          };
          return { displayText: String(parsed.reply), metadata };
        }
      } catch (err) {}
    }
  }

  return { displayText: rawText, metadata: null };
}

let typingElement = null;
function showTypingIndicator() {
  if (typingElement) return;
  typingElement = document.createElement('div');
  typingElement.className = 'message-row agent';
  typingElement.innerHTML = `
    <div class="avatar">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
    </div>
    <div class="typing-indicator">
      <div class="dots-wave">
        <span class="dot-wave"></span>
        <span class="dot-wave"></span>
        <span class="dot-wave"></span>
      </div>
      <span class="typing-text">Northstar AI đang phân tích và gọi công cụ...</span>
    </div>
  `;
  chat.appendChild(typingElement);
  window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
}

function hideTypingIndicator() {
  if (typingElement) {
    typingElement.remove();
    typingElement = null;
  }
}

// Fetch server metadata
fetch('/api/meta')
  .then(r => r.json())
  .then(meta => {
    if (meta.artifact_version) document.querySelector('#metaVersion').textContent = meta.artifact_version;
    if (meta.provider) document.querySelector('#metaProvider').textContent = meta.provider;
    if (meta.model) document.querySelector('#metaModel').textContent = meta.model;
  })
  .catch(() => {});

// Central message submission handler
async function submitMessage(customText) {
  const message = (customText !== undefined ? customText : input.value).trim();
  if (!message) return;

  block('user', 'Bạn', message);
  input.value = '';
  input.style.height = 'auto';
  submitBtn.disabled = true;
  showTypingIndicator();

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message, history })
    });
    const data = await response.json();
    hideTypingIndicator();

    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    const { displayText, metadata } = extractAssistantReply(data.assistant_text);
    block('agent', 'Northstar Assistant', displayText, data.rounds, metadata);
    history.push({ role: 'user', content: message }, { role: 'assistant', content: data.assistant_text });
  } catch (error) {
    hideTypingIndicator();
    block('error', 'Lỗi hệ thống', String(error));
  } finally {
    submitBtn.disabled = false;
    input.focus();
  }
}

// Form submit event
form.addEventListener('submit', (e) => {
  e.preventDefault();
  submitMessage();
});
</script>
</body>
</html>"""


class HelpdeskWebApp:
    def __init__(self, *, provider_name: str, model: str, version: str) -> None:
        self.provider_name = provider_name
        self.model = model
        self.provider = make_provider(provider_name)
        self.system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
        self.tools_path = ARTIFACTS_DIR / "tools.yaml"
        self.system_prompt = self.system_prompt_path.read_text(encoding="utf-8")
        self.tools = to_openai_tools(load_tool_declarations(self.tools_path))
        self.artifact = build_artifact_version(version, self.system_prompt_path, self.tools_path)

    def meta(self) -> dict[str, Any]:
        return {
            **artifact_version_dict(self.artifact),
            "provider": self.provider_name,
            "model": self.model,
        }

    def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        message = payload.get("message")
        history = payload.get("history", [])
        if not isinstance(message, str) or not message.strip():
            raise ValueError("message must be a non-empty string")
        if not isinstance(history, list) or len(history) > 12:
            raise ValueError("history must contain at most 12 messages")

        safe_history: list[dict[str, str]] = []
        for item in history:
            if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
                raise ValueError("invalid history item")
            content = item.get("content")
            if not isinstance(content, str) or len(content) > 4000:
                raise ValueError("invalid history content")
            safe_history.append({"role": item["role"], "content": content})

        result = run_model_tool_loop(
            provider=self.provider,
            messages=[{"role": "system", "content": self.system_prompt}, *safe_history, {"role": "user", "content": message.strip()}],
            tools=self.tools,
            model=self.model,
            max_tool_rounds=4,
        )
        self.save_transcript(payload.get("session_id", "ui"), message.strip(), result)
        return {**self.meta(), **result}

    def save_transcript(self, session_id: Any, message: str, result: dict[str, Any]) -> None:
        transcript_id = "ui_" + safe_slug(str(session_id))[:80]
        path = TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json"
        if path.exists():
            transcript = json.loads(path.read_text(encoding="utf-8"))
        else:
            transcript = {"transcript_id": transcript_id, **self.meta(), "created_at": datetime.now().isoformat(timespec="seconds"), "turns": []}
        transcript["turns"].append({"user": message, **result})
        transcript["updated_at"] = datetime.now().isoformat(timespec="seconds")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @property
    def app(self) -> HelpdeskWebApp:
        return self.server.app  # type: ignore[attr-defined, no-any-return]

    def do_GET(self) -> None:
        if self.path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/meta":
            self.send_json(200, self.app.meta())
        else:
            self.send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self.send_json(404, {"error": "not_found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 100_000:
                raise ValueError("invalid request size")
            payload = json.loads(self.rfile.read(size))
            self.send_json(200, self.app.chat(payload))
        except Exception as exc:
            self.send_json(400, {"error": f"{type(exc).__name__}: {exc}"})


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal browser UI for the IT Helpdesk agent.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--provider", choices=["openai", "openrouter", "anthropic", "gemini"], default="openai")
    parser.add_argument("--model", default="gpt-4.1-mini-2025-04-14")
    parser.add_argument("--version", default="v3_bonus")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.app = HelpdeskWebApp(provider_name=args.provider, model=args.model, version=args.version)  # type: ignore[attr-defined]
    print(f"UI: http://{args.host}:{args.port} ({server.app.artifact.artifact_version})")  # type: ignore[attr-defined]
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
