import React from 'react';
import Card from '../Card';
import './ShopRow.css';

const ShopRow = ({ shopCards, coins, onBuyCard, isShoppingPhase }) => {
    return (
        <div className="shop-row">
            <div className="shop-label">SHOP</div>
            <div className="shop-cards-container">
                {shopCards.map((card, index) => (
                    <div
                        key={card ? card.uid : `empty-${index}`}
                        className={`shop-slot ${card ? 'filled' : 'empty'} ${isShoppingPhase && card && coins >= 3 ? 'buyable' : ''}`}
                        onClick={() => card && onBuyCard(index)}
                    >
                        {card ? (
                            <>
                                <Card
                                    rank={card.rank}
                                    suit={card.suit}
                                    isFace={card.is_face}
                                    faceRank={card.face_rank}
                                    isAce={card.is_ace}
                                />
                                <div className="price-tag">3 🪙</div>
                            </>
                        ) : (
                            <div className="empty-slot-placeholder" />
                        )}
                    </div>
                ))}
            </div>
            <div className="coin-display">
                <span className="coin-icon">🪙</span> {coins}
            </div>
        </div>
    );
};

export default ShopRow;
