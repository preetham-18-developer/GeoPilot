"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";

interface CommandItem {
  id: string;
  type: "section" | "project" | "question" | "keyword" | "competitor" | "action";
  label: string;
  description?: string;
  onSelect: () => void;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  items: CommandItem[];
}

const TYPE_LABELS: Record<CommandItem["type"], string> = {
  section: "Navigate",
  project: "Project",
  question: "Question",
  keyword: "Keyword",
  competitor: "Competitor",
  action: "Action",
};

export function CommandPalette({ isOpen, onClose, items }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [highlighted, setHighlighted] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const filtered = query.trim()
    ? items.filter(
        (item) =>
          item.label.toLowerCase().includes(query.toLowerCase()) ||
          item.description?.toLowerCase().includes(query.toLowerCase()) ||
          item.type.toLowerCase().includes(query.toLowerCase())
      )
    : items.slice(0, 8);

  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setHighlighted(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    setHighlighted(0);
  }, [query]);

  const handleSelect = useCallback(
    (item: CommandItem) => {
      item.onSelect();
      onClose();
    },
    [onClose]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setHighlighted((h) => Math.min(h + 1, filtered.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setHighlighted((h) => Math.max(h - 1, 0));
      } else if (e.key === "Enter" && filtered[highlighted]) {
        handleSelect(filtered[highlighted]);
      } else if (e.key === "Escape") {
        onClose();
      }
    },
    [filtered, highlighted, handleSelect, onClose]
  );

  // Global Ctrl+K / Cmd+K listener
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        if (!isOpen) return; // parent controls open
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className="command-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
    >
      <div
        className="command-palette animate-fade-in"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Search Input */}
        <div className="command-input-wrapper">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-dark)" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            ref={inputRef}
            className="command-input"
            placeholder="Search sections, projects, keywords..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
          <kbd>Esc</kbd>
        </div>

        {/* Results */}
        <div className="command-results" ref={listRef}>
          {filtered.length > 0 ? (
            filtered.map((item, i) => (
              <div
                key={item.id}
                className={`command-result-item ${i === highlighted ? "highlighted" : ""}`}
                onClick={() => handleSelect(item)}
                onMouseEnter={() => setHighlighted(i)}
                role="option"
                aria-selected={i === highlighted}
              >
                <span className="command-result-type">{TYPE_LABELS[item.type]}</span>
                <div className="flex-1 min-w-0">
                  <div style={{ color: "var(--text-main)", fontSize: "0.875rem" }}>{item.label}</div>
                  {item.description && (
                    <div style={{ color: "var(--text-dark)", fontSize: "0.75rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {item.description}
                    </div>
                  )}
                </div>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-dark)" strokeWidth="2">
                  <path d="m9 18 6-6-6-6" />
                </svg>
              </div>
            ))
          ) : (
            <div style={{ textAlign: "center", padding: "2rem", color: "var(--text-dark)", fontSize: "0.875rem" }}>
              No results for &ldquo;{query}&rdquo;
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="command-footer">
          <span><kbd>↑↓</kbd> navigate</span>
          <span><kbd>↵</kbd> select</span>
          <span><kbd>Esc</kbd> close</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Hook to manage command palette open state and Ctrl+K binding.
 */
export function useCommandPalette() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  return {
    isOpen,
    open: () => setIsOpen(true),
    close: () => setIsOpen(false),
  };
}
