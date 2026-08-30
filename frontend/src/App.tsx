// frontend/src/App.tsx
//
// FULL REPLACEMENT FILE — supersedes the previous App.tsx. Two structural
// changes, no new backend calls beyond one extra read:
//
// 1. LANDING PAGE now opens with a short explanation of what this portal
//    is and a numbered "How it works" overview, BEFORE the existing-schools
//    list / registration form — so a first-time visitor understands the
//    product before being asked to do anything.
//
// 2. DASHBOARD (once a school is selected) is now a guided, numbered flow
//    with section headers explaining what each part does, plus a status
//    strip at the top (Data Logged? / Prioritized? / Budgeted?) computed
//    from GET /explorer/schools/{id}, with click-to-jump links to each
//    section — instead of four unlabeled panels stacked with no context.
//
// No existing component (PriorityDashboard, BudgetPlanner, SchoolExplorer,
// ModuleUpload, SchoolDataForm) is modified — this file only rearranges
// and labels them.

import { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import { SchoolDataForm } from './components/SchoolDataForm';
import { ModuleUpload } from './components/ModuleUpload';
import { PriorityDashboard } from './components/PriorityDashboard';
import { BudgetPlanner } from './components/BudgetPlanner';
import { SchoolExplorer } from './components/SchoolExplorer';
import { ManualProblemForm } from './components/ManualProblemForm'; // >>> ADDED
import { CostOverrideForm } from './components/CostOverrideForm'; // >>> ADDED
import { CbseAffiliation } from './components/CbseAffiliation'; // >>> ADDED
import {
    FiFlag, FiTrendingUp, FiDollarSign, FiEye, FiHome,
    FiCheckCircle, FiCircle, FiArrowRight, FiRefreshCw,
} from 'react-icons/fi';

const API_BASE = 'http://localhost:8000/api/v1';

interface ExistingSchool {
    school_id: string;
    name: string;
    problem_count: number;
    prioritization_last_run_at: string | null;
    budget_plan_last_run_at: string | null;
}

interface SchoolStatus {
    problemCount: number;
    hasPrioritization: boolean;
    hasBudgetPlan: boolean;
}

const HOW_IT_WORKS = [
    { icon: <FiHome />, title: '1. Register a School', text: 'Create a school profile — the anchor every other record attaches to.' },
    { icon: <FiFlag />, title: '2. Log Data & Flag Problems', text: 'Record attendance, learning, teacher, and infrastructure data; flag problems via AI photo scan or manual entry.' },
    { icon: <FiTrendingUp />, title: '3. Prioritize', text: 'The engine scores every open problem — severity, impact, reach, urgency, confidence, and school context — into a ranked, explainable list.' },
    { icon: <FiDollarSign />, title: '4. Plan the Budget', text: 'Given a budget ceiling, the optimizer funds safety-critical issues first, then the combination of remaining problems that covers the most total need.' },
    { icon: <FiEye />, title: '5. Explore Everything', text: 'See every raw record and every computed result for a school in one place, at any time.' },
];

function App() {
    const [activeSchoolId, setActiveSchoolId] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'main' | 'cbse'>('main'); // >>> ADDED
    const [existingSchools, setExistingSchools] = useState<ExistingSchool[]>([]);
    const [loadingSchools, setLoadingSchools] = useState(true);
    const [loadError, setLoadError] = useState<string | null>(null);
    const [status, setStatus] = useState<SchoolStatus | null>(null);
    const [statusLoading, setStatusLoading] = useState(false);

    const [budgetRefreshTrigger, setBudgetRefreshTrigger] = useState(0);

    const [problemsRefreshTrigger, setProblemsRefreshTrigger] = useState(0);

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

    const fetchSchoolStatus = async (schoolId: string) => {
        setStatusLoading(true);
        try {
            const res = await axios.get(`${API_BASE}/explorer/schools/${schoolId}`);
            setStatus({
                problemCount: (res.data.problems || []).length,
                hasPrioritization: !!res.data.latest_prioritization_run,
                hasBudgetPlan: !!res.data.latest_budget_plan,
            });
        } catch (err) {
            console.error('Failed to fetch school status', err);
        } finally {
            setStatusLoading(false);
        }
    };

    useEffect(() => {
        fetchExistingSchools();
    }, []);

    useEffect(() => {
        if (activeSchoolId) fetchSchoolStatus(activeSchoolId);
        else setStatus(null);
    }, [activeSchoolId]);

    const handleManualIdChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setActiveSchoolId(e.target.value);
    };

    const scrollTo = (id: string) => {
        document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };

    return (
        <div className="App">
            <header className="App-header">
                <h1>Vidyalaya Saathi</h1>
                <p>A diagnostic engine for government school infrastructure and outcomes.</p>
                <div style={{ marginTop: '1rem', display: 'flex', gap: '1rem' }}>
                    <button 
                        style={{ padding: '0.5rem 1rem', background: activeTab === 'main' ? '#2563eb' : '#e2e8f0', color: activeTab === 'main' ? 'white' : '#0f172a', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 600 }}
                        onClick={() => setActiveTab('main')}
                    >
                        Dashboard
                    </button>
                    <button 
                        style={{ padding: '0.5rem 1rem', background: activeTab === 'cbse' ? '#2563eb' : '#e2e8f0', color: activeTab === 'cbse' ? 'white' : '#0f172a', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 600 }}
                        onClick={() => setActiveTab('cbse')}
                    >
                        CBSE Affiliation
                    </button>
                </div>
            </header>
            <main className="App-main">
                {activeTab === 'cbse' ? (
                    <div style={{ padding: '2rem' }}>
                        <CbseAffiliation />
                    </div>
                ) : !activeSchoolId ? (
                    <div className="landing-container">
                        <section className="intro-panel">
                            <h2>What this portal does</h2>
                            <p className="intro-text">
                                Vidyalaya Saathi turns raw school data and flagged problems into a ranked,
                                explainable list of what needs fixing first — and, given a budget, exactly
                                what that budget should fund. Follow the five steps below for any school.
                            </p>
                            <div className="how-it-works-grid">
                                {HOW_IT_WORKS.map((step) => (
                                    <div className="how-it-works-card" key={step.title}>
                                        <div className="hiw-icon">{step.icon}</div>
                                        <h4>{step.title}</h4>
                                        <p>{step.text}</p>
                                    </div>
                                ))}
                            </div>
                        </section>

                        <section className="existing-schools-panel">
                            <h3>Continue with an Existing School</h3>
                            {loadingSchools && <p className="landing-hint">Checking backend for existing schools...</p>}
                            {loadError && <p className="landing-error">{loadError}</p>}
                            {!loadingSchools && !loadError && existingSchools.length === 0 && (
                                <p className="landing-hint">
                                    No schools found yet. Register one below to get started.
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
                        </section>

                        <div className="landing-divider">or register a new school</div>

                        <SchoolDataForm onSchoolCreated={setActiveSchoolId} />
                    </div>
                ) : (
                    <div className="dashboard-container">
                        <div className="dashboard-notice">
                            <label style={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '10px' }}>
                                Active School ID:
                                <input
                                    value={activeSchoolId}
                                    onChange={handleManualIdChange}
                                    placeholder="Enter assigned School ID"
                                    style={{ padding: '5px', borderRadius: '4px', border: '1px solid #ccc', minWidth: '300px' }}
                                />
                            </label>
                            <button onClick={() => setActiveSchoolId(null)} className="switch-school-btn">Change School</button>
                        </div>

                        {/* Guided flow: status strip + jump links */}
                        <div className="flow-strip">
                            <div className="flow-strip-header">
                                <span>Progress for this school</span>
                                <button className="flow-refresh-btn" onClick={() => fetchSchoolStatus(activeSchoolId)} disabled={statusLoading}>
                                    <FiRefreshCw className={statusLoading ? 'spin' : ''} /> Refresh status
                                </button>
                            </div>
                            <div className="flow-steps">
                                <button className="flow-step" onClick={() => scrollTo('step-data')}>
                                    {status && status.problemCount > 0 ? <FiCheckCircle className="flow-done" /> : <FiCircle className="flow-pending" />}
                                    <span>Data & Problems {status ? `(${status.problemCount})` : ''}</span>
                                </button>
                                <FiArrowRight className="flow-arrow" />
                                <button className="flow-step" onClick={() => scrollTo('step-prioritize')}>
                                    {status?.hasPrioritization ? <FiCheckCircle className="flow-done" /> : <FiCircle className="flow-pending" />}
                                    <span>Prioritize</span>
                                </button>
                                <FiArrowRight className="flow-arrow" />
                                <button className="flow-step" onClick={() => scrollTo('step-budget')}>
                                    {status?.hasBudgetPlan ? <FiCheckCircle className="flow-done" /> : <FiCircle className="flow-pending" />}
                                    <span>Budget Plan</span>
                                </button>
                                <FiArrowRight className="flow-arrow" />
                                <button className="flow-step" onClick={() => scrollTo('step-explore')}>
                                    <FiEye className="flow-neutral" />
                                    <span>Explore Data</span>
                                </button>
                            </div>
                        </div>

                        <section id="step-data" className="flow-section">
                            <h3 className="flow-section-title">Step 1 · Log Data &amp; Flag Problems</h3>
                            <p className="flow-section-desc">
                                Record attendance/learning/teacher/infrastructure data, and flag problems —
                                either via photo upload (AI-analyzed) or manually below.
                            </p>
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
                            {/* >>> ADDED: manual problem flagging, no photo required */}
                            <ManualProblemForm
                                schoolId={activeSchoolId}
                                onProblemCreated={() => {
                                    fetchSchoolStatus(activeSchoolId);
                                    setProblemsRefreshTrigger(prev => prev + 1);
                                }}
                            />
                        </section>

                        <section id="step-prioritize" className="flow-section">
                            <h3 className="flow-section-title">Step 2 · Prioritize the Problems</h3>
                            <p className="flow-section-desc">
                                Scores every open problem across six weighted factors into a ranked, explainable list.
                            </p>
                            <PriorityDashboard schoolId={activeSchoolId} />
                        </section>

                        <section id="step-budget" className="flow-section">
                            <h3 className="flow-section-title">Step 3 A Plan the Budget</h3>
                            <p className="flow-section-desc">
                                Enter a budget ceiling to see exactly which problems get funded, and why.
                                You can also override the cost of specific problems before planning.
                            </p>
                            <CostOverrideForm 
                                schoolId={activeSchoolId} 
                                refreshTrigger={problemsRefreshTrigger}
                                onCostOverridden={() => {
                                    fetchSchoolStatus(activeSchoolId);
                                    setBudgetRefreshTrigger(prev => prev + 1);
                                }} 
                            />
                            <BudgetPlanner schoolId={activeSchoolId} refreshTrigger={budgetRefreshTrigger} />
                        </section>

                        <section id="step-explore" className="flow-section">
                            <h3 className="flow-section-title">Step 4 · Explore the Full Data</h3>
                            <p className="flow-section-desc">
                                A read-only view of every record stored for this school, across every step above.
                            </p>
                            <SchoolExplorer schoolId={activeSchoolId} />
                        </section>
                    </div>
                )}
            </main>
        </div>
    );
}

export default App;