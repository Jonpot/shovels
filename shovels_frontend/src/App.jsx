import React from 'react'
import Button from './components/Button'
import Card from './components/Card'
import Stack from './components/Stack'

function App() {
  const sampleCards = [
    { rank: 'A', suit: 'Spades' },
    { rank: 'K', suit: 'Hearts' },
    { rank: 'Q', suit: 'Diamonds' },
    { rank: 'J', suit: 'Clubs' },
    { rank: '10', suit: 'Spades' },
  ];

  const pipCards = [
    { rank: '2', suit: 'Hearts' },
    { rank: '5', suit: 'Diamonds' },
    { rank: '7', suit: 'Spades' },
    { rank: '10', suit: 'Clubs' },
  ];

  const faceShowcase = [
    { rank: 'K', suit: 'Hearts' },
    { rank: 'Q', suit: 'Diamonds' },
    { rank: 'J', suit: 'Clubs' },
    { rank: 'J', suit: 'Spades' },
  ];

  return (
    <div className="layout-root">
      <aside className="sidebar">
        <div>
          <h1 style={{ color: 'var(--primary-gold)', marginBottom: '0.5rem' }}>SHOVELS</h1>
          <p className="section-title">Design System</p>
        </div>
        <nav>
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <li style={{ color: 'var(--primary-gold)', fontWeight: 600, cursor: 'pointer' }}>Style Guide</li>
            <li style={{ color: 'var(--text-dim)', cursor: 'not-allowed' }}>Game Board (WIP)</li>
          </ul>
        </nav>
      </aside>

      <main className="main-content">
        <section>
          <h2 style={{ marginBottom: '2rem' }}>Style Guide</h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '4rem' }}>
            {/* Buttons Section */}
            <div>
              <p className="section-title">Buttons</p>
              <div style={{ display: 'flex', gap: '2rem', alignItems: 'center', flexWrap: 'wrap' }}>
                <Button variant="primary">Primary Action</Button>
                <Button variant="secondary">Danger/Hearts</Button>
                <Button disabled>Disabled State</Button>
              </div>
            </div>

            {/* Cards Section */}
            <div>
              <p className="section-title">Face Cards & Aces</p>
              <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
                {faceShowcase.map(card => (
                  <Card key={card.rank + card.suit} rank={card.rank} suit={card.suit} />
                ))}
                <Card rank="A" suit="Hearts" />
                <Card isFaceUp={false} />
              </div>
            </div>

            {/* Number Cards Section */}
            <div>
              <p className="section-title">Number Cards (Pip Layouts)</p>
              <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
                {pipCards.map(card => (
                  <Card key={card.rank + card.suit} rank={card.rank} suit={card.suit} />
                ))}
              </div>
            </div>

            {/* Stacks Section */}
            <div>
              <p className="section-title">Stacks (Hover to Fan)</p>
              <div style={{ display: 'flex', gap: '4rem' }}>
                <Stack cards={sampleCards} />
                <Stack cards={[...pipCards, { rank: 'J', suit: 'Spades' }]} />
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
