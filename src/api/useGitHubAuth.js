import { useState, useEffect, useCallback } from 'react';

const useGitHubAuth = (onSuccess) => {
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleAuthPopup = useCallback((sessionId) => {
    if (!sessionId) {
      setError(new Error("Session ID is required to initiate GitHub auth."));
      return;
    }

    setLoading(true);
    setError(null);

    const authUrl = `/api/v1/auth/github/login?session_id=${sessionId}`;
    const popup = window.open(authUrl, 'github-auth', 'width=600,height=700');

    const handleMessage = (event) => {
      // IMPORTANT: Check the origin of the message for security
      if (event.origin !== window.location.origin) {
        return;
      }

      const { data } = event;
      if (data && data.provider === 'github' && data.token) {
        // The popup sent us the token data.
        setLoading(false);
        if (popup) popup.close();
        
        // Verify session_id matches if it was sent back
        if (data.session_id && data.session_id === sessionId) {
            onSuccess(data);
        } else {
            setError(new Error("Session ID mismatch during GitHub authentication."));
        }

        // Clean up the event listener
        window.removeEventListener('message', handleMessage);
      } else if (data && data.error) {
        setLoading(false);
        setError(new Error(data.error));
        if (popup) popup.close();
        window.removeEventListener('message', handleMessage);
      }
    };

    window.addEventListener('message', handleMessage);

    // Poll to see if the popup was closed by the user
    const timer = setInterval(() => {
      if (popup && popup.closed) {
        clearInterval(timer);
        setLoading(false);
        // Only set error if we weren't already successful
        if (!onSuccess.called) {
            // This check is conceptual; you'd need to track if onSuccess was called.
            // A simpler way is to just let the loading state reset.
        }
        window.removeEventListener('message', handleMessage);
      }
    }, 500);

  }, [onSuccess]);

  return {
    handleAuthPopup,
    loading,
    error,
  };
};

export default useGitHubAuth;