Spade card actions seem totally broken right now.

Using a spade action on a character seems to delete that character's entire card stack up to the face card. It doesn't even discard these cards, they just disappear from the game entirely.

As per the official rules, the appropriate behavior for spade actions should be:
- Find the value of the spades action- the sum of the ranks of all spade cards played/discarded in that action.
- Count up that value from the "top" of the target character's stack. These cards are flagged.
- Of the flagged cards, the player effectively repeats their turn, but are no longer required to discard a block of cards from the top of the stack- they are instead permitted to choose any of the flagged cards to discard towards their next action- including another spade action.
- This simulates using the spade action to "dig through" the target character's stack to find better cards to discard for future actions, rather than just deleting a block of cards from the top of the stack.
- Note that if the spade action value exceeds the number of cards in the target character's stack, all cards in that stack are flagged, allowing you to pick and choose from the entire stack for your next action. If you can dig all the way to your character's face card, you may even perform a face strike as your next action.

I think it would be helpful to have some sort of visual indicator on the frontend to show which cards are available to be dug up for the next action after a spade action is performed. Maybe a glowing green border, which is distinct from the glowing blue border used to indicate selected cards for the current action.

Please ensure that when selecting flagged cards, you do not have to select them in a block from the top of the stack- you should be able to pick and choose any of the flagged cards individually.