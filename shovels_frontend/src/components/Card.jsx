import React from 'react';
import './Card.css';

const SuitIcon = ({ suit }) => {
    if (!suit) return null;
    switch (suit.toLowerCase()) {
        case 'hearts':
            return (
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
                </svg>
            );
        case 'diamonds':
            return (
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2L3.5 12 12 22l8.5-10L12 2z" />
                </svg>
            );
        case 'spades':
            return (
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C12 2 17.5 7.5 17.5 11C17.5 13.5 15.5 15.5 13 15.5C12.2 15.5 11.5 15.3 10.9 14.9C10.3 15.3 9.6 15.5 8.8 15.5C6.3 15.5 4.3 13.5 4.3 11C4.3 7.5 9.8 2 9.8 2L12 2ZM11 16L8 22H16L13 16H11Z" />
                </svg>
            );
        case 'clubs':
            return (
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <circle cx="12" cy="8.5" r="3.5" />
                    <circle cx="8" cy="14.5" r="3.5" />
                    <circle cx="16" cy="14.5" r="3.5" />
                    <rect x="11" y="15" width="2" height="6" />
                    <path d="M10 21h4v-1h-4v1z" />
                </svg>
            );
        default:
            return null;
    }
};

const PipLayout = ({ rank, suit }) => {
    const count = parseInt(rank) || 0;
    if (count === 0) return null;

    const pips = Array.from({ length: count });

    return (
        <div className={`pip-container rank-${rank}`}>
            {pips.map((_, i) => (
                <div key={i} className="pip">
                    <SuitIcon suit={suit} />
                </div>
            ))}
        </div>
    );
};

const Card = ({ rank, suit, isFaceUp = true, className = '' }) => {
    const isRed = suit && (suit.toLowerCase() === 'hearts' || suit.toLowerCase() === 'diamonds');
    const isFaceCard = ['J', 'Q', 'K'].includes(rank);
    const isAce = rank === 'A';

    if (!isFaceUp) {
        return (
            <div className={`shovels-card card-back ${className}`}>
                <div className="card-pattern"></div>
            </div>
        );
    }

    // Map face cards to their specific suit images
    const getFaceImage = (r, s) => {
        const rankMap = { 'J': 'jack', 'Q': 'queen', 'K': 'king' };
        const fileName = `${rankMap[r]} of ${s.toLowerCase()}.png`;
        return new URL(`../assets/faces/${fileName}`, import.meta.url).href;
    };

    return (
        <div className={`shovels-card ${isRed ? 'red' : 'black'} ${className} ${isFaceCard ? 'face-card' : ''}`}>
            <div className="card-corner top-left">
                <span className="card-rank">{rank}</span>
                <div className="card-suit-mini"><SuitIcon suit={suit} /></div>
            </div>

            <div className="card-center">
                {isFaceCard ? (
                    <img src={getFaceImage(rank, suit)} alt={`${rank} of ${suit}`} className="face-art-placeholder" />
                ) : isAce ? (
                    <div className="ace-center">
                        <SuitIcon suit={suit} />
                    </div>
                ) : (
                    <PipLayout rank={rank} suit={suit} />
                )}
            </div>

            <div className="card-corner bottom-right">
                <span className="card-rank">{rank}</span>
                <div className="card-suit-mini"><SuitIcon suit={suit} /></div>
            </div>
        </div>
    );
};

export default Card;
