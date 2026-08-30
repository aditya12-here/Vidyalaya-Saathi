import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { FiDollarSign } from 'react-icons/fi';
import './CostOverrideForm.css';

const API_BASE = 'http://localhost:8000/api/v1';

interface FlaggedProblem {
    problem_id: string;
    title: string;
    category: string;
    condition: string | null;
}

interface CostOverrideFormProps {
    schoolId: string;
    onCostOverridden?: () => void;
    refreshTrigger?: number;
}

export const CostOverrideForm: React.FC<CostOverrideFormProps> = ({ schoolId, onCostOverridden, refreshTrigger }) => {
    const [flagged, setFlagged] = useState<FlaggedProblem[]>([]);
    const [loadingList, setLoadingList] = useState(false);
    const [selectedProblemId, setSelectedProblemId] = useState<string>('');
    const [cost, setCost] = useState<string>('');
    const [notes, setNotes] = useState<string>('');
    
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMsg, setSuccessMsg] = useState<string | null>(null);

    const fetchFlagged = async () => {
        setLoadingList(true);
        try {
            const res = await axios.get(`${API_BASE}/problems/school/${schoolId}`);
            setFlagged(res.data || []);
        } catch (err) {
            console.error('Failed to fetch flagged problems', err);
        } finally {
            setLoadingList(false);
        }
    };

    useEffect(() => {
        if (schoolId) {
            fetchFlagged();
        }
    }, [schoolId, refreshTrigger]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        if (!selectedProblemId) {
            setError('Please select a problem.');
            return;
        }

        const costNum = parseFloat(cost);
        if (isNaN(costNum) || costNum < 0) {
            setError('Please enter a valid cost amount.');
            return;
        }

        setSubmitting(true);
        setError(null);
        setSuccessMsg(null);

        try {
            await axios.put(`${API_BASE}/budget/cost/${selectedProblemId}`, {
                school_id: schoolId,
                cost: costNum,
                notes: notes || undefined
            });

            // Automatically run the budget planner for the school when a cost override is applied,
            // using a default/current budget ceiling (e.g. 200000, which is the default in BudgetPlanner)
            try {
                // To maintain the current budget ceiling, we try to fetch it first. 
                // If there's no previous plan, we fallback to 200000.
                let currentCeiling = 200000;
                try {
                    const latestRes = await axios.get(`${API_BASE}/budget/school/${schoolId}/plan/latest`);
                    if (latestRes.data && latestRes.data.budget_ceiling) {
                        currentCeiling = latestRes.data.budget_ceiling;
                    }
                } catch (e) {
                    // ignore if no latest plan exists yet
                }

                await axios.post(`${API_BASE}/budget/school/${schoolId}/plan`, {
                    budget_ceiling: currentCeiling, 
                    triggered_by: 'ADMIN_AUTO_AFTER_COST_OVERRIDE',
                });
            } catch (planErr) {
                console.error('Automatically running budget plan failed (this is non-fatal)', planErr);
            }

            setSuccessMsg(`Cost override applied successfully.`);
            setCost('');
            setNotes('');
            setSelectedProblemId('');
            
            onCostOverridden?.();
        } catch (err: any) {
            console.error('Failed to override cost', err);
            setError(err?.response?.data?.detail || 'Failed to apply cost override.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="cost-override-form">
            <h4 className="cof-heading">Override Problem Cost</h4>
            <p className="cof-subtitle">Manually set the exact budget required to fix a specific problem.</p>

            <form onSubmit={handleSubmit} className="cof-form">
                <label className="cof-field cof-field-full">
                    <span>Select Problem *</span>
                    <select 
                        value={selectedProblemId} 
                        onChange={(e) => setSelectedProblemId(e.target.value)}
                        required
                        disabled={loadingList || flagged.length === 0}
                    >
                        <option value="" disabled>
                            {loadingList ? 'Loading problems...' : 
                             flagged.length === 0 ? 'No problems found for this school' : 
                             '-- Select a problem --'}
                        </option>
                        {flagged.map(p => (
                            <option key={p.problem_id} value={p.problem_id}>
                                {p.title} ({p.category})
                            </option>
                        ))}
                    </select>
                </label>

                <div className="cof-row">
                    <label className="cof-field">
                        <span>Cost Amount (₹) *</span>
                        <input 
                            type="number" 
                            min="0"
                            step="0.01"
                            value={cost} 
                            onChange={(e) => setCost(e.target.value)} 
                            placeholder="e.g. 45000" 
                            required 
                        />
                    </label>
                </div>

                <label className="cof-field cof-field-full">
                    <span>Notes / Justification (optional)</span>
                    <textarea 
                        value={notes} 
                        onChange={(e) => setNotes(e.target.value)} 
                        rows={2} 
                        placeholder="e.g. Electrician quote for full rewiring" 
                    />
                </label>

                {error && <div className="cof-error">{error}</div>}
                {successMsg && <div className="cof-success">{successMsg}</div>}

                <button type="submit" className="cof-submit-btn" disabled={submitting || !selectedProblemId}>
                    <FiDollarSign /> {submitting ? 'Applying...' : 'Apply Cost Override'}
                </button>
            </form>
        </div>
    );
};
