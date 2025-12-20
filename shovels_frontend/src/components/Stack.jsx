import React from 'react';
import './Stack.css';
import Card from './Card';

const Stack = ({ cards, className = '' }) => {
    return (
        <div className={`shovels-stack ${className}`}>
            {cards.map((card, index) => (
                <div
                    key={`${card.suit}-${card.rank}-${index}`}
                    className="stack-card-wrapper"
                    style={{
                        '--card-index': index,
                        zIndex: index
                    }}
                >
                    <Card rank={card.rank} suit={card.suit} />
                </div>
            ))}
        </div>
    );
};

export default Stack;
