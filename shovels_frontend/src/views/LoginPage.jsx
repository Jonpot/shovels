import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { LogIn } from 'lucide-react';
import Button from '../components/Button';
import { login, getAuthMode, localLogin, setAuthToken } from '../utils/api';
import './LoginPage.css';

const LoginPage = () => {
    const [authMode, setAuthMode] = useState(null);
    const [localName, setLocalName] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        getAuthMode().then(data => setAuthMode(data.mode)).catch(() => setAuthMode('google'));
    }, []);

    const handleLocalLogin = async (e) => {
        e.preventDefault();
        if (!localName.trim()) return;

        setLoading(true);
        try {
            const data = await localLogin(localName.trim());
            setAuthToken(data.access_token);
            window.location.reload();
        } catch (error) {
            alert('Login failed: ' + error.message);
            setLoading(false);
        }
    };

    if (authMode === null) {
        return null; // Loading
    }

    return (
        <div className="login-container">
            <div className="login-overlay" />

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, ease: "easeOut" }}
                className="login-card"
            >
                <div className="login-header">
                    <motion.h1
                        initial={{ letterSpacing: "0.2em", opacity: 0 }}
                        animate={{ letterSpacing: "0.05em", opacity: 1 }}
                        transition={{ delay: 0.3, duration: 1 }}
                        className="game-logo"
                    >
                        SHOVELS
                    </motion.h1>
                    <p className="game-subtitle">A Build-&-Battle Card Game</p>
                </div>

                <div className="login-divider" />

                <div className="login-content">
                    <p className="login-description">
                        Sign in to join lobbies, battle friends, and master the art of the dig.
                    </p>

                    {authMode === 'local' ? (
                        <form onSubmit={handleLocalLogin} style={{ width: '100%' }}>
                            <input
                                type="text"
                                placeholder="Enter your name"
                                value={localName}
                                onChange={(e) => setLocalName(e.target.value)}
                                className="local-name-input"
                                disabled={loading}
                                style={{
                                    width: '100%',
                                    padding: '0.75rem 1rem',
                                    marginBottom: '1rem',
                                    border: '1px solid var(--border-dim)',
                                    borderRadius: '4px',
                                    background: 'var(--bg-tertiary)',
                                    color: 'var(--text-primary)',
                                    fontSize: '1rem',
                                }}
                            />
                            <Button
                                variant="primary"
                                type="submit"
                                disabled={loading || !localName.trim()}
                                style={{ width: '100%' }}
                            >
                                <LogIn size={20} className="btn-icon" />
                                {loading ? 'Logging in...' : 'Login (Local Mode)'}
                            </Button>
                            <p style={{
                                marginTop: '1rem',
                                fontSize: '0.875rem',
                                color: 'var(--text-secondary)',
                                textAlign: 'center'
                            }}>
                                Local development mode - no Google OAuth required
                            </p>
                        </form>
                    ) : (
                        <Button
                            variant="primary"
                            className="google-login-btn"
                            onClick={login}
                        >
                            <LogIn size={20} className="btn-icon" />
                            Login with Google
                        </Button>
                    )}
                </div>

                <div className="login-footer">
                    <p>Early Access v0.1.0</p>
                </div>
            </motion.div>

            {/* Background Decorative Elements */}
            <div className="bg-shapes">
                {[...Array(6)].map((_, i) => (
                    <motion.div
                        key={i}
                        className="bg-shape"
                        animate={{
                            y: [0, -20, 0],
                            opacity: [0.1, 0.2, 0.1],
                        }}
                        transition={{
                            duration: 5 + i,
                            repeat: Infinity,
                            ease: "easeInOut",
                            delay: i * 0.5
                        }}
                    />
                ))}
            </div>
        </div>
    );
};

export default LoginPage;
