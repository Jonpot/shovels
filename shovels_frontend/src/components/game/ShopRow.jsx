import React from 'react';
import Card from '../Card';
import './ShopRow.css';

const ShopRow = ({ shopCards, coins, onBuyCard, isShoppingPhase, selectedSlot }) => {
    const getCardPrice = (card) => {
        if (!card) return 0;
        if (card.is_face && card.face_rank) {
            return { 'J': 3, 'Q': 4, 'K': 5 }[card.face_rank];
        }
        return card.is_ace ? 10 : card.rank;
    };

    return (
        <div className="shop-row">
            <div className="shop-label">SHOP</div>
            <div className="shop-cards-container">
                {shopCards.map((card, index) => {
                    const price = getCardPrice(card);
                    return (
                        <div
                            key={card ? card.uid : `empty-${index}`}
                            className={`shop-slot ${card ? 'filled' : 'empty'} ${isShoppingPhase && card && coins >= price ? 'buyable' : ''} ${selectedSlot === index ? 'selected-shop' : ''}`}
                            onClick={() => card && isShoppingPhase && onBuyCard(index)}
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
                                    <div className="price-tag">{price} 🪙</div>
                                </>
                            ) : (
                                <div className="empty-slot-placeholder" />
                            )}
                        </div>
                    );
                })}
            </div>
            <div className="coin-display">
                <span className="coin-icon">🪙</span> {coins}
            </div>
        </div>
    );
};

export default ShopRow;
