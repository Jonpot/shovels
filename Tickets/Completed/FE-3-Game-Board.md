# FE-3: Frontend Game Board

Implement the core game board interface and interactions.

## 1. Game Board Layout
- [ ] Create `GameBoard` component structure
    - [ ] `PlayerArea` (Self)
    - [ ] `OpponentArea` (x3 max)
    - [ ] `DecksArea` (Deck, Discard)
    - [ ] `ShopRow` (Shared pool)
- [ ] Style the board using the Design System

## 2. Phase 1 Mechanics (Setup)
- [ ] **Draw Phase UI**
    - [ ] Logic to highlight Deck/Discard based on validity
    - [ ] Click handlers to send `draw_cards` action
- [ ] **Discard Phase UI**
    - [ ] UI to select card from hand
    - [ ] Click handler to send `discard_card` action
- [ ] **Play Phase UI**
    - [ ] Drag-and-drop or Click-to-Select for playing cards to Characters
    - [ ] Handler for `play_card` action

## 3. Phase 2 Mechanics (Battle)
- [ ] **Action Menu**
    - [ ] Context menu on Character click (Attack, Tap, Strike)
- [ ] **Hand Action UI**
    - [ ] Select multiple cards from character stack
    - [ ] Select Suit and Target
- [ ] **Subphase UI**
    - [ ] **Shopping**: Click shop card -> Select character
    - [ ] **Gravedigging**: Modal to select cards from pool

## 4. State Sync & Animation
- [ ] Handle `state_update` to re-render board
- [ ] Add basic animations (cards flying to hand/stack)
