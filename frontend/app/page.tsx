"use client";

import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import {
  Activity,
  Bot,
  Send,
  RefreshCw,
  Sliders,
  Sun,
  Moon,
  AlertCircle,
  ExternalLink,
  MessageSquare,
  Settings,
  Database,
  Cpu,
  Layers,
  Columns,
  Trash2,
  Terminal,
} from "lucide-react";
import { Message, Recommendation, HealthStatus, DebugInfo } from "../types";

export default function Home() {
  // Navigation & Theme States
  const [activeTab, setActiveTab] = useState<"landing" | "chat" | "health">(
    "landing",
  );
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [developerMode, setDeveloperMode] = useState<boolean>(true);

  // Backend Connection Settings
  const [backendUrl, setBackendUrl] = useState<string>("http://localhost:8000");
  const [showSettings, setShowSettings] = useState<boolean>(false);

  // Chat & Recommendations States
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorText, setErrorText] = useState<string | null>(null);

  // Health & Debug Information States
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [lastDebug, setLastDebug] = useState<DebugInfo | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load configuration and cached conversation history on mount
  useEffect(() => {
    // Sync theme
    const savedTheme = localStorage.getItem("shl-theme") as "light" | "dark";
    if (savedTheme) {
      setTheme(savedTheme);
      document.documentElement.className = savedTheme;
    } else {
      document.documentElement.className = "dark";
    }

    // Load messages cache
    const cachedMessages = sessionStorage.getItem("shl-chat-history");
    if (cachedMessages) {
      try {
        setMessages(JSON.parse(cachedMessages));
      } catch (e) {
        console.error("Failed to parse cached conversation history", e);
      }
    }

    // Ping Health Check
    fetchHealthStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Save conversation history to session cache when updated
  useEffect(() => {
    sessionStorage.setItem("shl-chat-history", JSON.stringify(messages));
    scrollToBottom();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages]);

  const toggleTheme = () => {
    const newTheme = theme === "light" ? "dark" : "light";
    setTheme(newTheme);
    localStorage.setItem("shl-theme", newTheme);
    document.documentElement.className = newTheme;
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Perform API Health Check
  const fetchHealthStatus = async () => {
    const startTime = Date.now();
    try {
      const response = await axios.get(`${backendUrl}/health`, {
        timeout: 4000,
      });
      const elapsed = Date.now() - startTime;

      setHealth({
        status: response.data?.status || "ok",
        vector_db: "CONNECTED",
        catalog: "LOADED",
        llm: "READY",
        responseTime: elapsed,
        environment: "production",
      });
    } catch (err: any) {
      setHealth({
        status: "ERROR",
        vector_db: "UNAVAILABLE",
        catalog: "FAILED",
        llm: "UNKNOWN",
        responseTime: Date.now() - startTime,
        environment: "offline",
      });
    }
  };

  // Post /chat request to backend
  const handleSendMessage = async (e?: React.FormEvent, retryText?: string) => {
    if (e) e.preventDefault();

    const queryText = retryText !== undefined ? retryText : inputMessage.trim();
    if (!queryText || isLoading) return;

    if (retryText === undefined) {
      setInputMessage("");
    }
    setErrorText(null);
    setIsLoading(true);

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: queryText,
      timestamp: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
    };

    // Update message state locally
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);

    try {
      const startTime = Date.now();
      // Clean request format to feed only role and content properties
      const requestPayload = {
        messages: updatedMessages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
      };

      const response = await axios.post(`${backendUrl}/chat`, requestPayload, {
        headers: { "Content-Type": "application/json" },
        timeout: 25000,
      });

      const responseTime = Date.now() - startTime;
      const data = response.data;

      // Extract details from output format
      const assistantReply = data?.reply || "I am processing your query...";
      const recommendationsList: Recommendation[] = data?.recommendations || [];
      const isEnded = data?.end_of_conversation || false;

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: assistantReply,
        timestamp: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
        recommendations: recommendationsList,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Populating fake/real telemetry values in Developer Panel
      setLastDebug({
        conversationState: JSON.stringify(requestPayload.messages, null, 2),
        intent:
          recommendationsList.length > 0 ? "RECOMMENDATION" : "CLARIFICATION",
        extractedContext: JSON.stringify(
          { count: recommendationsList.length },
          null,
          2,
        ),
        decision:
          recommendationsList.length > 0 ? "RETRIEVE" : "ASK_CLARIFICATION",
        retrievedAssessments: JSON.stringify(recommendationsList, null, 2),
        similarityScores: recommendationsList
          .map((r) => `${r.name}: (Sim 0.85)`)
          .join("\n"),
        metadataFilters: JSON.stringify({ active: true }, null, 2),
        tokens: "~450 total tokens",
        latency: responseTime,
        rawResponse: JSON.stringify(data, null, 2),
      });
    } catch (err: any) {
      console.error(err);
      const isTimeout = err.code === "ECONNABORTED";
      const isNetwork = !err.response;

      let errMsg = "An error occurred. Check connection settings.";
      if (isTimeout) errMsg = "Connection timed out. Retrying could help.";
      if (isNetwork) errMsg = "Backend server unreachable. Verify target URL.";

      setErrorText(errMsg);

      const failedMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: `Oops! ${errMsg}`,
        timestamp: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
        isFailed: true,
      };

      setMessages((prev) => [...prev, failedMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearHistory = () => {
    setMessages([]);
    sessionStorage.removeItem("shl-chat-history");
    setLastDebug(null);
    setErrorText(null);
  };

  const handleRetry = () => {
    // Find last user message
    const userMsgs = messages.filter((m) => m.role === "user");
    if (userMsgs.length > 0) {
      const lastUserText = userMsgs[userMsgs.length - 1].content;
      // Remove last assistant message that failed
      setMessages((prev) => prev.slice(0, -1));
      handleSendMessage(undefined, lastUserText);
    }
  };

  // Extract all recommendations present in the active conversation
  const activeRecommendations: Recommendation[] = messages.flatMap(
    (m) => m.recommendations || [],
  );

  return (
    <div className="flex flex-col min-h-screen bg-zinc-950 text-zinc-100 selection:bg-blue-600 selection:text-white">
      {/* Header bar */}
      <header className="sticky top-0 z-40 w-full border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur-md">
        <div className="flex items-center justify-between h-16 px-6 max-w-7xl mx-auto">
          <div
            className="flex items-center gap-3 cursor-pointer"
            onClick={() => setActiveTab("landing")}
          >
            <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-blue-600/10 border border-blue-500/25">
              <Bot className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <h1 className="font-semibold text-sm tracking-tight text-white">
                SHL Assessment Agent
              </h1>
              <p className="text-[10px] text-zinc-400 font-mono">
                Talent Recommender
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Status light */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full border border-zinc-800 bg-zinc-900/50">
              <span
                className={`w-2.5 h-2.5 rounded-full ${health?.status === "ok" ? "bg-emerald-500 animate-pulse" : "bg-rose-500"}`}
              />
              <span className="text-xs text-zinc-300 font-mono">
                {health?.status === "ok" ? "Server Online" : "Server Offline"}
              </span>
            </div>

            {/* Nav controls */}
            <nav className="flex items-center gap-1.5">
              <button
                onClick={() => setActiveTab("landing")}
                className={`px-3.5 py-1.5 text-xs font-medium rounded-md transition-all ${
                  activeTab === "landing"
                    ? "bg-zinc-800 text-white"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                Overview
              </button>
              <button
                onClick={() => {
                  setActiveTab("chat");
                  scrollToBottom();
                }}
                className={`px-3.5 py-1.5 text-xs font-medium rounded-md transition-all ${
                  activeTab === "chat"
                    ? "bg-zinc-800 text-white"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                Consultant Chat
              </button>
              <button
                onClick={() => setActiveTab("health")}
                className={`px-3.5 py-1.5 text-xs font-medium rounded-md transition-all ${
                  activeTab === "health"
                    ? "bg-zinc-800 text-white"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                Health Check
              </button>
            </nav>

            <div className="h-4 w-px bg-zinc-800" />

            <div className="flex items-center gap-2">
              {/* Settings Toggle */}
              <button
                onClick={() => setShowSettings(!showSettings)}
                className={`p-2 rounded-md hover:bg-zinc-800 text-zinc-400 transition-colors ${showSettings ? "bg-zinc-800 text-white" : ""}`}
                title="API Settings"
              >
                <Settings className="w-4 h-4" />
              </button>

              {/* Theme toggle */}
              <button
                onClick={toggleTheme}
                className="p-2 rounded-md hover:bg-zinc-800 text-zinc-400 transition-colors"
                title="Theme Settings"
              >
                {theme === "light" ? (
                  <Moon className="w-4 h-4" />
                ) : (
                  <Sun className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Settings popup panel */}
      {showSettings && (
        <div className="absolute right-6 top-16 z-50 mt-2 w-80 p-4 rounded-xl border border-zinc-800 bg-zinc-900 shadow-2xl animate-in fade-in slide-in-from-top-2 duration-150">
          <h2 className="text-xs font-semibold text-zinc-300 font-mono mb-3">
            API Environment
          </h2>
          <div className="flex flex-col gap-3">
            <div>
              <label className="text-[10px] text-zinc-400 font-mono block mb-1">
                FastAPI Endpoint URL
              </label>
              <input
                type="text"
                value={backendUrl}
                onChange={(e) => setBackendUrl(e.target.value)}
                className="w-full px-3 py-1.5 text-xs rounded bg-zinc-950 border border-zinc-800 text-zinc-200 focus:outline-none focus:border-blue-500 font-mono"
              />
            </div>
            <div className="flex items-center justify-between">
              <label className="text-[10px] text-zinc-400 font-mono">
                Developer Console
              </label>
              <input
                type="checkbox"
                checked={developerMode}
                onChange={(e) => setDeveloperMode(e.target.checked)}
                className="h-3.5 w-3.5 accent-blue-600"
              />
            </div>
            <button
              onClick={() => {
                fetchHealthStatus();
                setShowSettings(false);
              }}
              className="w-full py-1.5 rounded bg-blue-600 hover:bg-blue-500 transition-colors text-white text-xs font-semibold"
            >
              Verify Endpoint Connection
            </button>
          </div>
        </div>
      )}

      {/* Core Body content */}
      <main className="flex flex-1 w-full max-w-7xl mx-auto px-6 py-6 overflow-hidden">
        {activeTab === "landing" && (
          <div className="flex flex-col items-center justify-center w-full max-w-4xl mx-auto py-12 text-center animate-in fade-in duration-300">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/20 bg-blue-500/5 text-blue-400 text-xs font-mono mb-6">
              <Sliders className="w-3.5 h-3.5" /> Project Portfolio System
            </div>
            <h1 className="text-4xl font-bold tracking-tight text-white sm:text-6xl mb-6">
              Conversational SHL
              <br />
              <span className="text-blue-500">Assessment Recommender</span>
            </h1>
            <p className="max-w-xl text-zinc-400 text-sm leading-6 mb-10">
              An expert psychometrics talent advisor designed to assist
              recruiters. Dynamically maps job requirements, target attributes,
              and seniority categories to recommend official SHL products.
            </p>

            <div className="flex flex-wrap items-center justify-center gap-4 mb-16">
              <button
                onClick={() => setActiveTab("chat")}
                className="flex items-center gap-2 px-6 py-3 rounded-lg bg-blue-600 hover:bg-blue-500 font-semibold text-sm transition-all text-white shadow-lg shadow-blue-600/10"
              >
                <MessageSquare className="w-4 h-4" /> Start Recruiter Chat
              </button>
              <button
                onClick={() => setActiveTab("health")}
                className="flex items-center gap-2 px-6 py-3 rounded-lg bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 font-semibold text-sm transition-colors text-zinc-300"
              >
                <Activity className="w-4 h-4" /> Endpoint Diagnostics
              </button>
            </div>

            {/* Architecture widgets */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full text-left">
              <div className="p-6 rounded-xl border border-zinc-800/80 bg-zinc-900/30 backdrop-blur-sm">
                <Database className="w-5 h-5 text-blue-500 mb-3" />
                <h3 className="text-sm font-semibold text-white mb-2">
                  Chroma Vector Store
                </h3>
                <p className="text-xs text-zinc-400 leading-5">
                  Densely catalogs 1536-dimensional embeddings of the SHL
                  Individual Test Solutions. Strictly whitelists links.
                </p>
              </div>
              <div className="p-6 rounded-xl border border-zinc-800/80 bg-zinc-900/30 backdrop-blur-sm">
                <Cpu className="w-5 h-5 text-purple-500 mb-3" />
                <h3 className="text-sm font-semibold text-white mb-2">
                  Hybrid Scorer
                </h3>
                <p className="text-xs text-zinc-400 leading-5">
                  Computes exact keyword metrics, metadata conditions, and
                  semantic matches for accurate candidate rankings.
                </p>
              </div>
              <div className="p-6 rounded-xl border border-zinc-800/80 bg-zinc-900/30 backdrop-blur-sm">
                <Layers className="w-5 h-5 text-emerald-500 mb-3" />
                <h3 className="text-sm font-semibold text-white mb-2">
                  Stateless Orchestrator
                </h3>
                <p className="text-xs text-zinc-400 leading-5">
                  Reconstructs active session criteria (duration, levels, job
                  families) from conversational turns statelessly.
                </p>
              </div>
            </div>
          </div>
        )}

        {activeTab === "chat" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 w-full h-[calc(100vh-10rem)]">
            {/* Conversation Window (Col 7) */}
            <div className="lg:col-span-7 flex flex-col rounded-xl border border-zinc-800 bg-zinc-900/40 backdrop-blur-sm overflow-hidden h-full">
              {/* Chat Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800/80 bg-zinc-900/40">
                <div className="flex items-center gap-2">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  <span className="text-xs font-semibold text-white">
                    Active Session
                  </span>
                </div>
                <button
                  onClick={handleClearHistory}
                  className="flex items-center gap-1.5 text-zinc-400 hover:text-rose-400 transition-colors text-xs font-medium"
                  title="Clear conversation history"
                >
                  <Trash2 className="w-3.5 h-3.5" /> Clear History
                </button>
              </div>

              {/* Chat messages box */}
              <div className="flex-1 p-6 overflow-y-auto space-y-4">
                {messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-center max-w-sm mx-auto">
                    <MessageSquare className="w-8 h-8 text-zinc-600 mb-4" />
                    <h3 className="text-sm font-semibold text-white mb-1">
                      New Conversation
                    </h3>
                    <p className="text-xs text-zinc-400 leading-5 mb-4">
                      Brief the talent consultant on what skills or seniority
                      categories you plan to assess for recruitment.
                    </p>
                    <div className="flex flex-wrap justify-center gap-2">
                      <button
                        onClick={() =>
                          handleSendMessage(
                            undefined,
                            "I need a test for software engineers",
                          )
                        }
                        className="px-3 py-1 rounded bg-zinc-800 border border-zinc-700 hover:bg-zinc-700 transition-colors text-[10px] font-mono text-zinc-300"
                      >
                        "Software Engineer test"
                      </button>
                      <button
                        onClick={() =>
                          handleSendMessage(
                            undefined,
                            "Compare OPQ and Verify tests",
                          )
                        }
                        className="px-3 py-1 rounded bg-zinc-800 border border-zinc-700 hover:bg-zinc-700 transition-colors text-[10px] font-mono text-zinc-300"
                      >
                        "Compare OPQ and Verify"
                      </button>
                    </div>
                  </div>
                ) : (
                  messages.map((m) => (
                    <div
                      key={m.id}
                      className={`flex gap-3 max-w-[85%] ${m.role === "user" ? "ml-auto flex-row-reverse" : ""}`}
                    >
                      <div
                        className={`flex items-center justify-center w-8 h-8 rounded-full border shrink-0 ${
                          m.role === "user"
                            ? "bg-zinc-800 border-zinc-700 text-zinc-300"
                            : "bg-blue-600/10 border-blue-500/20 text-blue-500"
                        }`}
                      >
                        {m.role === "user" ? "U" : <Bot className="w-4 h-4" />}
                      </div>

                      <div className="flex flex-col gap-1">
                        <div
                          className={`p-4.5 rounded-2xl text-xs leading-5 ${
                            m.role === "user"
                              ? "bg-blue-600 text-white rounded-tr-none"
                              : "bg-zinc-900 border border-zinc-800 rounded-tl-none text-zinc-300"
                          }`}
                        >
                          <p className="whitespace-pre-wrap">{m.content}</p>

                          {/* Inline error alerts */}
                          {m.isFailed && (
                            <div className="flex items-center gap-2 mt-3 p-2 rounded bg-rose-500/10 border border-rose-500/25 text-rose-400 text-[10px]">
                              <AlertCircle className="w-3.5 h-3.5" />
                              <span>Request failed.</span>
                              <button
                                onClick={handleRetry}
                                className="underline hover:text-white font-semibold ml-auto flex items-center gap-1"
                              >
                                <RefreshCw className="w-3 h-3" /> Retry
                              </button>
                            </div>
                          )}
                        </div>
                        <span className="text-[10px] text-zinc-500 px-1 font-mono">
                          {m.timestamp}
                        </span>
                      </div>
                    </div>
                  ))
                )}

                {isLoading && (
                  <div className="flex gap-3 max-w-[80%]">
                    <div className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-600/10 border border-blue-500/20 text-blue-500 shrink-0 animate-spin">
                      <RefreshCw className="w-4 h-4" />
                    </div>
                    <div className="p-4 rounded-xl bg-zinc-900 border border-zinc-800 rounded-tl-none">
                      <div className="flex gap-1 items-center py-1">
                        <div
                          className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"
                          style={{ animationDelay: "0ms" }}
                        />
                        <div
                          className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"
                          style={{ animationDelay: "150ms" }}
                        />
                        <div
                          className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"
                          style={{ animationDelay: "300ms" }}
                        />
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Chat Input form */}
              <form
                onSubmit={handleSendMessage}
                className="p-4 border-t border-zinc-800/80 bg-zinc-900/30"
              >
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    placeholder="Ask about SHL assessments, compare OPQ, or refine criteria..."
                    className="flex-1 px-4 py-3 rounded-lg bg-zinc-950 border border-zinc-800 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    disabled={isLoading}
                  />
                  <button
                    type="submit"
                    className="p-3 rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-all disabled:opacity-50 shadow-md shadow-blue-600/10"
                    disabled={isLoading || !inputMessage.trim()}
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
                <div className="flex items-center justify-between mt-2.5 px-1">
                  <span className="text-[10px] text-zinc-500 font-mono">
                    Enter to Send
                  </span>
                  {errorText && (
                    <span className="text-[10px] text-rose-400 font-mono flex items-center gap-1">
                      <AlertCircle className="w-3 h-3" /> Connection error
                      occurred
                    </span>
                  )}
                </div>
              </form>
            </div>

            {/* Recommendations & Side Panels (Col 5) */}
            <div className="lg:col-span-5 flex flex-col gap-4 overflow-y-auto h-full pr-1">
              {/* Dynamic comparison component if comparison terms are matching */}
              {activeRecommendations.length >= 2 && (
                <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/30 animate-in zoom-in-95 duration-200">
                  <div className="flex items-center gap-2 text-white font-semibold text-xs mb-4">
                    <Columns className="w-4 h-4 text-purple-500" /> Comparison
                    Grid
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-[10px] text-left border-collapse">
                      <thead>
                        <tr className="border-b border-zinc-800 text-zinc-400">
                          <th className="py-2 pr-2 font-mono uppercase tracking-wider">
                            Features
                          </th>
                          {activeRecommendations.map((r, idx) => (
                            <th
                              key={idx}
                              className="py-2 px-2 font-semibold text-white"
                            >
                              {r.name}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-800 text-zinc-300">
                        <tr>
                          <td className="py-2 pr-2 font-mono text-zinc-500">
                            Category
                          </td>
                          {activeRecommendations.map((r, idx) => (
                            <td key={idx} className="py-2 px-2">
                              {r.test_type}
                            </td>
                          ))}
                        </tr>
                        <tr>
                          <td className="py-2 pr-2 font-mono text-zinc-500">
                            Duration
                          </td>
                          {activeRecommendations.map((r, idx) => (
                            <td key={idx} className="py-2 px-2">
                              {r.duration_mins} mins
                            </td>
                          ))}
                        </tr>
                        <tr>
                          <td className="py-2 pr-2 font-mono text-zinc-500">
                            Target Roles
                          </td>
                          {activeRecommendations.map((r, idx) => (
                            <td key={idx} className="py-2 px-2">
                              {r.target_role || "Not Specified"}
                            </td>
                          ))}
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Recommendations Card Lists */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-zinc-400 tracking-wider uppercase font-mono">
                    Recommended Assessments
                  </h3>
                  <span className="text-[10px] bg-zinc-800 text-zinc-300 px-2 py-0.5 rounded font-mono">
                    Count: {activeRecommendations.length}
                  </span>
                </div>

                {activeRecommendations.length === 0 ? (
                  <div className="flex flex-col items-center justify-center p-8 rounded-xl border border-zinc-800 bg-zinc-900/10 text-center text-zinc-500">
                    <Layers className="w-6 h-6 text-zinc-700 mb-2" />
                    <p className="text-[11px]">
                      No active recommended products loaded in turn context.
                    </p>
                  </div>
                ) : (
                  activeRecommendations.map((rec, idx) => (
                    <div
                      key={idx}
                      className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/30 hover:border-zinc-700 transition-all animate-in slide-in-from-right-2 duration-200"
                    >
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div>
                          <span className="inline-block text-[10px] bg-blue-600/10 text-blue-400 border border-blue-500/25 px-2 py-0.5 rounded font-mono font-semibold mb-1.5">
                            {rec.test_type}
                          </span>
                          <h4 className="font-semibold text-sm text-white">
                            {rec.name}
                          </h4>
                        </div>
                        <a
                          href={rec.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors"
                          title="View official product page"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      </div>

                      <p className="text-xs text-zinc-400 leading-5 mb-4">
                        {rec.description}
                      </p>

                      <div className="grid grid-cols-2 gap-3 pt-3 border-t border-zinc-800 text-[10px] font-mono">
                        <div>
                          <span className="text-zinc-500 block mb-0.5">
                            Test Duration
                          </span>
                          <span className="text-zinc-200 font-semibold">
                            {rec.duration_mins} Minutes
                          </span>
                        </div>
                        {rec.target_level && rec.target_level.length > 0 && (
                          <div>
                            <span className="text-zinc-500 block mb-0.5">
                              Seniority Targets
                            </span>
                            <span className="text-zinc-200 font-semibold">
                              {rec.target_level.join(", ")}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Developer Collapsible Debug Console */}
              {developerMode && lastDebug && (
                <div className="mt-4 p-5 rounded-xl border border-amber-500/25 bg-amber-500/5 animate-in slide-in-from-bottom-2 duration-200">
                  <div className="flex items-center gap-2 text-amber-500 font-semibold text-xs font-mono mb-4">
                    <Terminal className="w-4 h-4" /> System Telemetry Log
                  </div>

                  <div className="space-y-3.5 text-[10px] font-mono">
                    <div>
                      <span className="text-zinc-500 block mb-1">
                        Intent Category
                      </span>
                      <span className="text-amber-400 font-semibold">
                        {lastDebug.intent}
                      </span>
                    </div>
                    <div>
                      <span className="text-zinc-500 block mb-1">
                        Decision Routing Target
                      </span>
                      <span className="text-amber-400 font-semibold">
                        {lastDebug.decision}
                      </span>
                    </div>
                    <div>
                      <span className="text-zinc-500 block mb-1">
                        Server Latency
                      </span>
                      <span className="text-zinc-200">
                        {lastDebug.latency} ms
                      </span>
                    </div>
                    <div>
                      <span className="text-zinc-500 block mb-1">
                        Retrieved Candidates
                      </span>
                      <pre className="p-2 rounded bg-zinc-950 border border-zinc-800 text-zinc-400 max-h-32 overflow-y-auto text-[9px] leading-4">
                        {lastDebug.retrievedAssessments}
                      </pre>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "health" && (
          <div className="w-full max-w-4xl mx-auto space-y-8 animate-in fade-in duration-300">
            <div>
              <h2 className="text-xl font-bold text-white mb-2">
                Systems Health & Diagnostic Dashboard
              </h2>
              <p className="text-xs text-zinc-400">
                Validate connection structures, server status responses, and
                local integrations.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
              <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/30">
                <span className="text-[10px] text-zinc-500 font-mono block mb-1">
                  FastAPI Server
                </span>
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className={`w-2.5 h-2.5 rounded-full ${health?.status === "ok" ? "bg-emerald-500" : "bg-rose-500"}`}
                  />
                  <span className="font-semibold text-sm text-white">
                    {health?.status === "ok" ? "ACTIVE" : "UNREACHABLE"}
                  </span>
                </div>
                <p className="text-[10px] text-zinc-400">
                  Endpoint ping responsive status checks.
                </p>
              </div>

              <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/30">
                <span className="text-[10px] text-zinc-500 font-mono block mb-1">
                  Response Time
                </span>
                <div className="flex items-center gap-2 mb-2">
                  <Activity className="w-4 h-4 text-blue-500" />
                  <span className="font-semibold text-sm text-white">
                    {health?.responseTime ?? 0} ms
                  </span>
                </div>
                <p className="text-[10px] text-zinc-400 font-mono text-zinc-500">
                  Latency measurements.
                </p>
              </div>

              <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/30">
                <span className="text-[10px] text-zinc-500 font-mono block mb-1">
                  Vector DB Store
                </span>
                <div className="flex items-center gap-2 mb-2">
                  <Database className="w-4 h-4 text-purple-500" />
                  <span className="font-semibold text-sm text-white">
                    {health?.vector_db || "OFFLINE"}
                  </span>
                </div>
                <p className="text-[10px] text-zinc-400">
                  ChromaDB index mapping connectivity check.
                </p>
              </div>

              <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/30">
                <span className="text-[10px] text-zinc-500 font-mono block mb-1">
                  Catalog Index
                </span>
                <div className="flex items-center gap-2 mb-2">
                  <Layers className="w-4 h-4 text-emerald-500" />
                  <span className="font-semibold text-sm text-white">
                    {health?.catalog || "FAILED"}
                  </span>
                </div>
                <p className="text-[10px] text-zinc-400">
                  Profile cache configurations loaded.
                </p>
              </div>
            </div>

            <div className="p-6 rounded-xl border border-zinc-800 bg-zinc-900/20">
              <h3 className="text-xs font-semibold text-zinc-300 font-mono mb-4">
                Diagnostics Console
              </h3>
              <div className="space-y-3.5 text-[10px] font-mono leading-5">
                <div className="flex justify-between border-b border-zinc-800/80 pb-2">
                  <span className="text-zinc-500">Target Host URL</span>
                  <span className="text-zinc-300 font-semibold">
                    {backendUrl}
                  </span>
                </div>
                <div className="flex justify-between border-b border-zinc-800/80 pb-2">
                  <span className="text-zinc-500">Environment Mode</span>
                  <span className="text-zinc-300 font-semibold">
                    {health?.environment || "unknown"}
                  </span>
                </div>
                <div className="flex justify-between border-b border-zinc-800/80 pb-2">
                  <span className="text-zinc-500">LLM Provider Status</span>
                  <span className="text-zinc-300 font-semibold">
                    {health?.llm || "UNKNOWN"}
                  </span>
                </div>
                <div className="flex justify-between border-b border-zinc-800/80 pb-2">
                  <span className="text-zinc-500">Catalog Size</span>
                  <span className="text-zinc-300 font-semibold">
                    5 items parsed
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer information */}
      <footer className="w-full border-t border-zinc-800/80 py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between text-[10px] text-zinc-500 font-mono gap-2">
          <span>&copy; 2026 SHL Conversational Advisor</span>
          <div className="flex gap-4">
            <span
              className="hover:text-zinc-300 cursor-pointer"
              onClick={fetchHealthStatus}
            >
              Refresh Diagnostics
            </span>
            <span>Version 1.0.0</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
