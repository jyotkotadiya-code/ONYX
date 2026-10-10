import React, { useState, useEffect, useRef } from 'react';
import {
  ShieldCheck,
  MessageSquare,
  UploadCloud,
  FileText,
  Search,
  Database,
  Activity,
  FolderKanban,
  Users,
  Sun,
  Moon,
  LogOut,
  Send,
  RefreshCw,
  Trash2,
  Eye,
  CheckCircle2,
  AlertTriangle,
  Cpu,
  HardDrive,
  Layers,
  Terminal,
  Sparkles,
  Lock,
  Plus,
  X,
  ChevronRight,
  FileImage,
  FileCode2,
  FileAudio,
  BarChart3,
  Settings,
  Building2,
} from 'lucide-react';
import { StructuredResponse } from './types/structured';
import { ResponseBlock } from './components/workspace/ResponseBlock';
import { Workspace } from './components/workspace/Workspace';
import { LoginPage } from './components/auth/LoginPage';
import { AuthTransitionState } from './components/auth/AuthStatus';
import { AppLoader, AppBootPhase } from './components/loading/AppLoader';
import { ServiceStatusItem } from './components/loading/ServiceStatus';
import { LoadingSkeleton } from './components/loading/LoadingSkeleton';
import { OnyxLogo } from './components/system/OnyxLogo';
import { PrivacyIndicator } from './components/system/PrivacyIndicator';
import { LocalAIStatus } from './components/system/LocalAIStatus';
import { ConnectionStatus } from './components/system/ConnectionStatus';
import { AdminConsole, AdminSection } from './components/admin/AdminConsole';
import { EmployeeWorkplaceApp } from './components/employee/EmployeeWorkplaceApp';
import { AdminWorkplacePortal } from './components/admin/AdminWorkplacePortal';
import { EmployeeWorkplacePortal } from './components/employee/EmployeeWorkplacePortal';
import { ImageVectorizerModal } from './components/tools/ImageVectorizerModal';

interface UserInfo {
  id: string;
  name?: string;
  email?: string;
  username: string;
  role: 'admin' | 'employee' | 'ADMIN' | 'MEMBER';
  role_display?: string;
  job_title?: string;
  department?: string | null;
  department_id?: string | null;
  groups?: Array<{ id: string; name: string }>;
  status?: string;
  workspace: string;
  workspace_id?: string;
  workplace_id?: string;
  workplace?: any;
  allowed_collections: string[];
  permissions?: string[];
  can_upload: boolean;
}

interface Citation {
  document_id: string;
  chunk_id: string;
  filename: string;
  modality: string;
  page_number: number;
  section_title: string;
  table?: string;
  row_id?: string;
  collection: string;
  label: string;
  locator: string;
}

interface ObservabilityData {
  query: string;
  route?: string;
  embedding_time_ms: number;
  retrieval_time_ms: number;
  llm_time_ms?: number;
  model_used?: string;
  runtime?: string;
  retrieved_chunks?: Array<{
    chunk_id: string;
    document_id?: string;
    filename: string;
    locator: string;
    similarity: number;
    vector_similarity?: number;
    keyword_score?: number;
    content: string;
  }>;
  final_context?: string;
  structured_response?: StructuredResponse;
}

interface ChatMsg {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  answer_found?: boolean;
  citations?: Citation[];
  observability?: ObservabilityData;
  structured_response?: StructuredResponse;
}

const PROCESSING_STAGES = [
  'Uploading...',
  'Extracting...',
  'OCR...',
  'Chunking...',
  'Embedding...',
  'Indexing...',
  'Complete ✓',
];

