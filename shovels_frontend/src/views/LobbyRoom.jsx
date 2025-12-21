import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Users, Shield, ArrowLeft, Play, UserPlus } from 'lucide-react';
import Button from '../components/Button';
import { getWsUrl } from '../utils/api';
import GameBoard from './GameBoard';
import './LobbyRoom.css';

const LobbyRoom = ({ roomId, user, onLeave }) => {
    const [gameState, setGameState] = useState(null);
    const [error, setError] = useState(null);
    const ws = useRef(null);

    useEffect(() => {
        const url = getWsUrl(roomId);
        // Use a local variable to capture the instance for cleanup
        const socket = new WebSocket(url);
        ws.current = socket;
        let isMounted = true;

        socket.onopen = () => {
            if (isMounted) console.log('Connected to lobby WS');
        };

        socket.onmessage = (event) => {
            if (!isMounted) return;
            const msg = JSON.parse(event.data);
            if (msg.type === 'state_update') {
                setGameState(msg.state);
                setError(null);
            } else if (msg.type === 'error') {
                setError(msg.message);
            }
        };

        socket.onerror = () => {
            if (isMounted) setError('WebSocket connection error');
        };

        socket.onclose = () => {
            if (isMounted) console.log('WS connection closed');
        };

        return () => {
            isMounted = false;
            if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
                socket.close();
            }
        };
    }, [roomId]);

    const sendMessage = (msg) => {
        if (ws.current) ws.current.send(JSON.stringify(msg));
    };

    const handleStartGame = () => {
        sendMessage({ type: 'start_game' });
    };

    // Determine if we are in active game or lobby
    // LOBBY phase is represented by phase="LOBBY" in our mock broadcast_lobby_state
    // Real game phases are numbers (e.g., 1)
    const isGameActive = gameState && gameState.phase !== "LOBBY";

    if (isGameActive) {
        return (
            <GameBoard
                gameState={gameState}
                user={user}
                sendMessage={sendMessage}
                error={error}
                setError={setError}
            />
        );
    }

    // Lobby View
    const players = gameState?.players || [
        { id: user.id, name: user.name, is_alive: true }
    ];

    const canStart = players.length >= 2;

    return (
        <div className="lobby-room">
            <header className="room-header">
                <button className="back-btn" onClick={onLeave}>
                    <ArrowLeft size={20} />
                    Leave Lobby
                </button>
                <div className="room-title">
                    <h2>Game Lobby</h2>
                    <span className="room-id">ID: {roomId}</span>
                </div>
                <div className="placeholder" />
            </header>

            <main className="room-content">
                <div className="slots-grid">
                    {[0, 1, 2, 3].map((i) => {
                        const player = players[i];
                        return (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: i * 0.1 }}
                                className={`player-slot ${player ? 'filled' : 'empty'}`}
                            >
                                {player ? (
                                    <>
                                        <div className="player-avatar">
                                            <Users size={32} />
                                        </div>
                                        <div className="player-info">
                                            <span className="player-name">
                                                {player.name}
                                                {player.id === user.id && <span className="self-tag">(You)</span>}
                                            </span>
                                            {i === 0 && (
                                                <div className="host-tag">
                                                    <Shield size={12} />
                                                    Host
                                                </div>
                                            )}
                                        </div>
                                    </>
                                ) : (
                                    <div className="empty-slot-content">
                                        <UserPlus size={24} opacity={0.3} />
                                        <span>Waiting for player...</span>
                                    </div>
                                )}
                            </motion.div>
                        );
                    })}
                </div>

                {error && <div className="room-error">{error}</div>}

                <div className="room-actions">
                    <p className="hint-text">
                        {players.length < 2
                            ? "Waiting for at least one more player..."
                            : "Lobby full. Ready to start?"}
                    </p>
                    {user.id === players[0]?.id && (
                        <Button
                            variant="primary"
                            size="large"
                            disabled={!canStart}
                            onClick={handleStartGame}
                        >
                            <Play size={20} />
                            Start Game
                        </Button>
                    )}
                </div>
            </main>
        </div>
    );
};

export default LobbyRoom;
