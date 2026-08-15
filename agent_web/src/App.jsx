import { useState } from 'react';
import AgentPage from './pages/AgentPage';
import DashboardPage from './pages/DashboardPage';
import AgentSidebar from './components/AgentSidebar';

export default function App() {
  const [chatKey, setChatKey] = useState(0);          // 登录/登出时重置对话
  const [pendingQuery, setPendingQuery] = useState(null);   // 侧边栏记录 → 对话查询
  const [view, setView] = useState('chat');           // chat | dashboard

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <AgentSidebar onAuthed={() => setChatKey(k => k + 1)}
        onQuery={(text) => { setPendingQuery(text); setView('chat'); }}
        view={view} onViewChange={setView} />
      <div style={{ flex: 1, minWidth: 0 }}>
        {view === 'dashboard'
          ? <DashboardPage key={chatKey} onAsk={(text) => { setPendingQuery(text); setView('chat'); }} />
          : <AgentPage key={chatKey} pendingQuery={pendingQuery}
              onQueryConsumed={() => setPendingQuery(null)} />}
      </div>
    </div>
  );
}
