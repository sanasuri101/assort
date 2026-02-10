import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import DashboardLayout from './layouts/DashboardLayout';
import Dashboard from './pages/Dashboard';
import Calls from './pages/Calls';
import CallDetail from './pages/CallDetail';
import Knowledge from './pages/Knowledge';
import Settings from './pages/Settings';
import LearningLoop from './pages/LearningLoop';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<DashboardLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="calls" element={<Calls />} />
              <Route path="calls/:callId" element={<CallDetail />} />
              <Route path="knowledge" element={<Knowledge />} />
              <Route path="learning" element={<LearningLoop />} />
              <Route path="settings" element={<Settings />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
