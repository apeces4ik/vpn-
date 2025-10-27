import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Globe, Lock, Zap, Server, Eye, ChevronRight, Check, Wallet } from 'lucide-react';
import { ethers } from 'ethers';
import TypingEffect from '../components/TypingEffect';
import './LandingPage.css';

const LandingPage = ({ user, createUser }) => {
  const navigate = useNavigate();
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (user) {
      navigate('/dashboard');
    }
  }, [user, navigate]);

  const connectWallet = async () => {
    setConnecting(true);
    setError('');

    try {
      if (!window.ethereum) {
        setError('Please install MetaMask to continue');
        setConnecting(false);
        return;
      }

      // Request account access
      const accounts = await window.ethereum.request({
        method: 'eth_requestAccounts'
      });

      const walletAddress = accounts[0];
      
      // Create user with wallet address
      await createUser(walletAddress, true); // true indicates wallet login
      navigate('/dashboard');
    } catch (err) {
      console.error('Wallet connection error:', err);
      if (err.code === 4001) {
        setError('Wallet connection rejected');
      } else {
        setError('Failed to connect wallet. Please try again.');
      }
    } finally {
      setConnecting(false);
    }
  };

  const features = [
    {
      icon: <Shield className="feature-icon" />,
      title: "Military-Grade Encryption",
      description: "AES-256 encryption with perfect forward secrecy"
    },
    {
      icon: <Eye className="feature-icon" />,
      title: "No-Log Policy",
      description: "Independently audited zero-logs infrastructure"
    },
    {
      icon: <Globe className="feature-icon" />,
      title: "50+ Global Locations",
      description: "High-speed servers across all continents"
    },
    {
      icon: <Lock className="feature-icon" />,
      title: "Anonymous Payments",
      description: "Pay with cryptocurrency for complete privacy"
    },
    {
      icon: <Zap className="feature-icon" />,
      title: "10 Gbps Speed",
      description: "Unlimited bandwidth with zero throttling"
    },
    {
      icon: <Server className="feature-icon" />,
      title: "Multi-Protocol Support",
      description: "WireGuard, OpenVPN, IKEv2, Shadowsocks"
    }
  ];

  const plans = [
    {
      name: "Basic",
      price: "19.99",
      devices: 3,
      speed: "1 Gbps",
      features: [
        "3 Simultaneous Devices",
        "50+ Server Locations",
        "Unlimited Bandwidth",
        "24/7 Support"
      ]
    },
    {
      name: "Pro",
      price: "39.99",
      devices: 5,
      speed: "10 Gbps",
      popular: true,
      features: [
        "5 Simultaneous Devices",
        "50+ Server Locations",
        "Double VPN",
        "Obfuscated Servers",
        "Priority Support"
      ]
    },
    {
      name: "Ultimate",
      price: "59.99",
      devices: 10,
      speed: "10 Gbps",
      features: [
        "10 Simultaneous Devices",
        "50+ Server Locations",
        "Double VPN",
        "Tor over VPN",
        "Dedicated IP",
        "24/7 Priority Support"
      ]
    }
  ];

  return (
    <div className="landing-page" data-testid="landing-page">
      {/* Hero Section */}
      <section className="hero-section">
        <nav className="nav" data-testid="navbar">
          <div className="nav-container">
            <div className="logo" data-testid="logo">
              <Shield size={32} />
              <span className="logo-text">AnonVPN</span>
            </div>
          </div>
        </nav>

        <div className="hero-content">
          <div className="hero-badge" data-testid="hero-badge">
            <Lock size={16} />
            <span>Enterprise-Grade Privacy</span>
          </div>
          
          <h1 className="hero-title" data-testid="hero-title">
            <span className="hero-title-line">
              <TypingEffect text="Your Privacy," delay={100} />
            </span>
            <br />
            <span className="gradient-text-bright">
              <TypingEffect text="Absolutely Anonymous" delay={100} startDelay={1500} />
            </span>
          </h1>
          
          <p className="hero-description" data-testid="hero-description">
            Connect to 50+ global servers with military-grade encryption.
            <br />
            Pay with crypto. No logs. No tracking. Complete anonymity.
          </p>

          <div className="hero-buttons">
            <button 
              className="btn btn-primary btn-lg wallet-connect-btn"
              onClick={connectWallet}
              disabled={connecting}
              data-testid="connect-wallet-btn"
            >
              {connecting ? (
                <>
                  <div className="spinner-small"></div>
                  Connecting...
                </>
              ) : (
                <>
                  <Wallet size={20} />
                  Connect Wallet (MetaMask)
                  <ChevronRight size={20} />
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="error-message" data-testid="wallet-error">
              {error}
            </div>
          )}

          <div className="hero-stats">
            <div className="stat" data-testid="stat-users">
              <div className="stat-value">100K+</div>
              <div className="stat-label">Active Users</div>
            </div>
            <div className="stat" data-testid="stat-locations">
              <div className="stat-value">50+</div>
              <div className="stat-label">Locations</div>
            </div>
            <div className="stat" data-testid="stat-uptime">
              <div className="stat-value">99.95%</div>
              <div className="stat-label">Uptime</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section" data-testid="features-section">
        <div className="section-header">
          <h2 className="section-title">Enterprise-Grade Security</h2>
          <p className="section-subtitle">
            Built for privacy enthusiasts, backed by cutting-edge technology
          </p>
        </div>

        <div className="features-grid">
          {features.map((feature, index) => (
            <div className="feature-card glass-effect" key={index} data-testid={`feature-card-${index}`}>
              <div className="feature-icon-wrapper">
                {feature.icon}
              </div>
              <h3 className="feature-title">{feature.title}</h3>
              <p className="feature-description">{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing Section */}
      <section className="pricing-section" data-testid="pricing-section">
        <div className="section-header">
          <h2 className="section-title">Choose Your Plan</h2>
          <p className="section-subtitle">
            All plans include 10% crypto discount • 30-day money-back guarantee
          </p>
        </div>

        <div className="pricing-grid">
          {plans.map((plan, index) => (
            <div 
              className={`pricing-card ${plan.popular ? 'popular' : ''}`} 
              key={index}
              data-testid={`pricing-card-${index}`}
            >
              {plan.popular && (
                <div className="popular-badge" data-testid="popular-badge">
                  Most Popular
                </div>
              )}
              <h3 className="plan-name">{plan.name}</h3>
              <div className="plan-price">
                <span className="price-currency">$</span>
                <span className="price-amount">{plan.price}</span>
                <span className="price-period">/month</span>
              </div>
              <ul className="plan-features">
                {plan.features.map((feature, i) => (
                  <li key={i} data-testid={`feature-${index}-${i}`}>
                    <Check size={18} className="check-icon" />
                    {feature}
                  </li>
                ))}
              </ul>
              <button 
                className={`btn ${plan.popular ? 'btn-primary' : 'btn-secondary'} btn-block`}
                onClick={connectWallet}
                disabled={connecting}
                data-testid={`select-plan-btn-${index}`}
              >
                {connecting ? 'Connecting...' : 'Select Plan'}
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section" data-testid="cta-section">
        <div className="cta-content">
          <h2 className="cta-title">Ready to Go Anonymous?</h2>
          <p className="cta-description">
            Join thousands of users protecting their privacy with AnonVPN
          </p>
          <button 
            className="btn btn-primary btn-lg"
            onClick={connectWallet}
            disabled={connecting}
            data-testid="cta-get-started-btn"
          >
            {connecting ? 'Connecting...' : (
              <>
                <Wallet size={20} />
                Connect Wallet Now
                <ChevronRight size={20} />
              </>
            )}
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="footer" data-testid="footer">
        <div className="footer-content">
          <div className="footer-brand">
            <Shield size={28} />
            <span>AnonVPN Enterprise</span>
          </div>
          <p className="footer-text">
            © 2025 AnonVPN. All rights reserved. No logs, no tracking.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
