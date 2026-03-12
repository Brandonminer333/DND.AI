import { useState } from 'react'
import './App.css'

function App() {
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [userInput, setUserInput] = useState("");  // ← was missing

  async function callApi() {
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
    <div>
      <input
        type="text"
        value={userInput}
        onChange={(e) => setUserInput(e.target.value)}
        placeholder="Write suggestion..."
      />
      <button onClick={callApi}>
        {loading ? "Loading..." : "Call API"}
      </button>

      {response && <p>{response.suggestion}</p>}  
    </div>
  );
}

export default App;