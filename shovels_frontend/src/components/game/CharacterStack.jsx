import React from 'react';
import { motion } from 'framer-motion';
import Card from '../Card';
import './CharacterStack.css';

const CharacterStack = ({ character, onStackClick, isTargetable, isSelected }) => {
    // character: { rank, suit, stack: [cards], is_tapped, shield }

    return (
        <motion.div
            className={`character-stack-container ${isTargetable ? 'targetable' : ''} ${isSelected ? 'selected' : ''} ${character.is_tapped ? 'tapped' : ''}`}
            onClick={onStackClick}
        >
            <div className="character-base">
                <div className="character-card" style={{ zIndex: 1 }}>
                    <Card rank={character.rank} suit={character.suit} isFace={true} faceRank={character.rank} />
                    {character.is_tapped && (
                        <div className="tapped-overlay">TAP</div>
                    )}
                </div>

                {/* Vertical Stack on top */}
                <div className="stack-layered" style={{ zIndex: 2 }}>
                    {character.stack.map((card, i) => (
                        <motion.div
                            key={card.uid}
                            className="stacked-card-wrapper"
                            style={{
                                zIndex: i + 2,
                                top: `${(i + 1) * 20}px`, // Default shift down
                                '--stack-index': i + 1
                            }}
                            initial={{ x: '-50%' }}
                            whileHover={{
                                x: '-50%',
                                zIndex: 100,
                                scale: 1.05,
                                transition: { duration: 0.2 }
                            }}
                        >
                            <Card
                                rank={card.rank}
                                suit={card.suit}
                                isFace={card.is_face}
                                faceRank={card.face_rank}
                                isAce={card.is_ace}
                            />
                        </motion.div>
                    ))}
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
