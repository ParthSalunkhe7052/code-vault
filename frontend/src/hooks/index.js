/**
 * Custom Hooks Index
 *
 * Re-exports all custom hooks for convenient imports.
 *
 * Usage:
 *   import { useDebounce, useKeyboardShortcuts, useFormValidation } from '@/hooks';
 */

export { default as useDebounce } from './useDebounce';
export { useConfirmDialog, ConfirmDialogProvider } from './useConfirmDialog';
export {
  useKeyboardShortcuts,
  useKeyboardShortcut,
  commonShortcuts
} from './useKeyboardShortcuts';
export {
  useFormValidation,
  validators
} from './useFormValidation';
