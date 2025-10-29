import React, { useState, useEffect } from 'react';
import './WhiteLabelConfig.css';

const WhiteLabelConfig = () => {
  const [loading, setLoading] = useState(false);
  const [organization, setOrganization] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    logo_url: '',
    primary_color: '#667eea',
    secondary_color: '#764ba2',
    custom_domain: ''
  });
  const [message, setMessage] = useState({ type: '', text: '' });

  // Get organization ID from localStorage or props
  const organizationId = localStorage.getItem('organization_id') || 'demo-org-id';

  useEffect(() => {
    loadOrganization();
  }, []);

  const loadOrganization = async () => {
    try {
      setLoading(true);
      const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
      const response = await fetch(`${backendUrl}/api/organizations/${organizationId}`);
      
      if (response.ok) {
        const data = await response.json();
        setOrganization(data);
        
        // Pre-fill form with existing data
        if (data.branding) {
          setFormData({
            name: data.name || '',
            logo_url: data.branding.logo_url || '',
            primary_color: data.branding.primary_color || '#667eea',
            secondary_color: data.branding.secondary_color || '#764ba2',
            custom_domain: data.branding.custom_domain || ''
          });
        } else {
          setFormData(prev => ({ ...prev, name: data.name || '' }));
        }
      }
    } catch (error) {
      console.error('Error loading organization:', error);
      setMessage({ type: 'error', text: 'Failed to load organization settings' });
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ type: '', text: '' });

    try {
      const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
      const response = await fetch(`${backendUrl}/api/organizations/${organizationId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: formData.name,
          branding: {
            logo_url: formData.logo_url,
            primary_color: formData.primary_color,
            secondary_color: formData.secondary_color,
            custom_domain: formData.custom_domain
          }
        })
      });

      if (response.ok) {
        setMessage({ type: 'success', text: 'White-label settings saved successfully!' });
        loadOrganization(); // Reload to show updated data
      } else {
        const error = await response.json();
        setMessage({ type: 'error', text: error.detail || 'Failed to save settings' });
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      setMessage({ type: 'error', text: 'Failed to save white-label settings' });
    } finally {
      setLoading(false);
    }
  };

  const applyPreview = () => {
    // Apply colors to preview
    document.documentElement.style.setProperty('--preview-primary', formData.primary_color);
    document.documentElement.style.setProperty('--preview-secondary', formData.secondary_color);
  };

  return (
    <div className="whitelabel-config-container">
      <div className="whitelabel-header">
        <h1>🎨 White-Label Branding</h1>
        <p>Customize the appearance of your VPN service for your organization</p>
      </div>

      {message.text && (
        <div className={`message ${message.type}`}>
          {message.text}
        </div>
      )}

      <div className="whitelabel-content">
        <div className="config-section">
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="name">
                <span className="label-icon">🏢</span>
                Organization Name
              </label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="Your Company Name"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="logo_url">
                <span className="label-icon">🖼️</span>
                Logo URL
              </label>
              <input
                type="url"
                id="logo_url"
                name="logo_url"
                value={formData.logo_url}
                onChange={handleChange}
                placeholder="https://example.com/logo.png"
              />
              <small>Enter a publicly accessible URL for your logo</small>
            </div>

            <div className="color-group">
              <div className="form-group">
                <label htmlFor="primary_color">
                  <span className="label-icon">🎨</span>
                  Primary Color
                </label>
                <div className="color-input-group">
                  <input
                    type="color"
                    id="primary_color"
                    name="primary_color"
                    value={formData.primary_color}
                    onChange={handleChange}
                  />
                  <input
                    type="text"
                    value={formData.primary_color}
                    onChange={(e) => setFormData({ ...formData, primary_color: e.target.value })}
                    className="color-text"
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="secondary_color">
                  <span className="label-icon">🎨</span>
                  Secondary Color
                </label>
                <div className="color-input-group">
                  <input
                    type="color"
                    id="secondary_color"
                    name="secondary_color"
                    value={formData.secondary_color}
                    onChange={handleChange}
                  />
                  <input
                    type="text"
                    value={formData.secondary_color}
                    onChange={(e) => setFormData({ ...formData, secondary_color: e.target.value })}
                    className="color-text"
                  />
                </div>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="custom_domain">
                <span className="label-icon">🌐</span>
                Custom Domain (Optional)
              </label>
              <input
                type="text"
                id="custom_domain"
                name="custom_domain"
                value={formData.custom_domain}
                onChange={handleChange}
                placeholder="vpn.yourcompany.com"
              />
              <small>Configure DNS to point to our servers</small>
            </div>

            <div className="button-group">
              <button
                type="button"
                onClick={applyPreview}
                className="preview-button"
                disabled={loading}
              >
                👁️ Preview Changes
              </button>
              <button
                type="submit"
                className="save-button"
                disabled={loading}
              >
                {loading ? '💾 Saving...' : '💾 Save Settings'}
              </button>
            </div>
          </form>
        </div>

        <div className="preview-section">
          <h3>Preview</h3>
          <div 
            className="branding-preview"
            style={{
              background: `linear-gradient(135deg, ${formData.primary_color} 0%, ${formData.secondary_color} 100%)`
            }}
          >
            {formData.logo_url ? (
              <img 
                src={formData.logo_url} 
                alt="Logo Preview" 
                className="preview-logo"
                onError={(e) => { e.target.style.display = 'none'; }}
              />
            ) : (
              <div className="preview-placeholder">
                <span>Your Logo Here</span>
              </div>
            )}
            <h2 className="preview-title">{formData.name || 'Your Company'}</h2>
            <p className="preview-subtitle">Anonymous VPN Service</p>
            <button 
              className="preview-cta"
              style={{ backgroundColor: formData.primary_color }}
            >
              Get Started
            </button>
          </div>

          <div className="preview-info">
            <h4>ℹ️ White-Label Features</h4>
            <ul>
              <li>✅ Custom logo and branding</li>
              <li>✅ Personalized color scheme</li>
              <li>✅ Custom domain support</li>
              <li>✅ Remove AnonVPN branding</li>
              <li>✅ Branded client applications</li>
            </ul>
          </div>
        </div>
      </div>

      {organization && (
        <div className="current-settings">
          <h3>📋 Current Settings</h3>
          <div className="settings-grid">
            <div className="setting-item">
              <strong>Organization:</strong>
              <span>{organization.name}</span>
            </div>
            <div className="setting-item">
              <strong>Team Size:</strong>
              <span>{organization.current_team_members || 0} / {organization.max_team_members || 0}</span>
            </div>
            <div className="setting-item">
              <strong>Plan:</strong>
              <span>{organization.plan_id || 'Not set'}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WhiteLabelConfig;
