import React from 'react';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon,
  action,
}) => {
  return (
    <div className="flex flex-col items-center justify-center text-center p-8 border border-dashed border-gray-800 rounded-xl bg-[#0b0f19]/30 min-h-[300px]">
      {icon ? (
        <div className="text-gray-600 mb-4 bg-gray-900/60 p-4 rounded-full border border-gray-800">
          {icon}
        </div>
      ) : (
        <div className="w-12 h-12 rounded-full bg-gray-900 border border-gray-800 mb-4 flex items-center justify-center text-gray-500">
          ?
        </div>
      )}
      <h3 className="text-base font-semibold text-gray-300 font-mono mb-1">{title}</h3>
      <p className="text-xs text-gray-500 max-w-sm mb-6 leading-relaxed">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
};
