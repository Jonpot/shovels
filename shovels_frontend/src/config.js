const config = {
    API_BASE_URL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    get WS_BASE_URL() {
        return this.API_BASE_URL.replace(/^http/, 'ws');
    }
};

export default config;
