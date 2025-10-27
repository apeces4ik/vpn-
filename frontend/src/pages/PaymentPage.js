import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { QRCodeSVG } from 'qrcode.react';
import copy from 'copy-to-clipboard';
import { 
  Shield, Check, ChevronLeft, Copy, ExternalLink, 
  RefreshCw, AlertCircle, Clock, Bitcoin
} from 'lucide-react';
import './PaymentPage.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PaymentPage = ({ user, setUser }) => {
  const navigate = useNavigate();
  const [tariffs, setTariffs] = useState([]);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [billingPeriod, setBillingPeriod] = useState('monthly');
  const [selectedCrypto, setSelectedCrypto] = useState('btc');
  const [currencies, setCurrencies] = useState([]);
  const [payment, setPayment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processingPayment, setProcessingPayment] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (payment && payment.status === 'waiting') {
      const interval = setInterval(() => {
        checkPaymentStatus();
      }, 5000);

      return () => clearInterval(interval);
    }
  }, [payment]);

  const fetchData = async () => {
    try {
      const [tariffsRes, currenciesRes] = await Promise.all([
        axios.get(`${API}/tariffs`),
        axios.get(`${API}/payments/currencies`)
      ]);
      
      setTariffs(tariffsRes.data);
      setCurrencies(currenciesRes.data.currencies || []);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch data:', error);
      setLoading(false);
    }
  };

  const checkPaymentStatus = async () => {
    if (!payment) return;

    try {
      const response = await axios.get(`${API}/payments/${payment.id}`);
      const updatedPayment = response.data;
      
      if (updatedPayment.status === 'finished') {
        setPayment(updatedPayment);
        toast.success('Payment confirmed! Your subscription is now active.');
        
        // Update user data
        const userResponse = await axios.get(`${API}/users/${user.id}`);
        const updatedUser = userResponse.data;
        localStorage.setItem('anonvpn_user', JSON.stringify(updatedUser));
        setUser(updatedUser);
        
        setTimeout(() => {
          navigate('/dashboard');
        }, 2000);
      } else if (updatedPayment.status === 'failed') {
        setPayment(updatedPayment);
        toast.error('Payment failed. Please try again.');
      }
    } catch (error) {
      console.error('Failed to check payment status:', error);
    }
  };

  const createPayment = async () => {
    if (!selectedPlan) {
      toast.error('Please select a plan');
      return;
    }

    setProcessingPayment(true);
    try {
      const response = await axios.post(`${API}/payments/create`, null, {
        params: {
          user_id: user.id,
          plan_id: selectedPlan.id,
          pay_currency: selectedCrypto,
          billing_period: billingPeriod
        }
      });

      setPayment(response.data);
      toast.success('Payment created! Please send the exact amount.');
    } catch (error) {
      console.error('Failed to create payment:', error);
      
      // Extract error message from response
      let errorMessage = 'Failed to create payment. Please try again.';
      
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.response?.status === 400) {
        errorMessage = 'Payment amount is too small. Please try annual billing or a higher tier plan.';
      } else if (error.response?.status === 500) {
        errorMessage = 'Payment service error. Please try a different cryptocurrency.';
      }
      
      toast.error(errorMessage, {
        duration: 5000
      });
    } finally {
      setProcessingPayment(false);
    }
  };

  const copyToClipboard = (text) => {
    copy(text);
    toast.success('Copied to clipboard!');
  };

  const getPrice = (plan) => {
    const price = billingPeriod === 'monthly' ? plan.price_monthly : plan.price_annual;
    return (price * (1 - plan.crypto_discount)).toFixed(2);
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
      </div>
    );
  }

  if (payment && payment.status !== 'failed') {
    return (
      <div className="payment-page" data-testid="payment-page">
        <nav className="payment-nav">
          <div className="nav-container">
            <div className="logo">
              <Shield size={28} />
              <span className="logo-text">AnonVPN</span>
            </div>
          </div>
        </nav>

        <div className="payment-container">
          <div className="payment-card" data-testid="payment-details-card">
            <div className="payment-header">
              <Bitcoin size={48} className="payment-icon" />
              <h2>Complete Your Payment</h2>
              {payment.status === 'finished' ? (
                <div className="payment-status success" data-testid="payment-success">
                  <Check size={20} />
                  Payment Confirmed
                </div>
              ) : (
                <div className="payment-status pending" data-testid="payment-pending">
                  <Clock size={20} />
                  Waiting for Payment
                </div>
              )}
            </div>

            <div className="payment-qr" data-testid="payment-qr">
              <a 
                href={`${payment.pay_currency}:${payment.pay_address}?amount=${payment.pay_amount}`}
                className="qr-link"
                data-testid="qr-deeplink"
              >
                <QRCodeSVG 
                  value={`${payment.pay_currency}:${payment.pay_address}?amount=${payment.pay_amount}`}
                  size={200}
                  level="H"
                  includeMargin={true}
                />
                <div className="qr-hint">Click to open wallet</div>
              </a>
            </div>

            <div className="payment-info">
              <div className="payment-detail">
                <div className="detail-label">Amount to Pay</div>
                <div className="detail-value highlight" data-testid="payment-amount">
                  {payment.pay_amount} {payment.pay_currency?.toUpperCase()}
                </div>
              </div>

              <div className="payment-detail">
                <div className="detail-label">Payment Address</div>
                <div className="detail-value-with-copy">
                  <code className="detail-value" data-testid="payment-address">
                    {payment.pay_address}
                  </code>
                  <button 
                    className="btn-icon"
                    onClick={() => copyToClipboard(payment.pay_address)}
                    data-testid="copy-address-btn"
                  >
                    <Copy size={18} />
                  </button>
                </div>
              </div>

              <div className="payment-detail">
                <div className="detail-label">Order ID</div>
                <div className="detail-value" data-testid="order-id">
                  {payment.id.substring(0, 16)}...
                </div>
              </div>
            </div>

            {payment.status !== 'finished' && (
              <div className="payment-notice" data-testid="payment-notice">
                <AlertCircle size={20} />
                <div>
                  <strong>Important:</strong> Send the exact amount shown above.
                  Your subscription will be activated automatically after confirmation.
                </div>
              </div>
            )}

            <button 
              className="btn btn-secondary btn-block"
              onClick={() => checkPaymentStatus()}
              disabled={payment.status === 'finished'}
              data-testid="refresh-payment-btn"
            >
              <RefreshCw size={18} />
              Refresh Payment Status
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="payment-page" data-testid="payment-selection-page">
      <nav className="payment-nav">
        <div className="nav-container">
          <button 
            className="btn-back"
            onClick={() => navigate('/dashboard')}
            data-testid="back-to-dashboard-btn"
          >
            <ChevronLeft size={20} />
            Back to Dashboard
          </button>
          <div className="logo">
            <Shield size={28} />
            <span className="logo-text">AnonVPN</span>
          </div>
        </div>
      </nav>

      <div className="payment-container">
        <div className="payment-header-section">
          <h1 className="payment-title" data-testid="payment-title">Select Your Plan</h1>
          <p className="payment-subtitle">
            All plans include 10% crypto discount • No logs, complete anonymity
          </p>
        </div>

        {/* Billing Period Toggle */}
        <div className="billing-toggle" data-testid="billing-toggle">
          <button 
            className={`billing-option ${billingPeriod === 'monthly' ? 'active' : ''}`}
            onClick={() => setBillingPeriod('monthly')}
            data-testid="monthly-billing-btn"
          >
            Monthly
          </button>
          <button 
            className={`billing-option ${billingPeriod === 'annual' ? 'active' : ''}`}
            onClick={() => setBillingPeriod('annual')}
            data-testid="annual-billing-btn"
          >
            Annual
            <span className="savings-badge">Save 50%</span>
          </button>
        </div>

        {/* Plans Grid */}
        <div className="plans-grid">
          {tariffs.map((plan, index) => (
            <div 
              className={`plan-card ${selectedPlan?.id === plan.id ? 'selected' : ''} ${plan.name === 'Pro' ? 'popular' : ''}`}
              key={plan.id}
              onClick={() => setSelectedPlan(plan)}
              data-testid={`plan-card-${index}`}
            >
              {plan.name === 'Pro' && (
                <div className="popular-badge">Most Popular</div>
              )}
              
              <h3 className="plan-name">{plan.name}</h3>
              
              <div className="plan-price">
                <span className="currency">$</span>
                <span className="amount">{getPrice(plan)}</span>
                <span className="period">/{billingPeriod === 'monthly' ? 'mo' : 'yr'}</span>
              </div>

              <div className="plan-discount">
                <Check size={16} />
                10% Crypto Discount Applied
              </div>

              <ul className="plan-features">
                <li data-testid={`plan-${index}-devices`}>
                  <Check size={18} />
                  {plan.device_limit} Simultaneous Devices
                </li>
                <li data-testid={`plan-${index}-speed`}>
                  <Check size={18} />
                  {plan.speed_tier} Speed
                </li>
                <li>
                  <Check size={18} />
                  50+ Server Locations
                </li>
                {plan.special_features.includes('double_vpn') && (
                  <li data-testid={`plan-${index}-double-vpn`}>
                    <Check size={18} />
                    Double VPN
                  </li>
                )}
                {plan.special_features.includes('obfuscation') && (
                  <li data-testid={`plan-${index}-obfuscation`}>
                    <Check size={18} />
                    Obfuscated Servers
                  </li>
                )}
                {plan.special_features.includes('tor_over_vpn') && (
                  <li data-testid={`plan-${index}-tor`}>
                    <Check size={18} />
                    Tor over VPN
                  </li>
                )}
                {plan.special_features.includes('dedicated_ip') && (
                  <li data-testid={`plan-${index}-dedicated-ip`}>
                    <Check size={18} />
                    Dedicated IP
                  </li>
                )}
              </ul>

              {selectedPlan?.id === plan.id && (
                <div className="selected-indicator" data-testid={`selected-indicator-${index}`}>
                  <Check size={20} />
                  Selected
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Crypto Selection */}
        {selectedPlan && (
          <div className="crypto-section" data-testid="crypto-section">
            <h3 className="section-title">Select Cryptocurrency</h3>
            
            {/* Payment minimum notice */}
            {billingPeriod === 'monthly' && selectedCrypto === 'btc' && (
              <div className="payment-notice warning" style={{marginBottom: '1rem'}}>
                <AlertCircle size={20} />
                <div>
                  <strong>Note:</strong> Bitcoin (BTC) has a minimum payment of ~$20.
                  For monthly plans, consider using ETH, LTC, or select annual billing.
                </div>
              </div>
            )}
            
            <div className="crypto-grid">
              {['btc', 'eth', 'ltc', 'xmr', 'usdt', 'usdc'].map((crypto) => (
                <button
                  key={crypto}
                  className={`crypto-option ${selectedCrypto === crypto ? 'selected' : ''}`}
                  onClick={() => setSelectedCrypto(crypto)}
                  data-testid={`crypto-${crypto}-btn`}
                >
                  <div className="crypto-icon">{crypto.toUpperCase()}</div>
                  {selectedCrypto === crypto && <Check size={18} className="check-mark" />}
                </button>
              ))}
            </div>
            
            <div className="crypto-recommendations" style={{marginTop: '1rem', fontSize: '0.9rem', color: '#888'}}>
              <p><strong>Recommended for monthly plans:</strong> ETH, LTC, USDT, USDC</p>
              <p><strong>Best for privacy:</strong> XMR (Monero)</p>
            </div>
          </div>
        )}

        {/* Checkout Button */}
        {selectedPlan && (
          <div className="checkout-section" data-testid="checkout-section">
            <button 
              className="btn btn-primary btn-lg btn-block"
              onClick={createPayment}
              disabled={processingPayment}
              data-testid="proceed-payment-btn"
            >
              {processingPayment ? (
                <>
                  <RefreshCw size={20} className="spin" />
                  Processing...
                </>
              ) : (
                <>
                  Proceed to Payment
                  <ExternalLink size={20} />
                </>
              )}
            </button>

            <div className="checkout-summary" data-testid="checkout-summary">
              <div className="summary-row">
                <span>Plan:</span>
                <strong>{selectedPlan.name} - {billingPeriod === 'monthly' ? 'Monthly' : 'Annual'}</strong>
              </div>
              <div className="summary-row">
                <span>Payment Method:</span>
                <strong>{selectedCrypto.toUpperCase()}</strong>
              </div>
              <div className="summary-row total">
                <span>Total:</span>
                <strong>${getPrice(selectedPlan)}</strong>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PaymentPage;
