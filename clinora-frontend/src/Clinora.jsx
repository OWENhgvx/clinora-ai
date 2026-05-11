import { useState } from "react";
import { flushSync } from "react-dom";
import {
  IllustWreath,
  ECGLine,
  AmbientBlobs,
} from "./components/illustrations";
import TopNav from "./components/TopNav";
import AuthPage from "./pages/AuthPage";
import InputPage from "./pages/InputPage";
import ChatPage from "./pages/ChatPage";
import ResultsPage from "./pages/ResultsPage";
import FlowPage from "./pages/FlowPage";
import HistoryPage from "./pages/HistoryPage";
import PatientsPage from "./pages/PatientsPage";
import EvalPage from "./pages/EvalPage";
import ProviderDashboard from "./pages/ProviderDashboard";
import { makeApi } from "./core/api";
import { useAuth } from "./core/auth";
import {
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";

/* ═══════════════════════════════════════════════════════════════════
   ROOT
═══════════════════════════════════════════════════════════════════ */
function AppInner() {
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [symptoms, setSymp] = useState(null);
  const [result, setResult] = useState(null);
  const [selPat, setSelPat] = useState(null);
  const [resumeSession, setResumeSession] = useState(null);
  const api = makeApi(auth.token);
  const page = location.pathname.replace(/^\//, "") || "input";
  const isProvider = auth.user?.role === "provider";

  if (!auth.ready)
    return (
      <div
        style={{
          minHeight: "100vh",
          background: "var(--paper)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          zIndex: 1,
        }}
      >
        <AmbientBlobs />
        <IllustWreath
          size={280}
          style={{
            position: "absolute",
            opacity: 0.14,
            animation: "drift 14s infinite",
          }}
        />
        <div style={{ textAlign: "center", position: "relative", zIndex: 1 }}>
          <div
            className="ink-bloom"
            style={{
              display: "inline-flex",
              width: 80,
              height: 80,
              borderRadius: 22,
              background: "linear-gradient(135deg,var(--paper2),var(--paper3))",
              border: "2px solid rgba(22,15,6,0.1)",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: 22,
              boxShadow: "var(--shadow-lg)",
              animation: "glowPulse 2.5s infinite",
              overflow: "hidden",
            }}
          >
            <img
              src="/Clinora.png"
              alt=""
              aria-hidden="true"
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                display: "block",
              }}
            />
          </div>
          <p
            style={{
              fontFamily: "var(--serif)",
              fontSize: 24,
              fontStyle: "italic",
              color: "var(--ink3)",
            }}
          >
            Loading Clinora…
          </p>
          <ECGLine
            style={{
              marginTop: 16,
              opacity: 0.45,
              maxWidth: 240,
              margin: "16px auto 0",
            }}
          />
        </div>
      </div>
    );

  const go = (nextPage) => navigate(`/${nextPage}`);
  const goHome = () => go(isProvider ? "provider" : "input");
  const goNew = () => {
    setSymp(null);
    setResult(null);
    setResumeSession(null);
    go("input");
  };
  const goResume = (session) => {
    setResumeSession(session);
    setSymp(session.symptoms || { description: session.description || "" });
    go("chat");
  };
  return (
    <>
      <TopNav
        user={auth.user}
        onLogout={() => {
          auth.logout();
          go("input");
        }}
        onNav={go}
        page={page}
      />
      <div key={location.pathname} className="page-fade">
        <Routes>
          <Route
            path="/"
            element={
              <Navigate to={isProvider ? "/provider" : "/input"} replace />
            }
          />
          <Route
            path="/auth"
            element={
              <AuthPage
                api={api}
                onLogin={(t, u) => {
                  auth.login(t, u);
                  navigate(u?.role === "provider" ? "/provider" : "/input");
                }}
                onSkip={() => go("input")}
              />
            }
          />
          <Route
            path="/provider"
            element={
              auth.user ? (
                isProvider ? (
                  <ProviderDashboard api={api} />
                ) : (
                  <Navigate to="/input" replace />
                )
              ) : (
                <AuthPage
                  api={api}
                  onLogin={(t, u) => {
                    auth.login(t, u);
                    navigate(u?.role === "provider" ? "/provider" : "/input");
                  }}
                  onSkip={() => go("input")}
                />
              )
            }
          />
          <Route
            path="/input"
            element={
              isProvider ? (
                <Navigate to="/provider" replace />
              ) : (
                <InputPage
                  api={api}
                  onSubmit={(f) => {
                    flushSync(() => setSymp(f));
                    go("chat");
                  }}
                  onEval={() => go("eval")}
                  selectedPatient={selPat}
                  onClearPatient={() => setSelPat(null)}
                />
              )
            }
          />
          <Route
            path="/patients"
            element={
              auth.user ? (
                isProvider ? (
                  <Navigate to="/provider" replace />
                ) : (
                  <PatientsPage
                    api={api}
                    onStartConsult={(p) => {
                      flushSync(() => setSelPat(p));
                      go("input");
                    }}
                  />
                )
              ) : (
                <AuthPage
                  api={api}
                  onLogin={(t, u) => {
                    auth.login(t, u);
                    navigate(
                      u?.role === "provider" ? "/provider" : "/patients",
                    );
                  }}
                  onSkip={() => go("input")}
                />
              )
            }
          />
          <Route
            path="/chat"
            element={
              symptoms ? (
                <ChatPage
                  api={api}
                  symptoms={symptoms}
                  resumeSession={resumeSession}
                  onBack={() => {
                    setResumeSession(null);
                    go(resumeSession ? "history" : "input");
                  }}
                  onComplete={(r) => {
                    flushSync(() => setResult(r));
                    go("result");
                  }}
                />
              ) : (
                <Navigate to="/input" replace />
              )
            }
          />
          <Route
            path="/result"
            element={
              result ? (
                <ResultsPage
                  api={api}
                  result={result}
                  onNew={goNew}
                  onHistory={() => go("history")}
                  onFlow={() => go("flow")}
                />
              ) : (
                <Navigate to="/input" replace />
              )
            }
          />
          <Route
            path="/flow"
            element={
              result ? (
                <FlowPage result={result} onBack={() => go("result")} />
              ) : (
                <Navigate to="/input" replace />
              )
            }
          />
          <Route
            path="/history"
            element={
              <HistoryPage
                api={api}
                onNew={isProvider ? goHome : goNew}
                onContinue={goResume}
              />
            }
          />
          <Route path="/eval" element={<EvalPage api={api} />} />
          <Route
            path="*"
            element={
              <Navigate to={isProvider ? "/provider" : "/input"} replace />
            }
          />
        </Routes>
      </div>
    </>
  );
}

export default function ClinoraApp() {
  return <AppInner />;
}
