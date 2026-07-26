"use client";

import { useState, useEffect } from "react";
import BarChartDisplay from "./components/BarChartDisplay";

// Reads the backend URL from environment variable, with local dev as fallback.
// On Vercel, set NEXT_PUBLIC_API_URL to your Render backend URL.
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function Home() {
  const [question, setQuestion] = useState("");
  const [conversation, setConversation] = useState([]); // [{question, answer, sources, timestamp}]
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState("query"); // "query" or "business-query"

  // Load saved conversation from localStorage once, when the page first opens
  useEffect(() => {
    const saved = localStorage.getItem("rag_conversation");
    if (saved) {
      try {
        setConversation(JSON.parse(saved));
      } catch (err) {
        console.error("Failed to parse saved conversation", err);
      }
    }
  }, []);

  // Whenever the conversation changes, save it to localStorage
  useEffect(() => {
    localStorage.setItem("rag_conversation", JSON.stringify(conversation));
  }, [conversation]);

  // Upload-related state
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadQueue, setUploadQueue] = useState([]); // [{name, status: 'pending'|'uploading'|'done'|'error', message}]
  const [uploading, setUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  // Document list state
  const [documents, setDocuments] = useState([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [showDocuments, setShowDocuments] = useState(true);

  const fetchDocuments = async () => {
    setLoadingDocs(true);
    try {
      const response = await fetch(`${API_URL}/documents`);
      const data = await response.json();
      setDocuments(data.documents || []);
    } catch (err) {
      console.error("Failed to fetch documents", err);
    } finally {
      setLoadingDocs(false);
    }
  };

  // Load the document list once when the page first opens
  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleDeleteDocument = async (documentId) => {
    try {
      await fetch(`${API_URL}/documents/${encodeURIComponent(documentId)}`, {
        method: "DELETE",
      });
      // Refresh the list after deleting
      fetchDocuments();
    } catch (err) {
      console.error("Failed to delete document", err);
    }
  };

  const handleFileChange = (e) => {
    setSelectedFiles(Array.from(e.target.files));
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    setSelectedFiles(files);
  };

  const uploadSingleFile = async (file) => {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_URL}/upload`, {
      method: "POST",
      body: formData,
    });
    return response.json();
  };

  const handleUploadAll = async () => {
    if (selectedFiles.length === 0) return;

    setUploading(true);
    // Initialize the queue so the UI can show per-file progress
    setUploadQueue(
      selectedFiles.map((f) => ({ name: f.name, status: "pending", message: "" }))
    );

    // Upload files one at a time so we can show clear progress for each
    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i];

      setUploadQueue((prev) =>
        prev.map((item, idx) => (idx === i ? { ...item, status: "uploading" } : item))
      );

      try {
        const data = await uploadSingleFile(file);

        if (data.error) {
          setUploadQueue((prev) =>
            prev.map((item, idx) =>
              idx === i ? { ...item, status: "error", message: data.error } : item
            )
          );
        } else {
          setUploadQueue((prev) =>
            prev.map((item, idx) =>
              idx === i
                ? { ...item, status: "done", message: `${data.chunks_stored} chunks stored` }
                : item
            )
          );
        }
      } catch (err) {
        setUploadQueue((prev) =>
          prev.map((item, idx) =>
            idx === i ? { ...item, status: "error", message: "Upload failed" } : item
          )
        );
      }
    }

    setUploading(false);
    setSelectedFiles([]);
    fetchDocuments(); // Refresh the document list to show the newly uploaded files
  };

  const handleAsk = async () => {
    if (!question.trim()) return;

    const askedQuestion = question;
    setLoading(true);
    setError("");
    setQuestion(""); // Clear the input immediately for a snappier feel

    try {
      const endpoint = mode === "business-query" ? "/business-query" : "/query";

      const response = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: askedQuestion }),
      });

      if (!response.ok) {
        throw new Error("Something went wrong while fetching the answer.");
      }

      const data = await response.json();

      // /business-query returns final_report instead of answer, and has no sources
      const answerText = mode === "business-query" ? data.final_report : data.answer;
      const sourcesList = mode === "business-query" ? [] : data.sources;
      const chartData = mode === "business-query" ? data.chart_data : null;

      // Add this exchange to the top of the conversation history
      setConversation((prev) => [
        {
          question: askedQuestion,
          answer: answerText,
          sources: sourcesList,
          chartData: chartData,
          timestamp: new Date().toLocaleTimeString(),
        },
        ...prev,
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleClearConversation = () => {
    setConversation([]);
    localStorage.removeItem("rag_conversation");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      handleAsk();
    }
  };

  const completedCount = uploadQueue.filter((f) => f.status === "done").length;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col items-center px-4 py-12">
      <div className="w-full max-w-2xl">
        <h1 className="text-3xl font-bold mb-2 text-center">
          Hello Mr. XYZ 🙂
        </h1>
        <p className="text-gray-400 text-center mb-1">
          I am your personal assistant.
        </p>
        <p className="text-gray-500 text-sm text-center mb-8">
          Upload your documents, then ask me anything about them.
        </p>

        {/* Upload area with drag & drop */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`bg-gray-900 border-2 border-dashed rounded-lg p-5 mb-6 transition-colors ${
            isDragging ? "border-blue-500 bg-gray-800/50" : "border-gray-800"
          }`}
        >
          <h2 className="text-sm uppercase tracking-wide text-gray-500 mb-3">
            Upload Documents
          </h2>

          <div className="flex gap-2">
            <input
              type="file"
              multiple
              accept=".txt,.xlsx,.xls,.csv"
              onChange={handleFileChange}
              className="flex-1 text-sm text-gray-300 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-gray-800 file:text-gray-200 file:cursor-pointer hover:file:bg-gray-700"
            />
            <button
              onClick={handleUploadAll}
              disabled={selectedFiles.length === 0 || uploading}
              className="bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium px-5 py-2 rounded-lg transition-colors whitespace-nowrap"
            >
              {uploading
                ? `Uploading ${completedCount}/${uploadQueue.length}...`
                : `Upload ${selectedFiles.length > 0 ? `(${selectedFiles.length})` : ""}`}
            </button>
          </div>

          <p className="text-xs text-gray-600 mt-2">
            Drag & drop files here, or click to browse. Supported: .txt, .xlsx, .xls, .csv
          </p>

          {/* Per-file progress list */}
          {uploadQueue.length > 0 && (
            <div className="mt-4 space-y-2">
              {uploadQueue.map((item, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between text-sm bg-gray-800/50 rounded px-3 py-2"
                >
                  <span className="text-gray-300 truncate">{item.name}</span>
                  <span
                    className={
                      item.status === "done"
                        ? "text-green-400"
                        : item.status === "error"
                        ? "text-red-400"
                        : item.status === "uploading"
                        ? "text-blue-400"
                        : "text-gray-500"
                    }
                  >
                    {item.status === "pending" && "Waiting..."}
                    {item.status === "uploading" && "Uploading..."}
                    {item.status === "done" && `✓ ${item.message}`}
                    {item.status === "error" && `✗ ${item.message}`}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Uploaded documents list */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-5 mb-8">
          <div className="flex items-center justify-between mb-3">
            <button
              onClick={() => setShowDocuments((prev) => !prev)}
              className="flex items-center gap-2 text-sm uppercase tracking-wide text-gray-500 hover:text-gray-300 transition-colors"
            >
              <span className={`transition-transform ${showDocuments ? "rotate-90" : ""}`}>
                ▶
              </span>
              Your Documents {documents.length > 0 && `(${documents.length})`}
            </button>
            <button
              onClick={fetchDocuments}
              className="text-xs text-gray-500 hover:text-gray-300"
            >
              Refresh
            </button>
          </div>

          {showDocuments && (
            <>
              {loadingDocs ? (
                <p className="text-sm text-gray-500">Loading...</p>
              ) : documents.length === 0 ? (
                <p className="text-sm text-gray-500">No documents uploaded yet.</p>
              ) : (
                <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                  {documents.map((doc) => (
                    <div
                      key={doc.document_id}
                      className="flex items-center justify-between bg-gray-800/50 rounded px-3 py-2 text-sm"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-gray-200 truncate">{doc.document_id}</p>
                        <p className="text-gray-500 text-xs">{doc.chunk_count} chunks</p>
                      </div>
                      <button
                        onClick={() => handleDeleteDocument(doc.document_id)}
                        className="text-red-400 hover:text-red-300 text-xs ml-3 px-2 py-1 rounded hover:bg-red-950/50"
                      >
                        Delete
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        {/* Mode toggle */}
        <div className="flex gap-2 mb-3">
          <button
            onClick={() => setMode("query")}
            className={`text-sm px-4 py-2 rounded-lg transition-colors ${
              mode === "query"
                ? "bg-blue-600 text-white"
                : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            Normal Search
          </button>
          <button
            onClick={() => setMode("business-query")}
            className={`text-sm px-4 py-2 rounded-lg transition-colors ${
              mode === "business-query"
                ? "bg-blue-600 text-white"
                : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            Business Analyst Mode
          </button>
        </div>

        {/* Question input area */}
        <div className="flex gap-2 mb-8">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question..."
            className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
          <button
            onClick={handleAsk}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium px-6 py-3 rounded-lg transition-colors"
          >
            {loading ? "Thinking..." : "Ask"}
          </button>
        </div>

        {/* Error message */}
        {error && (
          <div className="bg-red-950 border border-red-800 text-red-300 rounded-lg px-4 py-3 mb-6">
            {error}
          </div>
        )}

        {/* Conversation history */}
        {conversation.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm uppercase tracking-wide text-gray-500">
                Conversation
              </h2>
              <button
                onClick={handleClearConversation}
                className="text-xs text-gray-500 hover:text-red-400 transition-colors"
              >
                Clear conversation
              </button>
            </div>

            <div className="space-y-6">
              {conversation.map((exchange, index) => (
                <div key={index}>
                  {/* The question, shown like a chat bubble */}
                  <div className="flex justify-end mb-2">
                    <div className="bg-blue-600/20 border border-blue-800/50 rounded-lg px-4 py-2 max-w-[85%]">
                      <p className="text-gray-100 text-sm">{exchange.question}</p>
                    </div>
                  </div>

                  {/* The answer */}
                  <div className="bg-gray-900 border border-gray-800 rounded-lg p-5 mb-3">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-xs uppercase tracking-wide text-gray-500">
                        Answer
                      </h3>
                      <span className="text-xs text-gray-600">{exchange.timestamp}</span>
                    </div>
                    <p className="text-gray-100 leading-relaxed whitespace-pre-wrap">
                      {exchange.answer}
                    </p>
                  </div>
                  {/* Chart, if this answer included one */}
                  {exchange.chartData && <BarChartDisplay chartData={exchange.chartData} />}

                  {/* Sources for this specific answer */}
                  {exchange.sources && exchange.sources.length > 0 && (
                    <div className="space-y-2 pl-2">
                      {exchange.sources.map((source, sIdx) => (
                        <div
                          key={sIdx}
                          className="bg-gray-900/50 border border-gray-800 rounded-lg px-3 py-2 text-xs text-gray-500"
                        >
                          {source}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}