import React from 'react';
import './Card.css';

const SuitIcon = ({ suit }) => {
    if (!suit) return null;
    switch (suit.toLowerCase()) {
        case 'hearts':
            return (
                <svg viewBox="300 357 216 242" fill="currentColor">
                    <path d="M 352.8827,357.0625 C 314.8623,357.0625 300.05446,382.83029 300.05446,404.94657 C 300.05446,473.68557 361.30309,555.43738 408.18327,599.0625 C 455.0631,555.43738 516.25824,473.68557 516.25824,404.94657 C 516.25824,382.83029 501.45023,357.0625 463.42998,357.0625 C 432.79932,357.0625 413.07369,377.65274 413.07369,398.82 C 413.07369,405.21367 415.04039,412.95412 408.18327,412.95412 C 401.32596,412.95412 403.23901,405.21367 403.23901,398.82 C 403.23901,377.65274 383.51321,357.0625 352.8827,357.0625 z" />
                </svg>
            );
        case 'diamonds':
            return (
                <svg viewBox="308 352 200 252" fill="currentColor">
                    <path d="M 408.15635,352.45099 C 385.76859,400.21284 352.76072,442.26342 308.15635,478.0625 C 352.76072,513.86156 385.76859,555.91215 408.15635,603.674 C 430.54411,555.91215 463.55198,513.86156 508.15635,478.0625 C 463.55198,442.26342 430.54411,400.21284 408.15635,352.45099 z" />
                </svg>
            );
        case 'spades':
            return (
                <svg viewBox="320 349 200 249" fill="currentColor">
                    <path d="M 420.37498,349.55102 C 360.40052,390.08152 320.37505,467.57634 320.375,514.71623 C 320.375,539.21657 340.29885,560.81235 366.92151,560.81235 C 388.48053,560.81235 406.86151,541.23743 406.86146,514.26579 C 406.86146,510.20054 408.9958,508.40994 410.76536,508.40994 C 413.08604,508.40994 415.42002,511.71285 415.42002,518.01954 C 415.42002,533.65083 407.57185,573.31705 396.95155,597.44898 C 403.08128,595.63666 411.25603,593.8454 420.37498,593.8454 C 429.49402,593.8454 437.81882,595.63666 443.94856,597.44898 C 433.32825,573.31705 425.48008,533.65083 425.48008,518.01954 C 425.48008,511.71285 427.81406,508.40994 430.13474,508.40994 C 431.9043,508.40994 433.88849,510.20054 433.88849,514.26579 C 433.88854,541.23743 452.41957,560.81235 473.97859,560.81235 C 500.60125,560.81235 520.375,539.21657 520.375,514.71623 C 520.37505,467.57634 480.34948,390.08152 420.37498,349.55102 z" />
                </svg>
            );
        case 'clubs':
            return (
                <svg viewBox="289 368 238 220" fill="currentColor">
                    <path d="M 408.15639,368.79905 C 379.39014,368.79906 356.02769,392.16149 356.02769,420.92775 C 356.02772,441.41782 367.85955,459.15021 385.07688,467.65086 C 390.25818,470.20901 384.60395,476.8313 380.79941,472.53939 C 371.24485,461.76088 357.31062,454.95947 341.78513,454.95947 C 313.01888,454.95946 289.65635,478.32191 289.65635,507.08817 C 289.65635,535.85443 313.01903,559.16987 341.78513,559.16987 C 370.33092,559.16987 393.61306,536.20881 393.91384,507.74624 C 393.96721,502.69704 401.7167,502.17398 401.7167,508.96838 C 401.7167,519.66771 391.43054,576.49172 385.92297,587.32595 C 391.9345,585.8101 401.95338,584.55266 408.15639,584.55265 C 414.35941,584.55266 424.37829,585.8101 430.38982,587.32595 C 424.88225,576.49172 414.59609,519.66771 414.59609,508.96838 C 414.59609,502.17398 422.34558,502.69704 422.39895,507.74624 C 422.69973,536.20881 445.98193,559.16987 474.52765,559.16987 C 503.29392,559.16987 526.65632,535.85443 526.65635,507.08817 C 526.65635,478.32191 503.29392,454.95946 474.52765,454.95947 C 459.00226,454.95947 445.06794,461.76088 435.51338,472.53939 C 431.70884,476.8313 426.05461,470.20901 431.23591,467.65086 C 448.45324,459.15021 460.28507,441.41782 460.28509,420.92775 C 460.28509,392.16149 436.92265,368.79906 408.15639,368.79905 z" />
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

const Card = ({ rank, suit, isFace = false, faceRank = null, isAce = false, isFaceUp = true, className = '' }) => {
    const isRed = suit && (suit.toLowerCase() === 'hearts' || suit.toLowerCase() === 'diamonds');
    const isFaceCard = isFace || ['J', 'Q', 'K'].includes(rank) || ['J', 'Q', 'K'].includes(faceRank);

    // Resolve what to show in the corner
    let displayRank = rank;
    if (isAce) displayRank = 'A';
    else if (isFace) displayRank = faceRank;
    else if (isFaceCard && !isFace) displayRank = rank; // Fallback if only rank "J" passed

    if (!isFaceUp) {
        return (
            <div className={`shovels-card card-back ${className}`}>
                <div className="card-pattern"></div>
            </div>
        );
    }

    const getFaceImage = (r, s) => {
        const rankMap = { 'J': 'jack', 'Q': 'queen', 'K': 'king' };
        const fileName = `${rankMap[r]} of ${s.toLowerCase()}.png`;
        return new URL(`../assets/faces/${fileName}`, import.meta.url).href;
    };

    return (
        <div className={`shovels-card ${isRed ? 'red' : 'black'} ${className} ${isFaceCard ? 'face-card' : ''}`}>
            <div className="card-corner top-left">
                <span className="card-rank">{displayRank}</span>
                <div className="card-suit-mini"><SuitIcon suit={suit} /></div>
            </div>

            <div className="card-center">
                {isFaceCard ? (
                    <img src={getFaceImage(isFace ? faceRank : rank, suit)} alt={`${displayRank} of ${suit}`} className="face-art-placeholder" />
                ) : isAce ? (
                    <div className="ace-center">
                        <SuitIcon suit={suit} />
                    </div>
                ) : (
                    <PipLayout rank={rank} suit={suit} />
                )}
            </div>

            <div className="card-corner bottom-right">
                <span className="card-rank">{displayRank}</span>
                <div className="card-suit-mini"><SuitIcon suit={suit} /></div>
            </div>
        </div>
    );
};

export default Card;
