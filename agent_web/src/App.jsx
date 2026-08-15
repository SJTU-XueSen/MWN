import { useState } from 'react';
import AgentPage from './pages/AgentPage';
import AgentSidebar from './components/AgentSidebar';

export default function App() {
  const [chatKey, setChatKey] = useState(0);          // 登录/登出时重置对话
  const [pendingQuery, setPendingQuery] = useState(null);   // 侧边栏记录 → 对话查询

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <AgentSidebar onAuthed={() => setChatKey(k => k + 1)}
        onQuery={(text) => setPendingQuery(text)} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <AgentPage key={chatKey} pendingQuery={pendingQuery}
          onQueryConsumed={() => setPendingQuery(null)} />
      </div>
    </div>
  );
}
