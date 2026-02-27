import React, { useState } from 'react';
import { Plus } from 'lucide-react';
import { 
    useWebhooks, 
    useWebhookEvents, 
    useCreateWebhook, 
    useUpdateWebhook, 
    useDeleteWebhook, 
    useTestWebhook
} from '../hooks/useWebhooks';
import { WebhookTable, WebhookFormModal, DeliveriesModal, EventsInfo } from '../components/webhooks';
import { useToast } from '../components/Toast';
import ConfirmDialog from '../components/ConfirmDialog';
import Spinner from '../components/Spinner';
import { Webhook, CreateWebhookRequest } from '../types/api';
import { webhooks as webhooksApi } from '../services/api';

const Webhooks: React.FC = () => {
    const toast = useToast();
    
    // Queries & Mutations
    const { data: webhookList = [], isLoading: loading } = useWebhooks();
    const { data: availableEvents = { events: [], descriptions: {} } } = useWebhookEvents();
    const createMutation = useCreateWebhook();
    const updateMutation = useUpdateWebhook();
    const deleteMutation = useDeleteWebhook();
    const testMutation = useTestWebhook();

    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showEditModal, setShowEditModal] = useState(false);
    const [showDeliveriesModal, setShowDeliveriesModal] = useState(false);
    const [selectedWebhook, setSelectedWebhook] = useState<Webhook | null>(null);
    const [deliveries, setDeliveries] = useState<any[]>([]);
    const [confirmDialog, setConfirmDialog] = useState<{
        isOpen: boolean;
        onConfirm: () => void;
    }>({
        isOpen: false,
        onConfirm: () => { }
    });
    const [formData, setFormData] = useState<CreateWebhookRequest>({
        name: '',
        url: '',
        secret: '',
        events: []
    });

    const handleCreate = async () => {
        if (!formData.name.trim()) {
            toast.warning('Please enter a webhook name.');
            return;
        }
        if (!formData.url.trim() || !formData.url.match(/^https?:\/\//)) {
            toast.warning('Please enter a valid URL starting with http:// or https://');
            return;
        }
        if (formData.events.length === 0) {
            toast.warning('Please select at least one event to subscribe to.');
            return;
        }
        try {
            await createMutation.mutateAsync(formData);
            setShowCreateModal(false);
            setFormData({ name: '', url: '', secret: '', events: [] });
            toast.success('Webhook created successfully');
        } catch (error: any) {
            console.error('Failed to create webhook:', error);
            toast.error(error.response?.data?.detail || 'Failed to create webhook. Please check your inputs.');
        }
    };

    const handleEdit = async () => {
        if (!selectedWebhook) return;
        try {
            await updateMutation.mutateAsync({ id: selectedWebhook.id, data: formData });
            setShowEditModal(false);
            setSelectedWebhook(null);
            toast.success('Webhook updated successfully');
        } catch (error: any) {
            console.error('Failed to update webhook:', error);
            toast.error(error.response?.data?.detail || 'Failed to update webhook');
        }
    };

    const handleDelete = (id: string) => {
        setConfirmDialog({
            isOpen: true,
            onConfirm: async () => {
                try {
                    await deleteMutation.mutateAsync(id);
                    toast.success('Webhook deleted successfully');
                } catch (error) {
                    console.error('Failed to delete webhook:', error);
                    toast.error('Failed to delete webhook');
                }
            }
        });
    };

    const handleTest = async (id: string) => {
        try {
            await testMutation.mutateAsync(id);
            toast.success('Test webhook sent! Check deliveries for the result.');
        } catch (error: any) {
            console.error('Failed to test webhook:', error);
            toast.error(error.response?.data?.detail || 'Failed to send test webhook. Make sure the webhook is active.');
        }
    };

    const handleToggleActive = async (webhook: Webhook) => {
        try {
            await updateMutation.mutateAsync({ id: webhook.id, data: { is_active: !webhook.is_active } });
            toast.success(webhook.is_active ? 'Webhook disabled' : 'Webhook enabled');
        } catch (error) {
            console.error('Failed to toggle webhook:', error);
            toast.error('Failed to update webhook status');
        }
    };

    const openEditModal = (webhook: Webhook) => {
        setSelectedWebhook(webhook);
        setFormData({
            name: webhook.name,
            url: webhook.url,
            secret: '',
            events: webhook.events
        });
        setShowEditModal(true);
    };

    const openDeliveriesModal = async (webhook: Webhook) => {
        setSelectedWebhook(webhook);
        try {
            const data = await webhooksApi.getDeliveries(webhook.id);
            setDeliveries(data);
            setShowDeliveriesModal(true);
        } catch (error) {
            console.error('Failed to load deliveries:', error);
        }
    };

    const openCreateModal = () => {
        setFormData({
            name: '',
            url: '',
            secret: '',
            events: ['license.validated', 'license.created', 'license.revoked'] as any[]
        });
        setShowCreateModal(true);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Spinner size="lg" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-white">Webhooks</h1>
                    <p className="text-slate-400 mt-1">Configure webhook notifications for license events</p>
                </div>
                <button
                    onClick={openCreateModal}
                    className="btn-primary flex items-center gap-2"
                >
                    <Plus size={16} />
                    Add Webhook
                </button>
            </div>

            {/* Webhook List */}
            <WebhookTable
                webhookList={webhookList}
                onTest={handleTest}
                onEdit={openEditModal}
                onViewDeliveries={openDeliveriesModal}
                onToggleActive={handleToggleActive}
                onDelete={handleDelete}
                onCreateClick={openCreateModal}
            />

            {/* Available Events Info */}
            <EventsInfo availableEvents={availableEvents} />

            {/* Create Modal */}
            <WebhookFormModal
                isOpen={showCreateModal}
                onClose={() => setShowCreateModal(false)}
                title="Create Webhook"
                formData={formData}
                setFormData={setFormData}
                availableEvents={availableEvents}
                onSubmit={handleCreate}
                submitLabel="Create Webhook"
            />

            {/* Edit Modal */}
            <WebhookFormModal
                isOpen={showEditModal}
                onClose={() => setShowEditModal(false)}
                title="Edit Webhook"
                formData={formData}
                setFormData={setFormData}
                availableEvents={availableEvents}
                onSubmit={handleEdit}
                submitLabel="Save Changes"
                isEdit={true}
            />

            {/* Deliveries Modal */}
            <DeliveriesModal
                isOpen={showDeliveriesModal}
                onClose={() => setShowDeliveriesModal(false)}
                webhookName={selectedWebhook?.name || ''}
                deliveries={deliveries}
            />

            {/* Confirm Dialog */}
            <ConfirmDialog
                isOpen={confirmDialog.isOpen}
                onClose={() => setConfirmDialog(prev => ({ ...prev, isOpen: false }))}
                onConfirm={confirmDialog.onConfirm}
                title="Delete Webhook"
                message="Are you sure you want to delete this webhook? This action cannot be undone."
                confirmText="Delete"
                confirmVariant="danger"
            />
        </div>
    );
};

export default Webhooks;
