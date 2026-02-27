/**
 * useKeyboardShortcuts Hook
 */

import { useEffect, useCallback, useRef } from 'react';

export interface ShortcutConfig {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  handler: (event: KeyboardEvent) => void;
  preventDefault?: boolean;
  enableInInputs?: boolean;
}

export interface ShortcutOptions {
  enabled?: boolean;
}

/**
 * Hook to register and manage keyboard shortcuts
 */
export function useKeyboardShortcuts(shortcuts: ShortcutConfig[], options: ShortcutOptions = {}) {
  const { enabled = true } = options;
  const shortcutsRef = useRef<ShortcutConfig[]>(shortcuts);

  // Keep shortcuts ref updated
  useEffect(() => {
    shortcutsRef.current = shortcuts;
  }, [shortcuts]);

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!enabled) return;

    // Check if user is typing in an input field
    const target = event.target as HTMLElement;
    const isInputField =
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.isContentEditable;

    for (const shortcut of shortcutsRef.current) {
      // Skip if in input field and not explicitly enabled
      if (isInputField && !shortcut.enableInInputs) {
        // Exception: always allow Escape to work
        if (shortcut.key !== 'Escape') {
          continue;
        }
      }

      // Check if the key matches
      const keyMatches =
        event.key.toLowerCase() === shortcut.key.toLowerCase() ||
        event.code.toLowerCase() === `key${shortcut.key.toLowerCase()}`;

      if (!keyMatches) continue;

      // Check modifier keys
      const ctrlMatch = shortcut.ctrl
        ? event.ctrlKey || event.metaKey // Support both Ctrl and Cmd
        : !event.ctrlKey && !event.metaKey;
      const shiftMatch = shortcut.shift
        ? event.shiftKey
        : !event.shiftKey;
      const altMatch = shortcut.alt
        ? event.altKey
        : !event.altKey;

      const modifiersMatch = ctrlMatch && shiftMatch && altMatch;

      if (keyMatches && modifiersMatch) {
        if (shortcut.preventDefault !== false) {
          event.preventDefault();
        }
        shortcut.handler(event);
        break; // Only trigger one shortcut per keypress
      }
    }
  }, [enabled]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown]);
}

/**
 * Hook for a single keyboard shortcut
 */
export function useKeyboardShortcut(
  key: string,
  handler: (event: KeyboardEvent) => void,
  options: Omit<ShortcutConfig, 'key' | 'handler'> & ShortcutOptions = {}
) {
  useKeyboardShortcuts([{ key, handler, ...options }], options);
}

/**
 * Common keyboard shortcuts for the application
 */
export const commonShortcuts = {
  goToSearch: { key: 'k', ctrl: true },
  goToDashboard: { key: 'd', ctrl: true, shift: true },
  goToProjects: { key: 'p', ctrl: true, shift: true },
  goToLicenses: { key: 'l', ctrl: true, shift: true },
  closeModal: { key: 'Escape' },
  submit: { key: 'Enter', ctrl: true },
  save: { key: 's', ctrl: true },
  refresh: { key: 'r', ctrl: true },
  newItem: { key: 'n', ctrl: true },
  focusSearch: { key: '/' },
};

export default useKeyboardShortcuts;
