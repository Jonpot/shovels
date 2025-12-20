import React, { useState, useEffect } from 'react';
import Button from './components/Button';
import Card from './components/Card';
import Stack from './components/Stack';
import LoginPage from './views/LoginPage';
import LobbyBrowser from './views/LobbyBrowser';
import LobbyRoom from './views/LobbyRoom';
import { getAuthToken, setAuthToken, joinRoom } from './utils/api';

// Simple JWT decoder (no verification, just payload extraction)
const decodeJwt = (token) => {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(function (c) {
      return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));
    return JSON.parse(jsonPayload);
  } catch (e) {
    return null;
  }
};

function App() {
  const [token, setToken] = useState(getAuthToken());
  const [user, setUser] = useState(null);
  const [currentView, setCurrentView] = useState('BROWSER'); // 'BROWSER', 'ROOM', 'STYLE_GUIDE'
  const [currentRoomId, setCurrentRoomId] = useState(null);

  useEffect(() => {
    // Check for token in URL hash (from backend redirect)
    const hash = window.location.hash;
    if (hash.includes('token=')) {
      const newToken = hash.split('token=')[1];
      setAuthToken(newToken);
      setToken(newToken);
      window.location.hash = ''; // Clear hash
    }

    if (token) {
      const payload = decodeJwt(token);
      if (payload) {
        setUser({
          id: payload.sub,
          email: payload.email,
          name: payload.name
        });
      } else {
        setToken(null);
      }
    }
  }, [token]);

  const handleJoinRoom = async (roomId) => {
    try {
      await joinRoom(roomId, user.id);
      setCurrentRoomId(roomId);
      setCurrentView('ROOM');
    } catch (err) {
      alert('Failed to join room: ' + err.message);
    }
  };

  if (!token || !user) {
    return <LoginPage />;
  }

  // --- Views ---

  if (currentView === 'ROOM') {
    return (
      <LobbyRoom
        roomId={currentRoomId}
        user={user}
        onLeave={() => setCurrentView('BROWSER')}
      />
    );
  }

  if (currentView === 'STYLE_GUIDE') {
    return <StyleGuide onBack={() => setCurrentView('BROWSER')} />;
  }

  return (
    <LobbyBrowser
      user={user}
      onJoinRoom={handleJoinRoom}
      onOpenStyleGuide={() => setCurrentView('STYLE_GUIDE')}
    />
  );
}

// Extracted the original App content into a StyleGuide view
function StyleGuide({ onBack }) {
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
        <nav style={{ flex: 1 }}>
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <li
              style={{ color: 'var(--primary-gold)', fontWeight: 600, cursor: 'pointer' }}
              onClick={onBack}
            >
              &larr; Back to Lobby
            </li>
          </ul>
        </nav>
      </aside>

      <main className="main-content">
        <section>
          <h2 style={{ marginBottom: '2rem' }}>Style Guide</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4rem' }}>
            <div>
              <p className="section-title">Buttons</p>
              <div style={{ display: 'flex', gap: '2rem', alignItems: 'center', flexWrap: 'wrap' }}>
                <Button variant="primary">Primary Action</Button>
                <Button variant="secondary">Danger/Hearts</Button>
                <Button disabled>Disabled State</Button>
              </div>
            </div>
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
            <div>
              <p className="section-title">Number Cards (Pip Layouts)</p>
              <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
                {pipCards.map(card => (
                  <Card key={card.rank + card.suit} rank={card.rank} suit={card.suit} />
                ))}
              </div>
            </div>
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
  );
}

export default App;
