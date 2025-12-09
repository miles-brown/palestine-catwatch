import React from 'react';

/**
 * Skeleton component for loading states.
 * Shows an animated placeholder while content is loading.
 */
export const Skeleton = ({ className = '', ...props }) => {
  return (
    <div
      className={`animate-pulse bg-gray-200 rounded ${className}`}
      {...props}
    />
  );
};

/**
 * Skeleton card for officer grid loading state
 */
export const OfficerCardSkeleton = () => {
  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden border-2 border-gray-100">
      {/* Image placeholder */}
      <div className="aspect-square bg-gray-200 animate-pulse" />

      {/* Content placeholder */}
      <div className="p-4 space-y-3">
        {/* Badge number */}
        <Skeleton className="h-4 w-24" />

        {/* Location */}
        <Skeleton className="h-3 w-32" />

        {/* Role badge */}
        <div className="flex items-center justify-between">
          <Skeleton className="h-6 w-16 rounded-full" />
          <Skeleton className="h-4 w-20" />
        </div>
      </div>
    </div>
  );
};

/**
 * Skeleton row for table loading state
 */
export const TableRowSkeleton = ({ columns = 4 }) => {
  return (
    <tr className="border-b border-gray-100">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="py-3 px-4">
          <Skeleton className="h-4 w-full max-w-[120px]" />
        </td>
      ))}
    </tr>
  );
};

/**
 * Skeleton for stat cards
 */
export const StatCardSkeleton = () => {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center gap-3 mb-2">
        <Skeleton className="h-6 w-6 rounded" />
        <Skeleton className="h-4 w-24" />
      </div>
      <Skeleton className="h-8 w-16 mb-1" />
      <Skeleton className="h-3 w-32" />
    </div>
  );
};

/**
 * Skeleton for report page header
 */
export const ReportHeaderSkeleton = () => {
  return (
    <div className="bg-slate-900 rounded-t-xl p-6">
      <div className="flex flex-col md:flex-row md:justify-between md:items-start gap-4">
        <div className="space-y-3">
          <Skeleton className="h-4 w-32 bg-slate-700" />
          <Skeleton className="h-8 w-48 bg-slate-700" />
          <Skeleton className="h-4 w-40 bg-slate-700" />
        </div>
        <div className="space-y-2 text-right">
          <Skeleton className="h-6 w-36 bg-slate-700 ml-auto" />
          <Skeleton className="h-4 w-28 bg-slate-700 ml-auto" />
        </div>
      </div>
    </div>
  );
};

/**
 * Skeleton for video player
 */
export const VideoPlayerSkeleton = () => {
  return (
    <div className="bg-black rounded-lg overflow-hidden">
      <div className="aspect-video bg-slate-800 animate-pulse flex items-center justify-center">
        <div className="w-16 h-16 rounded-full bg-slate-700" />
      </div>
      <div className="bg-slate-900 p-3 space-y-3">
        <Skeleton className="h-2 w-full bg-slate-700 rounded-full" />
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Skeleton className="h-8 w-8 rounded-full bg-slate-700" />
            <Skeleton className="h-8 w-8 rounded-full bg-slate-700" />
            <Skeleton className="h-8 w-8 rounded-full bg-slate-700" />
          </div>
          <Skeleton className="h-4 w-20 bg-slate-700" />
        </div>
      </div>
    </div>
  );
};

/**
 * Grid skeleton for officer cards
 */
export const OfficerGridSkeleton = ({ count = 8 }) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {Array.from({ length: count }).map((_, i) => (
        <OfficerCardSkeleton key={i} />
      ))}
    </div>
  );
};

export default Skeleton;
