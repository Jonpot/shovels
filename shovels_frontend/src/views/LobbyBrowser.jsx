import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Users, PlayCircle, LogOut, RefreshCw } from 'lucide-react';
import Button from '../components/Button';
import { getRooms, createRoom, removeAuthToken } from '../utils/api';
import './LobbyBrowser.css';

const LobbyBrowser = ({ onJoinRoom, onOpenStyleGuide, user }) => {
    const [rooms, setRooms] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newRoomName, setNewRoomName] = useState('');

    const fetchRooms = async () => {
        setIsLoading(true);
        try {
            const data = await getRooms();
            setRooms(data);
        } catch (err) {
            console.error('Failed to fetch rooms:', err);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchRooms();
    }, []);

    const handleCreateRoom = async (e) => {
        e.preventDefault();
        if (!newRoomName.trim()) return;

        try {
            const room = await createRoom(newRoomName);
            setShowCreateModal(false);
            setNewRoomName('');
            onJoinRoom(room.room_id);
        } catch (err) {
            alert('Failed to create room: ' + err.message);
        }
    };

    const handleLogout = () => {
        removeAuthToken();
        window.location.reload();
    };

    return (
        <div className="lobby-browser">
            <header className="lobby-header">
                <div className="header-left">
                    <h1 className="logo-small">SHOVELS</h1>
                    <div className="user-badge">
                        <span className="user-name">{user.name}</span>
                        <button className="logout-btn" onClick={handleLogout} title="Logout">
                            <LogOut size={16} />
                        </button>
                    </div>
                </div>

                <div className="header-actions">
                    <Button variant="secondary" onClick={onOpenStyleGuide}>
                        Style Guide
                    </Button>
                    <Button variant="secondary" onClick={fetchRooms} disabled={isLoading}>
                        <RefreshCw size={18} className={isLoading ? 'spin' : ''} />
                    </Button>
                    <Button variant="primary" onClick={() => setShowCreateModal(true)}>
                        <Plus size={20} />
                        Create Room
                    </Button>
                </div>
            </header>

            <main className="lobby-main">
                <div className="lobby-container">
                    <h2 className="section-title">Active Rooms</h2>

                    {isLoading && rooms.length === 0 ? (
                        <div className="lobby-loading">
                            <RefreshCw size={48} className="spin" />
                            <p>Fetching active lobbies...</p>
                        </div>
                    ) : rooms.length === 0 ? (
                        <div className="lobby-empty">
                            <Users size={64} opacity={0.3} />
                            <p>No active rooms found. Why not create one?</p>
                            <Button variant="primary" onClick={() => setShowCreateModal(true)} style={{ marginTop: '1.5rem' }}>
                                Start a New Lobby
                            </Button>
                        </div>
                    ) : (
                        <div className="room-grid">
                            {rooms.map((room) => (
                                <motion.div
                                    key={room.room_id}
                                    layoutId={room.room_id}
                                    className="room-card"
                                    whileHover={{ y: -5, borderColor: 'var(--primary-gold)' }}
                                >
                                    <div className="room-info">
                                        <h3 className="room-name">{room.name}</h3>
                                        <div className="room-stats">
                                            <div className="stat-item">
                                                <Users size={16} />
                                                <span>{room.player_count}/4</span>
                                            </div>
                                            <div className={`status-pill ${room.is_started ? 'started' : 'waiting'}`}>
                                                {room.is_started ? 'In Game' : 'Waiting'}
                                            </div>
                                        </div>
                                    </div>
                                    <Button
                                        variant={room.is_started ? 'secondary' : 'primary'}
                                        onClick={() => onJoinRoom(room.room_id)}
                                        disabled={room.is_started && room.player_count >= 4}
                                    >
                                        {room.is_started ? 'Spectate' : 'Join'}
                                    </Button>
                                </motion.div>
                            ))}
                        </div>
                    )}
                </div>
            </main>

            {/* Create Room Modal */}
            <AnimatePresence>
                {showCreateModal && (
                    <div className="modal-backdrop">
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            className="modal-content"
                        >
                            <h3>Create New Room</h3>
                            <form onSubmit={handleCreateRoom}>
                                <div className="input-group">
                                    <label>Room Name</label>
                                    <input
                                        type="text"
                                        placeholder="E.g., The Dig Zone"
                                        value={newRoomName}
                                        onChange={(e) => setNewRoomName(e.target.value)}
                                        autoFocus
                                    />
                                </div>
                                <div className="modal-actions">
                                    <Button variant="secondary" type="button" onClick={() => setShowCreateModal(false)}>
                                        Cancel
                                    </Button>
                                    <Button variant="primary" type="submit">
                                        Create Lobby
                                    </Button>
                                </div>
                            </form>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default LobbyBrowser;
