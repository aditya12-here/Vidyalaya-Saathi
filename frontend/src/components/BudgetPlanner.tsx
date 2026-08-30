// frontend/src/components/BudgetPlanner.tsx
//
// Lets an admin enter a budget ceiling, run the optimizer, and see which
// problems get funded (mandatory safety items first, then the knapsack-
// optimized remainder) vs. which are left out — with a coverage percentage
// so it's clear how much of the school's total priority-weighted need this
// budget actually addresses.

import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { FiShield, FiTrendingUp, FiXCircle } from 'react-icons/fi';
import './BudgetPlanner.css';

const API_BASE = 'http://localhost:8000/api/v1';

interface Allocation {
    problem_id: string;
    title: string;
    category: string;
    cost: number;
    priority_score: number;
    selected: boolean;
    selection_reason: 'MANDATORY_SAFETY' | 'OPTIMIZED' | 'NOT_SELECTED';
    score_per_currency_unit?: number | null;
}

interface BudgetPlanResponse {
    plan_id?: string;
    school_id: string;
    budget_ceiling: number;
    mandatory_cost: number;
    optimized_cost: number;
    total_spent: number;
    over_budget_on_mandatory: boolean;
    total_priority_score_available: number;
    total_priority_score_covered: number;
    coverage_pct: number;
    allocations: Allocation[];
    message?: string;
}

interface BudgetPlannerProps {
    schoolId: string;
}

const REASON_LABEL: Record<string, string> = {
    MANDATORY_SAFETY: 'Safety-critical (mandatory)',
    OPTIMIZED: 'Funded (optimized)',
    NOT_SELECTED: 'Not funded this round',
};

export const BudgetPlanner: React.FC<BudgetPlannerProps & { refreshTrigger?: number }> = ({ schoolId, refreshTrigger }) => {
    // Default the budget input field to the budget value from the backend, if possible,
    // otherwise fallback to a default value.
    const [budget, setBudget] = useState<string>('200000');
    const [plan, setPlan] = useState<BudgetPlanResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchLatest = async () => {
        try {
            const res = await axios.get(`${API_BASE}/budget/school/${schoolId}/plan/latest`);
            if (res.data.allocations) {
                setPlan(res.data);
                if (res.data.budget_ceiling) {
                    setBudget(res.data.budget_ceiling.toString());
                }
            }
        } catch (err) {
            console.error('Failed to fetch latest budget plan', err);
        }
    };

    useEffect(() => {
        if (schoolId) fetchLatest();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [schoolId, refreshTrigger]);

    const runPlan = async () => {
        const budgetNum = parseFloat(budget);
        if (!budgetNum || budgetNum <= 0) {
            setError('Enter a valid budget amount.');
            return;
        }
        setLoading(true);
        setError(null);
        try {
            const res = await axios.post(`${API_BASE}/budget/school/${schoolId}/plan`, {
                budget_ceiling: budgetNum,
                triggered_by: 'ADMIN',
            });
            setPlan(res.data);
        } catch (err: any) {
            console.error('Failed to run budget plan', err);
            const detail = err?.response?.data?.detail;
            setError(detail || 'Failed to generate a budget plan. Have you run prioritization for this school yet?');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="budget-planner">
            <div className="budget-planner-header">
                <div>
                    <h3>Budget Planner</h3>
                    <p className="budget-subtitle">
                        Enter an available budget to see which problems can be funded —
                        safety-critical issues are always funded first, the rest are
                        chosen to maximize total priority impact covered.
                    </p>
                </div>
                <div className="budget-input-row">
                    <span className="budget-currency">₹</span>
                    <input
                        type="number"
                        value={budget}
                        onChange={(e) => setBudget(e.target.value)}
                        placeholder="Budget ceiling"
                    />
                    <button onClick={runPlan} disabled={loading}>
                        {loading ? 'Optimizing...' : 'Generate Plan'}
                    </button>
                </div>
            </div>

            {error && <div className="budget-error">{error}</div>}

            {plan && plan.allocations && plan.allocations.length > 0 && (
                <>
                    {plan.over_budget_on_mandatory && (
                        <div className="budget-warning">
                            <FiXCircle /> Mandatory safety-critical items alone (₹{plan.mandatory_cost.toLocaleString()})
                            exceed this budget. Nothing else can be funded until the budget increases
                            or the budget ceiling covers at least the mandatory items.
                        </div>
                    )}

                    <div className="budget-summary-grid">
                        <div className="budget-summary-item">
                            <span className="budget-summary-label">Total spent</span>
                            <span className="budget-summary-value">₹{plan.total_spent.toLocaleString()}</span>
                        </div>
                        <div className="budget-summary-item">
                            <span className="budget-summary-label">Mandatory (safety)</span>
                            <span className="budget-summary-value">₹{plan.mandatory_cost.toLocaleString()}</span>
                        </div>
                        <div className="budget-summary-item">
                            <span className="budget-summary-label">Optimized selections</span>
                            <span className="budget-summary-value">₹{plan.optimized_cost.toLocaleString()}</span>
                        </div>
                        <div className="budget-summary-item highlight">
                            <span className="budget-summary-label">Impact coverage</span>
                            <span className="budget-summary-value">{plan.coverage_pct.toFixed(1)}%</span>
                        </div>
                    </div>

                    <div className="budget-allocation-list">
                        {plan.allocations.map((a) => (
                            <div key={a.problem_id} className={`budget-allocation-row ${a.selected ? 'selected' : 'unselected'}`}>
                                <span className="budget-alloc-icon">
                                    {a.selection_reason === 'MANDATORY_SAFETY' ? <FiShield /> :
                                        a.selected ? <FiTrendingUp /> : <FiXCircle />}
                                </span>
                                <div className="budget-alloc-main">
                                    <strong>{a.title}</strong>
                                    <span className="budget-alloc-meta">{a.category} · {REASON_LABEL[a.selection_reason]}</span>
                                </div>
                                <span className="budget-alloc-score">score {a.priority_score.toFixed(1)}</span>
                                <span className="budget-alloc-cost">₹{a.cost.toLocaleString()}</span>
                            </div>
                        ))}
                    </div>
                </>
            )}

            {plan && plan.message && (
                <p className="budget-empty">{plan.message}</p>
            )}
        </div>
    );
};