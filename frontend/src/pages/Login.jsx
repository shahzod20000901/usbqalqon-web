import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { apiError } from "../api";
import Icon from "../components/Icon";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username.trim(), password);
      const from = location.state?.from || "/";
      navigate(from, { replace: true });
    } catch (err) {
      setError(apiError(err, "Tizimga kirib bo'lmadi"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <section className="login-visual">
          <div className="login-visual-glow" />
          <div className="login-brand">
            <span className="login-logo">
              <Icon name="shield" size={34} />
            </span>
            <div>
              <strong>USB Qalqon</strong>
              <small>Oflayn nazorat tizimi</small>
            </div>
          </div>

          <div className="login-visual-copy">
            <h1>Qurilmalaringizni markazlashgan holda boshqaring</h1>
            <p>
              Bo'limlar ierarxiyasi, ruxsat etilgan qurilmalar bazasi, qora
              ro'yxat va desktop agentlar — barchasi bir joyda.
            </p>
          </div>

          <ul className="login-features">
            <li>
              <Icon name="users" size={17} />
              Bo'limlar ierarxiyasi
            </li>
            <li>
              <Icon name="database" size={17} />
              Devices.txt import va qidiruv
            </li>
            <li>
              <Icon name="shield" size={17} />
              Qora ro'yxat va agent API
            </li>
          </ul>
        </section>

        <section className="login-form-wrap">
          <div className="login-form-head">
            <h2>Tizimga kirish</h2>
            <p>Hisobingiz ma'lumotlarini kiriting</p>
          </div>

          <form className="login-form" onSubmit={handleSubmit}>
            <label className="field">
              <span>Login</span>
              <div className="input-with-icon">
                <Icon name="user" size={17} />
                <input
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  placeholder="admin"
                  autoComplete="username"
                  autoFocus
                  required
                />
              </div>
            </label>

            <label className="field">
              <span>Parol</span>
              <div className="input-with-icon">
                <Icon name="lock" size={17} />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  className="input-action"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? "Parolni yashirish" : "Parolni ko'rsatish"}
                >
                  <Icon name={showPassword ? "eyeOff" : "eye"} size={17} />
                </button>
              </div>
            </label>

            {error ? (
              <div className="form-error">
                <Icon name="alert" size={16} />
                {error}
              </div>
            ) : null}

            <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
              {loading ? "Kirilmoqda..." : "Kirish"}
              {!loading ? <Icon name="chevron" size={17} /> : null}
            </button>
          </form>

          <div className="login-demo">
            <span>Demo hisob</span>
            <code>admin / admin123</code>
          </div>
        </section>
      </div>
      <footer className="login-footer">
        USB Qalqon web boshqaruv paneli · FastAPI + React
      </footer>
    </div>
  );
}
