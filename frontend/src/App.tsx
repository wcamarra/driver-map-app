import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { Layout } from './components/Layout';
import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';
import { EditorPage } from './pages/EditorPage';
import { GeneratePage } from './pages/GeneratePage';
import { MyRoutesPage } from './pages/MyRoutesPage';
import { RouteDetailPage } from './pages/RouteDetailPage';

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<HomePage />} />
            <Route path="login" element={<LoginPage />} />
            <Route path="generate" element={<GeneratePage />} />
            <Route path="editor" element={<EditorPage />} />
            <Route path="editor/:id" element={<EditorPage />} />
            <Route path="mine" element={<MyRoutesPage />} />
            <Route path="routes/:id" element={<RouteDetailPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
