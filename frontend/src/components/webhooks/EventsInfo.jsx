import React from 'react';

const EventsInfo = ({ availableEvents }) => {
    return (
        <div className="glass-card p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Available Events</h2>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {availableEvents.events.map(event => (
                    <div key={event} className="p-3 bg-slate-800/50 rounded-lg">
                        <div className="font-medium text-white text-sm">{event}</div>
                        <div className="text-slate-400 text-xs mt-1">
                            {availableEvents.descriptions[event]}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default EventsInfo;
