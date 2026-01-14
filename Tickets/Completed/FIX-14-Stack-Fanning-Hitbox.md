# FIX-14: Stack Fanning Hitbox Extension

## Goal
Extend the hover hitbox for stack fanning to cover the full visible stack area.

## User Reports
- BUG-16: Stack fanning hitbox is too small. Mouse can be fully over the bottom card of a stack but fanning doesn't trigger. Causes flickering between zoomed and compressed states.

## Description
**Current Behavior:**
- Stack fanning only triggers when hovering over specific area (likely just top card)
- Bottom cards in a compressed stack don't trigger the fan
- Results in glitchy flickering behavior as mouse moves over stack
- Poor UX when trying to inspect stacked cards

**Correct Behavior:**
- Hovering anywhere on the visible stack should trigger fanning
- Hitbox should extend from topmost visible card to bottommost visible card
- Smooth transition into fanned state without flickering
- Mouse leaving the entire fanned area should collapse the stack

## Technical Approach
**Frontend (`shovels_frontend/src/components/game/Stack.jsx` or similar):**

1. **Identify Current Hover Implementation:**
   - Find the hover event handlers for stack fanning
   - Check if hover is on individual cards vs container
   - Understand the current hitbox boundaries

2. **Extend Hitbox:**
   - Wrap entire stack in a container div that handles hover
   - Container should encompass full rendered height of stack
   - Use `onMouseEnter`/`onMouseLeave` on container, not individual cards

3. **Prevent Flickering:**
   - Add slight delay before collapsing (debounce)
   - Ensure fanned state hitbox is at least as large as compressed state
   - Consider using CSS `pointer-events` strategically

4. **Implementation Options:**
   - **Option A:** Invisible overlay div sized to full stack bounds
   - **Option B:** Container div with calculated height based on card count
   - **Option C:** Use CSS `::before` pseudo-element for extended hit area

```jsx
// Example approach
<div
  className="stack-container"
  style={{ height: calculateStackHeight(cards.length) }}
  onMouseEnter={() => setIsHovered(true)}
  onMouseLeave={() => setIsHovered(false)}
>
  {cards.map((card, i) => <Card key={i} ... />)}
</div>
```

## Definition of Done
- Hovering anywhere on visible stack triggers fanning
- No flickering when moving mouse over stack
- Smooth transitions between compressed and fanned states
- Works consistently across all character stacks
- Mouse must fully leave stack area to collapse
