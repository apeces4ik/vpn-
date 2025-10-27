import React from 'react';
import './LoadingSkeleton.css';

export const ServerCardSkeleton = () => (
  <div className="skeleton-card server-card-skeleton">
    <div className="skeleton-header">
      <div className="skeleton-avatar skeleton-shimmer"></div>
      <div className="skeleton-text-group">
        <div className="skeleton-text skeleton-shimmer" style={{ width: '120px', height: '18px' }}></div>
        <div className="skeleton-text skeleton-shimmer" style={{ width: '80px', height: '14px', marginTop: '8px' }}></div>
      </div>
    </div>
    <div className="skeleton-stats">
      <div className="skeleton-stat skeleton-shimmer"></div>
      <div className="skeleton-stat skeleton-shimmer"></div>
    </div>
    <div className="skeleton-actions">
      <div className="skeleton-button skeleton-shimmer"></div>
      <div className="skeleton-button skeleton-shimmer"></div>
    </div>
  </div>
);

export const InfoCardSkeleton = () => (
  <div className="skeleton-card info-card-skeleton">
    <div className="skeleton-text skeleton-shimmer" style={{ width: '150px', height: '20px', marginBottom: '20px' }}></div>
    <div className="skeleton-row skeleton-shimmer"></div>
    <div className="skeleton-row skeleton-shimmer"></div>
    <div className="skeleton-row skeleton-shimmer"></div>
  </div>
);

export const ConnectionStatusSkeleton = () => (
  <div className="skeleton-card connection-status-skeleton">
    <div className="skeleton-status-icon skeleton-shimmer"></div>
    <div className="skeleton-text-group">
      <div className="skeleton-text skeleton-shimmer" style={{ width: '140px', height: '24px' }}></div>
      <div className="skeleton-text skeleton-shimmer" style={{ width: '180px', height: '16px', marginTop: '12px' }}></div>
    </div>
    <div className="skeleton-button skeleton-shimmer" style={{ width: '150px', height: '48px' }}></div>
  </div>
);

export const DashboardSkeleton = () => (
  <div className="dashboard-skeleton">
    <ConnectionStatusSkeleton />
    
    <div className="skeleton-info-grid">
      <InfoCardSkeleton />
      <InfoCardSkeleton />
    </div>
    
    <div className="skeleton-section-header">
      <div className="skeleton-text skeleton-shimmer" style={{ width: '200px', height: '28px' }}></div>
      <div className="skeleton-text skeleton-shimmer" style={{ width: '120px', height: '20px' }}></div>
    </div>
    
    <div className="skeleton-servers-grid">
      <ServerCardSkeleton />
      <ServerCardSkeleton />
      <ServerCardSkeleton />
      <ServerCardSkeleton />
      <ServerCardSkeleton />
      <ServerCardSkeleton />
    </div>
  </div>
);
