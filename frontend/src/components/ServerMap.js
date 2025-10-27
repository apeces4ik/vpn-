import React, { useState } from 'react';
import { MapPin, Globe } from 'lucide-react';
import './ServerMap.css';

const ServerMap = ({ locations, onLocationSelect }) => {
  const [selectedRegion, setSelectedRegion] = useState(null);

  // Group servers by region
  const regions = [
    { name: 'North America', count: locations.filter(l => l.includes('US') || l.includes('Canada')).length, position: { x: '20%', y: '35%' }, color: '#10b981' },
    { name: 'Europe', count: locations.filter(l => l.includes('UK') || l.includes('Germany') || l.includes('France') || l.includes('Netherlands')).length, position: { x: '50%', y: '30%' }, color: '#3b82f6' },
    { name: 'Asia', count: locations.filter(l => l.includes('Singapore') || l.includes('Japan') || l.includes('India')).length, position: { x: '75%', y: '40%' }, color: '#8b5cf6' },
    { name: 'South America', count: locations.filter(l => l.includes('Brazil') || l.includes('Argentina')).length, position: { x: '30%', y: '70%' }, color: '#f59e0b' },
    { name: 'Africa', count: locations.filter(l => l.includes('Africa')).length, position: { x: '52%', y: '65%' }, color: '#ef4444' },
    { name: 'Oceania', count: locations.filter(l => l.includes('Australia') || l.includes('New Zealand')).length, position: { x: '82%', y: '75%' }, color: '#06b6d4' }
  ];

  const handleRegionClick = (region) => {
    setSelectedRegion(selectedRegion?.name === region.name ? null : region);
    if (onLocationSelect) {
      onLocationSelect(region);
    }
  };

  return (
    <div className="server-map-container">
      <div className="map-header">
        <div className="map-title">
          <Globe size={24} />
          <h3>Global Server Network</h3>
        </div>
        <div className="map-stats">
          <span>{locations.length} locations worldwide</span>
        </div>
      </div>

      <div className="world-map">
        {/* Background grid */}
        <div className="map-grid"></div>
        
        {/* Animated globe lines */}
        <svg className="map-overlay" viewBox="0 0 800 400" preserveAspectRatio="none">
          <defs>
            <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" style={{ stopColor: '#10b981', stopOpacity: 0 }} />
              <stop offset="50%" style={{ stopColor: '#10b981', stopOpacity: 0.6 }} />
              <stop offset="100%" style={{ stopColor: '#10b981', stopOpacity: 0 }} />
            </linearGradient>
          </defs>
          
          {/* Horizontal lines */}
          {[100, 150, 200, 250, 300].map((y, i) => (
            <line
              key={`h-${i}`}
              x1="0"
              y1={y}
              x2="800"
              y2={y}
              stroke="url(#lineGradient)"
              strokeWidth="1"
              className="map-line"
              style={{ animationDelay: `${i * 0.2}s` }}
            />
          ))}
          
          {/* Vertical lines */}
          {[100, 200, 300, 400, 500, 600, 700].map((x, i) => (
            <line
              key={`v-${i}`}
              x1={x}
              y1="0"
              x2={x}
              y2="400"
              stroke="url(#lineGradient)"
              strokeWidth="1"
              className="map-line"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </svg>

        {/* Region markers */}
        {regions.map((region, index) => (
          <div
            key={region.name}
            className={`region-marker ${selectedRegion?.name === region.name ? 'selected' : ''}`}
            style={{
              left: region.position.x,
              top: region.position.y,
              '--marker-color': region.color,
              animationDelay: `${index * 0.1}s`
            }}
            onClick={() => handleRegionClick(region)}
          >
            <div className="marker-pulse"></div>
            <div className="marker-dot">
              <MapPin size={16} />
            </div>
            <div className="marker-label">
              <div className="marker-region">{region.name}</div>
              <div className="marker-count">{region.count} servers</div>
            </div>
          </div>
        ))}

        {/* Connection lines animation */}
        {selectedRegion && regions.map((region, index) => {
          if (region.name === selectedRegion.name) return null;
          return (
            <svg key={`line-${index}`} className="connection-line" style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
              <line
                x1={selectedRegion.position.x}
                y1={selectedRegion.position.y}
                x2={region.position.x}
                y2={region.position.y}
                stroke="rgba(16, 185, 129, 0.3)"
                strokeWidth="2"
                strokeDasharray="5,5"
                className="animated-line"
              />
            </svg>
          );
        })}
      </div>

      {/* Region details */}
      {selectedRegion && (
        <div className="region-details">
          <div className="region-details-header">
            <h4>{selectedRegion.name}</h4>
            <span className="region-server-count">{selectedRegion.count} Servers Available</span>
          </div>
          <div className="region-features">
            <div className="region-feature">
              <Zap size={16} />
              <span>10 Gbps Speed</span>
            </div>
            <div className="region-feature">
              <Shield size={16} />
              <span>Military-Grade Encryption</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ServerMap;
