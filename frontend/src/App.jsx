import { useState } from 'react'
import './App.css'

function App() {
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [userInput, setUserInput] = useState("");
  // Add a new state to track if we are currently recording
  const [isRecording, setIsRecording] = useState(false); 

// Inside App.jsx
  async function record() {
    setLoading(true);
    setIsRecording(true); 
    try {
      // Changed to POST to match FastAPI
      const res = await fetch(`http://localhost:8000/record`, {
        method: "POST", 
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
      });
      const data = await res.json();
      setResponse(data);
    } catch (err) {
      setResponse({ error: "Something went wrong" });
      setIsRecording(false); // Revert on error
    } finally {
      setLoading(false);
    }
  }

  async function stopRecord() {
    try {
      // Changed to POST
      const res = await fetch(`http://localhost:8000/stop-record`, {
        method: "POST", 
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
      });
      const data = await res.json();
      setResponse(data);
    } catch (err) {
      setResponse({ error: "Failed to stop recording" });
    } finally {
      setIsRecording(false); 
    }
  }
  
  async function suggest() {
    setLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/suggest?context=${encodeURIComponent(userInput)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
      });
      const data = await res.json();
      setResponse(data);
    } catch (err) {
      setResponse({ error: "Something went wrong" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div>
        {/* Conditionally render Start/Stop buttons based on state */}
        {!isRecording ? (
          <button onClick={record} disabled={loading}>
            {loading ? "Starting..." : "Start recording"}
          </button>
        ) : (
          <button onClick={stopRecord}>
            Stop recording
          </button>
        )}

      </div>
      <div>
        <h1>
          
        </h1>
      </div>
      <div>
        <input
          type="text"
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          placeholder="Write suggestion..."
        />

        <button onClick={suggest} disabled={loading || isRecording}>
          {loading ? "Loading..." : "Call API"}
        </button>

        {response && <p>{response.suggestion || response.message}</p>}  
      </div>
    </>
  );
}

export default App;