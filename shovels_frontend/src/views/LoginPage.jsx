import React from 'react';
import { motion } from 'framer-motion';
import { LogIn } from 'lucide-react';
import Button from '../components/Button';
import { login } from '../utils/api';
import './LoginPage.css';

const LoginPage = () => {
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

                    <Button
                        variant="primary"
                        className="google-login-btn"
                        onClick={login}
                    >
                        <LogIn size={20} className="btn-icon" />
                        Login with Google
                    </Button>
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
