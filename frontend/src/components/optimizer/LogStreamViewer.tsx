"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Terminal, Pause, Play, Download, Trash2 } from 'lucide-react';

interface LogEntry {
  timestamp: string;
  level?: string;
  message: string;
  logger?: string;
  type?: string; // For heartbeat and error messages
}

interface LogStreamViewerProps {
  isActive: boolean;
  onClose?: () => void;
}

export const LogStreamViewer: React.FC<LogStreamViewerProps> = ({ isActive, onClose }) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const logContainerRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (!isPaused && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, isPaused]);

  // Connect to SSE endpoint when active
  useEffect(() => {
    if (isActive && !eventSourceRef.current) {
      connectToLogStream();
    } else if (!isActive && eventSourceRef.current) {
      disconnectFromLogStream();
    }

    return () => {
      disconnectFromLogStream();
    };
  }, [isActive]); // eslint-disable-line react-hooks/exhaustive-deps

  const connectToLogStream = () => {
    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const eventSource = new EventSource(`${API_BASE_URL}/logs/stream`);
      
      eventSource.onopen = () => {
        setIsConnected(true);
        setConnectionError(null);
        console.log('Connected to log stream');
      };

      eventSource.onmessage = (event) => {
        if (!isPaused) {
          try {
            const logEntry: LogEntry = JSON.parse(event.data);
            // Skip heartbeat messages
            if (logEntry.type === 'heartbeat') {
              return;
            }
            setLogs(prevLogs => {
              const newLogs = [...prevLogs, logEntry];
              // Keep only last 500 logs to prevent memory issues
              return newLogs.slice(-500);
            });
          } catch (error) {
            console.error('Error parsing log entry:', error);
          }
        }
      };

      eventSource.onerror = (error) => {
        console.error('Log stream error:', error);
        setIsConnected(false);
        setConnectionError('Connection to log stream failed');
        eventSource.close();
        eventSourceRef.current = null;
      };

      eventSourceRef.current = eventSource;
    } catch (error) {
      console.error('Failed to connect to log stream:', error);
      setConnectionError('Failed to establish connection');
    }
  };

  const disconnectFromLogStream = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    }
  };

  const togglePause = () => {
    setIsPaused(!isPaused);
  };

  const clearLogs = () => {
    setLogs([]);
  };

  const downloadLogs = () => {
    const logText = logs.map(log => 
      `[${log.timestamp}] ${log.level || 'INFO'} - ${log.logger || 'system'} - ${log.message}`
    ).join('\n');
    
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `portfolio-optimization-logs-${new Date().toISOString().slice(0, 19)}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getLogLevelColor = (level?: string) => {
    if (!level) return 'text-gray-300';
    
    switch (level.toUpperCase()) {
      case 'ERROR':
        return 'text-red-400';
      case 'WARNING':
      case 'WARN':
        return 'text-yellow-400';
      case 'INFO':
        return 'text-blue-400';
      case 'DEBUG':
        return 'text-gray-400';
      default:
        return 'text-gray-300';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleTimeString();
    } catch {
      return timestamp;
    }
  };

  return (
    <Card className="bg-slate-900/95 border-slate-700 shadow-xl backdrop-blur-sm">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Terminal className="h-5 w-5 text-green-400" />
            <div>
              <CardTitle className="text-lg font-semibold text-white">
                Backend Logs
              </CardTitle>
              <CardDescription className="text-slate-400 text-sm">
                Real-time portfolio optimization process logs
                {isConnected && (
                  <span className="ml-2 inline-flex items-center gap-1">
                    <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                    Connected
                  </span>
                )}
                {connectionError && (
                  <span className="ml-2 text-red-400">
                    {connectionError}
                  </span>
                )}
              </CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={togglePause}
              className="text-slate-400 hover:text-white"
            >
              {isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearLogs}
              className="text-slate-400 hover:text-white"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={downloadLogs}
              className="text-slate-400 hover:text-white"
              disabled={logs.length === 0}
            >
              <Download className="h-4 w-4" />
            </Button>
            {onClose && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="text-slate-400 hover:text-white"
              >
                ×
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div
          ref={logContainerRef}
          className="bg-black/50 rounded-lg p-4 h-96 overflow-y-auto font-mono text-sm border border-slate-700"
        >
          {logs.length === 0 ? (
            <div className="text-slate-500 italic text-center py-8">
              {isActive ? 'Waiting for logs...' : 'Log stream not active'}
            </div>
          ) : (
            <div className="space-y-1">
              {logs.map((log, index) => (
                <div key={index} className="flex gap-2 text-xs">
                  <span className="text-slate-500 shrink-0">
                    {formatTimestamp(log.timestamp)}
                  </span>
                  <span className={`shrink-0 font-semibold ${getLogLevelColor(log.level)}`}>
                    {log.level?.toUpperCase() || 'INFO'}
                  </span>
                  <span className="text-slate-400 shrink-0">
                    {log.logger || 'system'}:
                  </span>
                  <span className="text-slate-200 break-all">
                    {log.message}
                  </span>
                </div>
              ))}
            </div>
          )}
          {isPaused && (
            <div className="sticky bottom-0 bg-yellow-900/80 text-yellow-200 text-xs p-2 rounded mt-2">
              ⏸️ Log stream paused - Click play to resume
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}; 