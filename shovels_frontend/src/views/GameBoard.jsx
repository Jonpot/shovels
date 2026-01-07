import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Users, Trash2, Zap, ArrowUpCircle, ArrowLeft, ChevronLeft, ChevronRight } from 'lucide-react';
import PlayerHand from '../components/game/PlayerHand';
import CharacterStack from '../components/game/CharacterStack';
import ShopRow from '../components/game/ShopRow';
import VictoryScreen from '../components/game/VictoryScreen';
import Card from '../components/Card';
import Button from '../components/Button';
import './GameBoard.css';

const GameBoard = ({ gameState, user, sendMessage, error, setError }) => {
    const [selectedHandIndices, setSelectedHandIndices] = useState([]);
    const [pendingDrawSources, setPendingDrawSources] = useState([]);
    const [actionPhase, setActionPhase] = useState(null);

    // Phase 2 Battle state
    const [selectedCharIndex, setSelectedCharIndex] = useState(null);
    const [selectedStackIndices, setSelectedStackIndices] = useState([]);
    const [selectedSuit, setSelectedSuit] = useState(null);
    const [targetMode, setTargetMode] = useState(null); // 'strike', 'attack', 'buy'
    const [selectedShopSlot, setSelectedShopSlot] = useState(null);
    const [selectedTargetPlayer, setSelectedTargetPlayer] = useState(null);
    const [selectedTargetChar, setSelectedTargetChar] = useState(null);

    // Opponent viewing state
    const [selectedOpponentId, setSelectedOpponentId] = useState(null); // null = list view, otherwise detailed view

    // Test mode detection
    const [isTestMode, setIsTestMode] = useState(false);
    const [autoPlaying, setAutoPlaying] = useState(false);

    // Check if in test mode (local mode)
    React.useEffect(() => {
        fetch('http://localhost:8000/auth/mode')
            .then(res => res.json())
            .then(data => setIsTestMode(data.mode === 'local'))
            .catch(() => setIsTestMode(false));
    }, []);

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
        // Reset Phase 2 state when subphase changes
        if (gameState.phase === 2) {
            setSelectedCharIndex(null);
            setSelectedStackIndices([]);
            setSelectedSuit(null);
            setTargetMode(null);
            setSelectedShopSlot(null);
            setSelectedTargetPlayer(null);
            setSelectedTargetChar(null);
        }
    }, [gameState.turn_subphase, gameState.phase]);

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
        } else if (gameState.phase === 2) {
            // Phase 2: Select character to act with
            if (targetMode === 'buy') {
                // Selecting character to receive bought card
                if (selectedShopSlot !== null) {
                    handleBuyCard(selectedShopSlot, charIndex);
                }
            } else {
                setSelectedCharIndex(charIndex);
                setSelectedStackIndices([]);
                setSelectedSuit(null);
            }
        }
    };

    // Phase 2: Stack card multi-select
    const handleStackCardClick = (charIndex, cardIndex) => {
        if (gameState.phase !== 2) return;

        // Auto-select character when clicking a card in its stack
        if (selectedCharIndex !== charIndex) {
            setSelectedCharIndex(charIndex);
            setSelectedStackIndices([]);
            setSelectedSuit(null);
        }

        const char = myPlayer.characters[charIndex];
        const stackLen = char.stack.length;

        // Clicking any card selects that card AND all cards above it (to the top)
        // Top of stack is at index stackLen - 1
        // If stackLen = 5, indices are 0,1,2,3,4 where 4 is the top

        // Select all cards from cardIndex to top (stackLen - 1)
        const selectedRange = [];
        for (let i = cardIndex; i < stackLen; i++) {
            selectedRange.push(i);
        }

        setSelectedStackIndices(selectedRange);
    };

    // Phase 2: Tap Hero Power
    const handleTapHero = () => {
        if (selectedCharIndex === null) {
            if (setError) setError("Select a character first");
            return;
        }

        const char = myPlayer.characters[selectedCharIndex];
        if (char.is_tapped) {
            if (setError) setError("Character is already tapped");
            return;
        }

        // Check if needs targets (Clubs)
        if (char.suit === "CLUBS") {
            setTargetMode('tap_clubs');
            if (setError) setError("Now select opponent character(s) to target");
            return;
        }

        // Send tap action
        sendMessage({
            type: 'action',
            data: {
                action_type: 'tap_hero',
                params: {
                    char_index: selectedCharIndex,
                    target_info: null
                }
            }
        });
        setSelectedCharIndex(null);
    };

    // Phase 2: Face Strike
    const handleFaceStrike = () => {
        if (selectedCharIndex === null) {
            if (setError) setError("Select a character first");
            return;
        }

        const char = myPlayer.characters[selectedCharIndex];
        const allCardsSelected = selectedStackIndices.length === char.stack.length;

        setTargetMode(allCardsSelected ? 'strike_with_discard' : 'strike');
        if (setError) setError("Now select an opponent character to strike");
    };

    // Phase 2: Perform Action (with stack cards)
    const handlePerformAction = (suit) => {
        if (selectedCharIndex === null) {
            if (setError) setError("Select a character first");
            return;
        }

        if (selectedStackIndices.length === 0) {
            if (setError) setError("Select cards from the stack first");
            return;
        }

        const selectedCards = selectedStackIndices.map(i => myPlayer.characters[selectedCharIndex].stack[i]);
        const validSuits = [...new Set(selectedCards.map(c => c.suit))];

        if (!validSuits.includes(suit)) {
            if (setError) setError(`Selected cards don't contain ${suit}`);
            return;
        }

        // Check if needs target (Clubs)
        if (suit === "CLUBS") {
            setSelectedSuit(suit);
            setTargetMode('attack');
            if (setError) setError("Now select an opponent character to attack");
            return;
        }

        // Send action
        sendMessage({
            type: 'action',
            data: {
                action_type: 'perform_action',
                params: {
                    char_index: selectedCharIndex,
                    top_n_cards: selectedStackIndices.length,
                    action_suit: suit,
                    target_info: null
                }
            }
        });

        setSelectedCharIndex(null);
        setSelectedStackIndices([]);
    };

    // Phase 2: Buy Card from Shop
    const handleBuyCard = (slot_index, char_index) => {
        sendMessage({
            type: 'action',
            data: {
                action_type: 'buy',
                params: {
                    slot_index: slot_index,
                    char_index: char_index
                }
            }
        });
        setSelectedShopSlot(null);
        setTargetMode(null);
    };

    // Navigate between opponents
    const navigateOpponent = (direction) => {
        if (!selectedOpponentId) return;
        const currentIndex = opponents.findIndex(o => o.id === selectedOpponentId);
        if (currentIndex === -1) return;

        let newIndex;
        if (direction === 'prev') {
            newIndex = currentIndex === 0 ? opponents.length - 1 : currentIndex - 1;
        } else {
            newIndex = currentIndex === opponents.length - 1 ? 0 : currentIndex + 1;
        }
        setSelectedOpponentId(opponents[newIndex].id);
    };

    // Phase 2: Target opponent character
    const handleOpponentCharClick = (oppPlayerId, charIndex) => {
        if (!targetMode) return;

        const targetPlayerId = oppPlayerId;

        if (targetMode === 'strike' || targetMode === 'strike_with_discard') {
            // Face Strike
            sendMessage({
                type: 'action',
                data: {
                    action_type: 'face_strike',
                    params: {
                        char_index: selectedCharIndex,
                        target_player_id: targetPlayerId,
                        target_char_index: charIndex,
                        discard_all_cards: targetMode === 'strike_with_discard'
                    }
                }
            });
            setSelectedCharIndex(null);
            setSelectedStackIndices([]);
            setTargetMode(null);
        } else if (targetMode === 'attack') {
            // Clubs attack
            sendMessage({
                type: 'action',
                data: {
                    action_type: 'perform_action',
                    params: {
                        char_index: selectedCharIndex,
                        top_n_cards: selectedStackIndices.length,
                        action_suit: selectedSuit,
                        target_info: {
                            target_player_id: targetPlayerId,
                            target_char_index: charIndex
                        }
                    }
                }
            });
            setSelectedCharIndex(null);
            setSelectedStackIndices([]);
            setSelectedSuit(null);
            setTargetMode(null);
        } else if (targetMode === 'tap_clubs') {
            // Clubs burst - for now just target one (TODO: multi-target)
            sendMessage({
                type: 'action',
                data: {
                    action_type: 'tap_hero',
                    params: {
                        char_index: selectedCharIndex,
                        target_info: {
                            targets: [{
                                target_player_id: targetPlayerId,
                                target_char_index: charIndex
                            }]
                        }
                    }
                }
            });
            setSelectedCharIndex(null);
            setTargetMode(null);
        }
    };

    // Phase 2: Check if player has taken an action this turn
    const hasPlayerActed = () => {
        // Check gameState.action_taken_this_turn, cards_removed_this_turn, character_tapped_this_turn
        return gameState.action_taken_this_turn ||
               gameState.cards_removed_this_turn ||
               gameState.character_tapped_this_turn;
    };

    // Phase 2: Check if player CAN act (for forced action rule)
    const canPlayerAct = () => {
        if (!myPlayer || !myPlayer.is_alive) return false;

        for (const char of myPlayer.characters) {
            // Can discard from stack?
            if (char.stack.length > 0) return true;

            // Can tap hero power?
            if (!char.is_tapped) return true;

            // Can face strike? (only if character has no stack)
            if (char.stack.length === 0) {
                // Check if any opponent has a valid target
                for (const opp of opponents) {
                    if (!opp.is_alive) continue;
                    for (const oppChar of opp.characters) {
                        // Can strike exposed faces or hearts that would break
                        if (oppChar.stack.length === 0) return true;

                        const topCard = oppChar.stack[oppChar.stack.length - 1];
                        if (topCard.suit === 'HEARTS' && (1 >= (topCard.rank + oppChar.shield))) {
                            return true;
                        }
                    }
                }
            }
        }

        return false;
    };

    // Phase 2: End Turn
    const handleEndTurn = () => {
        // Enforce forced action rule in BATTLE_ACTION phase
        if (gameState.turn_subphase === 'BATTLE_ACTION' && !hasPlayerActed()) {
            if (!canPlayerAct()) {
                // Player cannot act - they will lose a character (fatigue)
                // Let the backend handle this
                sendMessage({
                    type: 'action',
                    data: {
                        action_type: 'end_turn',
                        params: {}
                    }
                });
            } else {
                if (setError) setError("You must take an action before ending your turn (discard, tap, or strike)");
                return;
            }
        } else {
            sendMessage({
                type: 'action',
                data: {
                    action_type: 'end_turn',
                    params: {}
                }
            });
        }
    };

    // Test Mode: Auto-play Phase 1
    const autoPlayPhase1Turn = () => {
        if (gameState.phase !== 1) {
            setAutoPlaying(false);
            return;
        }

        const currentPlayer = gameState.players[gameState.current_turn_index];
        if (!currentPlayer || currentPlayer.id !== user.id) {
            // Not our turn, wait for it
            return;
        }

        console.log('[AutoPlay] Playing turn:', gameState.turn_subphase, 'for', currentPlayer.id);

        try {
            if (gameState.turn_subphase === "DRAW") {
                    // Determine draw sources
                    const deckCount = gameState.deck.length;
                    const discardCount = gameState.discard_pile.length;
                    let sources = [];

                    if (deckCount >= 2) {
                        sources = ["DECK", "DECK"];
                    } else if (deckCount === 1 && discardCount >= 1) {
                        sources = ["DISCARD", "DECK"]; // Must draw discard first
                    } else if (deckCount === 0 && discardCount >= 2) {
                        sources = ["DISCARD", "DISCARD"];
                    } else if (deckCount === 1 && discardCount === 0) {
                        sources = ["DECK"];
                    } else if (deckCount === 0 && discardCount === 1) {
                        sources = ["DISCARD"];
                    } else {
                        // Not enough cards, end turn
                        sendMessage({
                            type: 'action',
                            data: { action_type: 'end_turn', params: {} }
                        });
                        return;
                    }

                    if (sources.length === 2) {
                        sendMessage({
                            type: 'action',
                            data: {
                                action_type: 'draw',
                                params: { sources }
                            }
                        });
                    } else {
                        // Can't draw 2 cards, end turn
                        sendMessage({
                            type: 'action',
                            data: { action_type: 'end_turn', params: {} }
                        });
                    }
                } else if (gameState.turn_subphase === "DISCARD") {
                    // Discard the lower card
                    const hand = currentPlayer.hand;
                    if (hand.length === 0) {
                        sendMessage({
                            type: 'action',
                            data: { action_type: 'end_turn', params: {} }
                        });
                        return;
                    }

                    // Find lower card (by rank, faces are 0)
                    let lowestIndex = 0;
                    let lowestValue = hand[0].is_face ? 100 : hand[0].rank; // Faces are valuable, keep them

                    hand.forEach((card, idx) => {
                        const value = card.is_face ? 100 : card.rank;
                        if (value < lowestValue) {
                            lowestValue = value;
                            lowestIndex = idx;
                        }
                    });

                    sendMessage({
                        type: 'action',
                        data: {
                            action_type: 'discard',
                            params: { card_index: lowestIndex }
                        }
                    });
                } else if (gameState.turn_subphase === "PLAY") {
                    // Play the remaining card to a random character
                    const hand = currentPlayer.hand;
                    if (hand.length === 0) {
                        sendMessage({
                            type: 'action',
                            data: { action_type: 'end_turn', params: {} }
                        });
                        return;
                    }

                    const card = hand[0]; // Should only be 1 card left

                    if (card.is_face) {
                        // Play face card to random character slot
                        const availableSlots = [];
                        for (let i = 0; i < currentPlayer.characters.length; i++) {
                            availableSlots.push(i);
                        }
                        // Can also create new character if under max
                        if (currentPlayer.characters.length < gameState.max_characters) {
                            availableSlots.push(currentPlayer.characters.length);
                        }

                        const randomSlot = availableSlots[Math.floor(Math.random() * availableSlots.length)];

                        sendMessage({
                            type: 'action',
                            data: {
                                action_type: 'play',
                                params: {
                                    card_index: 0,
                                    character_index: randomSlot
                                }
                            }
                        });
                    } else {
                        // Number card, play to random existing character
                        if (currentPlayer.characters.length === 0) {
                            // No characters to play to, shouldn't happen but handle it
                            sendMessage({
                                type: 'action',
                                data: { action_type: 'end_turn', params: {} }
                            });
                            return;
                        }

                        const randomChar = Math.floor(Math.random() * currentPlayer.characters.length);
                        sendMessage({
                            type: 'action',
                            data: {
                                action_type: 'play',
                                params: {
                                    card_index: 0,
                                    character_index: randomChar
                                }
                            }
                        });
                    }
                }
        } catch (err) {
            console.error("[AutoPlay] Error:", err);
            if (setError) setError(`AutoPlay error: ${err.message}`);
            setAutoPlaying(false);
        }
    };

    // Auto-continue if in auto-play mode
    React.useEffect(() => {
        if (!autoPlaying) return;

        if (gameState.phase === 2) {
            // Phase 1 complete, stop auto-playing
            setAutoPlaying(false);
            if (setError) setError("✅ Phase 1 complete! Now entering Phase 2");
            return;
        }

        if (gameState.phase === 1 && isMyTurn) {
            // Small delay to let state settle
            const timer = setTimeout(() => {
                autoPlayPhase1Turn();
            }, 400);
            return () => clearTimeout(timer);
        }
    }, [gameState, autoPlaying, isMyTurn]);

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
                        {isTestMode && !autoPlaying && (
                            <Button
                                onClick={() => setAutoPlaying(true)}
                                variant="ghost"
                                className="test-mode-btn"
                                style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}
                            >
                                ⚡ Skip Phase 1 (Test Mode)
                            </Button>
                        )}
                        {autoPlaying && (
                            <div className="auto-playing-indicator">
                                ⚡ Auto-playing Phase 1...
                            </div>
                        )}
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

        // Phase 2 Battle Controls
        if (gameState.phase === 2) {
            if (gameState.turn_subphase === "BATTLE_ACTION") {
                const selectedChar = selectedCharIndex !== null ? myPlayer.characters[selectedCharIndex] : null;
                const selectedCards = selectedChar ? selectedStackIndices.map(i => selectedChar.stack[i]) : [];
                const availableSuits = selectedCards.length > 0
                    ? [...new Set(selectedCards.map(c => c.suit))]
                    : [];

                return (
                    <div className="phase-controls phase2-battle">
                        <h3>Battle Phase</h3>
                        {targetMode ? (
                            <p className="instruction">🎯 {
                                targetMode === 'strike' || targetMode === 'strike_with_discard' ? 'Select opponent character to STRIKE' :
                                targetMode === 'attack' ? 'Select opponent character to ATTACK' :
                                'Select opponent character to target'
                            }</p>
                        ) : selectedChar ? (
                            <div className="battle-actions">
                                <p className="selected-char-label">
                                    Acting with: {selectedChar.rank} of {selectedChar.suit}
                                    {selectedChar.stack.length > 0 && ` (${selectedChar.stack.length} cards)`}
                                </p>

                                {selectedStackIndices.length > 0 && (
                                    <div className="selected-stack-info">
                                        <p>{selectedStackIndices.length} card(s) selected</p>
                                        <div className="suit-buttons">
                                            {availableSuits.map(suit => (
                                                <Button
                                                    key={suit}
                                                    onClick={() => handlePerformAction(suit)}
                                                    variant="primary"
                                                    className={`suit-btn suit-${suit.toLowerCase()}`}
                                                >
                                                    {suit === 'CLUBS' ? '♣' : suit === 'DIAMONDS' ? '♦' : suit === 'HEARTS' ? '♥' : '♠'} {suit}
                                                </Button>
                                            ))}
                                        </div>
                                        {/* Show face strike if ALL cards are selected */}
                                        {selectedStackIndices.length === selectedChar.stack.length && (
                                            <Button onClick={handleFaceStrike} variant="primary" className="face-strike-btn">
                                                Face Strike (discard all)
                                            </Button>
                                        )}
                                    </div>
                                )}

                                <div className="battle-action-buttons">
                                    <Button onClick={handleTapHero} disabled={selectedChar.is_tapped} variant="primary">
                                        <Zap size={16} /> Tap Hero
                                    </Button>
                                    {selectedChar.stack.length === 0 && (
                                        <Button onClick={handleFaceStrike} variant="primary">
                                            Face Strike
                                        </Button>
                                    )}
                                    <Button onClick={() => setSelectedCharIndex(null)} variant="ghost">
                                        Cancel
                                    </Button>
                                </div>
                            </div>
                        ) : (
                            <p className="instruction">Select a character to act</p>
                        )}

                        <Button onClick={handleEndTurn} variant="ghost" className="end-turn-btn">
                            End Turn
                        </Button>
                    </div>
                );
            } else if (gameState.turn_subphase === "SHOPPING" || gameState.turn_subphase === "SHOP_FREE_BUY") {
                return (
                    <div className="phase-controls phase2-shop">
                        <h3>Shopping Phase</h3>
                        <p className="instruction">
                            {targetMode === 'buy'
                                ? 'Select character to receive card'
                                : 'Click shop card, then select character'}
                        </p>
                        <Button onClick={handleEndTurn} variant="primary">
                            Done Shopping
                        </Button>
                    </div>
                );
            } else if (gameState.turn_subphase === "GRAVEDIGGING") {
                return (
                    <div className="phase-controls phase2-gravedig">
                        <h3>Gravedigging</h3>
                        <p className="instruction">Spades power: Select cards from gravedig pool</p>
                        <Button onClick={handleEndTurn} variant="primary">
                            Confirm Selection
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

            {/* Victory Screen */}
            {gameState.is_over && (
                <VictoryScreen
                    gameState={gameState}
                    user={user}
                    sendMessage={sendMessage}
                />
            )}

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
                                charIndex={i}
                                onStackClick={() => handleCharacterClick(i)}
                                onCardClick={(cardIndex) => handleStackCardClick(i, cardIndex)}
                                isTargetable={
                                    (gameState.turn_subphase === 'PLAY' && selectedHandIndices.length === 1) ||
                                    (gameState.phase === 2 && (targetMode === 'buy' || !targetMode))
                                }
                                isSelected={selectedCharIndex === i}
                                selectedStackIndices={selectedCharIndex === i ? selectedStackIndices : []}
                                phase={gameState.phase}
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
                        isShoppingPhase={isMyTurn && (gameState.turn_subphase === 'SHOPPING' || gameState.turn_subphase === 'SHOP_FREE_BUY')}
                        onBuyCard={(slotIndex) => {
                            setSelectedShopSlot(slotIndex);
                            setTargetMode('buy');
                            if (setError) setError("Now select a character to receive this card");
                        }}
                        selectedSlot={selectedShopSlot}
                    />
                </div>

                {/* Right: Opponent Viewer */}
                <div className="actions-history-sidebar">
                    {!selectedOpponentId ? (
                        /* List View */
                        <>
                            <h3>Opponents</h3>
                            <div className="opponents-list">
                                {opponents.map((opp) => (
                                    <div
                                        key={opp.id}
                                        className="opponent-list-item"
                                        onClick={() => setSelectedOpponentId(opp.id)}
                                    >
                                        <div className="opp-list-header">
                                            <Users size={16} /> <strong>{opp.name}</strong>
                                        </div>
                                        <div className="opp-list-stats">
                                            {opp.hand.length} cards | 🪙 {opp.coins} | {opp.characters.length} chars
                                        </div>
                                        <div className="opp-list-chars-preview">
                                            {opp.characters.map((c, idx) => (
                                                <div key={idx} className="opp-char-mini">
                                                    {gameState.phase === 1 ? (
                                                        <div className="mini-char-back">?</div>
                                                    ) : (
                                                        <div className="mini-char-face" title={`${c.rank} of ${c.suit}`}>
                                                            {c.rank.slice(0, 1)}
                                                            {c.suit === 'CLUBS' ? '♣' : c.suit === 'DIAMONDS' ? '♦' : c.suit === 'HEARTS' ? '♥' : '♠'}
                                                        </div>
                                                    )}
                                                    {c.stack.length > 0 && (
                                                        <div className="mini-stack-count">{c.stack.length}</div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </>
                    ) : (
                        /* Detail View - Show selected opponent's characters */
                        (() => {
                            const selectedOpp = opponents.find(o => o.id === selectedOpponentId);
                            if (!selectedOpp) return null;

                            return (
                                <>
                                    <div className="opp-detail-header">
                                        <Button
                                            variant="ghost"
                                            onClick={() => setSelectedOpponentId(null)}
                                            className="opp-back-btn"
                                        >
                                            <ArrowLeft size={16} /> Back
                                        </Button>
                                        <h3>Opponent - {selectedOpp.name}</h3>
                                        <div className="opp-nav-arrows">
                                            <Button
                                                variant="ghost"
                                                onClick={() => navigateOpponent('prev')}
                                                className="opp-nav-btn"
                                            >
                                                <ChevronLeft size={16} />
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                onClick={() => navigateOpponent('next')}
                                                className="opp-nav-btn"
                                            >
                                                <ChevronRight size={16} />
                                            </Button>
                                        </div>
                                    </div>
                                    <div className="opp-detail-stats">
                                        {selectedOpp.hand.length} cards | 🪙 {selectedOpp.coins}
                                    </div>
                                    <div className="characters-scroll-list">
                                        {selectedOpp.characters.map((char, charIndex) => (
                                            <CharacterStack
                                                key={char.uid}
                                                character={char}
                                                charIndex={charIndex}
                                                onStackClick={() => targetMode && handleOpponentCharClick(selectedOpp.id, charIndex)}
                                                isTargetable={targetMode !== null}
                                                phase={gameState.phase}
                                                isOpponent={true}
                                            />
                                        ))}
                                    </div>
                                </>
                            );
                        })()
                    )}
                </div>
            </div>

            {/* Fixed Bottom: Player Hand (only shown in Phase 1) */}
            {gameState.phase === 1 && (
                <PlayerHand
                    hand={myPlayer.hand}
                    selectedIndices={selectedHandIndices}
                    onCardClick={handleCardClick}
                />
            )}
        </div>
    );
};

export default GameBoard;
