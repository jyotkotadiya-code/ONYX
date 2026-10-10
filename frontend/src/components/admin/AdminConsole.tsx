import React, { useState, useEffect, useCallback } from 'react';
import {
  Shield,
  Users,
  Building2,
  UsersRound,
  FileLock2,
  FolderLock,
  KeyRound,
  Eye,
  ScrollText,
  Activity,
  Plus,
  CheckCircle2,
  RefreshCw,
  Trash2,
  UserCheck,
  UserX,
  Lock,
  X,
  BarChart3,
  Settings,
  Archive,
  FolderInput,
  UploadCloud,
  MessageSquare,
  Copy,
  Check,
  Sparkles,
  FileText,
  ExternalLink,
} from 'lucide-react';
import { ImageVectorizerModal } from '../tools/ImageVectorizerModal';

export type AdminSection =
  | 'overview'
  | 'employees'
  | 'knowledge'
  | 'collections'
  | 'access'
  | 'analytics'
  | 'settings'
  | 'audit';

interface AdminConsoleProps {
  token: string;
  currentUser: any;
  workplace: any;
  workplaces: any[];
  onSwitchWorkplace: (workplaceId: string) => Promise<void>;
  onCreateWorkplace: (payload: any) => Promise<void>;
  documents: any[];
  collections: any[];
  sysStatus: any;
  activeSection?: AdminSection;
  onChangeSection?: (sec: AdminSection) => void;
  onNavigateToUpload?: () => void;
  onNavigateToChat?: () => void;
  onOpenDocumentPreview?: (docId: string) => void;
  onRefreshGlobalData: () => void;
}

const ACCESS_LEVEL_LABELS: Record<string, { label: string; color: string }> = {
  ADMIN_ONLY: {
    label: 'Admin Only',
    color: 'bg-rose-500/15 text-rose-600 dark:text-rose-300 border-rose-500/30',
  },
  EMPLOYEE_SHARED: {
    label: 'All Employees',
    color: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-300 border-emerald-500/30',
  },
  DEPARTMENT_ONLY: {
    label: 'Department Only',
    color: 'bg-blue-500/15 text-blue-600 dark:text-blue-300 border-blue-500/30',
  },
  GROUP_ONLY: {
    label: 'Group Only',
    color: 'bg-purple-500/15 text-purple-600 dark:text-purple-300 border-purple-500/30',
  },
  USER_SPECIFIC: {
    label: 'Selected Users',
    color: 'bg-amber-500/15 text-amber-600 dark:text-amber-300 border-amber-500/30',
  },
};

