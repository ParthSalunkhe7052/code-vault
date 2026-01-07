/**
 * useKeyboardShortcuts Hook
 *
 * Provides global keyboard shortcut handling for the CodeVault application.
 * Supports both single keys and key combinations (e.g., Ctrl+K, Cmd+/).
 */

import { useEffect, useCallback, useRef } from 'react';

/**
 * @typedef {Object} ShortcutConfig
 * @property {string} key - The key to listen for (e.g., 'k', 'Escape', '/')
 * @property {boolean} [ctrl] - Require Ctrl/Cmd key
 * @property {boolean} [shift] - Require Shift key
 * @property {boolean} [alt] - Require Alt key
 * @property {function} handler - Callback function when shortcut is triggered
 * @property {boolean} [preventDefault] - Whether to prevent default browser behavior
 * @property {boolean} [enableInInputs] - Allow shortcut to work in input/textarea elements
 */

/**
 * Hook to register and manage keyboard shortcuts
 *
 * @param {ShortcutConfig[]} shortcuts - Array of shortcut configurations
 * @param {Object} options - Additional options
 * @param {boolean} [options.enabled=true] - Whether shortcuts are enabled
 */
export function useKeyboardShortcuts(shortcuts, options = {}) {
  const { enabled = true } = options;
  const shortcutsRef = useRef(shortcuts);

  // Keep shortcuts ref updated
  useEffect(() => {
    shortcutsRef.current = shortcuts;
  }, [shortcuts]);

  const handleKeyDown = useCallback((event) => {
    if (!enabled) return;

    // Check if user is typing in an input field
    const target = event.target;
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

      // ctrlMatch/shiftMatch/altMatch already handle the case where modifier is not required
      // They check: shortcut.ctrl ? event.ctrlKey : !event.ctrlKey
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
 *
 * @param {string} key - The key to listen for
 * @param {function} handler - Callback when shortcut is triggered
 * @param {Object} options - Shortcut options
 */
export function useKeyboardShortcut(key, handler, options = {}) {
  useKeyboardShortcuts([{ key, handler, ...options }], options);
}

/**
 * Common keyboard shortcuts for the application
 * These can be used with the useKeyboardShortcuts hook
 */
export const commonShortcuts = {
  // Navigation
  goToSearch: { key: 'k', ctrl: true },
  goToDashboard: { key: 'd', ctrl: true, shift: true },
  goToProjects: { key: 'p', ctrl: true, shift: true },
  goToLicenses: { key: 'l', ctrl: true, shift: true },

  // Actions
  closeModal: { key: 'Escape' },
  submit: { key: 'Enter', ctrl: true },
  save: { key: 's', ctrl: true },
  refresh: { key: 'r', ctrl: true },
  newItem: { key: 'n', ctrl: true },

  // Focus
  focusSearch: { key: '/' },
};

export default useKeyboardShortcuts;
