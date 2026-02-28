<script>
    import { token, user } from '../stores';
    let isLogin = true;
    let username = '';
    let email = '';
    let password = '';
    let error = '';
    let loading = false;

    async function handleSubmit() {
        error = '';
        loading = true;
        const endpoint = isLogin ? '/users/login' : '/users/create';
        
        try {
            let body;
            let headers = {};
            
            if (isLogin) {
                // OAuth2PasswordRequestForm expects form data
                body = new URLSearchParams();
                body.append('username', username);
                body.append('password', password);
                headers['Content-Type'] = 'application/x-www-form-urlencoded';
            } else {
                body = JSON.stringify({ username, email, password });
                headers['Content-Type'] = 'application/json';
            }

            const response = await fetch(`http://localhost:8000${endpoint}`, {
                method: 'POST',
                headers,
                body
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Something went wrong');
            }

            if (isLogin) {
                token.set(data.access_token);
                // Fetch user info
                const userRes = await fetch('http://localhost:8000/users/me', {
                    headers: { 'Authorization': `Bearer ${data.access_token}` }
                });
                const userData = await userRes.json();
                user.set(userData);
            } else {
                isLogin = true;
                error = 'Account created! Please login.';
            }
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }
</script>

<div class="auth-container">
    <div class="auth-card">
        <h2>{isLogin ? 'Login' : 'Register'}</h2>
        <p class="subtitle">{isLogin ? 'Welcome back to Chatty' : 'Join the conversation today'}</p>
        
        <form on:submit|preventDefault={handleSubmit}>
            <div class="input-group">
                <label for="username">Username</label>
                <input type="text" id="username" bind:value={username} required placeholder="Choose a username" />
            </div>

            {#if !isLogin}
                <div class="input-group">
                    <label for="email">Email</label>
                    <input type="email" id="email" bind:value={email} required placeholder="your@email.com" />
                </div>
            {/if}

            <div class="input-group">
                <label for="password">Password</label>
                <input type="password" id="password" bind:value={password} required placeholder="••••••••" />
            </div>

            {#if error}
                <p class="error">{error}</p>
            {/if}

            <button type="submit" disabled={loading}>
                {loading ? 'Processing...' : (isLogin ? 'Sign In' : 'Create Account')}
            </button>
        </form>

        <div class="toggle">
            <button class="link-btn" on:click={() => isLogin = !isLogin}>
                {isLogin ? "Don't have an account? Register" : "Already have an account? Login"}
            </button>
        </div>
    </div>
</div>

<style>
    .auth-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 80vh;
    }

    .auth-card {
        background: rgba(26, 26, 40, 0.8);
        backdrop-filter: blur(10px);
        padding: 2.5rem;
        border-radius: 1.5rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        width: 100%;
        max-width: 400px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    h2 {
        margin: 0 0 0.5rem;
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #6c63ff, #ff6584);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .subtitle {
        color: #6b6b8a;
        margin-bottom: 2rem;
        font-size: 0.9rem;
    }

    .input-group {
        margin-bottom: 1.25rem;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #e8e8f0;
        margin-left: 0.25rem;
    }

    input {
        background: rgba(13, 13, 24, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 0.8rem 1rem;
        border-radius: 0.75rem;
        color: white;
        transition: all 0.2s;
    }

    input:focus {
        outline: none;
        border-color: #6c63ff;
        box-shadow: 0 0 0 2px rgba(108, 99, 255, 0.2);
    }

    .error {
        color: #ff6584;
        font-size: 0.85rem;
        margin-bottom: 1rem;
    }

    button[type="submit"] {
        width: 100%;
        padding: 0.9rem;
        background: linear-gradient(135deg, #6c63ff, #ff6584);
        color: white;
        border: none;
        border-radius: 0.75rem;
        font-weight: 700;
        cursor: pointer;
        transition: transform 0.2s, opacity 0.2s;
        margin-top: 1rem;
    }

    button[type="submit"]:hover {
        opacity: 0.9;
        transform: translateY(-1px);
    }

    button[type="submit"]:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }

    .toggle {
        margin-top: 1.5rem;
        text-align: center;
    }

    .link-btn {
        background: none;
        border: none;
        color: #6c63ff;
        font-size: 0.85rem;
        cursor: pointer;
        transition: color 0.2s;
    }

    .link-btn:hover {
        color: #ff6584;
        text-decoration: underline;
    }
</style>
