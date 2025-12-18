# Shovels Technical Specification

This document serves as the source of truth for all "Shovels" game mechanics, constants, and data models.

## 1. Game Constants

### Deck Composition
- **Total Decks**: 2 Standard 52-card decks (104 cards total).
- **Ranks**: 2–10 (Face value), Ace = 10.
- **Faces**: Jack (J), Queen (Q), King (K).
- **Suits**: Clubs (♣), Diamonds (♦), Hearts (♥), Spades (♠).

### Setup Values
- **Initial Characters**: 3 per player (drawn from Jacks, Queens, Kings).
- **Shop Pile**: 20 cards set aside face-down.
- **Shop Row**: 3 cards face-up.
- **Max Characters**: 3 per player (unless "Mass Armies" variant is active).

## 2. Core Data Models

### Card
- `rank`: Integer (2-10)
- `suit`: Enum (CLUBS, DIAMONDS, HEARTS, SPADES)
- `is_face`: Boolean

### Character
- `rank`: Enum (JACK, QUEEN, KING)
- `suit`: Enum (CLUBS, DIAMONDS, HEARTS, SPADES)
- `stack`: List[Card] (Top card is index -1)
- `is_tapped`: Boolean

### Player
- `id`: String
- `name`: String
- `characters`: List[Character]
- `coins`: Integer (Transient, only during Diamonds action)
- `is_alive`: Boolean

## 3. Phase Mechanics

### Phase 1: Character Creation
- **Turn**: Draw 2 (Deck or Discard), Discard 1, Play 1.
- **Play Logic**:
  - Number card -> Top of any owned character stack.
  - Face card -> Replace existing face card (discard old face) OR discard new face.
- **End Condition**: Deck empty + equal turns.
- **First Player Phase 2**: Owner of highest-rank Spade in any stack (Ace > 10...2).

### Phase 2: Battle
- **Action Hand**: Lift $N$ cards from top. Select 1 suit present.
  - **Clubs (Attack)**: $D = \sum Rank$. Target Heart rank $H$. If $D \ge H$, discard Heart + all cards above.
  - **Diamonds (Coins)**: $C = \sum Rank$. Spend $C$ in Shop.
  - **Hearts (Stall)**: Pass turn.
  - **Spades (Shovel)**: $D = \sum Rank$. Dig $D$ cards, form new action hand from any subset.
- **Free Face-Strike**: 1 damage. Must be top card or dug to. Must result in card removal. No tap/discard.
- **Must-Act Rule**: Every turn must result in a discard (Action Hand), a Power Tap, or a successful Face-Strike. Otherwise, the player must discard one of their own face cards (Character dies).

## 4. Hero Powers (Tap Once per Life)

| Suit | Jack | Queen | King |
| :--- | :--- | :--- | :--- |
| **Clubs** | 1x10 dmg | 2x10 dmg (diff targets) | 3x10 dmg (diff targets) |
| **Diamonds** | 1 Free Card | 2 Free Cards | 3 Free Cards |
| **Spades** | Draw 5, Keep 1 | Draw 5, Keep 2 | Draw 5, Keep 3 |
| **Hearts** | +3 Shield (Out-of-turn) | +5 Shield | +10 Shield |

## 5. Shop Prices
- **Number Card**: Rank (Ace = 10)
- **Jack**: 3 coins
- **Queen**: 4 coins
- **King**: 5 coins
- **Refresh Row**: 2 coins
