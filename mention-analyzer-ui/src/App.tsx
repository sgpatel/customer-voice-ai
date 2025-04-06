// src/App.jsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
// Import charting components from Recharts
import { PieChart, Pie, Cell, Tooltip, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts';
// Import an icon library (optional, for visual flair)
import { TextSelect, ListChecks, BarChart3, PieChart as PieChartIcon, AlertCircle, CheckCircle, Loader2, XCircle } from 'lucide-react';

// --- Configuration ---
const API_BASE_URL = 'http://localhost:8000/api/v1';
const POLLING_INTERVAL = 7000; // Poll slightly less often: 7 seconds

// --- Helper Components (Cards, Charts) ---

// Card component for displaying summary stats
function StatCard({ title, value, icon, color = 'text-indigo-600' }) {
  const IconComponent = icon;
  return (
    <div className="bg-white p-6 rounded-lg shadow border border-gray-200 flex items-center space-x-4">
      {IconComponent && <IconComponent className={`w-8 h-8 ${color}`} />}
      <div>
        <p className="text-sm font-medium text-gray-500">{title}</p>
        <p className="text-2xl font-semibold text-gray-900">{value}</p>
      </div>
    </div>
  );
}

// Pie chart for sentiment distribution
function SentimentPieChart({ data }) {
    // Define colors for sentiments
    const COLORS = {
        positive: '#28a745', // Green
        negative: '#dc3545', // Red
        neutral: '#ffc107',  // Amber
    };
    // Convert data from {sentiment: count} to [{ name: sentiment, value: count }]
    const chartData = Object.entries(data || {}).map(([name, value]) => ({ name, value }));

    if (!chartData || chartData.length === 0) {
        return <p className="text-center text-gray-500 py-4">No sentiment data available.</p>;
    }

    return (
        <div className="bg-white p-6 rounded-lg shadow border border-gray-200 h-80"> {/* Fixed height */}
            <h3 className="text-lg font-semibold mb-4 text-gray-700">Sentiment Analysis</h3>
            <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                    <Pie
                        data={chartData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                        nameKey="name"
                        label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                    >
                        {chartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[entry.name.toLowerCase()] || '#cccccc'} />
                        ))}
                    </Pie>
                    <Tooltip formatter={(value, name) => [value, name]} />
                    <Legend />
                </PieChart>
            </ResponsiveContainer>
        </div>
    );
}

// Bar chart for status distribution
function StatusBarsChart({ data }) {
     const STATUS_COLORS = {
        pending: '#ffc107', // Amber
        processing: '#17a2b8', // Teal
        completed: '#28a745', // Green
        failed: '#dc3545', // Red
    };
    // Convert data from {status: count} to [{ name: status, count: count }]
    const chartData = Object.entries(data || {}).map(([name, value]) => ({ name, count: value }));

     if (!chartData || chartData.length === 0) {
        return <p className="text-center text-gray-500 py-4">No status data available.</p>;
    }

    return (
         <div className="bg-white p-6 rounded-lg shadow border border-gray-200 h-80"> {/* Fixed height */}
            <h3 className="text-lg font-semibold mb-4 text-gray-700">Mentions by Status</h3>
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis allowDecimals={false} />
                    <Tooltip cursor={{ fill: 'rgba(230, 230, 230, 0.5)' }} />
                    {/* <Legend /> */}
                    <Bar dataKey="count" name="Count" barSize={40}>
                         {chartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={STATUS_COLORS[entry.name.toLowerCase()] || '#cccccc'} />
                        ))}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}


