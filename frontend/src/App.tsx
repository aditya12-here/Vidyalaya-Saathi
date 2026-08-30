import { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import { useAuth } from './contexts/AuthContext';
import { AuthPage } from './pages/AuthPage';
import { SchoolDataForm } from './components/SchoolDataForm';
import { ModuleUpload } from './components/ModuleUpload';
import { PriorityDashboard } from './components/PriorityDashboard';
import { BudgetPlanner } from './components/BudgetPlanner';
import { SchoolExplorer } from './components/SchoolExplorer';
import { ManualProblemForm } from './components/ManualProblemForm';
import { CostOverrideForm } from './components/CostOverrideForm';
import { CbseAffiliation } from './components/CbseAffiliation';
import { InviteUserModal } from './components/InviteUserModal';
import {
    FiFlag, FiTrendingUp, FiDollarSign, FiEye, FiHome,
    FiCheckCircle, FiCircle, FiArrowRight, FiRefreshCw,
    FiLogOut, FiUser, FiShield, FiAward, FiUserPlus,
    FiMapPin, FiCamera
} from 'react-icons/fi';

const API_BASE = 'http://localhost:8000/api/v1';

interface ExistingSchool {
    school_id: string;
    name: string;
    school_code?: string;
    state?: string;
    district?: string;
    total_enrollment?: number;
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
    { icon: <FiHome />, title: '1. Register / Select School', text: 'Manage foundational school profiles and infrastructure data.' },
    { icon: <FiCamera />, title: '2. AI Photo Scan & Problems', text: 'Extract infrastructure anomalies via AI vision scans or manual problem logging.' },
    { icon: <FiTrendingUp />, title: '3. Deterministic Prioritize', text: 'Score open problems based on severity, urgency, student impact, and safety risks.' },
    { icon: <FiDollarSign />, title: '4. Budget Optimization', text: 'Select high-ROI interventions under a defined capital budget ceiling.' },
    { icon: <FiEye />, title: '5. Comprehensive Explorer', text: 'Inspect complete diagnostic audit trails, cost estimates, and outcomes.' },
];

function App() {
    const { user, token, logout, isLoading } = useAuth();

    const [activeSchoolId, setActiveSchoolId] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'main' | 'cbse'>('main');
    const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
    const [existingSchools, setExistingSchools] = useState<ExistingSchool[]>([]);
    const [loadingSchools, setLoadingSchools] = useState(true);
    const [loadError, setLoadError] = useState<string | null>(null);
    const [status, setStatus] = useState<SchoolStatus | null>(null);
    const [statusLoading, setStatusLoading] = useState(false);

    const [budgetRefreshTrigger, setBudgetRefreshTrigger] = useState(0);
    const [problemsRefreshTrigger, setProblemsRefreshTrigger] = useState(0);

    // Sync school ID for school-scoped roles
    useEffect(() => {
        if (user) {
            if (user.role === 'SCHOOL_MANAGEMENT' || user.role === 'COMMUNITY') {
                setActiveSchoolId(user.school_id || null);
            }
        } else {
            setActiveSchoolId(null);
        }
    }, [user]);

    const fetchExistingSchools = async () => {
        setLoadingSchools(true);
        setLoadError(null);
        try {
            const res = await axios.get(`${API_BASE}/explorer/schools`);
            setExistingSchools(res.data.schools || []);
        } catch (err) {
            console.error('Failed to fetch existing schools', err);
            setLoadError('Could not reach backend to list schools. Please verify the backend server is running.');
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
        if (token && user) {
            fetchExistingSchools();
        }
    }, [token, user]);

    useEffect(() => {
        if (activeSchoolId) {
            fetchSchoolStatus(activeSchoolId);
        } else {
            setStatus(null);
        }
    }, [activeSchoolId]);

    const scrollTo = (id: string) => {
        document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };

    // 1. Loading State
    if (isLoading) {
        return (
            <div className="auth-loading-screen">
                <div className="auth-spinner" />
                <p>Authenticating session...</p>
            </div>
        );
    }

    // 2. Unauthenticated State -> Always show Auth Page
    if (!token || !user) {
        return <AuthPage />;
    }

    // Role helper badges
    const getRoleBadge = () => {
        switch (user.role) {
            case 'DISTRICT_OFFICER':
                return <span className="role-badge role-admin"><FiShield /> District Officer (Admin)</span>;
            case 'SCHOOL_MANAGEMENT':
                return <span className="role-badge role-management"><FiHome /> School Management ({user.school_id || 'Unassigned'})</span>;
            case 'SURVEYOR':
                return <span className="role-badge role-surveyor"><FiCamera /> Field Surveyor</span>;
            case 'COMMUNITY':
                return <span className="role-badge role-community"><FiUser /> Community Member ({user.school_id || 'Local'})</span>;
            default:
                return <span className="role-badge">{user.role}</span>;
        }
    };

    const isGlobalRole = user.role === 'DISTRICT_OFFICER' || user.role === 'SURVEYOR';

    return (
        <div className="App">
            {/* Top Global Header */}
            <header className="App-header">
                <div className="header-top-row">
                    <div className="brand-section">
                        <h1>Vidyalaya Saathi</h1>
                        <p>Diagnostic Engine for School Infrastructure & Outcomes</p>
                    </div>

                    <div className="user-profile-bar">
                        <div className="user-info">
                            {getRoleBadge()}
                            <span className="user-email"><FiUser /> {user.email}</span>
                        </div>

                        <button className="logout-btn" onClick={logout} title="Sign Out">
                            <FiLogOut /> Logout
                        </button>
                    </div>
                </div>

                {/* Role Specific Navigation Bar */}
                <div className="header-nav-bar">
                    {user.role === 'DISTRICT_OFFICER' && (
                        <div className="nav-tabs">
                            <button
                                className={`nav-tab-btn ${activeTab === 'main' ? 'active' : ''}`}
                                onClick={() => setActiveTab('main')}
                            >
                                <FiHome /> District Dashboard
                            </button>
                            <button
                                className={`nav-tab-btn ${activeTab === 'cbse' ? 'active' : ''}`}
                                onClick={() => setActiveTab('cbse')}
                            >
                                <FiAward /> CBSE Affiliation Tool
                            </button>
                            <button
                                className="nav-tab-action"
                                onClick={() => setIsInviteModalOpen(true)}
                            >
                                <FiUserPlus /> Invite User / School Staff
                            </button>
                        </div>
                    )}

                    {user.role === 'SURVEYOR' && (
                        <div className="nav-tabs">
                            <button className="nav-tab-btn active">
                                <FiCamera /> Field Survey &amp; Inspection Dashboard
                            </button>
                        </div>
                    )}

                    {user.role === 'SCHOOL_MANAGEMENT' && (
                        <div className="nav-tabs">
                            <button className="nav-tab-btn active">
                                <FiHome /> School Management Portal
                            </button>
                        </div>
                    )}

                    {user.role === 'COMMUNITY' && (
                        <div className="nav-tabs">
                            <button className="nav-tab-btn active">
                                <FiUser /> Community Grievance &amp; Transparency Portal
                            </button>
                        </div>
                    )}
                </div>
            </header>

            {/* Main Application Container */}
            <main className="App-main">
                {/* CBSE Tool (District Officer only) */}
                {activeTab === 'cbse' && user.role === 'DISTRICT_OFFICER' ? (
                    <div className="cbse-wrapper">
                        <CbseAffiliation />
                    </div>
                ) : (
                    <>
                        {/* ========================================================================= */}
                        {/* VIEW 1: GLOBAL USERS (District Officer & Surveyor) WHEN NO SCHOOL SELECTED */}
                        {/* ========================================================================= */}
                        {isGlobalRole && !activeSchoolId ? (
                            <div className="landing-container">
                                <section className="intro-panel">
                                    <h2>
                                        {user.role === 'DISTRICT_OFFICER' 
                                            ? 'District Infrastructure Command Center' 
                                            : 'Field Surveyor Inspection Center'}
                                    </h2>
                                    <p className="intro-text">
                                        Select an existing school from the district registry below to launch diagnostics,
                                        view AI-ranked priorities, update inspection surveys, or optimize funding.
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

                                {/* School Registry Selection */}
                                <section className="existing-schools-panel">
                                    <div className="panel-header-row">
                                        <h3>Registered District Schools</h3>
                                        <button className="refresh-schools-btn" onClick={fetchExistingSchools} disabled={loadingSchools}>
                                            <FiRefreshCw className={loadingSchools ? 'spin' : ''} /> Refresh Directory
                                        </button>
                                    </div>

                                    {loadingSchools && <p className="landing-hint">Querying district database for schools...</p>}
                                    {loadError && <p className="landing-error">{loadError}</p>}
                                    {!loadingSchools && !loadError && existingSchools.length === 0 && (
                                        <p className="landing-hint">No schools registered yet. Add a new school below to start.</p>
                                    )}

                                    {existingSchools.length > 0 && (
                                        <div className="existing-schools-grid">
                                            {existingSchools.map((s) => (
                                                <div key={s.school_id} className="school-directory-card">
                                                    <div className="school-card-main">
                                                        <div className="school-card-title">
                                                            <strong>{s.name}</strong>
                                                            <span className="school-card-id">{s.school_id}</span>
                                                        </div>
                                                        <div className="school-card-tags">
                                                            <span className="sc-tag problems-tag">
                                                                <FiFlag /> {s.problem_count} Problem{s.problem_count === 1 ? '' : 's'}
                                                            </span>
                                                            {s.prioritization_last_run_at && (
                                                                <span className="sc-tag prioritized-tag">
                                                                    <FiCheckCircle /> Prioritized
                                                                </span>
                                                            )}
                                                            {s.budget_plan_last_run_at && (
                                                                <span className="sc-tag budgeted-tag">
                                                                    <FiDollarSign /> Budgeted
                                                                </span>
                                                            )}
                                                        </div>
                                                        <div className="school-card-location">
                                                            <FiMapPin /> {s.district || 'District'}, {s.state || 'State'}
                                                        </div>
                                                    </div>
                                                    <button
                                                        className="school-select-btn"
                                                        onClick={() => setActiveSchoolId(s.school_id)}
                                                    >
                                                        {user.role === 'SURVEYOR' ? 'Start Inspection' : 'Manage & Diagnose'} <FiArrowRight />
                                                    </button>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </section>

                                {/* Only District Officer can register a new school */}
                                {user.role === 'DISTRICT_OFFICER' && (
                                    <>
                                        <div className="landing-divider">or register a new school into system</div>
                                        <SchoolDataForm onSchoolCreated={(newId) => {
                                            fetchExistingSchools();
                                            setActiveSchoolId(newId);
                                        }} />
                                    </>
                                )}
                            </div>
                        ) : activeSchoolId ? (
                            /* ========================================================================= */
                            /* VIEW 2: ACTIVE SCHOOL DASHBOARD (Scoped by Role)                          */
                            /* ========================================================================= */
                            <div className="dashboard-container">
                                {/* School Context Strip */}
                                <div className="dashboard-notice">
                                    <div className="active-school-meta">
                                        <span className="school-label">Active School:</span>
                                        <strong className="school-code-badge">{activeSchoolId}</strong>
                                        {user.role === 'SCHOOL_MANAGEMENT' && <span className="school-lock-pill">Assigned School</span>}
                                        {user.role === 'COMMUNITY' && <span className="school-lock-pill">Local Community Campus</span>}
                                    </div>
                                    
                                    {isGlobalRole && (
                                        <button onClick={() => setActiveSchoolId(null)} className="switch-school-btn">
                                            <FiArrowRight style={{ transform: 'rotate(180deg)' }} /> Change / Switch School
                                        </button>
                                    )}
                                </div>

                                {/* Flow Progress Strip (Guided Navigation) */}
                                <div className="flow-strip">
                                    <div className="flow-strip-header">
                                        <span>System Diagnostic Flow</span>
                                        <button className="flow-refresh-btn" onClick={() => fetchSchoolStatus(activeSchoolId)} disabled={statusLoading}>
                                            <FiRefreshCw className={statusLoading ? 'spin' : ''} /> Refresh Status
                                        </button>
                                    </div>
                                    <div className="flow-steps">
                                        <button className="flow-step" onClick={() => scrollTo('step-data')}>
                                            {status && status.problemCount > 0 ? <FiCheckCircle className="flow-done" /> : <FiCircle className="flow-pending" />}
                                            <span>
                                                {user.role === 'COMMUNITY' ? '1. Report Grievance' : '1. Data & Problems'} 
                                                {status ? ` (${status.problemCount})` : ''}
                                            </span>
                                        </button>
                                        
                                        {user.role !== 'COMMUNITY' && (
                                            <>
                                                <FiArrowRight className="flow-arrow" />
                                                <button className="flow-step" onClick={() => scrollTo('step-prioritize')}>
                                                    {status?.hasPrioritization ? <FiCheckCircle className="flow-done" /> : <FiCircle className="flow-pending" />}
                                                    <span>2. AI Prioritize</span>
                                                </button>
                                            </>
                                        )}

                                        {user.role === 'DISTRICT_OFFICER' && (
                                            <>
                                                <FiArrowRight className="flow-arrow" />
                                                <button className="flow-step" onClick={() => scrollTo('step-budget')}>
                                                    {status?.hasBudgetPlan ? <FiCheckCircle className="flow-done" /> : <FiCircle className="flow-pending" />}
                                                    <span>3. Budget Plan</span>
                                                </button>
                                            </>
                                        )}

                                        {user.role === 'SCHOOL_MANAGEMENT' && (
                                            <>
                                                <FiArrowRight className="flow-arrow" />
                                                <button className="flow-step" onClick={() => scrollTo('step-cost-override')}>
                                                    <FiDollarSign className="flow-neutral" />
                                                    <span>3. Cost Quotes</span>
                                                </button>
                                            </>
                                        )}

                                        <FiArrowRight className="flow-arrow" />
                                        <button className="flow-step" onClick={() => scrollTo('step-explore')}>
                                            <FiEye className="flow-neutral" />
                                            <span>{user.role === 'COMMUNITY' ? '2. School Status Explorer' : '4. Data Explorer'}</span>
                                        </button>
                                    </div>
                                </div>

                                {/* ------------------------------------------------------------- */}
                                {/* STEP 1: FOUNDATIONAL DATA & EVIDENCE LOGGING                  */}
                                {/* ------------------------------------------------------------- */}
                                <section id="step-data" className="flow-section">
                                    <h3 className="flow-section-title">
                                        {user.role === 'COMMUNITY' ? 'Step 1 · Submit Grievance / Report Problem' : 'Step 1 · Diagnostic Data & Problem Flagging'}
                                    </h3>
                                    <p className="flow-section-desc">
                                        {user.role === 'COMMUNITY'
                                            ? 'Report any broken infrastructure, hazardous conditions, or urgent repair needs observed at your school.'
                                            : user.role === 'SURVEYOR'
                                            ? 'Upload inspection photos across school facilities for AI computer vision anomaly detection, and log manual observations.'
                                            : 'Upload module evidence, analyze physical school conditions with AI vision, and register infrastructure anomalies.'}
                                    </p>

                                    {/* AI Vision Modules (Available to District Officer, Management, and Surveyor) */}
                                    {user.role !== 'COMMUNITY' && (
                                        <div className="placeholder-modules">
                                            <div className="module-card">
                                                <h3>FLN &amp; Student Data</h3>
                                                <p className="coming-soon">AI Reading / Attendance Scan</p>
                                                <ModuleUpload activeSchoolId={activeSchoolId} moduleName="FLN & Student Data" />
                                            </div>
                                            <div className="module-card">
                                                <h3>Teacher Workload</h3>
                                                <p className="coming-soon">Timetable / Staff Allocation</p>
                                                <ModuleUpload activeSchoolId={activeSchoolId} moduleName="Teacher Workload" />
                                            </div>
                                            <div className="module-card">
                                                <h3>Infrastructure Photos</h3>
                                                <p className="coming-soon">Vision AI Defect Detection</p>
                                                <ModuleUpload activeSchoolId={activeSchoolId} moduleName="Infrastructure" />
                                            </div>
                                        </div>
                                    )}

                                    {/* Manual Problem Flagging Form (All roles can flag problems) */}
                                    <ManualProblemForm
                                        schoolId={activeSchoolId}
                                        onProblemCreated={() => {
                                            fetchSchoolStatus(activeSchoolId);
                                            setProblemsRefreshTrigger(prev => prev + 1);
                                        }}
                                    />
                                </section>

                                {/* ------------------------------------------------------------- */}
                                {/* STEP 2: PRIORITIZATION ENGINE (Officer, Management, Surveyor)  */}
                                {/* ------------------------------------------------------------- */}
                                {user.role !== 'COMMUNITY' && (
                                    <section id="step-prioritize" className="flow-section">
                                        <h3 className="flow-section-title">Step 2 · AI Prioritization Engine</h3>
                                        <p className="flow-section-desc">
                                            Scores eligible open problems across severity, student reach, educational impact,
                                            urgency, and data confidence into an explainable ranked priority list.
                                        </p>
                                        <PriorityDashboard schoolId={activeSchoolId} />
                                    </section>
                                )}

                                {/* ------------------------------------------------------------- */}
                                {/* STEP 3: BUDGET PLANNING & COST CONTROLS                       */}
                                {/* ------------------------------------------------------------- */}
                                {user.role === 'DISTRICT_OFFICER' && (
                                    <section id="step-budget" className="flow-section">
                                        <h3 className="flow-section-title">Step 3 · Budget Optimization Engine</h3>
                                        <p className="flow-section-desc">
                                            Allocate capital under a budget ceiling. Safety-critical issues are funded first,
                                            followed by high-ROI interventions that maximize covered need.
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
                                )}

                                {user.role === 'SCHOOL_MANAGEMENT' && (
                                    <section id="step-cost-override" className="flow-section">
                                        <h3 className="flow-section-title">Step 3 · Local Contractor Quotes &amp; Cost Overrides</h3>
                                        <p className="flow-section-desc">
                                            Submit local quotations or actual vendor estimates for problems flagged at your school.
                                            These real-world costs inform the District Officer's budget allocation.
                                        </p>
                                        <CostOverrideForm
                                            schoolId={activeSchoolId}
                                            refreshTrigger={problemsRefreshTrigger}
                                            onCostOverridden={() => {
                                                fetchSchoolStatus(activeSchoolId);
                                                setBudgetRefreshTrigger(prev => prev + 1);
                                            }}
                                        />
                                    </section>
                                )}

                                {/* ------------------------------------------------------------- */}
                                {/* STEP 4: EXPLORE FULL SCHOOL DATA (All Roles)                  */}
                                {/* ------------------------------------------------------------- */}
                                <section id="step-explore" className="flow-section">
                                    <h3 className="flow-section-title">
                                        {user.role === 'COMMUNITY' ? 'Step 2 · School Diagnostic & Funding Explorer' : 'Step 4 · Complete School Records Explorer'}
                                    </h3>
                                    <p className="flow-section-desc">
                                        A comprehensive read-only audit view of all student metrics, teacher data, infrastructure records,
                                        flagged issues, and funding decisions recorded for this school.
                                    </p>
                                    <SchoolExplorer schoolId={activeSchoolId} />
                                </section>
                            </div>
                        ) : (
                            <div className="empty-state-notice">
                                <p>No school assigned to this account. Please contact your District Administrator.</p>
                            </div>
                        )}
                    </>
                )}
            </main>

            {/* Invite User Modal (District Officer only) */}
            {user.role === 'DISTRICT_OFFICER' && (
                <InviteUserModal
                    isOpen={isInviteModalOpen}
                    onClose={() => setIsInviteModalOpen(false)}
                    availableSchools={existingSchools.map(s => ({ school_id: s.school_id, name: s.name }))}
                />
            )}
        </div>
    );
}

export default App;