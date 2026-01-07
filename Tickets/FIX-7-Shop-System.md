# FIX-7: Shop System Improvements

## Goal
Add shop refresh functionality and fix auto-exit after Diamond Face tapping.

## User Reports
- BUG-4: Stuck in shop after using Diamond Face free purchases
- BUG-5: Shop missing refresh button

## Prerequisites
- [CORE-4: Hero Powers & Shop](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/Completed/CORE-4-Hero-Powers-Shop.md)

## Description
**Shop Refresh (BUG-5):**
- Currently: No way to refresh shop cards
- Required: Add "Refresh Shop" button that costs 2 coins
- When clicked, replace all 3 shop cards with new random cards from shop deck
- Can refresh multiple times per shop visit (if you have coins)

**Auto-Exit After Face Tap (BUG-4):**
- Currently: After tapping Diamond Face (J♦/Q♦/K♦), enter shop with free purchases
- Bug: After using all free purchases, stuck in shop mode
- Required: Automatically exit shop and return to battle view after last free purchase

**Key Distinction:**
- Tapping Diamond Face → limited free purchases, auto-exit after
- Discarding Diamonds cards → enter shop with coins, stay until manually exit
- These are two different shop entry modes

## Technical Approach
**Engine (`shovels_engine/engine.py`):**

1. **Shop Refresh Function:**
   ```python
   def refresh_shop(game: GameState, player_id: str) -> GameState:
       """Costs 2 coins, replaces all shop cards"""
       player = get_player(game, player_id)
       if player.coins < 2:
           raise ValueError("Not enough coins to refresh")

       player.coins -= 2
       # Return old shop cards to shop deck
       game.shop_deck.extend(game.shop_row)
       # Draw new shop row
       game.shop_row = draw_from_deck(game.shop_deck, 3)
       random.shuffle(game.shop_deck)

       return game
   ```

2. **Track Shop Entry Mode:**
   - Add `shop_entry_mode: Optional[str]` to GameState
   - Values: "FREE_PURCHASES" (from face tap) or "COIN_PURCHASES" (from diamonds)
   - Add `free_purchases_remaining: int` to GameState

3. **Auto-Exit After Free Purchases:**
   - In `buy_card()`, check if `shop_entry_mode == "FREE_PURCHASES"`
   - After purchase, decrement `free_purchases_remaining`
   - If `free_purchases_remaining == 0`, auto-exit shop (set subphase to BATTLE_ACTION)

4. **Face Tap Entry:**
   - When tapping J♦/Q♦/K♦, set:
     - `shop_entry_mode = "FREE_PURCHASES"`
     - `free_purchases_remaining = rank_value` (11/12/13)
     - `subphase = SHOPPING`

**Backend (`shovels_backend/main.py`):**
- Add WebSocket route for "refresh_shop" action
- Broadcast updated shop state after refresh

**Frontend (`shovels_frontend/src/`):**

1. **Refresh Button:**
   - Add "Refresh Shop (2 coins)" button in shop view
   - Show coin cost and disable if player has < 2 coins
   - On click, send refresh_shop action via WebSocket

2. **Shop Mode Indicator:**
   - Show "Free Purchases Remaining: X" when in FREE_PURCHASES mode
   - Auto-close shop modal when free purchases depleted
   - Show "Shopping" when in COIN_PURCHASES mode with manual exit button

## Definition of Done
- Shop refresh button costs 2 coins and replaces all cards
- After Diamond Face tap, auto-exit shop when free purchases used
- Frontend shows different UI for free vs coin purchases
- Shop deck properly cycles cards back after refresh
- Unit tests for refresh logic and auto-exit
- Integration test for full shop flow