// --- MentionForm Component (using Tailwind) ---
function MentionForm({ onMentionAdded }) {
  const [text, setText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!text.trim()) {
      setError('Mention text cannot be empty.');
      return;
    }
    setIsLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE_URL}/mentions/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ text: text, source: 'react-ui-v2' }),
      });

      if (!response.ok) {
        let errorDetail = `HTTP error! Status: ${response.status}`;
        try { const errorData = await response.json(); errorDetail = errorData.detail || errorDetail; }
        catch (parseError) { console.warn("Could not parse error response JSON:", parseError); }
        throw new Error(errorDetail);
      }
      const newMention = await response.json();
      onMentionAdded(newMention);
      setText('');
    } catch (err) {
      console.error('Failed to submit mention:', err);
      setError(`Submit failed: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mb-8 p-4 border border-gray-200 rounded-lg bg-gray-50 shadow-sm">
      <label htmlFor="mentionText" className="block text-sm font-medium text-gray-700 mb-1">
        Submit New Mention
      </label>
      <div className="flex items-start space-x-3">
        <textarea
          id="mentionText"
          value={text}
          onChange={(e) => { setText(e.target.value); setError(''); }}
          placeholder="Enter mention text here..."
          rows="3"
          className="flex-grow block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm disabled:opacity-50"
          disabled={isLoading}
          aria-label="Mention Text Input"
        />
        <button
          type="submit"
          disabled={isLoading || !text.trim()}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-indigo-300 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <> <Loader2 className="animate-spin -ml-1 mr-2 h-4 w-4" /> Submitting... </>
          ) : ( 'Submit' )}
        </button>
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </form>
  );
}

// --- MentionItem Component (using Tailwind) ---
function MentionItem({ mention }) {
  const getStatusClasses = (status) => {
    switch (status) {
      case 'pending': return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'processing': return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'completed': return 'bg-green-100 text-green-800 border-green-300';
      case 'failed': return 'bg-red-100 text-red-800 border-red-300';
      default: return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  return (
    <li className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 mb-4">
      <div className="flex justify-between items-start mb-2">
        <span className="text-xs font-mono text-gray-500 break-all">ID: {mention.id}</span>
        <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusClasses(mention.status)}`}>
          {mention.status}
        </span>
      </div>
      <p className="text-gray-800 mb-2">{mention.text}</p>
      <div className="text-xs text-gray-500 flex justify-between">
        <span>Source: {mention.source || 'N/A'}</span>
        <span>Created: {new Date(mention.created_at).toLocaleString()}</span>
      </div>

      {mention.status === 'completed' && mention.analysis_result && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <h4 className="text-sm font-medium text-gray-600 mb-1">Analysis:</h4>
          <pre className="bg-gray-50 p-3 rounded text-xs text-gray-700 border border-gray-200 overflow-x-auto">
            {JSON.stringify(mention.analysis_result, null, 2)}
          </pre>
        </div>
      )}
      {mention.status === 'failed' && mention.error_message && (
         <div className="mt-3 pt-3 border-t border-red-200">
             <p className="text-sm text-red-700">
                <XCircle className="inline w-4 h-4 mr-1" />
                <strong>Error:</strong> {mention.error_message}
             </p>
         </div>
      )}
    </li>
  );
}

