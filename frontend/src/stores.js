import { writable } from 'svelte/store';

export const token = writable(localStorage.getItem('token') || null);
export const user = writable(null);

token.subscribe(value => {
    if (value) {
        localStorage.setItem('token', value);
    } else {
        localStorage.removeItem('token');
    }
});
