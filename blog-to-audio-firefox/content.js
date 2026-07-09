window.addEventListener('message', (event) => {
  if (event.origin !== 'https://text-to-audio-online.vercel.app') return;
  if (!event.data || event.data.type !== 'AUTH_SESSION_FOR_EXTENSION') return;

  browser.runtime.sendMessage({
    type: 'AUTH_SESSION',
    access_token: event.data.access_token,
    refresh_token: event.data.refresh_token,
    expires_at: event.data.expires_at,
    email: event.data.email,
  });
});
