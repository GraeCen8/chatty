<script>
  import { onMount } from "svelte";
  import { token, user } from "./stores";
  import Auth from "./lib/Auth.svelte";
  import Chat from "./lib/Chat.svelte";

  onMount(async () => {
    if ($token && !$user) {
      try {
        const res = await fetch("http://localhost:8000/users/me", {
          headers: { Authorization: `Bearer ${$token}` },
        });
        if (res.ok) {
          const userData = await res.json();
          user.set(userData);
        } else {
          token.set(null);
        }
      } catch (e) {
        console.error("Failed to fetch user:", e);
        token.set(null);
      }
    }
  });
</script>

<div class="app-container">
  <div class="noise"></div>

  <main>
    {#if !$token}
      <Auth />
    {:else}
      <Chat />
    {/if}
  </main>
</div>

<style>
  :global(body) {
    background-color: #0a0a0f;
    color: #e8e8f0;
    font-family:
      "Inter",
      system-ui,
      -apple-system,
      sans-serif;
    margin: 0;
    padding: 0;
    overflow: hidden;
  }

  .app-container {
    min-height: 100vh;
    width: 100vw;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
    z-index: 1;
  }

  .noise {
    position: fixed;
    inset: 0;
    pointer-events: none;
    opacity: 0.03;
    z-index: -1;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  }

  main {
    width: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
  }
</style>
