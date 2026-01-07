import React from 'react';
import { motion } from 'framer-motion';
import { Trophy, Home } from 'lucide-react';
import Button from '../Button';
import './VictoryScreen.css';

const VictoryScreen = ({ gameState, user, sendMessage }) => {
    const winner = gameState.players.find(p => p.id === gameState.winner_id);
    const isWinner = gameState.winner_id === user.id;
    const isDraw = gameState.winner_id === "DRAW";

    return (
        <motion.div
            className="victory-screen-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
        >
            <motion.div
                className="victory-screen-content"
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.2, type: "spring" }}
            >
                <div className="victory-icon">
                    <Trophy size={80} />
                </div>

                {isDraw ? (
                    <h1 className="victory-title">Draw!</h1>
                ) : isWinner ? (
                    <>
                        <h1 className="victory-title">Victory!</h1>
                        <p className="victory-message">You have won the game!</p>
                    </>
                ) : (
                    <>
                        <h1 className="victory-title defeat">Defeat</h1>
                        <p className="victory-message">{winner?.name || 'Unknown'} wins!</p>
                    </>
                )}

                <div className="game-stats">
                    <div className="stat-item">
                        <span className="stat-label">Total Turns</span>
                        <span className="stat-value">{gameState.turn_count}</span>
                    </div>
                    <div className="stat-item">
                        <span className="stat-label">Final Players</span>
                        <span className="stat-value">{gameState.players.filter(p => p.is_alive).length}</span>
                    </div>
                </div>

                <Button
                    variant="primary"
                    onClick={() => sendMessage({ type: 'return_to_lobby' })}
                    className="return-lobby-btn"
                >
                    <Home size={20} />
                    Return to Lobby
                </Button>
            </motion.div>
        </motion.div>
    );
};

export default VictoryScreen;
