import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { AccountabilityPage } from "./pages/AccountabilityPage";
import { AIPredictionsPage } from "./pages/AIPredictionsPage";
import { AuthPage } from "./pages/AuthPage";
import { ChatAssistantPage } from "./pages/ChatAssistantPage";
import { DashboardPage } from "./pages/DashboardPage";
import { MarketAnalysisPage } from "./pages/MarketAnalysisPage";
import { PredictionComparisonPage } from "./pages/PredictionComparisonPage";
import { PredictionHistoryPage } from "./pages/PredictionHistoryPage";
import { RiskAnalysisPage } from "./pages/RiskAnalysisPage";
import { TradingSimulatorPage } from "./pages/TradingSimulatorPage";

const PAGE_TITLES = {
  "/": "Main Dashboard",
  "/analysis": "Live Stock Analysis",
  "/predictions": "AI Predictions Studio",
  "/history": "Prediction History",
  "/comparison": "Prediction Comparison",
  "/accountability": "Accountability Dashboard",
  "/trading": "Real-Time Virtual Trading",
  "/risk": "Risk Analysis",
  "/assistant": "AI Chat Assistant",
};

function ProtectedRoutes() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-500 dark:bg-slate-950">
        Initializing TradeWise AI...
      </div>
    );
  }

  if (!user) {
    return <AuthPage />;
  }

  const title = PAGE_TITLES[location.pathname] || "TradeWise AI";

  return (
    <Layout title={title}>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/analysis" element={<MarketAnalysisPage />} />
        <Route path="/predictions" element={<AIPredictionsPage />} />
        <Route path="/history" element={<PredictionHistoryPage />} />
        <Route path="/comparison" element={<PredictionComparisonPage />} />
        <Route path="/accountability" element={<AccountabilityPage />} />
        <Route path="/trading" element={<TradingSimulatorPage />} />
        <Route path="/risk" element={<RiskAnalysisPage />} />
        <Route path="/assistant" element={<ChatAssistantPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <ProtectedRoutes />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