export default function App() {
  const [darkMode, setDarkMode] = useState(true);
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserInfo | null>(null);

  const isAdmin = Boolean(user && String(user.role).toLowerCase() === 'admin');

  // Auth & Boot State Machine
  const [authTransition, setAuthTransition] = useState<AuthTransitionState>('idle');
  const [loginErrorTitle, setLoginErrorTitle] = useState<string | undefined>(undefined);
  const [loginError, setLoginError] = useState('');
  const [sessionExpired, setSessionExpired] = useState(false);

  const [bootPhase, setBootPhase] = useState<AppBootPhase>('BOOT');
  const [bootScreenDismissed, setBootScreenDismissed] = useState(false);
  const [apiAvailable, setApiAvailable] = useState(true);
  const [isRetryingConnection, setIsRetryingConnection] = useState(false);
  const [dataLoading, setDataLoading] = useState(true);
  const [bootTechDetails, setBootTechDetails] = useState<string | undefined>(undefined);

  // Navigation Tabs & Admin Section
  const [activeTab, setActiveTab] = useState<
    'chat' | 'dashboard' | 'upload' | 'documents' | 'search' | 'collections' | 'admin' | 'health'
  >(() => {
    const p = window.location.pathname;
    if (p.startsWith('/admin/ai')) return 'chat';
    if (p.startsWith('/admin')) return 'admin';
    return 'admin';
  });
  const [adminSection, setAdminSection] = useState<AdminSection>('overview');
  const [adminView, setAdminView] = useState<'portal' | 'dashboard'>('portal');
  const [employeeView, setEmployeeView] = useState<'portal' | 'chat'>('portal');

  // Workplace & Global System Status
  const [workplace, setWorkplace] = useState<any>(null);
  const [workplaces, setWorkplaces] = useState<any[]>([]);
  const [sysStatus, setSysStatus] = useState<any>(null);
  const [collections, setCollections] = useState<any[]>([]);
  const [selectedCollection, setSelectedCollection] = useState<string>('ALL');
  const [documents, setDocuments] = useState<any[]>([]);

  // Chat & Dynamic Workspace State
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [chatSessions, setChatSessions] = useState<any[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeWorkspace, setActiveWorkspace] = useState<StructuredResponse | null>(null);
  const [questionInput, setQuestionInput] = useState('');
  const [chatMode, setChatMode] = useState<'rag' | 'exact'>('rag');
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeObservability, setActiveObservability] = useState<ObservabilityData | null>(null);
  const [showDebugDrawer, setShowDebugDrawer] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Upload & Database Ingestion State
  const [uploadCollection, setUploadCollection] = useState('General');
  const [uploadStageIdx, setUploadStageIdx] = useState<number>(-1);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dbConnUrl, setDbConnUrl] = useState('');
  const [inspectedTables, setInspectedTables] = useState<any[]>([]);
  const [checkedTables, setCheckedTables] = useState<string[]>([]);

  // Direct Search State
  const [searchQuery, setSearchQuery] = useState('');
  const [searchMode, setSearchMode] = useState<'rag' | 'exact'>('rag');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searchTiming, setSearchTiming] = useState<{ emb: number; ret: number } | null>(null);

  // Document Preview Modal State
  const [previewDoc, setPreviewDoc] = useState<any | null>(null);
  const [previewHighlightChunkId, setPreviewHighlightChunkId] = useState<string | null>(null);
  const [previewHighlightPage, setPreviewHighlightPage] = useState<number | null>(null);

  // Image Vectorizer Modal State
  const [vectorizerOpen, setVectorizerOpen] = useState(false);
  const [vectorizerDocId, setVectorizerDocId] = useState<string | undefined>(undefined);
  const [vectorizerFilename, setVectorizerFilename] = useState<string | undefined>(undefined);

  const openVectorizer = (docId?: string, filename?: string) => {
    setVectorizerDocId(docId);
    setVectorizerFilename(filename);
    setVectorizerOpen(true);
  };

  // New Collection & New User Forms
  const [newColName, setNewColName] = useState('');
  const [newColDesc, setNewColDesc] = useState('');
  const [usersList, setUsersList] = useState<any[]>([]);
  const [newUsername, setNewUsername] = useState('');
  const [newUserPassword, setNewUserPassword] = useState('');
  const [newUserRole, setNewUserRole] = useState<'MEMBER' | 'ADMIN'>('MEMBER');

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  // Role-Based Route Protection (/login <-> /admin/* for Admin, /chat & /profile for Employee)
  useEffect(() => {
    const path = window.location.pathname;
    if (!token || !user) {
      if (path !== '/login') {
        window.history.replaceState(null, '', '/login');
      }
    } else if (!isAdmin) {
      if (path !== '/chat' && path !== '/profile') {
        window.history.replaceState(null, '', '/chat');
      }
    } else {
      if (path === '/login' || path === '/' || path === '/chat') {
        window.history.replaceState(null, '', '/admin');
      }
    }
  }, [token, user, isAdmin]);

  const authHeaders = (overrideToken?: string | null): Record<string, string> => {
    const t = overrideToken !== undefined ? overrideToken : token;
    return {
      ...(t ? { Authorization: `Bearer ${t}` } : {}),
      'ngrok-skip-browser-warning': 'true',
    };
  };

  const handleSessionExpired = () => {
    setSessionExpired(true);
    setToken(null);
    setUser(null);
    localStorage.removeItem('rag_token');
    localStorage.removeItem('rag_user');
    sessionStorage.removeItem('rag_token');
    sessionStorage.removeItem('rag_user');
  };

  const fetchSystemData = async (isInitialBoot = false, activeToken?: string | null) => {
    const tok = activeToken !== undefined ? activeToken : token;
    if (isInitialBoot) {
      setIsRetryingConnection(true);
      setBootPhase(tok ? 'AUTHENTICATING' : 'CHECKING_SERVICES');
    }

    try {
      const stResp = await fetch('/api/system/status', { headers: authHeaders(tok) });
      if (!stResp.ok) {
        throw new Error(`System status returned HTTP ${stResp.status}`);
      }
      const statusJson = await stResp.json();
      setSysStatus(statusJson);
      setApiAvailable(true);
      setBootTechDetails(undefined);

      if (!tok) {
        setBootPhase('READY');
        setBootScreenDismissed(true);
        setIsRetryingConnection(false);
        return;
      }

      if (isInitialBoot) {
        setBootPhase('LOADING_WORKSPACE');
      }

      // Verify session & progressively load workplace metadata
      const meResp = await fetch('/api/auth/me', { headers: authHeaders(tok) });
      if (meResp.status === 401 || meResp.status === 403) {
        handleSessionExpired();
        setIsRetryingConnection(false);
        return;
      }
      let freshUserObj = user;
      if (meResp.ok) {
        freshUserObj = await meResp.json();
        setUser(freshUserObj);
        if (freshUserObj?.workplace) {
          setWorkplace(freshUserObj.workplace);
        }
      }

      if (isInitialBoot) {
        setBootPhase('CHECKING_SERVICES');
      }

      const [wpResp, colResp, docResp, sessResp] = await Promise.all([
        fetch('/api/workplaces/current', { headers: authHeaders(tok) }),
        fetch('/api/collections', { headers: authHeaders(tok) }),
        fetch('/api/documents', { headers: authHeaders(tok) }),
        fetch('/api/chats', { headers: authHeaders(tok) }),
      ]);

      if (colResp.status === 401 || docResp.status === 401) {
        handleSessionExpired();
        setIsRetryingConnection(false);
        return;
      }

      if (wpResp.ok) setWorkplace(await wpResp.json());
      if (colResp.ok) setCollections(await colResp.json());
      if (docResp.ok) setDocuments(await docResp.json());
      if (sessResp.ok) setChatSessions(await sessResp.json());
      setDataLoading(false);

      const userIsAdmin = Boolean(
        freshUserObj && String(freshUserObj.role).toLowerCase() === 'admin'
      );
      if (userIsAdmin) {
        const [usrResp, wpsResp] = await Promise.all([
          fetch('/api/users', { headers: authHeaders(tok) }),
          fetch('/api/workplaces', { headers: authHeaders(tok) }),
        ]);
        if (usrResp.ok) setUsersList(await usrResp.json());
        if (wpsResp.ok) setWorkplaces(await wpsResp.json());
      }

      const hasDegraded =
        (statusJson.llm !== 'online' && statusJson.llm !== 'local_fallback_ready') ||
        statusJson.vector_database !== 'online' ||
        statusJson.ocr === 'unavailable';

      setBootPhase(hasDegraded ? 'DEGRADED' : 'READY');
      if (isInitialBoot) {
        setTimeout(() => setBootScreenDismissed(true), 260);
      }
    } catch (e: any) {
      setApiAvailable(false);
      setBootTechDetails('Local API endpoint (/api/system/status) did not respond.');
      if (isInitialBoot) {
        setBootPhase('ERROR');
      }
    } finally {
      setIsRetryingConnection(false);
    }
  };

  useEffect(() => {
    fetchSystemData(true);
    const interval = setInterval(() => fetchSystemData(false), 30000);
    return () => clearInterval(interval);
  }, [token]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const handleLogin = async (usernameInput: string, passwordInput: string, rememberMe: boolean) => {
    setLoginError('');
    setLoginErrorTitle(undefined);
    setAuthTransition('signing_in');

    try {
      const resp = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: usernameInput, password: passwordInput }),
      });

      if (!resp.ok) {
        setAuthTransition('idle');
        if (resp.status === 401 || resp.status === 400) {
          setLoginErrorTitle('Unable to sign in');
          setLoginError('Check your username and password and try again.');
        } else {
          setLoginErrorTitle('Authentication service unavailable');
          setLoginError('Please wait a moment and try signing in again.');
        }
        return;
      }

      const data = await resp.json();
      setSessionExpired(false);
      setAuthTransition('authenticated');

      const storage = rememberMe ? localStorage : sessionStorage;
      storage.setItem('rag_token', data.access_token);
      storage.setItem('rag_user', JSON.stringify(data.user));
      if (data.workplace) setWorkplace(data.workplace);

      setTimeout(() => {
        setAuthTransition('preparing_workspace');
      }, 180);

      setTimeout(() => {
        setToken(data.access_token);
        setUser(data.user);
        setMessages([]);
        setActiveSessionId(null);
        setActiveWorkspace(null);
        setBootScreenDismissed(true);
        setAuthTransition('idle');
        fetchSystemData(false, data.access_token);
      }, 420);
    } catch {
      setAuthTransition('idle');
      setApiAvailable(false);
      setLoginErrorTitle('Backend unavailable');
      setLoginError('Make sure the local RAG server is running and try again.');
    }
  };

  const handleActivateInvite = async (inviteToken: string, passwordInput: string) => {
    setLoginError('');
    setLoginErrorTitle(undefined);
    try {
      const resp = await fetch('/api/auth/activate-invite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ invite_token: inviteToken, password: passwordInput }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        setLoginErrorTitle('Invite activation failed');
        setLoginError(data.detail || 'Invalid or expired workplace invite token.');
        return;
      }
      localStorage.setItem('rag_token', data.access_token);
      localStorage.setItem('rag_user', JSON.stringify(data.user));
      if (data.workplace) setWorkplace(data.workplace);
      setToken(data.access_token);
      setUser(data.user);
      setMessages([]);
      setActiveSessionId(null);
      setBootScreenDismissed(true);
      fetchSystemData(false, data.access_token);
    } catch {
      setLoginError('Could not connect to workplace server.');
    }
  };

  const handleSwitchWorkplace = async (workplaceId: string) => {
    try {
      const resp = await fetch(`/api/workplaces/${workplaceId}/switch`, {
        method: 'POST',
        headers: authHeaders(),
      });
      if (resp.ok) {
        const data = await resp.json();
        localStorage.setItem('rag_token', data.access_token);
        localStorage.setItem('rag_user', JSON.stringify(data.user));
        setToken(data.access_token);
        setUser(data.user);
        setWorkplace(data.workplace);
        setMessages([]);
        setActiveSessionId(null);
        setActiveWorkspace(null);
        fetchSystemData(false, data.access_token);
      }
    } catch (e) {
      console.error('Failed switching workplace:', e);
    }
  };

  const handleCreateWorkplace = async (payload: any) => {
    const resp = await fetch('/api/workplaces', {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (resp.ok) {
      const created = await resp.json();
      await handleSwitchWorkplace(created.id);
    }
  };

  const handleSelectChatSession = async (sessionId: string) => {
    try {
      const resp = await fetch(`/api/chat/sessions/${sessionId}`, { headers: authHeaders() });
      if (resp.ok) {
        const data = await resp.json();
        setActiveSessionId(sessionId);
        const loadedMsgs: ChatMsg[] = (data.messages || []).map((m: any) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          answer_found: m.answer_found,
          citations: m.citations || [],
          observability: m.observability,
          structured_response: m.structured_response,
        }));
        setMessages(loadedMsgs);
        const lastWithWs = [...loadedMsgs].reverse().find((m) => m.structured_response);
        setActiveWorkspace(lastWithWs?.structured_response || null);
      }
    } catch (e) {
      console.error('Failed loading chat session:', e);
    }
  };

  const handleDeleteChatSession = async (sessionId: string) => {
    try {
      const resp = await fetch(`/api/chat/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: authHeaders(),
      });
      if (resp.ok) {
        if (activeSessionId === sessionId) {
          setActiveSessionId(null);
          setMessages([]);
          setActiveWorkspace(null);
        }
        fetchSystemData(false);
      }
    } catch (e) {
      console.error('Failed deleting chat session:', e);
    }
  };

  const handleNewChat = () => {
    setActiveSessionId(null);
    setMessages([]);
    setActiveWorkspace(null);
    setQuestionInput('');
  };

  const handleLogout = () => {
    setToken(null);
    setUser(null);
    setMessages([]);
    setActiveSessionId(null);
    setActiveWorkspace(null);
    setSessionExpired(false);
    localStorage.removeItem('rag_token');
    localStorage.removeItem('rag_user');
    sessionStorage.removeItem('rag_token');
    sessionStorage.removeItem('rag_user');
    window.history.replaceState(null, '', '/login');
  };

  const openDocumentPreview = async (docId: string, chunkId?: string, pageNum?: number) => {
    if (!docId) return;
    try {
      const resp = await fetch(`/api/documents/${docId}`, { headers: authHeaders() });
      if (resp.ok) {
        const data = await resp.json();
        setPreviewDoc(data);
        setPreviewHighlightChunkId(chunkId || null);
        setPreviewHighlightPage(pageNum || null);
      }
    } catch (e) {
      console.error('Failed to open document preview:', e);
    }
  };

  const handleMutateWorkspace = async (command: string, baseWorkspace?: StructuredResponse) => {
    const targetWs = baseWorkspace || activeWorkspace;
    if (!targetWs || !command.trim()) return;
    try {
      const resp = await fetch('/api/workspace/mutate', {
        method: 'POST',
        headers: {
          ...authHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          command,
          active_workspace: targetWs,
          session_id: activeSessionId,
        }),
      });
      if (resp.ok) {
        const data = await resp.json();
        const updated: StructuredResponse = data.structured_response;
        setActiveWorkspace(updated);
        // Also update the most recent assistant message's structured_response
        setMessages((prev) => {
          const copy = [...prev];
          for (let i = copy.length - 1; i >= 0; i--) {
            if (copy[i].role === 'assistant') {
              copy[i] = { ...copy[i], structured_response: updated };
              break;
            }
          }
          return copy;
        });
      }
    } catch (e) {
      console.error('Failed to mutate workspace:', e);
    }
  };

  const handleSendChat = async (e?: React.FormEvent, overrideQuestion?: string) => {
    if (e) e.preventDefault();
    const q = (overrideQuestion !== undefined ? overrideQuestion : questionInput).trim();
    if (!q || isStreaming) return;

    const userMessage: ChatMsg = {
      id: `u_${Date.now()}`,
      role: 'user',
      content: q,
    };
    const assistantMsgId = `a_${Date.now()}`;
    const placeholderAssistant: ChatMsg = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      citations: [],
    };

    setMessages((prev) => [...prev, userMessage, placeholderAssistant]);
    setQuestionInput('');
    setIsStreaming(true);

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          ...authHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: q,
          session_id: activeSessionId,
          collection: selectedCollection,
          mode: chatMode,
          top_k: 5,
          stream: true,
          active_workspace: activeWorkspace,
        }),
      });

      if (!resp.ok || !resp.body) {
        const err = await resp.json().catch(() => ({ detail: 'Chat request failed' }));
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId ? { ...m, content: `Error: ${err.detail}` } : m
          )
        );
        setIsStreaming(false);
        return;
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      const handleEvent = (evt: any) => {
        if (evt.type === 'metadata') {
          if (evt.session_id) setActiveSessionId(evt.session_id);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId ? { ...m, citations: evt.citations || [] } : m
            )
          );
        } else if (evt.type === 'token') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId ? { ...m, content: m.content + evt.token } : m
            )
          );
        } else if (evt.type === 'done') {
          const structResp: StructuredResponse | undefined =
            evt.structured_response || evt.observability?.structured_response;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? {
                    ...m,
                    content: m.content || evt.answer || '',
                    answer_found: evt.answer_found,
                    citations: evt.citations || [],
                    observability: evt.observability,
                    structured_response: structResp,
                  }
                : m
            )
          );
          if (evt.observability) {
            setActiveObservability(evt.observability);
          }
          if (structResp) {
            const hasVisuals = structResp.components?.some((c) =>
              ['table', 'chart', 'stat', 'timeline', 'comparison'].includes(c.type)
            );
            if (hasVisuals || evt.observability?.route === 'workspace_followup') {
              setActiveWorkspace(structResp);
            }
          }
          fetchSystemData(false);
        }
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          if (buffer.trim()) {
            const trailing = buffer.split(/\r?\n\r?\n/);
            for (const line of trailing) {
              const clean = line.replace(/\r/g, '').trim();
              if (!clean.startsWith('data:')) continue;
              const jsonStr = clean.replace(/^data:\s*/, '').trim();
              if (jsonStr) {
                try {
                  handleEvent(JSON.parse(jsonStr));
                } catch {}
              }
            }
          }
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split(/\r?\n\r?\n/);
        buffer = lines.pop() || '';

        for (const line of lines) {
          const clean = line.replace(/\r/g, '').trim();
          if (!clean.startsWith('data:')) continue;
          const jsonStr = clean.replace(/^data:\s*/, '').trim();
          if (!jsonStr) continue;
          try {
            handleEvent(JSON.parse(jsonStr));
          } catch (e) {
            console.error('Failed to parse SSE event:', e, jsonStr);
          }
        }
      }
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsgId ? { ...m, content: `Connection error: ${err.message}` } : m
        )
      );
    } finally {
      setIsStreaming(false);
    }
  };

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploadError(null);
    setUploadResult(null);

    const file = files[0];
    // Animate step progression while local ingestion runs
    setUploadStageIdx(0);
    const timer = setInterval(() => {
      setUploadStageIdx((prev) => (prev < 5 ? prev + 1 : prev));
    }, 350);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('collection', uploadCollection);
      formData.append('sync', 'true');

      const resp = await fetch('/api/documents/upload', {
        method: 'POST',
        headers: authHeaders(),
        body: formData,
      });
      clearInterval(timer);

      const data = await resp.json();
      if (!resp.ok) {
        setUploadStageIdx(-1);
        setUploadError(data.detail || 'Upload failed');
        return;
      }
      setUploadStageIdx(6);
      setUploadResult(data);
      fetchSystemData();
    } catch (e: any) {
      clearInterval(timer);
      setUploadStageIdx(-1);
      setUploadError(e.message || 'Upload error');
    }
  };

  const handleInspectDatabase = async () => {
    if (!dbConnUrl.trim()) return;
    setUploadError(null);
    try {
      const resp = await fetch('/api/database/inspect', {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ connection_url: dbConnUrl.trim() }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        setUploadError(data.detail || 'Failed to inspect database');
        return;
      }
      setInspectedTables(data.tables || []);
      setCheckedTables((data.tables || []).map((t: any) => t.table));
    } catch (e: any) {
      setUploadError(e.message);
    }
  };

  const handleIngestDatabase = async () => {
    if (!dbConnUrl.trim()) return;
    setUploadStageIdx(1);
    try {
      const resp = await fetch('/api/database/ingest', {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          connection_url: dbConnUrl.trim(),
          selected_tables: checkedTables,
          collection: uploadCollection,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        setUploadStageIdx(-1);
        setUploadError(data.detail || 'Database ingestion failed');
        return;
      }
      setUploadStageIdx(6);
      setUploadResult(data);
      fetchSystemData();
    } catch (e: any) {
      setUploadStageIdx(-1);
      setUploadError(e.message);
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    const resp = await fetch(`/api/documents/${docId}`, {
      method: 'DELETE',
      headers: authHeaders(),
    });
    if (resp.ok) {
      fetchSystemData();
    }
  };

  const handleReindexDocument = async (docId: string) => {
    const resp = await fetch(`/api/documents/${docId}/reindex`, {
      method: 'POST',
      headers: authHeaders(),
    });
    if (resp.ok) {
      fetchSystemData();
    }
  };

  const handleDirectSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    const resp = await fetch('/api/search', {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: searchQuery,
        collection: selectedCollection,
        mode: searchMode,
        top_k: 10,
      }),
    });
    if (resp.ok) {
      const data = await resp.json();
      setSearchResults(data.results || []);
      setSearchTiming({ emb: data.embedding_time_ms, ret: data.retrieval_time_ms });
    }
  };

  const handleCreateCollection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newColName.trim()) return;
    const resp = await fetch('/api/collections', {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newColName.trim(), description: newColDesc.trim() }),
    });
    if (resp.ok) {
      setNewColName('');
      setNewColDesc('');
      fetchSystemData();
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUsername.trim() || !newUserPassword.trim()) return;
    const resp = await fetch('/api/users', {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: newUsername.trim(),
        password: newUserPassword.trim(),
        role: newUserRole,
        allowed_collections: newUserRole === 'ADMIN' ? ['*'] : ['General', 'Projects', 'Research'],
      }),
    });
    if (resp.ok) {
      setNewUsername('');
      setNewUserPassword('');
      fetchSystemData();
    }
  };

  // Construct real service status items for AppLoader / SystemInitialization
  const bootServices: ServiceStatusItem[] = [
    {
      id: 'auth',
      label: 'Authentication',
      detail: user ? user.username : 'Verified',
      state: !apiAvailable ? 'error' : token ? 'success' : 'pending',
    },
    {
      id: 'sqlite',
      label: 'Local database',
      detail: 'SQLite',
      state: !apiAvailable
        ? 'error'
        : sysStatus?.sqlite === 'online'
        ? 'success'
        : bootPhase === 'AUTHENTICATING'
        ? 'loading'
        : 'pending',
    },
    {
      id: 'vector_db',
      label: 'Vector database',
      detail: sysStatus?.vector_details?.engine || 'ChromaDB',
      state: !apiAvailable
        ? 'error'
        : sysStatus?.vector_database === 'online'
        ? 'success'
        : sysStatus
        ? 'warning'
        : 'loading',
    },
    {
      id: 'embedding',
      label: 'Embedding model',
      detail: sysStatus?.embedding?.model || 'multilingual-e5-small',
      state: !apiAvailable
        ? 'error'
        : sysStatus?.embedding_model === 'online' || sysStatus?.embedding_model === 'unloaded'
        ? 'success'
        : 'loading',
    },
    {
      id: 'llm',
      label: 'Local Llama',
      detail: sysStatus?.llm_details?.selected_model || 'Local runtime',
      state: !apiAvailable
        ? 'error'
        : sysStatus?.llm === 'online' || sysStatus?.llm === 'local_fallback_ready'
        ? 'success'
        : sysStatus
        ? 'warning'
        : 'loading',
    },
    {
      id: 'ocr',
      label: 'OCR engine',
      detail: sysStatus?.ocr_details?.engine || 'RapidOCR',
      state: !apiAvailable
        ? 'pending'
        : sysStatus?.ocr === 'online' || sysStatus?.ocr === 'available'
        ? 'success'
        : sysStatus
        ? 'warning'
        : 'pending',
      optional: true,
    },
  ];

  const degradedServicesList: string[] = [];
  if (sysStatus) {
    if (sysStatus.vector_database !== 'online') degradedServicesList.push('Vector Database');
    if (sysStatus.ocr === 'unavailable') degradedServicesList.push('OCR');
  }

  // ─── 1. Redesigned Login Experience (/login) ───────────────────────────────
  if (!token || !user) {
    return (
      <LoginPage
        darkMode={darkMode}
        onToggleDarkMode={() => setDarkMode(!darkMode)}
        onLogin={handleLogin}
        onActivateInvite={handleActivateInvite}
        transitionState={authTransition}
        errorTitle={loginErrorTitle}
        errorMessage={loginError}
        sessionExpired={sessionExpired}
        sysStatus={sysStatus}
        apiAvailable={apiAvailable}
        onRetryConnection={() => fetchSystemData(true)}
      />
    );
  }

  // ─── 2. Real Application Boot / Initialization Screen ──────────────────────
  if (!bootScreenDismissed || bootPhase === 'ERROR') {
    return (
      <AppLoader
        phase={bootPhase}
        services={bootServices}
        offlineMode={sysStatus?.offline_mode ?? true}
        verifiedPrivate={sysStatus?.verified_private ?? true}
        technicalDetails={bootTechDetails}
        onRetry={() => fetchSystemData(true)}
        isRetrying={isRetryingConnection}
      />
    );
  }

  // ─── 3. Dedicated Employee Private AI Workplace Experience (/chat, /profile) ───
  if (!isAdmin) {
    if (employeeView === 'portal') {
      return (
        <EmployeeWorkplacePortal
          user={user}
          currentWorkplace={workplace}
          darkMode={darkMode}
          onToggleDarkMode={() => setDarkMode(!darkMode)}
          onLogout={handleLogout}
          onJoinWorkplace={async (wpId) => {
            await handleSwitchWorkplace(wpId);
            setEmployeeView('chat');
          }}
          onEnterActiveChat={() => setEmployeeView('chat')}
        />
      );
    }

    return (
      <EmployeeWorkplaceApp
        user={user}
        workplace={workplace}
        darkMode={darkMode}
        onToggleDarkMode={() => setDarkMode(!darkMode)}
        onLogout={handleLogout}
        messages={messages}
        activeSessionId={activeSessionId}
        activeWorkspace={activeWorkspace}
        onSelectWorkspace={setActiveWorkspace}
        onMutateWorkspace={handleMutateWorkspace}
        questionInput={questionInput}
        onQuestionChange={setQuestionInput}
        onSendChat={handleSendChat}
        isStreaming={isStreaming}
        onNewChat={handleNewChat}
        chatSessions={chatSessions}
        onSelectSession={handleSelectChatSession}
        onDeleteSession={handleDeleteChatSession}
        onOpenCitationPreview={(docId, chunkId, pageNum) =>
          openDocumentPreview(docId, chunkId, pageNum)
        }
        previewDoc={previewDoc}
        onClosePreview={() => setPreviewDoc(null)}
        chatEndRef={chatEndRef}
        onOpenPortal={() => setEmployeeView('portal')}
      />
    );
  }

  // ─── 4. Admin Workplace Control Plane & AI Console (/admin/*) ──────────────
  if (adminView === 'portal') {
    return (
      <AdminWorkplacePortal
        user={user}
        workplaces={workplaces}
        currentWorkplace={workplace}
        darkMode={darkMode}
        onToggleDarkMode={() => setDarkMode(!darkMode)}
        onLogout={handleLogout}
        onSelectWorkplace={async (wpId) => {
          await handleSwitchWorkplace(wpId);
          setAdminView('dashboard');
        }}
        onCreateWorkplace={async (payload) => {
          await handleCreateWorkplace(payload);
          setAdminView('dashboard');
        }}
        onEnterDashboard={() => setAdminView('dashboard')}
      />
    );
  }

  return (
    <div className="min-h-screen flex bg-[#f8f9fa] dark:bg-[#0b0c0e] text-zinc-900 dark:text-zinc-100 animate-onyx-page">
      {/* ─── Left Navigation Sidebar (Admin Control Plane) ─── */}
      <aside className="w-64 shrink-0 border-r border-zinc-200/90 dark:border-zinc-800/80 bg-white dark:bg-[#111317] flex flex-col justify-between p-4">
        <div className="overflow-y-auto pr-0.5">
          {/* Brand Header */}
          <div className="flex items-center justify-between px-2 pb-3 border-b border-zinc-200/80 dark:border-zinc-800/80">
            <div className="flex items-center gap-2.5 min-w-0">
              <OnyxLogo size="sm" />
              <div className="min-w-0">
                <div className="font-semibold text-sm tracking-tight truncate">
                  {workplace?.name || user.workspace || 'ONYX Studio'}
                </div>
                <div className="text-[11px] text-zinc-500 dark:text-zinc-400 truncate">
                  Workplace Admin Console
                </div>
              </div>
            </div>
            <button
              onClick={() => setDarkMode(!darkMode)}
              className="p-1.5 rounded-lg hover:bg-zinc-200/70 dark:hover:bg-zinc-800 text-zinc-500 dark:text-zinc-400 transition-colors shrink-0"
              title="Toggle theme"
              aria-label="Toggle theme"
            >
              {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
          </div>

          {/* Quick Workplaces Hub Switcher */}
          <button
            onClick={() => setAdminView('portal')}
            className="w-full mt-3 flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-800/80 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-200 text-xs font-semibold transition border border-zinc-200/60 dark:border-zinc-700/60"
            title="Switch or create organization workspaces"
          >
            <Building2 className="w-3.5 h-3.5 text-emerald-500" />
            <span>Workplace Portal</span>
          </button>

          {/* Honest Privacy Indicator */}
          <div className="mt-4 px-1">
            <PrivacyIndicator
              offlineMode={sysStatus?.offline_mode ?? true}
              verifiedPrivate={sysStatus?.verified_private ?? true}
              compact
            />
          </div>

          {/* Collection Filter Selector */}
          <div className="mt-4">
            <label className="block text-[11px] font-semibold uppercase tracking-wider text-zinc-400 mb-1.5 px-1">
              Active Knowledge Scope
            </label>
            <select
              value={selectedCollection}
              onChange={(e) => setSelectedCollection(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-800 text-xs font-medium focus:outline-none focus:border-zinc-900 dark:focus:border-zinc-300"
            >
              <option value="ALL">All Permitted Collections</option>
              {collections.map((c) => (
                <option key={c.id} value={c.name}>
                  📁 {c.name} ({c.document_count})
                </option>
              ))}
            </select>
          </div>

          {/* Admin Workplace Control Plane Navigation */}
          <div className="mt-5">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400 px-2 mb-1.5">
              Workplace Management
            </div>
            <nav className="space-y-1">
              {[
                { id: 'overview', label: 'Workplace Overview', icon: Layers },
                { id: 'employees', label: 'Employees & Invites', icon: Users },
                { id: 'knowledge', label: 'Knowledge & Access', icon: FileText },
                { id: 'collections', label: 'Collections & Depts', icon: FolderKanban },
                { id: 'access', label: 'Access Matrix', icon: ShieldCheck },
                { id: 'analytics', label: 'Workplace Analytics', icon: BarChart3 },
                { id: 'settings', label: 'Workplace Settings', icon: Settings },
              ].map((sec) => {
                const Icon = sec.icon;
                const active = activeTab === 'admin' && adminSection === sec.id;
                return (
                  <button
                    key={sec.id}
                    onClick={() => {
                      setActiveTab('admin');
                      setAdminSection(sec.id as AdminSection);
                      window.history.replaceState(null, '', `/admin/${sec.id}`);
                    }}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition ${
                      active
                        ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-950'
                        : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200/60 dark:hover:bg-zinc-800/60'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{sec.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* AI & Technical Tools */}
          <div className="mt-5">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400 px-2 mb-1.5">
              AI & Knowledge Operations
            </div>
            <nav className="space-y-1">
              {[
                { id: 'chat', label: 'AI Chat & Testing', icon: MessageSquare },
                { id: 'upload', label: 'Upload & Ingestion', icon: UploadCloud },
                { id: 'documents', label: 'Documents & Versions', icon: FileText },
                { id: 'search', label: 'Vector Search Inspector', icon: Search },
                { id: 'health', label: 'System Health & LLM', icon: Activity },
              ].map((item) => {
                const Icon = item.icon;
                const active = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      setActiveTab(item.id as any);
                      window.history.replaceState(null, '', `/admin/${item.id}`);
                    }}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition ${
                      active
                        ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-950'
                        : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200/60 dark:hover:bg-zinc-800/60'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>
        </div>

        {/* User Profile & Role Badge Footer */}
        <div className="pt-4 border-t border-zinc-200 dark:border-zinc-800/80 flex items-center justify-between">
          <div className="min-w-0 pr-2">
            <div className="text-xs font-semibold truncate">{user.name || user.username}</div>
            <div className="flex flex-wrap items-center gap-1 mt-0.5">
              <span className="inline-block text-[10px] px-1.5 py-0.5 rounded font-mono font-medium bg-emerald-500/15 text-emerald-500">
                Administrator
              </span>
              {user.job_title && (
                <span className="text-[10px] text-zinc-500 dark:text-zinc-400 truncate">
                  {user.job_title}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="p-2 rounded-lg hover:bg-red-500/10 text-zinc-400 hover:text-red-400 transition shrink-0"
            title="Sign Out"
            aria-label="Sign Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </aside>

      {/* ─── Main Content Area ─── */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Global API / Degraded Service Connection Banner */}
        <ConnectionStatus
          apiAvailable={apiAvailable}
          degradedServices={degradedServicesList}
          onRetry={() => fetchSystemData(false)}
          isRetrying={isRetryingConnection}
        />

        {/* Top Status Bar */}
        <header className="h-14 shrink-0 border-b border-zinc-200/80 dark:border-zinc-800/80 px-6 flex items-center justify-between bg-white/70 dark:bg-[#111317]/80 backdrop-blur">
          <div className="flex items-center gap-4 text-xs">
            <LocalAIStatus
              status={
                !apiAvailable
                  ? 'unavailable'
                  : sysStatus?.llm === 'online'
                  ? 'online'
                  : sysStatus?.llm === 'local_fallback_ready'
                  ? 'local_fallback_ready'
                  : sysStatus
                  ? 'degraded'
                  : 'connecting'
              }
              modelName={sysStatus?.llm_details?.selected_model}
              onRetry={() => fetchSystemData(false)}
              isRetrying={isRetryingConnection}
            />
            <span className="text-zinc-300 dark:text-zinc-700">|</span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              Embeddings:{' '}
              <span className="font-mono text-zinc-500 dark:text-zinc-300">
                {sysStatus?.embedding?.model || 'multilingual-e5-small'}
              </span>
            </span>
            <span className="text-zinc-300 dark:text-zinc-700">|</span>
            <span className="font-mono text-zinc-500 dark:text-zinc-400">
              {sysStatus?.stats?.documents ?? 0} Docs • {sysStatus?.stats?.chunks ?? 0} Chunks
            </span>
          </div>

          {isAdmin && (
            <button
              onClick={() => setShowDebugDrawer(!showDebugDrawer)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono border transition ${
                showDebugDrawer
                  ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300'
                  : 'border-zinc-300 dark:border-zinc-800 text-zinc-500 hover:text-zinc-200'
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>RAG Observability</span>
            </button>
          )}
        </header>

        {/* Tab Views */}
        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 overflow-y-auto">
            {/* 1. CHAT & DYNAMIC WORKSPACE VIEW */}
            {activeTab === 'chat' && (
              <div className="h-full flex gap-4 px-4 py-4 overflow-hidden">
                {/* Left Column: Conversation Stream */}
                <div
                  className={`h-full flex flex-col ${
                    activeWorkspace ? 'flex-1 min-w-[340px]' : 'max-w-4xl w-full mx-auto'
                  }`}
                >
                  <div className="flex-1 overflow-y-auto space-y-6 pr-2">
                    {messages.length === 0 ? (
                      <div className="h-full flex flex-col items-center justify-center text-center py-10">
                        <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-4">
                          <Sparkles className="w-7 h-7" />
                        </div>
                        <h2 className="text-xl font-bold tracking-tight">
                          Structured Multimodal RAG Workspace
                        </h2>
                        <p className="text-sm text-zinc-500 dark:text-zinc-400 max-w-md mt-1">
                          Ask questions across PDFs, scanned marksheets, Word docs, XML records, images, or SQLite databases. Automatically renders tables, charts, KPIs, timelines, and interactive workspaces.
                        </p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 mt-6 w-full max-w-xl text-left">
                          {[
                            'What is our refund policy?',
                            'Show employee names and departments',
                            'Show revenue by month',
                            'Compare revenue across departments',
                            'How much did revenue increase?',
                            'Analyze Q1 performance',
                          ].map((sampleQ) => (
                            <button
                              key={sampleQ}
                              onClick={() => setQuestionInput(sampleQ)}
                              className="p-3 rounded-xl border border-zinc-200 dark:border-zinc-800/90 hover:border-emerald-500/50 bg-white dark:bg-zinc-900/60 text-xs text-zinc-600 dark:text-zinc-300 transition flex items-center justify-between group"
                            >
                              <span className="line-clamp-2">{sampleQ}</span>
                              <ChevronRight className="w-4 h-4 text-zinc-500 group-hover:text-emerald-400 shrink-0 ml-2" />
                            </button>
                          ))}
                        </div>
                      </div>
                    ) : (
                      messages.map((m) => (
                        <div
                          key={m.id}
                          className={`flex flex-col ${
                            m.role === 'user' ? 'items-end' : 'items-start'
                          }`}
                        >
                          <div
                            className={`w-full max-w-3xl rounded-2xl px-5 py-4 text-sm leading-relaxed ${
                              m.role === 'user'
                                ? 'max-w-xl bg-emerald-600 text-white'
                                : 'bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800'
                            }`}
                          >
                            {m.role === 'assistant' && m.answer_found !== undefined && (
                              <div className="mb-2 flex items-center justify-between gap-2">
                                <span
                                  className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-semibold ${
                                    m.answer_found
                                      ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                                      : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                                  }`}
                                >
                                  {m.answer_found ? 'ANSWER FOUND' : 'ANSWER NOT FOUND'}
                                </span>
                                {m.observability?.route && (
                                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500">
                                    route: {m.observability.route}
                                  </span>
                                )}
                              </div>
                            )}

                            {/* Render Structured Response via Component Registry if available */}
                            {m.role === 'assistant' && m.structured_response ? (
                              <ResponseBlock
                                structured={m.structured_response}
                                onSelectSource={(docId, chunkId, page) =>
                                  openDocumentPreview(docId, chunkId, page)
                                }
                                onOpenWorkspace={(ws) => setActiveWorkspace(ws)}
                                onMutateCommand={(cmd) =>
                                  handleMutateWorkspace(cmd, m.structured_response)
                                }
                              />
                            ) : (
                              <>
                                <div className="whitespace-pre-wrap">
                                  {m.content || 'Thinking...'}
                                </div>

                                {/* Clickable Source Citations */}
                                {m.role === 'assistant' &&
                                  m.citations &&
                                  m.citations.length > 0 && (
                                    <div className="mt-4 pt-3 border-t border-zinc-200 dark:border-zinc-800">
                                      <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 mb-2">
                                        Sources (Click to preview document & chunk)
                                      </div>
                                      <div className="flex flex-wrap gap-2">
                                        {m.citations.map((cit, idx) => (
                                          <button
                                            key={idx}
                                            onClick={() =>
                                              openDocumentPreview(
                                                cit.document_id,
                                                cit.chunk_id,
                                                cit.page_number
                                              )
                                            }
                                            className="text-xs px-2.5 py-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-800/90 hover:bg-emerald-500/20 hover:border-emerald-500/40 border border-zinc-300 dark:border-zinc-700 text-zinc-700 dark:text-zinc-200 transition flex items-center gap-1.5"
                                          >
                                            <span>{cit.label}</span>
                                            <Eye className="w-3 h-3 text-emerald-400" />
                                          </button>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                              </>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                    <div ref={chatEndRef} />
                  </div>

                  {/* Chat Input Bar */}
                  <form
                    onSubmit={handleSendChat}
                    className="mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-800/80 flex items-center gap-2.5"
                  >
                    <select
                      value={chatMode}
                      onChange={(e) => setChatMode(e.target.value as 'rag' | 'exact')}
                      className="px-3 py-3 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-800 text-xs font-medium"
                      title="Retrieval Mode"
                    >
                      <option value="rag">Semantic + Hybrid RAG</option>
                      <option value="exact">Exact / ID Match</option>
                    </select>
                    <input
                      type="text"
                      value={questionInput}
                      onChange={(e) => setQuestionInput(e.target.value)}
                      placeholder={`Ask a question or follow-up ("Make this a table", "Show revenue by month")...`}
                      className="flex-1 px-4 py-3 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-800 text-sm focus:outline-none focus:border-emerald-500"
                    />
                    <button
                      type="submit"
                      disabled={isStreaming}
                      className="px-5 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm font-medium flex items-center gap-2 transition"
                    >
                      <Send className="w-4 h-4" />
                      <span>Send</span>
                    </button>
                  </form>
                </div>

                {/* Right Column: Interactive Workspace / Artifact Canvas */}
                {activeWorkspace && (
                  <Workspace
                    workspace={activeWorkspace}
                    onClose={() => setActiveWorkspace(null)}
                    onMutate={(cmd) => handleMutateWorkspace(cmd, activeWorkspace)}
                    onRestoreVersion={(snap) => setActiveWorkspace(snap)}
                    onSelectSource={(docId, chunkId, page) =>
                      openDocumentPreview(docId, chunkId, page)
                    }
                  />
                )}
              </div>
            )}

            {/* 2. DASHBOARD VIEW */}
            {activeTab === 'dashboard' && (
              <div className="p-8 max-w-6xl mx-auto space-y-8">
                <div>
                  <h2 className="text-2xl font-bold tracking-tight">System Overview Dashboard</h2>
                  <p className="text-sm text-zinc-400 mt-1">
                    Real-time metrics across your local vector store, SQLite metadata, and hardware runtime.
                  </p>
                </div>

                {dataLoading ? (
                  <LoadingSkeleton variant="analytics" />
                ) : (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                      {
                        label: 'Indexed Documents',
                        val: sysStatus?.stats?.documents ?? 0,
                        sub: `${sysStatus?.stats?.ready_documents ?? 0} Ready`,
                      },
                      {
                        label: 'Knowledge Chunks',
                        val: sysStatus?.stats?.chunks ?? 0,
                        sub: `${sysStatus?.stats?.vectors ?? 0} Chroma Vectors`,
                      },
                      {
                        label: 'Active Collections',
                        val: sysStatus?.stats?.collections ?? 0,
                        sub: `Workspace: ${user.workspace}`,
                      },
                      {
                        label: 'Local Disk Usage',
                        val: `${sysStatus?.stats?.storage_mb ?? 0} MB`,
                        sub: '100% On-Premise NVMe',
                      },
                    ].map((card, i) => (
                      <div
                        key={i}
                        className="p-5 rounded-2xl bg-white dark:bg-zinc-900/70 border border-zinc-200 dark:border-zinc-800"
                      >
                        <div className="text-xs text-zinc-400 font-medium">{card.label}</div>
                        <div className="text-2xl font-bold mt-2">{card.val}</div>
                        <div className="text-xs text-emerald-400 mt-1">{card.sub}</div>
                      </div>
                    ))}
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/70 border border-zinc-200 dark:border-zinc-800 space-y-4">
                    <h3 className="font-semibold text-sm flex items-center gap-2">
                      <Cpu className="w-4 h-4 text-emerald-400" />
                      <span>Local AI Stack Status</span>
                    </h3>
                    <div className="space-y-2.5 text-xs">
                      <div className="flex justify-between py-1.5 border-b border-zinc-800">
                        <span className="text-zinc-400">Generation Model</span>
                        <span className="font-mono">
                          {sysStatus?.llm_details?.configured_model}
                        </span>
                      </div>
                      <div className="flex justify-between py-1.5 border-b border-zinc-800">
                        <span className="text-zinc-400">Embedding Model</span>
                        <span className="font-mono">
                          {sysStatus?.embedding_details?.model} ({sysStatus?.embedding_details?.device})
                        </span>
                      </div>
                      <div className="flex justify-between py-1.5 border-b border-zinc-800">
                        <span className="text-zinc-400">Vector Database</span>
                        <span className="font-mono">{sysStatus?.vector_details?.engine}</span>
                      </div>
                      <div className="flex justify-between py-1.5">
                        <span className="text-zinc-400">Local OCR Engine</span>
                        <span className="font-mono">{sysStatus?.ocr_details?.engine}</span>
                      </div>
                    </div>
                  </div>

                  <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/70 border border-zinc-200 dark:border-zinc-800 space-y-4">
                    <h3 className="font-semibold text-sm flex items-center gap-2">
                      <HardDrive className="w-4 h-4 text-emerald-400" />
                      <span>Detected Hardware Profile</span>
                    </h3>
                    <div className="space-y-2.5 text-xs">
                      <div className="flex justify-between py-1.5 border-b border-zinc-800">
                        <span className="text-zinc-400">Processor</span>
                        <span className="font-mono">{sysStatus?.cpu_Info}</span>
                      </div>
                      <div className="flex justify-between py-1.5 border-b border-zinc-800">
                        <span className="text-zinc-400">Dedicated GPU</span>
                        <span className="font-mono">{sysStatus?.gpu_name}</span>
                      </div>
                      <div className="flex justify-between py-1.5 border-b border-zinc-800">
                        <span className="text-zinc-400">System Memory</span>
                        <span className="font-mono">
                          {sysStatus?.ram_total_gb} GB ({sysStatus?.ram_used_pct}% used)
                        </span>
                      </div>
                      <div className="flex justify-between py-1.5">
                        <span className="text-zinc-400">Offline Privacy Enforcement</span>
                        <span className="text-emerald-400 font-semibold">ACTIVE (OFFLINE_MODE=true)</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 3. MULTIMODAL UPLOAD & DATABASE INGESTION VIEW */}
            {activeTab === 'upload' && (
              <div className="p-8 max-w-4xl mx-auto space-y-8">
                <div>
                  <h2 className="text-2xl font-bold tracking-tight">Multimodal Knowledge Ingestion</h2>
                  <p className="text-sm text-zinc-400 mt-1">
                    Upload PDFs, Scanned PDFs, Word (.docx/.doc), XML, Images (.png/.jpg/.webp), Audio (.wav/.mp3), or SQLite Databases (.db).
                  </p>
                </div>

                <div className="flex items-center gap-4">
                  <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                    Target Collection:
                  </label>
                  <select
                    value={uploadCollection}
                    onChange={(e) => setUploadCollection(e.target.value)}
                    className="px-3.5 py-2 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-800 text-xs font-medium"
                  >
                    {collections.map((c) => (
                      <option key={c.id} value={c.name}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Drag and Drop Box */}
                <label
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    handleFileUpload(e.dataTransfer.files);
                  }}
                  className="block border-2 border-dashed border-zinc-300 dark:border-zinc-800 hover:border-emerald-500/60 rounded-2xl p-10 text-center cursor-pointer bg-white/40 dark:bg-zinc-900/40 transition"
                >
                  <input
                    type="file"
                    className="hidden"
                    onChange={(e) => handleFileUpload(e.target.files)}
                  />
                  <UploadCloud className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
                  <div className="text-base font-semibold">
                    Drag & Drop files here, or click to browse
                  </div>
                  <p className="text-xs text-zinc-400 mt-1">
                    Supported: PDF, Scanned PDF (Auto-OCR), DOCX, DOC, TXT, XML, PNG, JPG, JPEG, WEBP, SQLite (.db), WAV/MP3 (Max {sysStatus?.max_mb || 100} MB)
                  </p>
                </label>

                {/* Step-by-Step Pipeline Progress */}
                {uploadStageIdx >= 0 && (
                  <div className="p-5 rounded-2xl bg-zinc-900 border border-zinc-800 space-y-3">
                    <div className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                      Ingestion Pipeline Progress
                    </div>
                    <div className="grid grid-cols-7 gap-2">
                      {PROCESSING_STAGES.map((st, idx) => {
                        const done = idx <= uploadStageIdx;
                        return (
                          <div
                            key={st}
                            className={`p-2 rounded-lg text-center text-[11px] font-mono border ${
                              done
                                ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300'
                                : 'bg-zinc-950 border-zinc-800 text-zinc-500'
                            }`}
                          >
                            {st}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {uploadError && (
                  <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/60 text-xs text-red-300 flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
                    <div>
                      <div className="font-semibold">Ingestion Error</div>
                      <div className="mt-1">{uploadError}</div>
                    </div>
                  </div>
                )}

                {uploadResult && (
                  <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-800/50 text-xs text-emerald-200 flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                    <div>
                      <div className="font-semibold">
                        {uploadResult.duplicate
                          ? 'Duplicate File Detected (Skipped Re-Indexing)'
                          : `Successfully Indexed: ${uploadResult.document?.filename}`}
                      </div>
                      <div className="mt-1 text-zinc-300">
                        Status: {uploadResult.document?.status} • Version: v
                        {uploadResult.document?.version} • Chunks:{' '}
                        {uploadResult.document?.chunk_count} • Modality:{' '}
                        {uploadResult.document?.modality}
                      </div>
                    </div>
                  </div>
                )}

                {/* SQLite / PostgreSQL / MySQL Connector */}
                <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/70 border border-zinc-200 dark:border-zinc-800 space-y-4">
                  <div className="flex items-center gap-2">
                    <Database className="w-5 h-5 text-emerald-400" />
                    <h3 className="font-semibold text-sm">
                      Structured Database Ingestion (SQLite / PostgreSQL / MySQL)
                    </h3>
                  </div>
                  <p className="text-xs text-zinc-400">
                    Inspect database tables and selectively index structured rows with primary keys and column metadata.
                  </p>
                  <div className="flex gap-3">
                    <input
                      type="text"
                      value={dbConnUrl}
                      onChange={(e) => setDbConnUrl(e.target.value)}
                      placeholder="Path to SQLite file (e.g. ./data/metadata/app.db) or postgresql://user:pass@localhost:5432/dbname"
                      className="flex-1 px-3.5 py-2 rounded-xl bg-zinc-950 border border-zinc-800 text-xs font-mono"
                    />
                    <button
                      type="button"
                      onClick={handleInspectDatabase}
                      className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-xs font-medium"
                    >
                      Inspect Schema
                    </button>
                  </div>

                  {inspectedTables.length > 0 && (
                    <div className="space-y-3 pt-2">
                      <div className="text-xs font-medium text-zinc-300">
                        Select Tables to Serialize & Vectorize:
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {inspectedTables.map((tb) => {
                          const isChecked = checkedTables.includes(tb.table);
                          return (
                            <label
                              key={tb.table}
                              className="flex items-center justify-between p-3 rounded-xl bg-zinc-950 border border-zinc-800 text-xs cursor-pointer"
                            >
                              <div className="flex items-center gap-2">
                                <input
                                  type="checkbox"
                                  checked={isChecked}
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      setCheckedTables([...checkedTables, tb.table]);
                                    } else {
                                      setCheckedTables(checkedTables.filter((x) => x !== tb.table));
                                    }
                                  }}
                                />
                                <span className="font-mono font-semibold">{tb.table}</span>
                              </div>
                              <span className="text-zinc-500 font-mono">
                                {tb.row_count} rows ({tb.columns.length} cols)
                              </span>
                            </label>
                          );
                        })}
                      </div>
                      <button
                        type="button"
                        onClick={handleIngestDatabase}
                        className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium"
                      >
                        Index Selected Tables ({checkedTables.length})
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 4. DOCUMENTS & VERSIONING VIEW */}
            {activeTab === 'documents' && (
              <div className="p-8 max-w-6xl mx-auto space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-2xl font-bold tracking-tight">
                      Knowledge Base Documents & Versions
                    </h2>
                    <p className="text-sm text-zinc-400 mt-1">
                      Inspect processing status, SHA-256 content hashes, chunk counts, or re-index/delete documents.
                    </p>
                  </div>
                  <button
                    onClick={() => fetchSystemData(false)}
                    className="px-3.5 py-2 rounded-xl border border-zinc-800 hover:bg-zinc-800 text-xs flex items-center gap-1.5"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Refresh</span>
                  </button>
                </div>

                {dataLoading ? (
                  <LoadingSkeleton variant="documents" count={4} />
                ) : (
                <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 overflow-hidden bg-white dark:bg-zinc-900/50">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-zinc-200 dark:border-zinc-800 text-zinc-400 bg-zinc-900/40">
                        <th className="py-3.5 px-4">Document</th>
                        <th className="py-3.5 px-4">Modality</th>
                        <th className="py-3.5 px-4">Collection</th>
                        <th className="py-3.5 px-4">Access Policy</th>
                        <th className="py-3.5 px-4">Version & SHA-256</th>
                        <th className="py-3.5 px-4">Status</th>
                        <th className="py-3.5 px-4">Chunks</th>
                        <th className="py-3.5 px-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800/70">
                      {documents.map((doc) => (
                        <tr key={doc.id} className="hover:bg-zinc-800/20">
                          <td className="py-3.5 px-4 font-medium">
                            <div>{doc.filename}</div>
                            {doc.error_message && (
                              <div className="text-[11px] text-red-400 mt-1">
                                Reason: {doc.error_message}
                                {doc.suggested_action && (
                                  <span className="block text-amber-300">
                                    Suggested: {doc.suggested_action}
                                  </span>
                                )}
                              </div>
                            )}
                          </td>
                          <td className="py-3.5 px-4 font-mono uppercase text-[11px] text-zinc-400">
                            {doc.modality}
                          </td>
                          <td className="py-3.5 px-4">
                            <span className="px-2 py-0.5 rounded bg-zinc-800 text-zinc-300">
                              {doc.collection}
                            </span>
                          </td>
                          <td className="py-3.5 px-4">
                            <span
                              className={`px-2 py-0.5 rounded font-mono text-[10px] ${
                                doc.access_level === 'ADMIN_ONLY'
                                  ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                                  : doc.access_level === 'DEPARTMENT_ONLY' || doc.access_level === 'GROUP_ONLY'
                                  ? 'bg-sky-500/15 text-sky-300 border border-sky-500/30'
                                  : doc.access_level === 'USER_SPECIFIC'
                                  ? 'bg-purple-500/15 text-purple-300 border border-purple-500/30'
                                  : 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                              }`}
                            >
                              {doc.access_level || 'EMPLOYEE_SHARED'}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 font-mono text-zinc-400">
                            v{doc.version} • {doc.content_hash?.slice(0, 10)}...
                          </td>
                          <td className="py-3.5 px-4">
                            <span
                              className={`px-2 py-0.5 rounded font-medium ${
                                doc.status === 'Ready'
                                  ? 'bg-emerald-500/15 text-emerald-400'
                                  : doc.status === 'Failed'
                                  ? 'bg-red-500/15 text-red-400'
                                  : 'bg-amber-500/15 text-amber-400'
                              }`}
                            >
                              {doc.status}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 font-mono">{doc.chunk_count}</td>
                          <td className="py-3.5 px-4 text-right space-x-2">
                            <button
                              onClick={() => openDocumentPreview(doc.id)}
                              className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-300"
                              title="Preview Chunks & Metadata"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                            {Boolean(doc.modality === 'image' || /\.(png|jpe?g|webp|bmp)$/i.test(doc.filename || '')) && (
                              <button
                                onClick={() => openVectorizer(doc.id, doc.filename)}
                                className="p-1.5 rounded-lg hover:bg-purple-500/20 text-purple-400"
                                title="Vectorize Image to Scalable SVG"
                              >
                                <Sparkles className="w-4 h-4" />
                              </button>
                            )}
                            {isAdmin && (
                              <>
                                <button
                                  onClick={() => handleReindexDocument(doc.id)}
                                  className="p-1.5 rounded-lg hover:bg-zinc-800 text-emerald-400"
                                  title="Re-index Document"
                                >
                                  <RefreshCw className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => handleDeleteDocument(doc.id)}
                                  className="p-1.5 rounded-lg hover:bg-red-500/20 text-red-400"
                                  title="Delete Document & Vectors"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </>
                            )}
                          </td>
                        </tr>
                      ))}
                      {documents.length === 0 && (
                        <tr>
                          <td colSpan={8} className="py-8 text-center text-zinc-500">
                            No documents uploaded yet. Go to Multimodal Ingestion to add files.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
                )}
              </div>
            )}

            {/* 5. DIRECT KNOWLEDGE BASE SEARCH VIEW */}
            {activeTab === 'search' && (
              <div className="p-8 max-w-5xl mx-auto space-y-6">
                <div>
                  <h2 className="text-2xl font-bold tracking-tight">
                    Direct Knowledge Base Search
                  </h2>
                  <p className="text-sm text-zinc-400 mt-1">
                    Search indexed chunks directly before invoking the LLM — inspect similarity scores, exact matches, and page locators.
                  </p>
                </div>

                <form onSubmit={handleDirectSearch} className="flex gap-3">
                  <select
                    value={searchMode}
                    onChange={(e) => setSearchMode(e.target.value as 'rag' | 'exact')}
                    className="px-3.5 py-2.5 rounded-xl bg-zinc-900 border border-zinc-800 text-xs"
                  >
                    <option value="rag">Hybrid Vector + BM25</option>
                    <option value="exact">Exact Keyword / ID Match</option>
                  </select>
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search knowledge base (e.g. 'refund policy', 'EMP-184', '15 November 2026')..."
                    className="flex-1 px-4 py-2.5 rounded-xl bg-zinc-900 border border-zinc-800 text-sm focus:outline-none focus:border-emerald-500"
                  />
                  <button
                    type="submit"
                    className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium"
                  >
                    Search Chunks
                  </button>
                </form>

                {searchTiming && (
                  <div className="text-xs font-mono text-zinc-400">
                    Found {searchResults.length} matching chunks (Embedding: {searchTiming.emb} ms •
                    Total Retrieval: {searchTiming.ret} ms)
                  </div>
                )}

                <div className="space-y-3">
                  {searchResults.map((r) => (
                    <div
                      key={r.chunk_id}
                      className="p-4 rounded-2xl bg-white dark:bg-zinc-900/70 border border-zinc-200 dark:border-zinc-800 space-y-2"
                    >
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2 font-semibold text-emerald-400">
                          <span>{r.citation?.label}</span>
                          <span className="px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 font-mono text-[10px]">
                            Collection: {r.collection}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 font-mono text-[11px] text-zinc-400">
                          <span>Score: {(r.similarity * 100).toFixed(1)}%</span>
                          <button
                            onClick={() =>
                              openDocumentPreview(r.document_id, r.chunk_id, r.page_number)
                            }
                            className="text-emerald-400 hover:underline"
                          >
                            Inspect in Document →
                          </button>
                        </div>
                      </div>
                      <p className="text-xs text-zinc-300 whitespace-pre-wrap font-mono bg-zinc-950/70 p-3 rounded-xl border border-zinc-800/80">
                        {r.content}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 6. COLLECTIONS & TEAM ACCESS VIEW */}
            {activeTab === 'collections' && (
              <div className="p-8 max-w-5xl mx-auto space-y-8">
                <div>
                  <h2 className="text-2xl font-bold tracking-tight">
                    Collections & Multi-Tenant Team Permissions
                  </h2>
                  <p className="text-sm text-zinc-400 mt-1">
                    Organize documents into isolated collections inside workspace{' '}
                    <span className="font-mono text-emerald-400">{user.workspace}</span>.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {collections.map((c) => (
                    <div
                      key={c.id}
                      className="p-5 rounded-2xl bg-white dark:bg-zinc-900/70 border border-zinc-200 dark:border-zinc-800 flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-center justify-between">
                          <h3 className="font-bold text-sm">📁 {c.name}</h3>
                          <span className="text-xs font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-300">
                            {c.document_count} docs
                          </span>
                        </div>
                        <p className="text-xs text-zinc-400 mt-2">{c.description}</p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Create Collection Form */}
                <form
                  onSubmit={handleCreateCollection}
                  className="p-6 rounded-2xl bg-zinc-900/60 border border-zinc-800 space-y-4 max-w-xl"
                >
                  <h3 className="text-sm font-semibold flex items-center gap-2">
                    <Plus className="w-4 h-4 text-emerald-400" />
                    <span>Create New Collection</span>
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <input
                      type="text"
                      value={newColName}
                      onChange={(e) => setNewColName(e.target.value)}
                      placeholder="Collection Name (e.g. Legal)"
                      className="px-3.5 py-2 rounded-xl bg-zinc-950 border border-zinc-800 text-xs"
                    />
                    <input
                      type="text"
                      value={newColDesc}
                      onChange={(e) => setNewColDesc(e.target.value)}
                      placeholder="Description"
                      className="px-3.5 py-2 rounded-xl bg-zinc-950 border border-zinc-800 text-xs"
                    />
                  </div>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium"
                  >
                    Create Collection
                  </button>
                </form>

                {/* Admin User Management */}
                {isAdmin && (
                  <div className="p-6 rounded-2xl bg-zinc-900/60 border border-zinc-800 space-y-4">
                    <h3 className="text-sm font-semibold flex items-center gap-2">
                      <Users className="w-4 h-4 text-emerald-400" />
                      <span>Team Members (Argon2 Password Hashed)</span>
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {usersList.map((u) => (
                        <div
                          key={u.id}
                          className="p-3.5 rounded-xl bg-zinc-950 border border-zinc-800 flex items-center justify-between text-xs"
                        >
                          <div>
                            <span className="font-semibold">{u.username}</span>
                            <span className="ml-2 px-1.5 py-0.5 rounded bg-zinc-800 font-mono text-[10px]">
                              {u.role}
                            </span>
                          </div>
                          <div className="text-zinc-400 font-mono text-[11px]">
                            Collections: {u.allowed_collections?.join(', ')}
                          </div>
                        </div>
                      ))}
                    </div>

                    <form onSubmit={handleCreateUser} className="flex flex-wrap gap-3 pt-2">
                      <input
                        type="text"
                        value={newUsername}
                        onChange={(e) => setNewUsername(e.target.value)}
                        placeholder="New teammate username"
                        className="px-3.5 py-2 rounded-xl bg-zinc-950 border border-zinc-800 text-xs"
                      />
                      <input
                        type="password"
                        value={newUserPassword}
                        onChange={(e) => setNewUserPassword(e.target.value)}
                        placeholder="Password"
                        className="px-3.5 py-2 rounded-xl bg-zinc-950 border border-zinc-800 text-xs"
                      />
                      <select
                        value={newUserRole}
                        onChange={(e) => setNewUserRole(e.target.value as any)}
                        className="px-3.5 py-2 rounded-xl bg-zinc-950 border border-zinc-800 text-xs"
                      >
                        <option value="employee">EMPLOYEE</option>
                        <option value="admin">ADMIN</option>
                      </select>
                      <button
                        type="submit"
                        className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium"
                      >
                        Add Teammate
                      </button>
                    </form>
                  </div>
                )}
              </div>
            )}

            {/* 7. ADMIN WORKPLACE CONTROL PLANE & RBAC CONSOLE */}
            {activeTab === 'admin' && isAdmin && (
              <AdminConsole
                token={token}
                currentUser={user}
                workplace={workplace}
                workplaces={workplaces}
                onSwitchWorkplace={handleSwitchWorkplace}
                onCreateWorkplace={handleCreateWorkplace}
                documents={documents}
                collections={collections}
                sysStatus={sysStatus}
                activeSection={adminSection}
                onChangeSection={setAdminSection}
                onNavigateToUpload={() => setActiveTab('upload')}
                onNavigateToChat={() => setActiveTab('chat')}
                onOpenDocumentPreview={(docId) => openDocumentPreview(docId)}
                onRefreshGlobalData={() => fetchSystemData(false)}
              />
            )}

            {/* 8. SYSTEM HEALTH VIEW */}
            {activeTab === 'health' && (
              <div className="p-8 max-w-4xl mx-auto space-y-6">
                <div>
                  <h2 className="text-2xl font-bold tracking-tight">System Health</h2>
                  <p className="text-sm text-zinc-400 mt-1">
                    Live verification of all local RAG subsystems and offline privacy enforcement.
                  </p>
                </div>

                <div className="p-6 rounded-2xl bg-zinc-900 border border-zinc-800 font-mono text-sm space-y-3">
                  {[
                    {
                      name: 'LLM',
                      ok: true,
                      label:
                        sysStatus?.llm === 'online'
                          ? `✓ Connected (${sysStatus?.llm_details?.selected_model})`
                          : `✓ Local Fallback Active (Configured for ${sysStatus?.llm_details?.configured_model})`,
                    },
                    {
                      name: 'Embedding',
                      ok: true,
                      label: `✓ Loaded (${sysStatus?.embedding_details?.model} on ${sysStatus?.embedding_details?.device?.toUpperCase()})`,
                    },
                    {
                      name: 'Vector DB',
                      ok: sysStatus?.vector_database === 'online',
                      label: `✓ Connected (${sysStatus?.vector_details?.engine})`,
                    },
                    {
                      name: 'SQLite',
                      ok: sysStatus?.sqlite === 'online',
                      label: '✓ Connected (./data/metadata/app.db)',
                    },
                    {
                      name: 'OCR',
                      ok: sysStatus?.ocr === 'available',
                      label:
                        sysStatus?.ocr === 'available'
                          ? `✓ Available (${sysStatus?.ocr_details?.engine})`
                          : '○ Unavailable',
                    },
                    {
                      name: 'Whisper',
                      ok: sysStatus?.audio === 'available',
                      label:
                        sysStatus?.audio === 'available'
                          ? '✓ Available'
                          : '○ Disabled (Optional Phase 2 — set AUDIO_ENABLED=true)',
                    },
                    {
                      name: 'GPU Hardware',
                      ok: true,
                      label: `✓ ${sysStatus?.gpu_name} (VRAM preserved for Ollama)`,
                      },
                    {
                      name: 'Offline Mode',
                      ok: sysStatus?.offline_mode === true,
                      label: sysStatus?.offline_mode ? '✓ Enabled (100% Local)' : '○ Disabled',
                    },
                  ].map((row) => (
                    <div
                      key={row.name}
                      className="flex items-center justify-between py-2 border-b border-zinc-800/80 last:border-none"
                    >
                      <span className="text-zinc-400 w-40">{row.name}</span>
                      <span className={row.ok ? 'text-emerald-400' : 'text-zinc-500'}>
                        {row.label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* ─── Admin Observability Drawer ─── */}
          {showDebugDrawer && isAdmin && (
            <aside className="w-96 border-l border-zinc-800 bg-zinc-900/90 p-5 overflow-y-auto space-y-4 text-xs font-mono">
              <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
                <span className="font-bold text-emerald-400">RAG OBSERVABILITY PANEL</span>
                <button onClick={() => setShowDebugDrawer(false)}>
                  <X className="w-4 h-4 text-zinc-400" />
                </button>
              </div>
              {!activeObservability ? (
                <div className="text-zinc-500">
                  Run a query in the Chat tab to inspect embedding latency, retrieved chunks, similarity scores, and final prompt context.
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <div className="text-zinc-500">Query:</div>
                    <div className="text-zinc-100 mt-0.5">{activeObservability.query}</div>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <div className="p-2 rounded bg-zinc-950 border border-zinc-800">
                      <div className="text-[10px] text-zinc-500">Embedding</div>
                      <div className="text-emerald-400">
                        {activeObservability.embedding_time_ms} ms
                      </div>
                    </div>
                    <div className="p-2 rounded bg-zinc-950 border border-zinc-800">
                      <div className="text-[10px] text-zinc-500">Retrieval</div>
                      <div className="text-emerald-400">
                        {activeObservability.retrieval_time_ms} ms
                      </div>
                    </div>
                    <div className="p-2 rounded bg-zinc-950 border border-zinc-800">
                      <div className="text-[10px] text-zinc-500">LLM Time</div>
                      <div className="text-emerald-400">
                        {activeObservability.llm_time_ms ?? 0} ms
                      </div>
                    </div>
                  </div>
                  <div>
                    <div className="text-zinc-500 mb-1.5">
                      Retrieved Chunks ({activeObservability.retrieved_chunks?.length || 0}):
                    </div>
                    <div className="space-y-2">
                      {(activeObservability.retrieved_chunks || []).map((ch, i) => (
                        <div
                          key={i}
                          className="p-2.5 rounded bg-zinc-950 border border-zinc-800 space-y-1"
                        >
                          <div className="flex justify-between text-emerald-400">
                            <span>
                              #{i + 1} {ch.filename} ({ch.locator})
                            </span>
                            <span>{(ch.similarity * 100).toFixed(1)}%</span>
                          </div>
                          <div className="text-zinc-400 line-clamp-3">{ch.content}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </aside>
          )}
        </div>
      </main>

      {/* ─── Document & Chunk Preview Modal ─── */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-6">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-4xl w-full max-h-[85vh] flex flex-col overflow-hidden shadow-2xl">
            <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-base flex items-center gap-2">
                  <span>{previewDoc.document?.filename}</span>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400">
                    v{previewDoc.document?.version} • {previewDoc.document?.modality}
                  </span>
                </h3>
                <p className="text-xs text-zinc-400 mt-0.5">
                  Collection: {previewDoc.document?.collection} • SHA-256:{' '}
                  {previewDoc.document?.content_hash?.slice(0, 16)}...
                </p>
              </div>
              <button
                onClick={() => setPreviewDoc(null)}
                className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-400"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {previewDoc.document?.modality === 'image' && (
                <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800 text-center space-y-3">
                  <img
                    src={`/api/documents/${previewDoc.document.id}/file`}
                    alt={previewDoc.document.filename}
                    className="max-h-72 mx-auto rounded-lg"
                  />
                  <div>
                    <button
                      type="button"
                      onClick={() => openVectorizer(previewDoc.document.id, previewDoc.document.filename)}
                      className="px-3.5 py-1.5 rounded-lg bg-purple-500/15 border border-purple-500/30 text-purple-300 hover:bg-purple-500/25 text-xs font-medium inline-flex items-center gap-1.5 transition-colors"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Vectorize to Scalable SVG</span>
                    </button>
                  </div>
                </div>
              )}

              <div className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Indexed Document Chunks ({previewDoc.chunks?.length || 0})
              </div>
              <div className="space-y-3">
                {(previewDoc.chunks || []).map((ch: any) => {
                  const isHighlighted =
                    ch.id === previewHighlightChunkId ||
                    (previewHighlightPage && ch.page_number === previewHighlightPage);
                  return (
                    <div
                      key={ch.id}
                      className={`p-4 rounded-xl border text-xs font-mono whitespace-pre-wrap transition ${
                        isHighlighted
                          ? 'bg-emerald-950/40 border-emerald-500 text-emerald-100 ring-1 ring-emerald-500/50'
                          : 'bg-zinc-950 border-zinc-800 text-zinc-300'
                      }`}
                    >
                      <div className="flex justify-between text-[11px] text-zinc-400 mb-2 pb-1.5 border-b border-zinc-800">
                        <span className="font-semibold text-emerald-400">
                          Chunk #{ch.chunk_index} — Page/Record {ch.page_number}{' '}
                          {ch.section_title ? `• ${ch.section_title}` : ''}
                        </span>
                        {isHighlighted && (
                          <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                            Cited Source Match
                          </span>
                        )}
                      </div>
                      {ch.content}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─── Raster-to-Vector SVG Tracing Modal ─── */}
      <ImageVectorizerModal
        isOpen={vectorizerOpen}
        onClose={() => setVectorizerOpen(false)}
        token={token || undefined}
        initialDocId={vectorizerDocId}
        initialFilename={vectorizerFilename}
      />
    </div>
  );
}
