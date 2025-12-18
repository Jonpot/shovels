# GYM-1: Environment Wrapper

## Goal
Create a Gymnasium-compatible environment for RL training.

## Prerequisites
- [CORE-5: Game Loop & Conditions](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/CORE-5-Game-Loop.md)

## Description
- Create `shovels_gym/envs/shovels_env.py`.
- **Observation Space:** Use a `Dict` space for the first iteration:
  - `active_player_state`: Box/MultiDiscrete representing stacks, health (Heart counts), and coins.
  - `opponent_states`: Array of states for other players.
  - `shop_row`: MultiDiscrete of 3 cards.
  - `visible_discard`: Top card of discard pile.
- **Action Space:** `Discrete` or `MultiDiscrete`:
  - `action_type`: (0: Action Hand, 1: Hero Power, 2: Shop Buy, 3: Shop Refresh, 4: Face Strike).
  - `target_indices`: MultiDiscrete for cards/players.
- **Step Function:** Map Gym actions to Engine calls.
- **Reward Function:** 
  - +1 for winning game.
  - +0.1 for killing an opponent's card.
  - -0.01 per turn (to encourage efficiency).
  - -1 for losing character.

## Definition of Done
- `gymnasium` environment that passes `check_env`.
- Observation and Action spaces well-documented.
