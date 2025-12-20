import config from '../config';

const { API_BASE_URL, WS_BASE_URL } = config;

export const getAuthToken = () => localStorage.getItem('shovels_token');
export const setAuthToken = (token) => localStorage.setItem('shovels_token', token);
export const removeAuthToken = () => localStorage.removeItem('shovels_token');

export const apiRequest = async (endpoint, options = {}) => {
    const token = getAuthToken();
    const headers = {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options.headers,
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
    });

    if (response.status === 401) {
        removeAuthToken();
        window.location.href = '/';
        throw new Error('Unauthorized');
    }

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || 'API request failed');
    }

    return response.json();
};

export const login = () => {
    window.location.href = `${API_BASE_URL}/auth/login`;
};

export const getRooms = () => apiRequest('/rooms');
export const createRoom = (name) => apiRequest('/rooms', {
    method: 'POST',
    body: JSON.stringify({ name }),
});
export const joinRoom = (roomId, playerId) => apiRequest(`/rooms/${roomId}/join?player_id=${playerId}`, {
    method: 'POST',
});

// WebSocket helper
export const getWsUrl = (roomId) => {
    const token = getAuthToken();
    return `${WS_BASE_URL}/ws/room/${roomId}?token=${token}`;
};
