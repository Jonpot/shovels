import React from 'react';
import Card from '../Card';
import './ShopRow.css';

const ShopRow = ({ shopCards, coins, onBuyCard, onRefreshShop, isShoppingPhase, selectedSlot, freeBuysRemaining }) => {
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
                                    <div className="price-tag">{price} G</div>
                                </>
                            ) : (
                                <div className="empty-slot-placeholder" />
                            )}
                        </div>
                    );
                })}
            </div>
            <div className="shop-controls">
                {isShoppingPhase && freeBuysRemaining !== undefined && freeBuysRemaining > 0 && (
                    <div className="free-buys-indicator">
                        Free Purchases Remaining: {freeBuysRemaining}
                    </div>
                )}
                {isShoppingPhase && !freeBuysRemaining && onRefreshShop && (
                    <button
                        className="refresh-shop-button"
                        onClick={onRefreshShop}
                        disabled={coins < 2}
                        title={coins < 2 ? "Need 2 coins to refresh" : "Refresh shop for 2 coins"}
                    >
                        Refresh Shop (2 G)
                    </button>
                )}
                <div className="coin-display">
                    <span className="coin-icon">G</span> {coins}
                </div>
            </div>
        </div>
    );
};

export default ShopRow;