export const AdminConsole: React.FC<AdminConsoleProps> = ({
  token,
  currentUser,
  workplace,
  workplaces,
  onSwitchWorkplace,
  onCreateWorkplace,
  documents,
  collections,
  sysStatus,
  activeSection,
  onChangeSection,
  onNavigateToUpload,
  onNavigateToChat,
  onOpenDocumentPreview,
  onRefreshGlobalData,
}) => {
  const [internalSection, setInternalSection] = useState<AdminSection>('overview');
  const section = activeSection || internalSection;
  const setSection = (s: AdminSection) => {
    setInternalSection(s);
    if (onChangeSection) onChangeSection(s);
  };

  const [users, setUsers] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [groups, setGroups] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [permissionsConfig, setPermissionsConfig] = useState<any>(null);
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

  // Employee Creation & Invite State
  const [empCreationMode, setEmpCreationMode] = useState<'create' | 'invite'>('create');
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newName, setNewName] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newRole, setNewRole] = useState<'employee' | 'admin'>('employee');
  const [newJobTitle, setNewJobTitle] = useState('Software Developer');
  const [newDeptId, setNewDeptId] = useState('');
  const [newGroupIds, setNewGroupIds] = useState<string[]>([]);
  const [newCanUpload, setNewCanUpload] = useState(false);
  const [generatedInvite, setGeneratedInvite] = useState<{
    username: string;
    token: string;
  } | null>(null);
  const [copiedInvite, setCopiedInvite] = useState(false);

  // Employee Profile Drawer State
  const [selectedEmpProfile, setSelectedEmpProfile] = useState<any | null>(null);
  const [resetPwdValue, setResetPwdValue] = useState('');

  // Department & Group Creation State
  const [deptName, setDeptName] = useState('');
  const [deptDesc, setDeptDesc] = useState('');
  const [groupName, setGroupName] = useState('');
  const [groupDesc, setGroupDesc] = useState('');
  const [groupMemberIds, setGroupMemberIds] = useState<string[]>([]);

  // New Collection State
  const [newColName, setNewColName] = useState('');
  const [newColDesc, setNewColDesc] = useState('');
  const [newColAccess, setNewColAccess] = useState('EMPLOYEE_SHARED');

  // Knowledge Filters & Document Access Editor Modal State
  const [docSearchFilter, setDocSearchFilter] = useState('');
  const [docColFilter, setDocColFilter] = useState('ALL');
  const [docPolicyFilter, setDocPolicyFilter] = useState('ALL');
  const [editingDoc, setEditingDoc] = useState<any | null>(null);
  const [docAccessLevel, setDocAccessLevel] = useState<string>('EMPLOYEE_SHARED');
  const [docDeptId, setDocDeptId] = useState<string>('');
  const [docGroupIds, setDocGroupIds] = useState<string[]>([]);
  const [docUserIds, setDocUserIds] = useState<string[]>([]);

  // Access Simulator & Test State
  const [previewUserId, setPreviewUserId] = useState<string>('');
  const [previewData, setPreviewData] = useState<any | null>(null);
  const [testUserId, setTestUserId] = useState<string>('');
  const [testDocId, setTestDocId] = useState<string>('');
  const [testResult, setTestResult] = useState<any | null>(null);

  // Workplace Settings Form State
  const [wpName, setWpName] = useState('');
  const [wpSlug, setWpSlug] = useState('');
  const [wpDesc, setWpDesc] = useState('');
  const [wpIndustry, setWpIndustry] = useState('');
  const [wpAssistantName, setWpAssistantName] = useState('ONYX AI');
  const [wpWelcomeMsg, setWpWelcomeMsg] = useState('');
  const [wpDefaultVisibility, setWpDefaultVisibility] = useState('EMPLOYEE_SHARED');
  const [wpAllowEmpUploads, setWpAllowEmpUploads] = useState(false);

  // Create New Workplace Modal State
  const [showCreateWpModal, setShowCreateWpModal] = useState(false);
  const [createWpName, setCreateWpName] = useState('');
  const [createWpSlug, setCreateWpSlug] = useState('');
  const [createWpDesc, setCreateWpDesc] = useState('');
  const [createWpIndustry, setCreateWpIndustry] = useState('Technology');

  // Image Vectorizer Modal State
  const [vectorizerOpen, setVectorizerOpen] = useState(false);
  const [vectorizerDocId, setVectorizerDocId] = useState<string | undefined>(undefined);
  const [vectorizerFilename, setVectorizerFilename] = useState<string | undefined>(undefined);

  const openVectorizer = (docId?: string, filename?: string) => {
    setVectorizerDocId(docId);
    setVectorizerFilename(filename);
    setVectorizerOpen(true);
  };

  const authHeaders = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  const notify = (type: 'ok' | 'err', text: string) => {
    setFeedback({ type, text });
    setTimeout(() => setFeedback(null), 4500);
  };

  useEffect(() => {
    if (workplace) {
      setWpName(workplace.name || '');
      setWpSlug(workplace.slug || '');
      setWpDesc(workplace.description || '');
      setWpIndustry(workplace.industry || 'Technology');
      setWpAssistantName(workplace.assistant_name || 'ONYX AI');
      setWpWelcomeMsg(workplace.welcome_message || '');
      setWpDefaultVisibility(workplace.default_doc_visibility || 'EMPLOYEE_SHARED');
      setWpAllowEmpUploads(Boolean(workplace.allow_employee_uploads));
    }
  }, [workplace]);

  const fetchAdminData = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [uRes, dRes, gRes, pRes, aRes, anRes] = await Promise.all([
        fetch('/api/users', { headers: { Authorization: `Bearer ${token}` } }),
        fetch('/api/departments', { headers: { Authorization: `Bearer ${token}` } }),
        fetch('/api/groups', { headers: { Authorization: `Bearer ${token}` } }),
        fetch('/api/admin/permissions', { headers: { Authorization: `Bearer ${token}` } }),
        fetch('/api/admin/audit-logs?limit=100', { headers: { Authorization: `Bearer ${token}` } }),
        fetch('/api/admin/analytics', { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      if (uRes.ok) {
        const uList = await uRes.json();
        setUsers(uList);
        if (!previewUserId && uList.length > 0) {
          const firstEmp = uList.find((x: any) => x.role === 'employee') || uList[0];
          setPreviewUserId(firstEmp.id);
          setTestUserId(firstEmp.id);
        }
      }
      if (dRes.ok) setDepartments(await dRes.json());
      if (gRes.ok) setGroups(await gRes.json());
      if (pRes.ok) setPermissionsConfig(await pRes.json());
      if (aRes.ok) setAuditLogs(await aRes.json());
      if (anRes.ok) setAnalytics(await anRes.json());
    } catch (e: any) {
      notify('err', e.message || 'Failed loading workplace admin data');
    } finally {
      setLoading(false);
    }
  }, [token, previewUserId]);

  useEffect(() => {
    fetchAdminData();
  }, [fetchAdminData]);

  useEffect(() => {
    if (documents.length > 0 && !testDocId) {
      setTestDocId(documents[0].id);
    }
  }, [documents, testDocId]);

  // Create or Invite Employee
  const handleCreateOrInviteUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (empCreationMode === 'invite') {
        if (!newName.trim() && !newUsername.trim()) return;
        const res = await fetch('/api/users/invite', {
          method: 'POST',
          headers: authHeaders,
          body: JSON.stringify({
            name: newName.trim() || newUsername.trim(),
            email: newEmail.trim(),
            username: newUsername.trim() || undefined,
            job_title: newJobTitle.trim(),
            department_id: newDeptId || null,
            group_ids: newGroupIds,
            can_upload: newCanUpload,
            allowed_collections: ['General', 'Company Policies'],
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed generating employee invite');
        setGeneratedInvite({
          username: data.user.username,
          token: data.invite_token,
        });
        setNewName('');
        setNewEmail('');
        setNewUsername('');
        notify('ok', `Generated workplace invite code for @${data.user.username}`);
        fetchAdminData();
        return;
      }

      if (!newUsername.trim() || !newPassword.trim()) return;
      const res = await fetch('/api/users', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          username: newUsername.trim(),
          password: newPassword,
          name: newName.trim() || newUsername.trim(),
          email: newEmail.trim(),
          role: newRole,
          job_title: newJobTitle.trim(),
          department_id: newDeptId || null,
          group_ids: newGroupIds,
          can_upload: newCanUpload,
          allowed_collections: ['General', 'Company Policies'],
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed creating user');
      setNewUsername('');
      setNewPassword('');
      setNewName('');
      setNewEmail('');
      setNewGroupIds([]);
      notify('ok', `Created ${data.role_display} '${data.username}'`);
      fetchAdminData();
    } catch (err: any) {
      notify('err', err.message);
    }
  };

  // Load Employee Profile Drawer
  const handleInspectEmployeeProfile = async (userId: string) => {
    try {
      const res = await fetch(`/api/admin/employees/${userId}/profile`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setSelectedEmpProfile(await res.json());
      }
    } catch (err: any) {
      notify('err', err.message);
    }
  };

  const handleUpdateUser = async (userId: string, patch: Record<string, any>) => {
    try {
      const res = await fetch(`/api/users/${userId}`, {
        method: 'PUT',
        headers: authHeaders,
        body: JSON.stringify(patch),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Update failed');
      notify('ok', `Updated employee '${data.username}'`);
      fetchAdminData();
      if (selectedEmpProfile?.employee?.id === userId) {
        handleInspectEmployeeProfile(userId);
      }
    } catch (err: any) {
      notify('err', err.message);
    }
  };

  const handleRevokeUserSessions = async (userId: string) => {
    try {
      const res = await fetch(`/api/users/${userId}/revoke-sessions`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        notify('ok', 'Revoked all active sessions for user');
      }
    } catch (err: any) {
      notify('err', err.message);
    }
  };

  const handleDeleteUser = async (userId: string, username: string) => {
    if (!window.confirm(`Are you sure you want to permanently remove member @${username}? This action cannot be undone.`)) return;
    try {
      const res = await fetch(`/api/users/${userId}`, {
        method: 'DELETE',
        headers: authHeaders,
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to remove member.');
      }
      notify('ok', `Member @${username} was removed successfully.`);
      fetchAdminData();
      if (selectedEmpProfile?.employee?.id === userId) {
        setSelectedEmpProfile(null);
      }
    } catch (err: any) {
      notify('err', err.message);
    }
  };

  // Archive / Unarchive Document
  const handleArchiveDocument = async (docId: string, isArchived: boolean) => {
    try {
      const res = await fetch(`/api/documents/${docId}/archive`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ is_archived: isArchived }),
      });
      if (res.ok) {
        notify('ok', isArchived ? 'Document archived' : 'Document restored from archive');
        onRefreshGlobalData();
        fetchAdminData();
      }
    } catch (err: any) {
      notify('err', err.message);
    }
  };

  // Move Document to Collection
  const handleMoveDocument = async (docId: string, targetCollection: string) => {
    try {
      const res = await fetch(`/api/documents/${docId}/move`, {
        method: 'PUT',
        headers: authHeaders,
        body: JSON.stringify({ collection: targetCollection }),
      });
      if (res.ok) {
        notify('ok', `Moved document to '${targetCollection}'`);
        onRefreshGlobalData();
      }
    } catch (err: any) {
      notify('err', err.message);
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    const res = await fetch(`/api/documents/${docId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      notify('ok', 'Document deleted from workplace');
      onRefreshGlobalData();
      fetchAdminData();
    }
  };

  const handleReindexDocument = async (docId: string) => {
    const res = await fetch(`/api/documents/${docId}/reindex`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      notify('ok', 'Document re-indexed');
      onRefreshGlobalData();
    }
  };

  // Create Collection
  const handleCreateCollection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newColName.trim()) return;
    try {
      const res = await fetch('/api/collections', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          name: newColName.trim(),
          description: newColDesc.trim(),
          access_level: newColAccess,
          is_private: newColAccess === 'ADMIN_ONLY',
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed creating collection');
      setNewColName('');
      setNewColDesc('');
      notify('ok', `Created collection '${data.name}'`);
      onRefreshGlobalData();
    } catch (err: any) {
      notify('err', err.message);
    }
  };

  // Create Department
  const handleCreateDepartment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!deptName.trim()) return;
    try {
      const res = await fetch('/api/departments', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ name: deptName.trim(), description: deptDesc.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed creating department');
      setDeptName('');
      setDeptDesc('');
      notify('ok', `Created department '${data.name}'`);
      fetchAdminData();
    } catch (err: any) {
      notify('err', err.message);
    }
  };

  const handleDeleteDepartment = async (deptId: string) => {
    try {
      const res = await fetch(`/api/departments/${deptId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed deleting department');
      notify('ok', 'Department removed (documents safely preserved)');
      fetchAdminData();
    } catch (err: any) {
      notify('err', err.message);
    }
  };

  // Create Group
  const handleCreateGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!groupName.trim()) return;
    try {
      const res = await fetch('/api/groups', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          name: groupName.trim(),
          description: groupDesc.trim(),
          member_ids: groupMemberIds,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed creating group');
      setGroupName('');
      setGroupDesc('');
      setGroupMemberIds([]);
      notify('ok', `Created group '${data.name}'`);
      fetchAdminData();
    } catch (err: any) {
      notify('err', err.message);
    }
  };

  const handleDeleteGroup = async (groupId: string) => {
    try {
      const res = await fetch(`/api/groups/${groupId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed deleting group');
      notify('ok', 'Group deleted');
      fetchAdminData();
    } catch (err: any) {
      notify('err', err.message);
    }
  };

  const openDocAccessModal = (doc: any) => {
    setEditingDoc(doc);
    setDocAccessLevel(doc.access_level || 'EMPLOYEE_SHARED');
    setDocDeptId(doc.department_id || (departments[0]?.id ?? ''));
    const rules = doc.access_rules || [];
    setDocGroupIds(rules.filter((r: any) => r.group_id).map((r: any) => r.group_id));
    setDocUserIds(
      rules
        .filter((r: any) => r.user_id && r.access_type !== 'EXPLICIT_DENY')
        .map((r: any) => r.user_id)
    );
  };

  const handleSaveDocumentAccess = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingDoc) return;
    try {
      const res = await fetch(`/api/documents/${editingDoc.id}/access`, {
        method: 'PUT',
        headers: authHeaders,
        body: JSON.stringify({
          access_level: docAccessLevel,
          department_id: docAccessLevel === 'DEPARTMENT_ONLY' ? docDeptId : null,
          allowed_department_ids:
            docAccessLevel === 'DEPARTMENT_ONLY' && docDeptId ? [docDeptId] : [],
          allowed_group_ids: docAccessLevel === 'GROUP_ONLY' ? docGroupIds : [],
          allowed_user_ids: docAccessLevel === 'USER_SPECIFIC' ? docUserIds : [],
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed updating document access');
      notify('ok', `Updated access policy for '${editingDoc.filename}' to ${docAccessLevel}`);
      setEditingDoc(null);
      onRefreshGlobalData();
      fetchAdminData();
    } catch (err: any) {
      notify('err', err.message);
    }
  };

  const handleUpdateCollectionAccess = async (
    colId: string,
    accessLevel: string,
    deptId?: string
  ) => {
    try {
      const res = await fetch(`/api/collections/${colId}/access`, {
        method: 'PUT',
        headers: authHeaders,
        body: JSON.stringify({
          access_level: accessLevel,
          is_private: accessLevel === 'ADMIN_ONLY',
          department_id: deptId || null,
        }),
      });
      if (!res.ok) throw new Error('Failed updating collection access');
      notify('ok', `Collection access policy updated to ${accessLevel}`);
      onRefreshGlobalData();
      fetchAdminData();
    } catch (err: any) {
      notify('err', err.message);
    }
  };

  const handleToggleEmployeeDefaultPermission = async (permKey: string) => {
    if (!permissionsConfig) return;
    const current: string[] = permissionsConfig.default_employee_permissions || [];
    const next = current.includes(permKey)
      ? current.filter((p) => p !== permKey)
      : [...current, permKey];
    try {
      const res = await fetch('/api/admin/permissions/employee-defaults', {
        method: 'PUT',
        headers: authHeaders,
        body: JSON.stringify({ permissions: next }),
      });
      if (res.ok) {
        const data = await res.json();
        setPermissionsConfig({
          ...permissionsConfig,
          default_employee_permissions: data.default_employee_permissions,
        });
        notify('ok', 'Updated default employee permissions');
      }
    } catch (err: any) {
      notify('err', err.message);
    }
  };

  const handleLoadAccessPreview = useCallback(
    async (uid: string) => {
      if (!uid) return;
      try {
        const res = await fetch(`/api/admin/access/preview/${uid}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          setPreviewData(await res.json());
        }
      } catch {
        // ignore
      }
    },
    [token]
  );

  useEffect(() => {
    if (section === 'access' && previewUserId) {
      handleLoadAccessPreview(previewUserId);
    }
  }, [section, previewUserId, handleLoadAccessPreview]);

  const handleRunAccessTest = async () => {
    if (!testUserId || !testDocId) return;
    try {
      const res = await fetch('/api/admin/access/test', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ user_id: testUserId, document_id: testDocId }),
      });
      if (res.ok) {
        setTestResult(await res.json());
      }
    } catch (err: any) {
      notify('err', err.message);
    }
  };

  // Save Workplace Settings
  const handleSaveWorkplaceSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/workplaces/current', {
        method: 'PUT',
        headers: authHeaders,
        body: JSON.stringify({
          name: wpName.trim(),
          slug: wpSlug.trim(),
          description: wpDesc.trim(),
          industry: wpIndustry.trim(),
          assistant_name: wpAssistantName.trim(),
          welcome_message: wpWelcomeMsg.trim(),
          default_doc_visibility: wpDefaultVisibility,
          allow_employee_uploads: wpAllowEmpUploads,
        }),
      });
      if (!res.ok) throw new Error('Failed saving workplace settings');
      notify('ok', 'Saved workplace settings');
      onRefreshGlobalData();
    } catch (err: any) {
      notify('err', err.message);
    }
  };

  const handleCreateWorkplaceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createWpName.trim()) return;
    await onCreateWorkplace({
      name: createWpName.trim(),
      slug: createWpSlug.trim() || undefined,
      description: createWpDesc.trim(),
      industry: createWpIndustry.trim(),
    });
    setShowCreateWpModal(false);
    setCreateWpName('');
    setCreateWpSlug('');
    setCreateWpDesc('');
    notify('ok', `Created new workplace '${createWpName}'`);
  };

  const handleDeleteWorkplace = async (workplaceId: string, workplaceName: string) => {
    if (!window.confirm(`Are you sure you want to permanently delete workplace '${workplaceName}'? All associated collections and document settings will be removed.`)) return;
    try {
      const res = await fetch(`/api/workplaces/${workplaceId}`, {
        method: 'DELETE',
        headers: authHeaders,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed deleting workplace');
      notify('ok', `Workplace '${workplaceName}' deleted successfully.`);
      onRefreshGlobalData();
      fetchAdminData();
    } catch (err: any) {
      notify('err', err.message);
    }
  };

  const handlePurgeAllSystemData = async () => {
    if (!window.confirm('⚠️ WARNING: Are you sure you want to purge ALL documents, chunks, vector embeddings, and database data? This resets the app to a clean state for fresh onboarding.')) return;
    try {
      const res = await fetch('/api/admin/system/purge-all-data', {
        method: 'POST',
        headers: authHeaders,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed purging system data');
      notify('ok', 'All database data and vector chunks successfully purged! App is clean.');
      onRefreshGlobalData();
      fetchAdminData();
    } catch (err: any) {
      notify('err', err.message);
    }
  };

  const filteredDocuments = documents.filter((d) => {
    if (docColFilter !== 'ALL' && d.collection !== docColFilter) return false;
    if (docPolicyFilter !== 'ALL' && d.access_level !== docPolicyFilter) return false;
    if (
      docSearchFilter.trim() &&
      !d.filename.toLowerCase().includes(docSearchFilter.trim().toLowerCase())
    ) {
      return false;
    }
    return true;
  });

  const navItems: { id: AdminSection; label: string; icon: React.ReactNode }[] = [
    { id: 'overview', label: 'Overview', icon: <Shield className="w-4 h-4" /> },
    { id: 'employees', label: 'Employees', icon: <Users className="w-4 h-4" /> },
    { id: 'knowledge', label: 'Knowledge', icon: <FileText className="w-4 h-4" /> },
    { id: 'collections', label: 'Collections', icon: <FolderLock className="w-4 h-4" /> },
    { id: 'access', label: 'Access Control', icon: <KeyRound className="w-4 h-4" /> },
    { id: 'analytics', label: 'Analytics', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'settings', label: 'Settings', icon: <Settings className="w-4 h-4" /> },
    { id: 'audit', label: 'Audit Logs', icon: <ScrollText className="w-4 h-4" /> },
  ];

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Workplace Top Bar & Switcher */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-emerald-500">
            <Building2 className="w-3.5 h-3.5" />
            <span>Workplace Control Plane</span>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-xl font-bold tracking-tight">
              {workplace?.name || currentUser?.workspace || 'ONYX Studio'}
            </h2>
            {workplaces && workplaces.length > 0 && (
              <select
                value={workplace?.id || ''}
                onChange={(e) => {
                  if (e.target.value === '__create__') {
                    setShowCreateWpModal(true);
                  } else if (e.target.value) {
                    onSwitchWorkplace(e.target.value);
                  }
                }}
                className="px-2.5 py-1 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs font-medium"
              >
                {workplaces.map((wp: any) => (
                  <option key={wp.id} value={wp.id}>
                    Switch: {wp.name}
                  </option>
                ))}
                <option value="__create__">+ Create New Workplace...</option>
              </select>
            )}
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            {workplace?.description ||
              'Manage workplace employees, private knowledge, collections, access policies, and AI settings.'}
          </p>
        </div>

        {/* Quick Actions */}
        <div className="flex flex-wrap items-center gap-2">
          {onNavigateToUpload && (
            <button
              onClick={onNavigateToUpload}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs transition"
            >
              <UploadCloud className="w-3.5 h-3.5" />
              <span>+ Add Knowledge</span>
            </button>
          )}
          <button
            onClick={() => setSection('employees')}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs font-medium transition"
          >
            <Plus className="w-3.5 h-3.5 text-emerald-500" />
            <span>+ Add Employee</span>
          </button>
          {onNavigateToChat && (
            <button
              onClick={onNavigateToChat}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs font-medium transition"
            >
              <MessageSquare className="w-3.5 h-3.5 text-emerald-500" />
              <span>Open AI Chat</span>
            </button>
          )}
          <button
            onClick={() => {
              fetchAdminData();
              onRefreshGlobalData();
            }}
            className="p-2 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:bg-zinc-50 dark:hover:bg-zinc-800 text-xs transition"
            title="Refresh Workplace State"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Feedback Banner */}
      {feedback && (
        <div
          className={`p-3 rounded-xl border text-xs flex items-center justify-between ${
            feedback.type === 'ok'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-300'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-600 dark:text-rose-300'
          }`}
        >
          <span>{feedback.text}</span>
          <button onClick={() => setFeedback(null)}>
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Sub-navigation Tabs */}
      <div className="flex flex-wrap gap-1.5 p-1.5 rounded-2xl bg-zinc-200/60 dark:bg-zinc-900/80 border border-zinc-200 dark:border-zinc-800">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setSection(item.id)}
            className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium transition ${
              section === item.id
                ? 'bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 shadow-sm'
                : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200'
            }`}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </div>

      {/* 1. OVERVIEW */}
      {section === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
              <div className="text-xs text-zinc-500">Workplace Team</div>
              <div className="text-2xl font-bold mt-1">
                {users.filter((u) => u.status === 'ACTIVE').length} / {users.length}
              </div>
              <div className="text-[11px] text-zinc-400 mt-1">
                {users.filter((u) => u.role === 'admin').length} Admins •{' '}
                {users.filter((u) => u.role === 'employee').length} Employees
              </div>
            </div>
            <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
              <div className="text-xs text-zinc-500">Knowledge Base</div>
              <div className="text-2xl font-bold mt-1">{documents.length} Docs</div>
              <div className="text-[11px] text-zinc-400 mt-1">
                {collections.length} Collections •{' '}
                {analytics?.summary?.total_chunks ?? 0} Indexed Chunks
              </div>
            </div>
            <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
              <div className="text-xs text-zinc-500">AI Assistant Usage</div>
              <div className="text-2xl font-bold mt-1">
                {analytics?.summary?.questions_asked ?? 0}
              </div>
              <div className="text-[11px] text-zinc-400 mt-1">
                Questions answered across {analytics?.summary?.chat_sessions ?? 0} sessions
              </div>
            </div>
            <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
              <div className="text-xs text-zinc-500">Local AI & Security</div>
              <div className="text-2xl font-bold mt-1 text-emerald-500">100% Local</div>
              <div className="text-[11px] text-zinc-400 mt-1">
                {sysStatus?.llm_details?.selected_model || 'Local Llama'} • Pre-retrieval RBAC
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-3">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <Lock className="w-4 h-4 text-emerald-500" />
                <span>Workplace Architecture & Security Guarantees</span>
              </h3>
              <ul className="space-y-2 text-xs text-zinc-600 dark:text-zinc-300">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                  <span>
                    <strong>Strict Workplace Isolation:</strong> Users, collections, documents, and vectors are strictly isolated per workplace.
                  </span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                  <span>
                    <strong>Dedicated Employee Chat Experience:</strong> Employees see only the clean {workplace?.assistant_name || 'ONYX AI'} assistant interface.
                  </span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                  <span>
                    <strong>Pre-Retrieval Vector Filtering:</strong> ChromaDB & BM25 filter by authorized document IDs before top-K retrieval.
                  </span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                  <span>
                    <strong>Immediate Session Revocation:</strong> Disabling an employee or changing their role immediately invalidates active tokens.
                  </span>
                </li>
              </ul>
            </div>

            <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-3">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-500" />
                <span>Recent Workplace Activity</span>
              </h3>
              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {auditLogs.slice(0, 6).map((log) => (
                  <div
                    key={log.id}
                    className="flex items-center justify-between text-xs p-2 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200/60 dark:border-zinc-800/60"
                  >
                    <div>
                      <span className="font-mono font-semibold text-zinc-800 dark:text-zinc-200">
                        {log.action}
                      </span>
                      <span className="text-zinc-400 ml-2">by {log.username}</span>
                    </div>
                    <span className="text-[11px] font-mono text-zinc-400">
                      {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : ''}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 2. EMPLOYEES MANAGEMENT */}
      {section === 'employees' && (
        <div className="space-y-6">
          <form
            onSubmit={handleCreateOrInviteUser}
            className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <Plus className="w-4 h-4 text-emerald-500" />
                <span>Add Workplace Employee</span>
              </h3>
              <div className="inline-flex rounded-xl p-1 bg-zinc-100 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-xs">
                <button
                  type="button"
                  onClick={() => setEmpCreationMode('create')}
                  className={`px-3 py-1 rounded-lg font-medium transition ${
                    empCreationMode === 'create'
                      ? 'bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 shadow-sm'
                      : 'text-zinc-500'
                  }`}
                >
                  Create with Password
                </button>
                <button
                  type="button"
                  onClick={() => setEmpCreationMode('invite')}
                  className={`px-3 py-1 rounded-lg font-medium transition ${
                    empCreationMode === 'invite'
                      ? 'bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 shadow-sm'
                      : 'text-zinc-500'
                  }`}
                >
                  Generate Invite Code
                </button>
              </div>
            </div>

            {generatedInvite && (
              <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex flex-wrap items-center justify-between gap-3 text-xs">
                <div>
                  <span className="font-semibold text-emerald-600 dark:text-emerald-300">
                    Invite Token for @{generatedInvite.username}:
                  </span>
                  <code className="ml-2 px-2 py-1 rounded bg-zinc-900 text-emerald-400 font-mono">
                    {generatedInvite.token}
                  </code>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard.writeText(generatedInvite.token);
                    setCopiedInvite(true);
                    setTimeout(() => setCopiedInvite(false), 2000);
                  }}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-500 text-zinc-950 font-semibold"
                >
                  {copiedInvite ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedInvite ? 'Copied' : 'Copy Token'}</span>
                </button>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label className="text-xs text-zinc-400 block mb-1">Full Name *</label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Rahul Verma"
                  required
                  className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
                />
              </div>
              <div>
                <label className="text-xs text-zinc-400 block mb-1">Username</label>
                <input
                  type="text"
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  placeholder="e.g. rahul"
                  required={empCreationMode === 'create'}
                  className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
                />
              </div>
              {empCreationMode === 'create' ? (
                <div>
                  <label className="text-xs text-zinc-400 block mb-1">Temporary Password *</label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
                  />
                </div>
              ) : (
                <div>
                  <label className="text-xs text-zinc-400 block mb-1">Work Email</label>
                  <input
                    type="email"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder="rahul@company.local"
                    className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
                  />
                </div>
              )}
              <div>
                <label className="text-xs text-zinc-400 block mb-1">Role</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value as 'employee' | 'admin')}
                  className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
                >
                  <option value="employee">Employee (Chat-Only Workplace Assistant)</option>
                  <option value="admin">Admin (Full Workplace Console)</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-zinc-400 block mb-1">Job Title / Position</label>
                <input
                  type="text"
                  value={newJobTitle}
                  onChange={(e) => setNewJobTitle(e.target.value)}
                  placeholder="e.g. Software Developer, HR Manager"
                  className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
                />
              </div>
              <div>
                <label className="text-xs text-zinc-400 block mb-1">Department</label>
                <select
                  value={newDeptId}
                  onChange={(e) => setNewDeptId(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
                >
                  <option value="">-- No Department --</option>
                  {departments.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-zinc-400">Assign Groups:</span>
                {groups.map((g) => {
                  const checked = newGroupIds.includes(g.id);
                  return (
                    <button
                      type="button"
                      key={g.id}
                      onClick={() =>
                        setNewGroupIds(
                          checked
                            ? newGroupIds.filter((x) => x !== g.id)
                            : [...newGroupIds, g.id]
                        )
                      }
                      className={`px-2.5 py-1 rounded-lg text-[11px] font-medium border transition ${
                        checked
                          ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400'
                          : 'border-zinc-300 dark:border-zinc-800 text-zinc-500'
                      }`}
                    >
                      {g.name}
                    </button>
                  );
                })}
              </div>

              <button
                type="submit"
                className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs transition"
              >
                {empCreationMode === 'invite'
                  ? 'Generate Invite Token'
                  : 'Create Workplace Account'}
              </button>
            </div>
          </form>

          {/* Employees Directory Table */}
          <div className="rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 overflow-hidden">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-800 text-zinc-400 bg-zinc-50/50 dark:bg-zinc-950/50">
                  <th className="py-3 px-4">Employee</th>
                  <th className="py-3 px-4">Role & Title</th>
                  <th className="py-3 px-4">Department</th>
                  <th className="py-3 px-4">Groups</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-950/40">
                    <td className="py-3 px-4">
                      <div className="font-semibold text-zinc-900 dark:text-zinc-100">
                        {u.name || u.username}
                      </div>
                      <div className="font-mono text-[11px] text-zinc-400">
                        @{u.username} {u.email ? `• ${u.email}` : ''}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono uppercase font-semibold mr-2 ${
                          u.role === 'admin'
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : 'bg-zinc-200 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300'
                        }`}
                      >
                        {u.role}
                      </span>
                      <span className="text-zinc-500">{u.job_title}</span>
                    </td>
                    <td className="py-3 px-4">
                      <select
                        value={u.department_id || ''}
                        onChange={(e) =>
                          handleUpdateUser(u.id, { department_id: e.target.value || '' })
                        }
                        className="px-2 py-1 rounded-lg bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
                      >
                        <option value="">None</option>
                        {departments.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex flex-wrap gap-1">
                        {(u.groups || []).map((g: any) => (
                          <span
                            key={g.id}
                            className="px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-[10px]"
                          >
                            {g.name}
                          </span>
                        ))}
                        {(!u.groups || u.groups.length === 0) && (
                          <span className="text-zinc-400">—</span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                          u.status === 'ACTIVE'
                            ? 'bg-emerald-500/15 text-emerald-500'
                            : 'bg-rose-500/15 text-rose-500'
                        }`}
                      >
                        {u.status || 'ACTIVE'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right space-x-1.5">
                      <button
                        onClick={() => handleInspectEmployeeProfile(u.id)}
                        className="px-2.5 py-1 rounded-lg border border-emerald-500/40 text-emerald-500 hover:bg-emerald-500/10 text-[11px]"
                      >
                        Inspect Profile
                      </button>
                      {u.username !== currentUser?.username && (
                        <>
                          <button
                            onClick={() =>
                              handleUpdateUser(u.id, {
                                status: u.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE',
                              })
                            }
                            className={`px-2.5 py-1 rounded-lg border text-[11px] ${
                              u.status === 'ACTIVE'
                                ? 'border-amber-500/30 text-amber-400 hover:bg-amber-500/10'
                                : 'border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10'
                            }`}
                          >
                            {u.status === 'ACTIVE' ? 'Disable' : 'Enable'}
                          </button>
                          <button
                            onClick={() => handleDeleteUser(u.id, u.username)}
                            className="px-2.5 py-1 rounded-lg border border-rose-500/40 text-rose-500 hover:bg-rose-500/10 text-[11px] font-medium transition"
                            title="Remove member permanently from workplace"
                          >
                            Remove
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 3. KNOWLEDGE MANAGEMENT */}
      {section === 'knowledge' && (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
            <div className="flex flex-wrap items-center gap-2 flex-1">
              <input
                type="text"
                value={docSearchFilter}
                onChange={(e) => setDocSearchFilter(e.target.value)}
                placeholder="Search workplace documents..."
                className="px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs min-w-[220px]"
              />
              <select
                value={docColFilter}
                onChange={(e) => setDocColFilter(e.target.value)}
                className="px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
              >
                <option value="ALL">All Collections</option>
                {collections.map((c) => (
                  <option key={c.id} value={c.name}>
                    {c.name}
                  </option>
                ))}
              </select>
              <select
                value={docPolicyFilter}
                onChange={(e) => setDocPolicyFilter(e.target.value)}
                className="px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
              >
                <option value="ALL">All Access Policies</option>
                {Object.keys(ACCESS_LEVEL_LABELS).map((lvl) => (
                  <option key={lvl} value={lvl}>
                    {ACCESS_LEVEL_LABELS[lvl].label}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => openVectorizer()}
                className="px-3.5 py-2 rounded-xl bg-purple-500/15 border border-purple-500/30 text-purple-400 hover:bg-purple-500/25 font-semibold text-xs flex items-center gap-1.5 transition-colors"
                title="Convert PNG/JPG raster images into scalable SVG vector geometry"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Vectorize Image (SVG)</span>
              </button>
              {onNavigateToUpload && (
                <button
                  type="button"
                  onClick={onNavigateToUpload}
                  className="px-3.5 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs flex items-center gap-1.5"
                >
                  <UploadCloud className="w-3.5 h-3.5" />
                  <span>+ Upload / Ingest Knowledge</span>
                </button>
              )}
            </div>
          </div>

          <div className="rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 overflow-hidden">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-800 text-zinc-400 bg-zinc-50/50 dark:bg-zinc-950/50">
                  <th className="py-3 px-4">Document</th>
                  <th className="py-3 px-4">Collection</th>
                  <th className="py-3 px-4">Access Policy</th>
                  <th className="py-3 px-4">Chunks</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
                {filteredDocuments.map((d) => {
                  const badge =
                    ACCESS_LEVEL_LABELS[d.access_level || 'EMPLOYEE_SHARED'] ||
                    ACCESS_LEVEL_LABELS.EMPLOYEE_SHARED;
                  return (
                    <tr key={d.id}>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-zinc-900 dark:text-zinc-100">
                          {d.filename}
                        </div>
                        <div className="text-[11px] text-zinc-400">
                          v{d.version} • {d.modality?.toUpperCase()} • by {d.owner}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <select
                          value={d.collection}
                          onChange={(e) => handleMoveDocument(d.id, e.target.value)}
                          className="px-2 py-1 rounded-lg bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
                        >
                          {collections.map((c) => (
                            <option key={c.id} value={c.name}>
                              {c.name}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-medium border ${badge.color}`}
                        >
                          {badge.label}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono">{d.chunk_count || 0}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                            d.is_archived || d.status === 'Archived'
                              ? 'bg-amber-500/15 text-amber-400'
                              : d.status === 'Ready'
                              ? 'bg-emerald-500/15 text-emerald-500'
                              : 'bg-zinc-500/15 text-zinc-400'
                          }`}
                        >
                          {d.is_archived ? 'Archived' : d.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right space-x-1">
                        {onOpenDocumentPreview && (
                          <button
                            type="button"
                            onClick={() => onOpenDocumentPreview(d.id)}
                            className="px-2 py-1 rounded-lg border border-zinc-300 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-[11px]"
                          >
                            Preview
                          </button>
                        )}
                        {Boolean(d.modality === 'image' || /\.(png|jpe?g|webp|bmp)$/i.test(d.filename || '')) && (
                          <button
                            type="button"
                            onClick={() => openVectorizer(d.id, d.filename)}
                            className="px-2 py-1 rounded-lg bg-purple-500/15 text-purple-400 border border-purple-500/30 hover:bg-purple-500/25 font-medium text-[11px] transition-colors"
                            title="Trace raster image to SVG vector"
                          >
                            Vectorize
                          </button>
                        )}
                        <button
                          onClick={() => openDocAccessModal(d)}
                          className="px-2 py-1 rounded-lg bg-emerald-500/15 text-emerald-500 hover:bg-emerald-500/25 font-medium text-[11px]"
                        >
                          Access
                        </button>
                        <button
                          onClick={() => handleArchiveDocument(d.id, !d.is_archived)}
                          className="px-2 py-1 rounded-lg border border-zinc-300 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-[11px]"
                        >
                          {d.is_archived ? 'Unarchive' : 'Archive'}
                        </button>
                        <button
                          onClick={() => handleReindexDocument(d.id)}
                          className="px-2 py-1 rounded-lg border border-zinc-300 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-[11px]"
                        >
                          Re-index
                        </button>
                        <button
                          onClick={() => handleDeleteDocument(d.id)}
                          className="px-2 py-1 rounded-lg border border-rose-500/30 text-rose-400 hover:bg-rose-500/10 text-[11px]"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 4. COLLECTIONS MANAGEMENT */}
      {section === 'collections' && (
        <div className="space-y-6">
          <form
            onSubmit={handleCreateCollection}
            className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex flex-wrap items-end gap-3"
          >
            <div className="flex-1 min-w-[180px]">
              <label className="text-xs text-zinc-400 block mb-1">Collection Name *</label>
              <input
                type="text"
                value={newColName}
                onChange={(e) => setNewColName(e.target.value)}
                placeholder="e.g. Operations, Legal, Product"
                required
                className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
              />
            </div>
            <div className="flex-1 min-w-[220px]">
              <label className="text-xs text-zinc-400 block mb-1">Description</label>
              <input
                type="text"
                value={newColDesc}
                onChange={(e) => setNewColDesc(e.target.value)}
                placeholder="Collection purpose and audience"
                className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-400 block mb-1">Default Access Policy</label>
              <select
                value={newColAccess}
                onChange={(e) => setNewColAccess(e.target.value)}
                className="px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
              >
                <option value="EMPLOYEE_SHARED">All Employees</option>
                <option value="DEPARTMENT_ONLY">Department Only</option>
                <option value="GROUP_ONLY">Group Only</option>
                <option value="ADMIN_ONLY">Admin Only</option>
              </select>
            </div>
            <button
              type="submit"
              className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs"
            >
              + Create Collection
            </button>
          </form>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {collections.map((c) => {
              const badge =
                ACCESS_LEVEL_LABELS[c.access_level || 'EMPLOYEE_SHARED'] ||
                ACCESS_LEVEL_LABELS.EMPLOYEE_SHARED;
              return (
                <div
                  key={c.id}
                  className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex items-center justify-between gap-4"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm">{c.name}</span>
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-medium border ${badge.color}`}
                      >
                        {badge.label}
                      </span>
                    </div>
                    <div className="text-xs text-zinc-400 mt-1">
                      {c.description || 'Workplace knowledge collection'} • {c.document_count} docs
                    </div>
                  </div>
                  <select
                    value={c.access_level || 'EMPLOYEE_SHARED'}
                    onChange={(e) => handleUpdateCollectionAccess(c.id, e.target.value)}
                    className="px-3 py-1.5 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
                  >
                    <option value="EMPLOYEE_SHARED">All Employees</option>
                    <option value="DEPARTMENT_ONLY">Department Only</option>
                    <option value="GROUP_ONLY">Group Only</option>
                    <option value="ADMIN_ONLY">Admin Only</option>
                  </select>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 5. ACCESS CONTROL (Departments, Groups, Simulator, Default Permissions) */}
      {section === 'access' && (
        <div className="space-y-6">
          {/* Departments & Groups Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Departments */}
            <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-4">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <Building2 className="w-4 h-4 text-emerald-500" />
                <span>Workplace Departments</span>
              </h3>
              <form onSubmit={handleCreateDepartment} className="flex gap-2">
                <input
                  type="text"
                  value={deptName}
                  onChange={(e) => setDeptName(e.target.value)}
                  placeholder="New department (e.g. Legal)"
                  required
                  className="flex-1 px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
                />
                <button
                  type="submit"
                  className="px-3 py-2 rounded-xl bg-emerald-500 text-zinc-950 font-semibold text-xs"
                >
                  Add
                </button>
              </form>
              <div className="space-y-2 max-h-56 overflow-y-auto">
                {departments.map((d) => (
                  <div
                    key={d.id}
                    className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200/70 dark:border-zinc-800/70 flex items-center justify-between text-xs"
                  >
                    <div>
                      <div className="font-semibold">{d.name}</div>
                      <div className="text-[11px] text-zinc-400">
                        {d.user_count} members • {d.document_count} department docs
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteDepartment(d.id)}
                      className="p-1.5 rounded-lg text-zinc-400 hover:text-rose-500"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Groups */}
            <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-4">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <UsersRound className="w-4 h-4 text-emerald-500" />
                <span>Cross-Functional Groups & Teams</span>
              </h3>
              <form onSubmit={handleCreateGroup} className="space-y-2.5">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={groupName}
                    onChange={(e) => setGroupName(e.target.value)}
                    placeholder="Group name (e.g. Leadership)"
                    required
                    className="flex-1 px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
                  />
                  <button
                    type="submit"
                    className="px-3 py-2 rounded-xl bg-emerald-500 text-zinc-950 font-semibold text-xs"
                  >
                    Create
                  </button>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {users.map((u) => {
                    const checked = groupMemberIds.includes(u.id);
                    return (
                      <button
                        type="button"
                        key={u.id}
                        onClick={() =>
                          setGroupMemberIds(
                            checked
                              ? groupMemberIds.filter((x) => x !== u.id)
                              : [...groupMemberIds, u.id]
                          )
                        }
                        className={`px-2 py-0.5 rounded text-[10px] border ${
                          checked
                            ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400'
                            : 'border-zinc-300 dark:border-zinc-800 text-zinc-400'
                        }`}
                      >
                        +{u.username}
                      </button>
                    );
                  })}
                </div>
              </form>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {groups.map((g) => (
                  <div
                    key={g.id}
                    className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200/70 dark:border-zinc-800/70 flex items-center justify-between text-xs"
                  >
                    <div>
                      <div className="font-semibold">{g.name}</div>
                      <div className="text-[11px] text-zinc-400">
                        {g.member_count} members:{' '}
                        {(g.members || []).map((m: any) => m.username).join(', ') || 'None'}
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteGroup(g.id)}
                      className="p-1.5 rounded-lg text-zinc-400 hover:text-rose-500"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Access Simulator & Policy Debugger */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-4">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <Eye className="w-4 h-4 text-emerald-500" />
                <span>Employee Access Simulator ("View As")</span>
              </h3>
              <select
                value={previewUserId}
                onChange={(e) => setPreviewUserId(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
              >
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name || u.username} (@{u.username} — {u.role} / {u.department || 'No Dept'})
                  </option>
                ))}
              </select>

              {previewData && (
                <div className="space-y-2 text-xs">
                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                      <div className="font-bold text-lg text-emerald-500">
                        {previewData.summary.accessible_documents_count}
                      </div>
                      <div className="text-[11px] text-zinc-400">Accessible Documents</div>
                    </div>
                    <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20">
                      <div className="font-bold text-lg text-rose-500">
                        {previewData.summary.restricted_documents_count}
                      </div>
                      <div className="text-[11px] text-zinc-400">Blocked Documents</div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-4">
              <h3 className="text-sm font-semibold">Single-Document Policy Tester</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <select
                  value={testUserId}
                  onChange={(e) => setTestUserId(e.target.value)}
                  className="px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
                >
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>
                      @{u.username} ({u.role})
                    </option>
                  ))}
                </select>
                <select
                  value={testDocId}
                  onChange={(e) => setTestDocId(e.target.value)}
                  className="px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
                >
                  {documents.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.filename} ({d.access_level})
                    </option>
                  ))}
                </select>
              </div>
              <button
                onClick={handleRunAccessTest}
                className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs"
              >
                Evaluate Access Policy
              </button>
              {testResult && (
                <div
                  className={`p-3 rounded-xl border text-xs ${
                    testResult.allowed
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                      : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                  }`}
                >
                  <div className="font-bold uppercase">
                    {testResult.allowed ? 'ACCESS ALLOWED' : 'ACCESS DENIED'}
                  </div>
                  <div className="mt-1">{testResult.reason}</div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 6. WORKPLACE ANALYTICS */}
      {section === 'analytics' && analytics && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
              <div className="text-xs text-zinc-500">Total Questions Asked</div>
              <div className="text-2xl font-bold mt-1">{analytics.summary.questions_asked}</div>
              <div className="text-[11px] text-zinc-400 mt-1">
                Across {analytics.summary.chat_sessions} workplace conversations
              </div>
            </div>
            <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
              <div className="text-xs text-zinc-500">Active Employees</div>
              <div className="text-2xl font-bold mt-1">{analytics.summary.active_employees}</div>
              <div className="text-[11px] text-zinc-400 mt-1">
                {analytics.summary.disabled_employees} disabled
              </div>
            </div>
            <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
              <div className="text-xs text-zinc-500">Ready Documents</div>
              <div className="text-2xl font-bold mt-1">{analytics.summary.ready_documents}</div>
              <div className="text-[11px] text-zinc-400 mt-1">
                {analytics.summary.archived_documents} archived
              </div>
            </div>
            <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
              <div className="text-xs text-zinc-500">Indexed Knowledge Chunks</div>
              <div className="text-2xl font-bold mt-1">{analytics.summary.total_chunks}</div>
              <div className="text-[11px] text-emerald-500 mt-1">
                Privacy-preserving aggregate metrics
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-3">
              <h3 className="text-sm font-semibold">Collections Knowledge Breakdown</h3>
              <div className="space-y-2">
                {(analytics.popular_collections || []).map((c: any) => (
                  <div
                    key={c.name}
                    className="flex items-center justify-between p-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200/60 dark:border-zinc-800/60 text-xs"
                  >
                    <div>
                      <span className="font-semibold">{c.name}</span>
                      <span className="ml-2 text-[10px] font-mono text-zinc-400">
                        {c.access_level}
                      </span>
                    </div>
                    <span className="font-mono text-zinc-500">{c.document_count} docs</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-3">
              <h3 className="text-sm font-semibold">Access Policy Distribution</h3>
              <div className="space-y-2">
                {(analytics.access_policy_breakdown || []).map((p: any) => (
                  <div
                    key={p.policy}
                    className="flex items-center justify-between p-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200/60 dark:border-zinc-800/60 text-xs"
                  >
                    <span className="font-mono">{p.policy}</span>
                    <span className="font-bold">{p.count} documents</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 7. WORKPLACE SETTINGS */}
      {section === 'settings' && (
        <div className="space-y-6 max-w-3xl">
          <form
            onSubmit={handleSaveWorkplaceSettings}
            className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-5"
          >
          <div>
            <h3 className="text-base font-semibold">Workplace Profile & AI Assistant Settings</h3>
            <p className="text-xs text-zinc-400 mt-1">
              Customize how your workplace and private AI assistant appear to employees.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-zinc-400 block mb-1">Workplace Name</label>
              <input
                type="text"
                value={wpName}
                onChange={(e) => setWpName(e.target.value)}
                required
                className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-400 block mb-1">Workplace Slug</label>
              <input
                type="text"
                value={wpSlug}
                onChange={(e) => setWpSlug(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs font-mono"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-400 block mb-1">Industry</label>
              <input
                type="text"
                value={wpIndustry}
                onChange={(e) => setWpIndustry(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-400 block mb-1">AI Assistant Name</label>
              <input
                type="text"
                value={wpAssistantName}
                onChange={(e) => setWpAssistantName(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="text-xs text-zinc-400 block mb-1">Workplace Description</label>
              <input
                type="text"
                value={wpDesc}
                onChange={(e) => setWpDesc(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="text-xs text-zinc-400 block mb-1">
                Employee Chat Welcome Message
              </label>
              <input
                type="text"
                value={wpWelcomeMsg}
                onChange={(e) => setWpWelcomeMsg(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-400 block mb-1">
                Default Document Visibility
              </label>
              <select
                value={wpDefaultVisibility}
                onChange={(e) => setWpDefaultVisibility(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
              >
                <option value="EMPLOYEE_SHARED">All Employees</option>
                <option value="DEPARTMENT_ONLY">Department Only</option>
                <option value="ADMIN_ONLY">Admin Only</option>
              </select>
            </div>
          </div>

          <button
            type="submit"
            className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs transition"
          >
            Save Workplace Settings
          </button>
        </form>

        {/* Workplaces Directory & Deletion Panel */}
        <div className="pt-6 border-t border-zinc-200 dark:border-zinc-800 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                Workplaces & Teams Directory
              </h3>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                Manage organization workspaces, switch contexts, or permanently remove obsolete workplaces.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowCreateWpModal(true)}
              className="px-3 py-1.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs font-semibold hover:bg-emerald-500/25 transition flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>+ Create Workplace</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {workplaces.map((wp) => (
              <div
                key={wp.id}
                className={`p-4 rounded-2xl border transition space-y-3 ${
                  wp.is_current || wp.id === workplace?.id
                    ? 'bg-emerald-500/10 border-emerald-500/40'
                    : 'bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-emerald-500 shrink-0" />
                    <span className="font-semibold text-xs text-zinc-900 dark:text-zinc-100">
                      {wp.name}
                    </span>
                  </div>
                  {wp.is_current || wp.id === workplace?.id ? (
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500 text-zinc-950">
                      Active Workspace
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => onSwitchWorkplace(wp.id)}
                      className="px-2.5 py-1 rounded-lg bg-zinc-200 dark:bg-zinc-800 text-[11px] font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-300 dark:hover:bg-zinc-700 transition"
                    >
                      Switch
                    </button>
                  )}
                </div>
                <div className="text-[11px] text-zinc-500 dark:text-zinc-400 space-y-1">
                  <div>{wp.description || 'Organization workplace'}</div>
                  <div className="flex items-center gap-3 text-[10px] font-mono text-zinc-400 pt-1">
                    <span>Employees: {wp.employee_count ?? 0}</span>
                    <span>•</span>
                    <span>Documents: {wp.document_count ?? 0}</span>
                  </div>
                </div>
                {workplaces.length > 1 && (
                  <div className="pt-2 border-t border-zinc-200/60 dark:border-zinc-800/60 flex justify-end">
                    <button
                      type="button"
                      onClick={() => handleDeleteWorkplace(wp.id, wp.name)}
                      className="px-2.5 py-1 rounded-lg border border-rose-500/30 text-rose-500 hover:bg-rose-500/10 text-xs font-medium flex items-center gap-1 transition"
                    >
                      <Trash2 className="w-3 h-3" />
                      <span>Delete Workplace</span>
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Danger Zone: System Reset & Purge All Data */}
        <div className="pt-6 border-t border-rose-500/20 space-y-3">
          <div className="p-4 rounded-2xl bg-rose-500/5 border border-rose-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h4 className="text-xs font-bold text-rose-600 dark:text-rose-400 uppercase tracking-wider">
                Danger Zone: System Data Purge & Reset
              </h4>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-0.5 max-w-xl">
                Wipe all uploaded documents, processed chunks, vector embeddings, chat messages, and non-default workplaces to return the system to a clean state for fresh onboarding.
              </p>
            </div>
            <button
              type="button"
              onClick={handlePurgeAllSystemData}
              className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs shadow-md shadow-rose-600/20 flex items-center justify-center gap-1.5 shrink-0 transition"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Purge All System Data</span>
            </button>
          </div>
        </div>
      </div>
      )}

      {/* 8. SECURITY AUDIT LOGS */}
      {section === 'audit' && (
        <div className="rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 overflow-hidden">
          <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold">Security & Authorization Audit Trail</h3>
              <p className="text-xs text-zinc-400">
                Records workplace logins, uploads, policy changes, and blocked access attempts.
              </p>
            </div>
            <span className="text-xs font-mono text-zinc-400">{auditLogs.length} events</span>
          </div>
          <div className="max-h-[520px] overflow-y-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-800 text-zinc-400 bg-zinc-50/50 dark:bg-zinc-950/50">
                  <th className="py-2.5 px-4">Timestamp</th>
                  <th className="py-2.5 px-4">User</th>
                  <th className="py-2.5 px-4">Action</th>
                  <th className="py-2.5 px-4">Resource</th>
                  <th className="py-2.5 px-4">Severity</th>
                  <th className="py-2.5 px-4">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
                {auditLogs.map((l) => (
                  <tr key={l.id}>
                    <td className="py-2.5 px-4 font-mono text-[11px] text-zinc-400">
                      {l.timestamp ? new Date(l.timestamp).toLocaleString() : ''}
                    </td>
                    <td className="py-2.5 px-4">
                      <span className="font-semibold">{l.username}</span>{' '}
                      <span className="text-[10px] font-mono text-zinc-400">({l.user_role})</span>
                    </td>
                    <td className="py-2.5 px-4 font-mono font-semibold">{l.action}</td>
                    <td className="py-2.5 px-4 text-zinc-400">
                      {l.resource_type}
                      {l.resource_id ? `:${String(l.resource_id).slice(0, 8)}` : ''}
                    </td>
                    <td className="py-2.5 px-4">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                          l.severity === 'ALERT' || !l.success
                            ? 'bg-rose-500/15 text-rose-400'
                            : 'bg-emerald-500/15 text-emerald-400'
                        }`}
                      >
                        {l.severity}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 font-mono text-[11px] text-zinc-400 truncate max-w-xs">
                      {JSON.stringify(l.details || {})}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Employee Profile Drawer Modal */}
      {selectedEmpProfile && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-end">
          <div className="w-full max-w-xl bg-white dark:bg-zinc-900 border-l border-zinc-200 dark:border-zinc-800 h-full overflow-y-auto p-6 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800 pb-4">
              <div>
                <div className="text-xs font-mono uppercase text-emerald-500">
                  Employee Profile & Knowledge Scope
                </div>
                <h3 className="text-lg font-bold">
                  {selectedEmpProfile.employee.name || selectedEmpProfile.employee.username}
                </h3>
                <p className="text-xs text-zinc-400">
                  @{selectedEmpProfile.employee.username} • {selectedEmpProfile.employee.job_title}
                </p>
              </div>
              <button
                onClick={() => setSelectedEmpProfile(null)}
                className="p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Accessible Knowledge Summary */}
            <div className="space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Effective Knowledge Access ({selectedEmpProfile.accessible_documents.length} Docs)
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {(selectedEmpProfile.accessible_collections || []).map((c: any) => (
                  <span
                    key={c.id}
                    className="px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-500"
                  >
                    Collection: {c.name} ({c.document_count})
                  </span>
                ))}
              </div>
              <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                {(selectedEmpProfile.accessible_documents || []).map((doc: any) => (
                  <div
                    key={doc.id}
                    className="p-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200/60 dark:border-zinc-800/60 flex items-center justify-between text-xs"
                  >
                    <span className="font-medium">{doc.filename}</span>
                    <span className="font-mono text-[10px] text-zinc-400">
                      {doc.collection} • {doc.access_level}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Granular Data Access & Collection Scope Management */}
            <div className="space-y-3 pt-3 border-t border-zinc-200 dark:border-zinc-800">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Grant / Restrict Collection Access
              </h4>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                Click a collection to grant or restrict this member's access in real-time.
              </p>
              <div className="flex flex-wrap gap-1.5">
                {collections.map((col) => {
                  const allowedList = selectedEmpProfile.employee.allowed_collections || ['General'];
                  const isAllowed = allowedList.includes('*') || allowedList.includes(col.name);
                  return (
                    <button
                      type="button"
                      key={col.id}
                      onClick={() => {
                        let updatedCols: string[];
                        if (allowedList.includes('*')) {
                          updatedCols = collections.map(c => c.name).filter(n => n !== col.name);
                        } else if (isAllowed) {
                          updatedCols = allowedList.filter((n: string) => n !== col.name);
                        } else {
                          updatedCols = [...allowedList, col.name];
                        }
                        handleUpdateUser(selectedEmpProfile.employee.id, {
                          allowed_collections: updatedCols,
                        });
                      }}
                      className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition ${
                        isAllowed
                          ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400'
                          : 'bg-rose-500/10 border-rose-500/30 text-rose-400 opacity-60 hover:opacity-100'
                      }`}
                    >
                      {isAllowed ? '✓ ' : '✗ '} {col.name}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Security & Access Management Controls */}
            <div className="pt-4 border-t border-zinc-200 dark:border-zinc-800 space-y-4">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Security & Account Actions
              </h4>
              <div className="flex gap-2">
                <input
                  type="password"
                  value={resetPwdValue}
                  onChange={(e) => setResetPwdValue(e.target.value)}
                  placeholder="New password..."
                  className="flex-1 px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 text-xs"
                />
                <button
                  onClick={() => {
                    if (resetPwdValue.trim()) {
                      handleUpdateUser(selectedEmpProfile.employee.id, {
                        password: resetPwdValue.trim(),
                      });
                      setResetPwdValue('');
                    }
                  }}
                  className="px-3 py-2 rounded-xl bg-emerald-500 text-zinc-950 font-semibold text-xs"
                >
                  Reset Password
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => handleRevokeUserSessions(selectedEmpProfile.employee.id)}
                  className="px-3 py-2 rounded-xl border border-amber-500/40 text-amber-500 hover:bg-amber-500/10 text-xs font-medium"
                >
                  Revoke Active Sessions
                </button>
                <button
                  onClick={() =>
                    handleUpdateUser(selectedEmpProfile.employee.id, {
                      role:
                        selectedEmpProfile.employee.role === 'admin' ? 'employee' : 'admin',
                    })
                  }
                  className="px-3 py-2 rounded-xl border border-zinc-300 dark:border-zinc-700 text-xs font-medium"
                >
                  {selectedEmpProfile.employee.role === 'admin'
                    ? 'Change to Employee'
                    : 'Promote to Admin'}
                </button>
                {selectedEmpProfile.employee.username !== currentUser?.username && (
                  <button
                    onClick={() => handleDeleteUser(selectedEmpProfile.employee.id, selectedEmpProfile.employee.username)}
                    className="px-3 py-2 rounded-xl border border-rose-500/40 text-rose-500 hover:bg-rose-500/10 text-xs font-medium transition"
                  >
                    Remove Member
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Document Access Policy Modal */}
      {editingDoc && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <form
            onSubmit={handleSaveDocumentAccess}
            className="w-full max-w-lg rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-6 space-y-4 shadow-2xl"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold">Configure Document Access Policy</h3>
                <p className="text-xs text-zinc-400 mt-0.5">{editingDoc.filename}</p>
              </div>
              <button
                type="button"
                onClick={() => setEditingDoc(null)}
                className="p-1 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-zinc-400 block mb-1">Access Policy Level</label>
                <select
                  value={docAccessLevel}
                  onChange={(e) => setDocAccessLevel(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800"
                >
                  <option value="ADMIN_ONLY">Admin Only (Confidential / HR / Executive)</option>
                  <option value="EMPLOYEE_SHARED">All Workplace Employees</option>
                  <option value="DEPARTMENT_ONLY">Specific Department Only</option>
                  <option value="GROUP_ONLY">Specific Group / Project Team Only</option>
                  <option value="USER_SPECIFIC">Selected Individual Employees Only</option>
                </select>
              </div>

              {docAccessLevel === 'DEPARTMENT_ONLY' && (
                <div>
                  <label className="text-zinc-400 block mb-1">Authorized Department</label>
                  <select
                    value={docDeptId}
                    onChange={(e) => setDocDeptId(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800"
                  >
                    {departments.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {docAccessLevel === 'GROUP_ONLY' && (
                <div>
                  <label className="text-zinc-400 block mb-1">Authorized Groups</label>
                  <div className="flex flex-wrap gap-1.5">
                    {groups.map((g) => {
                      const checked = docGroupIds.includes(g.id);
                      return (
                        <button
                          type="button"
                          key={g.id}
                          onClick={() =>
                            setDocGroupIds(
                              checked
                                ? docGroupIds.filter((x) => x !== g.id)
                                : [...docGroupIds, g.id]
                            )
                          }
                          className={`px-2.5 py-1 rounded-lg border ${
                            checked
                              ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400'
                              : 'border-zinc-300 dark:border-zinc-800 text-zinc-400'
                          }`}
                        >
                          {g.name}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {docAccessLevel === 'USER_SPECIFIC' && (
                <div>
                  <label className="text-zinc-400 block mb-1">Authorized Users</label>
                  <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto">
                    {users.map((u) => {
                      const checked = docUserIds.includes(u.id);
                      return (
                        <button
                          type="button"
                          key={u.id}
                          onClick={() =>
                            setDocUserIds(
                              checked
                                ? docUserIds.filter((x) => x !== u.id)
                                : [...docUserIds, u.id]
                            )
                          }
                          className={`px-2.5 py-1 rounded-lg border ${
                            checked
                              ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400'
                              : 'border-zinc-300 dark:border-zinc-800 text-zinc-400'
                          }`}
                        >
                          @{u.username}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-zinc-200 dark:border-zinc-800">
              <button
                type="button"
                onClick={() => setEditingDoc(null)}
                className="px-4 py-2 rounded-xl border border-zinc-300 dark:border-zinc-800 text-xs"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs"
              >
                Save Policy & Update Vector Filter
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Create New Workplace Modal */}
      {showCreateWpModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <form
            onSubmit={handleCreateWorkplaceSubmit}
            className="w-full max-w-md rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-6 space-y-4 shadow-2xl"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold">Create New Workplace</h3>
              <button
                type="button"
                onClick={() => setShowCreateWpModal(false)}
                className="p-1 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="space-y-3 text-xs">
              <div>
                <label className="text-zinc-400 block mb-1">Workplace Name *</label>
                <input
                  type="text"
                  value={createWpName}
                  onChange={(e) => setCreateWpName(e.target.value)}
                  placeholder="e.g. ONYX Studio, Nova Labs"
                  required
                  className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800"
                />
              </div>
              <div>
                <label className="text-zinc-400 block mb-1">Workplace Slug</label>
                <input
                  type="text"
                  value={createWpSlug}
                  onChange={(e) => setCreateWpSlug(e.target.value)}
                  placeholder="e.g. nova-labs"
                  className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800 font-mono"
                />
              </div>
              <div>
                <label className="text-zinc-400 block mb-1">Industry</label>
                <input
                  type="text"
                  value={createWpIndustry}
                  onChange={(e) => setCreateWpIndustry(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800"
                />
              </div>
              <div>
                <label className="text-zinc-400 block mb-1">Description</label>
                <input
                  type="text"
                  value={createWpDesc}
                  onChange={(e) => setCreateWpDesc(e.target.value)}
                  placeholder="Organization or team description"
                  className="w-full px-3 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-800"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowCreateWpModal(false)}
                className="px-4 py-2 rounded-xl border border-zinc-300 dark:border-zinc-800 text-xs"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 rounded-xl bg-emerald-500 text-zinc-950 font-semibold text-xs"
              >
                Create Workplace
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Raster to Vector SVG Modal */}
      <ImageVectorizerModal
        isOpen={vectorizerOpen}
        onClose={() => setVectorizerOpen(false)}
        token={token}
        initialDocId={vectorizerDocId}
        initialFilename={vectorizerFilename}
      />
    </div>
  );
};