// --- Main App Component ---
function App() {
  const [mentions, setMentions] = useState([]);
  const [summary, setSummary] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const isInitialLoad = useRef(true);

  // Fetch both mentions list and summary data
  const fetchData = useCallback(async () => {
    // Don't show main loading indicator for polls, only initial
    if (isInitialLoad.current) setIsLoading(true);
    // Clear error only if not already loading (prevents flicker during polling errors)
    // setError(null);

    try {
      // Fetch mentions and summary in parallel
      const [mentionsResponse, summaryResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/mentions/?limit=50`),
        fetch(`${API_BASE_URL}/mentions/summary`)
      ]);

      // Process mentions response
      if (!mentionsResponse.ok) {
        throw new Error(`HTTP error fetching mentions! Status: ${mentionsResponse.status}`);
      }
      const mentionsData = await mentionsResponse.json();
      setMentions(mentionsData);

      // Process summary response
      if (!summaryResponse.ok) {
        throw new Error(`HTTP error fetching summary! Status: ${summaryResponse.status}`);
      }
      const summaryData = await summaryResponse.json();
      setSummary(summaryData);

      setError(null); // Clear error only if both fetches succeed

    } catch (err) {
      console.error("Failed to fetch data:", err);
      setError(`Failed to load data: ${err.message}. Is the backend running & CORS configured?`);
    } finally {
      if (isInitialLoad.current) {
        setIsLoading(false);
        isInitialLoad.current = false;
      }
    }
  }, []); // Empty dependency array - created once

  // Effect for initial load and polling
  useEffect(() => {
    fetchData(); // Initial fetch
    const intervalId = setInterval(fetchData, POLLING_INTERVAL);
    return () => clearInterval(intervalId); // Cleanup interval
  }, [fetchData]); // Run effect when fetchData changes (once)

  // Callback for when a new mention is added
  const handleMentionAdded = useCallback((newMention) => {
    // Optimistically add to list
    setMentions(prevMentions => [newMention, ...prevMentions]);
    // Optionally trigger an immediate data refresh instead of waiting for poll
    // fetchData();
  }, []); // Empty dependency array - created once

  // Render UI
  return (
    <div className="max-w-6xl mx-auto p-4 md:p-6 lg:p-8">
      <header className="mb-8 text-center">
        <h1 className="text-3xl font-bold text-gray-800">Mention Analysis Dashboard</h1>
      </header>

      {/* Display loading indicator */}
      {isLoading && (
         <div className="flex justify-center items-center h-40">
            <Loader2 className="animate-spin h-8 w-8 text-indigo-600" />
            <span className="ml-3 text-gray-600">Loading initial data...</span>
         </div>
      )}

      {/* Display error message */}
      {error && !isLoading && (
         <div className="bg-red-50 border border-red-300 text-red-800 px-4 py-3 rounded relative mb-6" role="alert">
            <strong className="font-bold mr-2">Error:</strong>
            <span className="block sm:inline">{error}</span>
         </div>
      )}

      {/* Only render content when not initial loading */}
      {!isLoading && (
        <>
          {/* Dashboard Section */}
          <section className="mb-10">
            <h2 className="text-xl font-semibold text-gray-700 mb-4 border-b pb-2">Dashboard Summary</h2>
            {summary ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                <StatCard title="Total Mentions" value={summary.total_mentions ?? 'N/A'} icon={ListChecks} color="text-blue-600" />
                <StatCard title="Completed" value={summary.by_status?.completed ?? 'N/A'} icon={CheckCircle} color="text-green-600" />
                <StatCard title="Pending" value={summary.by_status?.pending ?? 'N/A'} icon={Loader2} color="text-yellow-600" />
                <StatCard title="Failed" value={summary.by_status?.failed ?? 'N/A'} icon={AlertCircle} color="text-red-600" />
              </div>
            ) : (
                !error && <p className="text-gray-500">Loading summary...</p> // Show loading only if no error
            )}
             {/* Charts Row */}
             {summary && (
                 <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <SentimentPieChart data={summary.by_sentiment} />
                    <StatusBarsChart data={summary.by_status} />
                 </div>
             )}
          </section>

          {/* Submission Form Section */}
          <section className="mb-10">
             {/* <h2 className="text-xl font-semibold text-gray-700 mb-4 border-b pb-2">Submit Mention</h2> */}
             <MentionForm onMentionAdded={handleMentionAdded} />
          </section>

          {/* Mentions List Section */}
          <section>
            <h2 className="text-xl font-semibold text-gray-700 mb-4 border-b pb-2">Latest Mentions</h2>
            {!error && mentions.length === 0 && <p className="text-gray-500">No mentions submitted yet.</p>}
            {!error && mentions.length > 0 && (
              <ul className="space-y-4">
                {mentions.map(mention => (
                  <MentionItem key={mention.id} mention={mention} />
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}

export default App;
