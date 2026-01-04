import React, { useState, forwardRef } from 'react';
import { Calendar, Tag, X, Check } from 'lucide-react';
import Modal from '../Modal';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';

// Custom input component for DatePicker that matches our styling
const CustomDateInput = forwardRef(({ value, onClick, placeholder }, ref) => (
    <button
        type="button"
        className="input flex-1 w-auto text-left cursor-pointer"
        onClick={onClick}
        ref={ref}
    >
        {value || <span className="text-slate-500">{placeholder}</span>}
    </button>
));
CustomDateInput.displayName = 'CustomDateInput';

const CreateLicenseModal = ({
    isOpen,
    onClose,
    onSubmit,
    projects,
    newLicense,
    setNewLicense,
    featureInput,
    setFeatureInput,
    onAddFeature,
    onRemoveFeature
}) => {
    const [isCalendarOpen, setIsCalendarOpen] = useState(false);

    const handleCreate = async (e) => {
        e.preventDefault();
        await onSubmit(e);
    };

    // Update project_id when projects change
    React.useEffect(() => {
        if (projects.length > 0 && !newLicense.project_id) {
            setNewLicense(prev => ({ ...prev, project_id: projects[0].id }));
        }
    }, [projects]);

    // Parse the date string to Date object for DatePicker
    const selectedDate = newLicense.expires_at ? new Date(newLicense.expires_at) : null;

    const handleDateChange = (date) => {
        if (date) {
            // Format to datetime-local compatible string
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const hours = String(date.getHours()).padStart(2, '0');
            const minutes = String(date.getMinutes()).padStart(2, '0');
            setNewLicense({ ...newLicense, expires_at: `${year}-${month}-${day}T${hours}:${minutes}` });
        } else {
            setNewLicense({ ...newLicense, expires_at: '' });
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title="Issue New License"
        >
            <form onSubmit={handleCreate} className="flex flex-col gap-4">
                <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">
                        Project
                    </label>
                    <select
                        value={newLicense.project_id}
                        onChange={(e) => setNewLicense({ ...newLicense, project_id: e.target.value })}
                        className="input"
                        required
                    >
                        <option value="" disabled>Select a project</option>
                        {projects.map(p => (
                            <option key={p.id} value={p.id}>{p.name}</option>
                        ))}
                    </select>
                </div>
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-400 mb-2">
                            Client Name
                        </label>
                        <input
                            type="text"
                            value={newLicense.client_name}
                            onChange={(e) => setNewLicense({ ...newLicense, client_name: e.target.value })}
                            className="input"
                            placeholder="John Doe"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-400 mb-2">
                            Max Machines
                        </label>
                        <input
                            type="number"
                            min="1"
                            max="100"
                            value={newLicense.max_machines}
                            onChange={(e) => setNewLicense({ ...newLicense, max_machines: parseInt(e.target.value) })}
                            className="input"
                        />
                    </div>
                </div>
                <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">
                        Client Email
                    </label>
                    <input
                        type="email"
                        value={newLicense.client_email}
                        onChange={(e) => setNewLicense({ ...newLicense, client_email: e.target.value })}
                        className="input"
                        placeholder="john@example.com"
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">
                        Expiration Date <span className="text-slate-500">(Optional)</span>
                    </label>
                    <div className="flex items-center gap-3">
                        <Calendar size={20} className="text-slate-400" />
                        <DatePicker
                            selected={selectedDate}
                            onChange={handleDateChange}
                            showTimeSelect
                            timeFormat="HH:mm"
                            timeIntervals={15}
                            dateFormat="MMM d, yyyy h:mm aa"
                            minDate={new Date()}
                            placeholderText="Select expiration date..."
                            customInput={<CustomDateInput />}
                            open={isCalendarOpen}
                            onInputClick={() => setIsCalendarOpen(true)}
                            onClickOutside={() => setIsCalendarOpen(false)}
                            calendarClassName="cv-datepicker"
                            popperClassName="cv-datepicker-popper"
                            wrapperClassName="flex-1"
                        >
                            <div className="flex justify-between items-center p-2 border-t border-slate-700 bg-slate-800">
                                <button
                                    type="button"
                                    className="text-sm text-slate-400 hover:text-white px-3 py-1.5 rounded"
                                    onClick={() => {
                                        handleDateChange(null);
                                        setIsCalendarOpen(false);
                                    }}
                                >
                                    Clear
                                </button>
                                <button
                                    type="button"
                                    className="flex items-center gap-1.5 text-sm bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-1.5 rounded font-medium"
                                    onClick={() => setIsCalendarOpen(false)}
                                >
                                    <Check size={14} />
                                    Done
                                </button>
                            </div>
                        </DatePicker>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">Leave empty for a perpetual license</p>
                </div>

                {/* Features Input */}
                <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">
                        <div className="flex items-center gap-2">
                            <Tag size={14} />
                            Feature Flags
                        </div>
                    </label>
                    <div className="flex gap-2 mb-2">
                        <input
                            type="text"
                            value={featureInput}
                            onChange={(e) => setFeatureInput(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), onAddFeature())}
                            className="input flex-1"
                            placeholder="e.g., pro, enterprise, beta"
                        />
                        <button
                            type="button"
                            onClick={onAddFeature}
                            className="btn btn-secondary"
                        >
                            Add
                        </button>
                    </div>
                    {newLicense.features.length > 0 && (
                        <div className="flex flex-wrap gap-2 p-3 bg-slate-900/50 rounded-lg border border-white/10">
                            {newLicense.features.map((feature, i) => (
                                <span
                                    key={i}
                                    className="flex items-center gap-1 px-3 py-1 bg-indigo-500/20 text-indigo-300 rounded-full text-sm"
                                >
                                    {feature}
                                    <button
                                        type="button"
                                        onClick={() => onRemoveFeature(feature)}
                                        className="hover:text-white ml-1"
                                    >
                                        <X size={12} />
                                    </button>
                                </span>
                            ))}
                        </div>
                    )}
                    <p className="text-xs text-slate-500 mt-1">
                        Features are passed to your application during license validation
                    </p>
                </div>

                <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">
                        Notes
                    </label>
                    <textarea
                        value={newLicense.notes}
                        onChange={(e) => setNewLicense({ ...newLicense, notes: e.target.value })}
                        className="input min-h-[80px]"
                        placeholder="Internal notes..."
                    />
                </div>
                <div className="flex justify-end gap-3 mt-4">
                    <button
                        type="button"
                        onClick={onClose}
                        className="btn btn-secondary"
                    >
                        Cancel
                    </button>
                    <button type="submit" className="btn btn-primary">
                        Issue License
                    </button>
                </div>
            </form>
        </Modal>
    );
};

export default CreateLicenseModal;

