import React from 'react';
import { motion } from 'framer-motion';
import Card from '../Card';
import './PlayerHand.css';

const PlayerHand = ({ hand, onCardClick, selectedIndices = [] }) => {
    return (
        <div className="player-hand-container">
            <div className="hand-fan">
                {hand.map((card, index) => {
                    const isSelected = selectedIndices.includes(index);

                    // Simple logic to fan cards: rotate around a center point
                    // Max rotation +/- 15 deg
                    const len = hand.length;
                    const center = (len - 1) / 2;
                    const rotate = (index - center) * 5; // 5 degrees per card
                    const y = Math.abs(index - center) * 5; // Arch effect

                    return (
                        <motion.div
                            key={card.uid}
                            className={`hand-card-wrapper ${isSelected ? 'selected' : ''}`}
                            initial={{ y: 100, opacity: 0 }}
                            animate={{
                                y: isSelected ? -30 : y,
                                rotate: rotate,
                                opacity: 1
                            }}
                            whileHover={{
                                y: -40,
                                rotate: 0,
                                zIndex: 10,
                                transition: { duration: 0.2 }
                            }}
                            onClick={() => onCardClick(index)}
                            style={{
                                zIndex: index,
                                marginLeft: index === 0 ? 0 : '-3rem' // Overlap
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
                    );
                })}
            </div>
        </div>
    );
};

export default PlayerHand;
