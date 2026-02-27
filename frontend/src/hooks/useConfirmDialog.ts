import { useState, useCallback } from 'react';

interface ConfirmOptions {
    title: string;
    message: string;
    confirmText?: string;
    confirmVariant?: 'danger' | 'primary' | 'warning';
    onConfirm: () => void | Promise<void>;
}

interface DialogState extends ConfirmOptions {
    isOpen: boolean;
}

/**
 * Hook for managing confirm dialogs
 * Eliminates repeated confirm dialog state setup
 *
 * @example
 * const { dialogProps, confirm } = useConfirmDialog();
 *
 * const handleDelete = (id: string) => {
 *   confirm({
 *     title: 'Delete Item',
 *     message: 'Are you sure you want to delete this item?',
 *     confirmText: 'Delete',
 *     confirmVariant: 'danger',
 *     onConfirm: async () => {
 *       await api.delete(id);
 *       toast.success('Deleted!');
 *       refetch();
 *     }
 *   });
 * };
 *
 * // In JSX:
 * <ConfirmDialog {...dialogProps} />
 */
const useConfirmDialog = () => {
    const [dialog, setDialog] = useState<DialogState>({
        isOpen: false,
        title: '',
        message: '',
        confirmText: 'Confirm',
        confirmVariant: 'danger',
        onConfirm: () => {}
    });

    /**
     * Show the confirm dialog
     */
    const confirm = useCallback(({
        title,
        message,
        confirmText = 'Confirm',
        confirmVariant = 'danger',
        onConfirm
    }: ConfirmOptions) => {
        setDialog({
            isOpen: true,
            title,
            message,
            confirmText,
            confirmVariant,
            onConfirm
        });
    }, []);

    /**
     * Close the dialog
     */
    const close = useCallback(() => {
        setDialog(prev => ({ ...prev, isOpen: false }));
    }, []);

    /**
     * Handle confirm action
     */
    const handleConfirm = useCallback(async () => {
        try {
            await dialog.onConfirm();
        } finally {
            close();
        }
    }, [dialog, close]);

    return {
        /**
         * Props to spread on ConfirmDialog component
         */
        dialogProps: {
            isOpen: dialog.isOpen,
            onClose: close,
            onConfirm: handleConfirm,
            title: dialog.title,
            message: dialog.message,
            confirmText: dialog.confirmText,
            confirmVariant: dialog.confirmVariant
        },
        /**
         * Function to show the dialog
         */
        confirm,
        /**
         * Function to close the dialog
         */
        close
    };
};

export default useConfirmDialog;
