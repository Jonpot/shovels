# GYM-2: Training Pipeline

## Goal
Set up a script to train RL agents using the Gymnasium environment.

## Prerequisites
- [GYM-1: Environment Wrapper](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/GYM-1-Env-Wrapper.md)

## Description
- Use `Stable Baselines3` (SB3).
- Implement `shovels_gym/train.py`.
- Setup a training loop for PPO (Proximal Policy Optimization).
- Include EvaluationCallback to track win rate against a Random policy.
- Model saving/loading logic.

## Definition of Done
- Script that runs training for N steps and saves a `.zip` model.
- Documented win-rate improvement over a random agent.
