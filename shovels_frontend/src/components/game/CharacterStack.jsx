import React from 'react';
import { motion } from 'framer-motion';
import Card from '../Card';
import './CharacterStack.css';

const CharacterStack = ({
    character,
    charIndex,
    onStackClick,
    onCardClick,
    isTargetable,
    isSelected,
    selectedStackIndices = [],
    phase = 1,
    isOpponent = false
}) => {
    // character: { rank, suit, stack: [cards], is_tapped, shield }
    const [mousePos, setMousePos] = React.useState({ x: 0, y: 0 });
    const [isHovering, setIsHovering] = React.useState(false);
    const containerRef = React.useRef(null);

    const handleCardClick = (e, cardIndex) => {
        if (phase === 2 && onCardClick) {
            e.stopPropagation(); // Prevent character click
            onCardClick(cardIndex);
        }
    };

    // Track mouse position for parallax effect
    const handleMouseMove = (e) => {
        if (!containerRef.current) return;
        const rect = containerRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        setMousePos({ x, y });
    };

    const handleMouseEnter = () => {
        setIsHovering(true);
    };

    const handleMouseLeave = () => {
        setIsHovering(false);
        setMousePos({ x: 0, y: 0 });
    };

    // Calculate parallax offset based on mouse position
    // Mouse at bottom = stack moves up significantly
    const calculateParallaxOffset = () => {
        if (!isHovering || !containerRef.current) return 0;

        const rect = containerRef.current.getBoundingClientRect();
        const containerHeight = rect.height;
        const normalizedY = mousePos.y / containerHeight; // 0 to 1

        // When mouse is at bottom (normalizedY = 1), offset is large negative
        // When mouse is at top (normalizedY = 0), offset is 0
        // Multiply by stack length for stronger effect on longer stacks
        const stackMultiplier = Math.min(character.stack.length * 0.5, 4); // Cap the multiplier
        const offset = -normalizedY * 150 * stackMultiplier;

        return offset;
    };

    const parallaxOffset = calculateParallaxOffset();

    // Show hidden card back for opponent characters in Phase 1
    const showHidden = isOpponent && phase === 1;

    // Handle dead characters (FIX-6)
    if (character.is_dead) {
        return (
            <motion.div
                ref={containerRef}
                className={`character-stack-container dead-character ${isTargetable ? 'targetable' : ''} ${isSelected ? 'selected' : ''}`}
                onClick={onStackClick}
            >
                <div className="character-base">
                    <div className="character-card dead" style={{ zIndex: 1 }}>
                        <div className="dead-char-placeholder">
                            <div className="skull-icon">💀</div>
                            <div className="dead-label">Empty Slot</div>
                        </div>
                    </div>
                </div>
            </motion.div>
        );
    }

    return (
        <motion.div
            ref={containerRef}
            className={`character-stack-container ${isTargetable ? 'targetable' : ''} ${isSelected ? 'selected' : ''} ${character.is_tapped ? 'tapped' : ''}`}
            onClick={onStackClick}
            onMouseMove={handleMouseMove}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
        >
            <div className="character-base">
                <div className="character-card" style={{ zIndex: 1 }}>
                    {showHidden ? (
                        <div className="char-back-card">
                            <div className="char-back-symbol">?</div>
                        </div>
                    ) : (
                        <Card rank={character.rank} suit={character.suit} isFace={true} faceRank={character.rank} />
                    )}
                    {character.is_tapped && (
                        <div className="tapped-overlay">TAP</div>
                    )}
                </div>

                {/* Vertical Stack on top */}
                <div
                    className="stack-layered"
                    style={{
                        zIndex: 2,
                        transform: isHovering ? `translateY(${parallaxOffset}px)` : 'translateY(0)',
                        transition: 'transform 0.1s ease-out'
                    }}
                >
                    {character.stack.map((card, i) => {
                        const isCardSelected = selectedStackIndices.includes(i);
                        // FIX-5: Check if card is dug (available for gravedigging)
                        const isDugCard = character.dug_cards && character.dug_cards.some(dc => dc.uid === card.uid);
                        return (
                            <motion.div
                                key={card.uid}
                                className={`stacked-card-wrapper ${isCardSelected ? 'card-selected' : ''} ${isDugCard ? 'dug-card' : ''} ${phase === 2 && isSelected ? 'clickable' : ''}`}
                                style={{
                                    zIndex: i + 2,
                                    top: `${(i + 1) * 20}px`,
                                    '--stack-index': i + 1
                                }}
                                onClick={(e) => handleCardClick(e, i)}
                                initial={{ x: '-50%' }}
                                whileHover={phase === 2 && isSelected ? {
                                    x: '-50%',
                                    zIndex: 100,
                                    scale: 1.25,
                                    transition: { duration: 0.15 }
                                } : {
                                    x: '-50%',
                                    zIndex: 100,
                                    scale: 1.2,
                                    transition: { duration: 0.15 }
                                }}
                            >
                                <Card
                                    rank={card.rank}
                                    suit={card.suit}
                                    isFace={card.is_face}
                                    faceRank={card.face_rank}
                                    isAce={card.is_ace}
                                />
                                {isCardSelected && (
                                    <div className="selected-card-overlay">✓</div>
                                )}
                            </motion.div>
                        );
                    })}
                </div>

                {character.shield > 0 && (
                    <div className="shield-display">
                        🛡️ {character.shield}
                    </div>
                )}
            </div>
        </motion.div>
    );
};

export default CharacterStack;
