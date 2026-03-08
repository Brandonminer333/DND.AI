import { useState } from 'react'
import './App.css'

function Example() {
  const [count, setCount] = useState(0)

  return (
    <>
      <div>
        <a href="https://vite.dev" target="_blank">
          <img src={viteLogo} className="logo" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>
      <h1>Vite + React</h1>
      <div className="card">
        <button onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </button>
        <p>
          Edit <code>src/App.jsx</code> and save to test HMR
        </p>
      </div>
      <p className="read-the-docs">
        Click on the Vite and React logos to learn more
      </p>
    </>
  )
}

function App() {
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);

  async function callApi() {
    setLoading(true);
    
    const res = await fetch("http://localhost:8000/", {
      method: "GET",                          // or "GET"
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "hello" })  // your request data
    });

    const data = await res.json();
    setResponse(data);
    setLoading(false);
  }

  return (
    <div>
      <button onClick={callApi}>
        {loading ? "Loading..." : "Call API"}
      </button>

      {response && <p>{JSON.stringify(response)}</p>}
    </div>

  );
}

export default App;