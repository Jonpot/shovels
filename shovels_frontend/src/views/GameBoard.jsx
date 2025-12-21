import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Users, Trash2, Zap, ArrowUpCircle } from 'lucide-react';
import PlayerHand from '../components/game/PlayerHand';
import CharacterStack from '../components/game/CharacterStack';
import ShopRow from '../components/game/ShopRow';
import Card from '../components/Card';
import Button from '../components/Button';
import './GameBoard.css';

const GameBoard = ({ gameState, user, sendMessage, error, setError }) => {
    const [selectedHandIndices, setSelectedHandIndices] = useState([]);
    const [pendingDrawSources, setPendingDrawSources] = useState([]);
    const [actionPhase, setActionPhase] = useState(null);

    console.log("[GameBoard] State Update:", { phase: gameState.phase, subphase: gameState.turn_subphase, current_turn: gameState.current_turn_index });

    if (!gameState) return <div className="loading">Loading Game State...</div>;

    const myPlayer = gameState.players.find(p => p.id === user.id);
    const opponents = gameState.players.filter(p => p.id !== user.id);
    const isMyTurn = gameState.current_turn_index !== undefined &&
        gameState.players[gameState.current_turn_index].id === user.id;

    // Reset pending draws if subphase changes
    React.useEffect(() => {
        if (gameState.turn_subphase !== "DRAW") {
            setPendingDrawSources([]);
        }
    }, [gameState.turn_subphase]);

    // --- Action Handlers ---

    const handleDrawClick = (source) => {
        if (!isMyTurn || gameState.turn_subphase !== "DRAW") return;
        if (pendingDrawSources.length >= 2) return;

        console.log(`[GameBoard] Adding draw source: ${source}`);
        const nextSources = [...pendingDrawSources, source];

        // Rule: If both selected, DISCARD must be first.
        if (nextSources.length === 2 && nextSources[0] === "DECK" && nextSources[1] === "DISCARD") {
            if (setError) setError("Rule: If drawing from both, you must pick from Discard first.");
            return;
        }

        setPendingDrawSources(nextSources);
    };

    const confirmDraw = () => {
        if (pendingDrawSources.length !== 2) return;
        console.log("[GameBoard] Sending draw action:", pendingDrawSources);
        sendMessage({
            type: 'action',
            data: {
                action_type: 'draw',
                params: { sources: pendingDrawSources }
            }
        });
        setPendingDrawSources([]);
    };

    const handleDiscard = () => {
        if (selectedHandIndices.length !== 1) {
            alert("Select exactly 1 card to discard");
            return;
        }
        console.log(`[GameBoard] Discarding hand index ${selectedHandIndices[0]}, card:`, myPlayer.hand[selectedHandIndices[0]]);
        sendMessage({
            type: 'action',
            data: {
                action_type: 'discard',
                params: { card_index: selectedHandIndices[0] }
            }
        });
        setSelectedHandIndices([]);
    };

    const handleCardClick = (index) => {
        console.log(`[GameBoard] Card clicked: index ${index}, card:`, myPlayer.hand[index]);
        // Toggle selection
        if (selectedHandIndices.includes(index)) {
            setSelectedHandIndices(selectedHandIndices.filter(i => i !== index));
        } else {
            setSelectedHandIndices([index]);
        }
        if (setError) setError(null);
    };

    const handleCharacterClick = (charIndex) => {
        console.log(`[GameBoard] Character clicked: index ${charIndex}, subphase: ${gameState.turn_subphase}`);
        if (gameState.phase === 1 && gameState.turn_subphase === "PLAY") {
            if (selectedHandIndices.length !== 1) {
                console.warn("[GameBoard] Play failed: exactly 1 card must be selected.");
                return;
            }
            console.log("[GameBoard] Sending play action:", { card_index: selectedHandIndices[0], character_index: charIndex });
            sendMessage({
                type: 'action',
                data: {
                    action_type: 'play',
                    params: {
                        card_index: selectedHandIndices[0],
                        character_index: charIndex
                    }
                }
            });
            setSelectedHandIndices([]);
        }
        // ...
    };

    const renderPhaseControls = () => {
        if (!isMyTurn) return <div className="turn-indicator">Opponent's Turn</div>;

        if (gameState.phase === 1) {
            if (gameState.turn_subphase === "DRAW") {
                return (
                    <div className="phase-controls">
                        <h3>Draw Phase</h3>
                        <p>Click Deck or Discard (Pick 2)</p>
                        <div className="pending-draw-list">
                            {pendingDrawSources.map((s, i) => (
                                <span key={i} className="draw-badge">{s}</span>
                            ))}
                        </div>
                        <div className="button-group">
                            <Button
                                onClick={confirmDraw}
                                disabled={pendingDrawSources.length !== 2}
                                variant="primary"
                            >
                                Confirm Draw
                            </Button>
                            <Button
                                onClick={() => setPendingDrawSources([])}
                                disabled={pendingDrawSources.length === 0}
                                variant="ghost"
                            >
                                Reset
                            </Button>
                        </div>
                    </div>
                );
            }
            if (gameState.turn_subphase === "DISCARD") {
                return (
                    <div className="phase-controls">
                        <h3>Discard Phase</h3>
                        <p>Select 1 card to discard</p>
                        <Button onClick={handleDiscard} disabled={selectedHandIndices.length !== 1}>
                            Discard Selected
                        </Button>
                    </div>
                );
            }
            if (gameState.turn_subphase === "PLAY") {
                return (
                    <div className="phase-controls">
                        <h3>Play Phase</h3>
                        <p>Select card -&gt; Click Character</p>
                        <Button onClick={() => sendMessage({ type: 'action', data: { action_type: 'action', params: {} } })}>
                            End Play / Start Battle
                        </Button>
                    </div>
                );
            }
        }

        return <div className="turn-indicator">Battle Phase ({gameState.turn_subphase})</div>;
    };

    return (
        <div className="game-board">
            <AnimatePresence>
                {error && (
                    <motion.div
                        initial={{ opacity: 0, y: -50 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -50 }}
                        className="error-toast"
                        onClick={() => setError(null)}
                    >
                        {error}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Top Bar: Opponents Mini View */}
            <div className="opponents-strip">
                {opponents.map(opp => (
                    <div key={opp.id} className="opponent-compact">
                        <Users size={16} /> {opp.name} ({opp.hand.length} cards)
                        <div className="opp-chars">
                            {opp.characters.map((c, i) => (
                                <div key={i} className="mini-char-pip" title={`${c.rank}${c.suit}`} />
                            ))}
                        </div>
                    </div>
                ))}
            </div>

            {/* Main Game Layout */}
            <div className="main-layout">
                {/* Left: My Characters */}
                <div className="my-characters-sidebar">
                    <h3>My Characters</h3>
                    <div className="characters-scroll-list">
                        {myPlayer.characters.map((char, i) => (
                            <CharacterStack
                                key={char.uid}
                                character={char}
                                onStackClick={() => handleCharacterClick(i)}
                                isTargetable={gameState.turn_subphase === 'PLAY' && selectedHandIndices.length === 1}
                                isSelected={false}
                            />
                        ))}
                    </div>
                </div>

                {/* Center: Table & Phase Controls */}
                <div className="table-center-column">
                    <div className="phase-indicator-area">
                        {renderPhaseControls()}
                    </div>

                    <div className="decks-area">
                        <div
                            className={`deck-pile ${pendingDrawSources.includes("DECK") ? 'pending' : ''}`}
                            onClick={() => handleDrawClick("DECK")}
                        >
                            Deck ({gameState.deck.length})
                        </div>

                        <div
                            className={`discard-pile-container ${pendingDrawSources.includes("DISCARD") ? 'pending' : ''}`}
                            onClick={() => handleDrawClick("DISCARD")}
                        >
                            {/* Show top 2 cards of discard */}
                            {gameState.discard_pile.slice(-2).map((card, idx) => (
                                <div
                                    key={card.uid}
                                    className="discard-card-layered"
                                    style={{
                                        transform: `translate(${idx * 15}px, ${idx * 15}px)`,
                                        zIndex: idx,
                                        '--idx': idx
                                    }}
                                >
                                    <Card
                                        rank={card.rank}
                                        suit={card.suit}
                                        isFace={card.is_face}
                                        faceRank={card.face_rank}
                                        isAce={card.is_ace}
                                    />
                                </div>
                            ))}
                            {gameState.discard_pile.length === 0 && <div className="deck-pile dummy">Discard</div>}
                            <div className="stack-count-badge top-left">
                                {gameState.discard_pile.length}
                            </div>
                        </div>
                    </div>

                    <ShopRow
                        shopCards={gameState.shop_row || []}
                        coins={myPlayer.coins}
                        isShoppingPhase={isMyTurn && gameState.turn_subphase === 'SHOPPING'}
                        onBuyCard={() => { }} // TODO
                    />
                </div>

                {/* Right: Detailed Opponent Info */}
                <div className="actions-history-sidebar">
                    <h3>Opponents</h3>
                    <div className="opponents-list">
                        {opponents.map(opp => (
                            <div key={opp.id} className="opponent-card">
                                <Users size={16} /> <strong>{opp.name}</strong>
                                <span>{opp.hand.length} cards</span>
                                <div className="opp-chars-mini">
                                    {opp.characters.map((c, i) => (
                                        <div key={i} className={`mini-status ${c.is_tapped ? 'tapped' : ''}`} title={`${c.rank} of ${c.suit}`}>
                                            <Card rank={c.rank} suit={c.suit} isFace={true} faceRank={c.rank} className="micro-card" />
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Fixed Bottom: Player Hand */}
            <PlayerHand
                hand={myPlayer.hand}
                selectedIndices={selectedHandIndices}
                onCardClick={handleCardClick}
            />
        </div>
    );
};

export default GameBoard;
