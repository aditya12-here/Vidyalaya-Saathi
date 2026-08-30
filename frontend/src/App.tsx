// frontend/src/App.tsx
//
// FULL REPLACEMENT FILE — supersedes the App.tsx from the Data Explorer
// feature. Fixes a pre-existing gap (present in the original App.tsx, not
// introduced by any of the added features): there was previously no way to
// return to a school you'd already registered — the app always started at
// the registration form, and `activeSchoolId` was only ever set by
// SchoolDataForm's onSchoolCreated callback after a fresh create.
//
// This version fetches the list of existing schools (via the Data
// Explorer's GET /explorer/schools — exactly what that endpoint is for)
// on load, and shows them as a "load existing school" list alongside the
// registration form, so you're not forced to re-register every time you
// restart the dev server.

import { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import { SchoolDataForm } from './components/SchoolDataForm';
import { ModuleUpload } from './components/ModuleUpload';
import { PriorityDashboard } from './components/PriorityDashboard';
import { BudgetPlanner } from './components/BudgetPlanner';
import { SchoolExplorer } from './components/SchoolExplorer';

const API_BASE = 'http://localhost:8000/api/v1';

interface ExistingSchool {
  school_id: string;
  name: string;
  problem_count: number;
  prioritization_last_run_at: string | null;
  budget_plan_last_run_at: string | null;
}

function App() {
  const [activeSchoolId, setActiveSchoolId] = useState<string | null>(null);
  const [existingSchools, setExistingSchools] = useState<ExistingSchool[]>([]);
  const [loadingSchools, setLoadingSchools] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const fetchExistingSchools = async () => {
    setLoadingSchools(true);
    setLoadError(null);
    try {
      const res = await axios.get(`${API_BASE}/explorer/schools`);
      setExistingSchools(res.data.schools || []);
    } catch (err) {
      console.error('Failed to fetch existing schools', err);
      setLoadError('Could not reach the backend to list existing schools. Is it running on :8000?');
    } finally {
      setLoadingSchools(false);
    }
  };

  useEffect(() => {
    fetchExistingSchools();
  }, []);

  const handleManualIdChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      setActiveSchoolId(e.target.value);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Vidyalaya Saathi</h1>
      </header>
      <main className="App-main">
        {!activeSchoolId ? (
            <div className="landing-container">
                {/* >>> ADDED: load an already-registered school instead of re-registering */}
                <div className="existing-schools-panel">
                    <h3>Existing Schools</h3>
                    {loadingSchools && <p className="landing-hint">Checking backend for existing schools...</p>}
                    {loadError && <p className="landing-error">{loadError}</p>}
                    {!loadingSchools && !loadError && existingSchools.length === 0 && (
                        <p className="landing-hint">
                            No schools found in the database yet. Register one below to get started.
                        </p>
                    )}
                    {existingSchools.length > 0 && (
                        <div className="existing-schools-list">
                            {existingSchools.map((s) => (
                                <button
                                    key={s.school_id}
                                    className="existing-school-btn"
                                    onClick={() => setActiveSchoolId(s.school_id)}
                                >
                                    <strong>{s.school_id}</strong>
                                    <span className="existing-school-meta">
                                        {s.name} · {s.problem_count} problem(s)
                                        {s.prioritization_last_run_at ? ' · prioritized' : ''}
                                        {s.budget_plan_last_run_at ? ' · budgeted' : ''}
                                    </span>
                                </button>
                            ))}
                        </div>
                    )}
                    <button className="refresh-schools-btn" onClick={fetchExistingSchools} disabled={loadingSchools}>
                        Refresh list
                    </button>
                </div>

                <div className="landing-divider">or</div>

                <SchoolDataForm onSchoolCreated={setActiveSchoolId} />
            </div>
        ) : (
            <div className="dashboard-container">
                <div className="dashboard-notice">
                    <label style={{fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '10px'}}>
                        Active School ID: 
                        <input 
                            value={activeSchoolId} 
                            onChange={handleManualIdChange}
                            placeholder="Enter assigned School ID"
                            style={{padding: '5px', borderRadius: '4px', border: '1px solid #ccc', minWidth: '300px'}}
                        />
                    </label>
                    <button onClick={() => setActiveSchoolId(null)} className="switch-school-btn">Change School</button>
                </div>
                
                <div className="placeholder-modules">
                    <div className="module-card">
                        <h3>FLN & Student Data Module</h3>
                        <p className="coming-soon">Coming Soon</p>
                        <ModuleUpload activeSchoolId={activeSchoolId} moduleName="FLN & Student Data" />
                    </div>
                    
                    <div className="module-card">
                        <h3>Teacher Workload Module</h3>
                        <p className="coming-soon">Coming Soon</p>
                        <ModuleUpload activeSchoolId={activeSchoolId} moduleName="Teacher Workload" />
                    </div>
                    
                    <div className="module-card">
                        <h3>Infrastructure Module</h3>
                        <p className="coming-soon">Coming Soon</p>
                        <ModuleUpload activeSchoolId={activeSchoolId} moduleName="Infrastructure" />
                    </div>
                </div>

                <PriorityDashboard schoolId={activeSchoolId} />

                <BudgetPlanner schoolId={activeSchoolId} />

                <SchoolExplorer schoolId={activeSchoolId} />
            </div>
        )}
      </main>
    </div>
  );
}

export default App;