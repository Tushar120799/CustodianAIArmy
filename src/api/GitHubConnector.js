import React, { useState } from 'react';
import useGitHubAuth from '../hooks/useGitHubAuth';

const GitHubConnector = ({ session, onConnectionSuccess }) => {
  const [connectionStatus, setConnectionStatus] = useState('');

  // This is the callback that runs after the popup successfully returns a token
  const handleAuthSuccess = async (authData) => {
    setConnectionStatus('Finalizing connection...');
    try {
      const response = await fetch('/api/v1/mvp/connect-github', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: session.session_id,
          github_token: authData.token,
          // repo_name can be added here if you have one at this stage
        }),
      });

      const result = await response.json();

      if (!response.ok || !result.success) {
        throw new Error(result.message || 'Failed to connect GitHub account on the backend.');
      }

      // The log message now includes the username!
      setConnectionStatus(`Connected as ${result.github_username}!`);
      console.log(`GitHub connected for user: ${result.github_username}`);

      // Notify the parent component of the success
      if (onConnectionSuccess) {
        onConnectionSuccess(result);
      }

    } catch (err) {
      setConnectionStatus(`Error: ${err.message}`);
      console.error(err);
    }
  };

  const { handleAuthPopup, loading, error } = useGitHubAuth(handleAuthSuccess);

  // Do not render the button if the session is not yet available.
  if (!session || !session.session_id) {
    return <p>Loading session...</p>;
  }

  if (session.github_connected) {
    return (
      <div>
        <p>✅ GitHub Connected as <strong>{session.github_username}</strong></p>
        {/* You can add a disconnect button here later */}
      </div>
    );
  }

  return (
    <div>
      <button onClick={() => handleAuthPopup(session.session_id)} disabled={loading}>
        {loading ? 'Waiting for GitHub...' : 'Connect to GitHub'}
      </button>
      {error && <p style={{ color: 'red' }}>Error: {error.message}</p>}
      {connectionStatus && <p>{connectionStatus}</p>}
    </div>
  );
};

export default GitHubConnector;