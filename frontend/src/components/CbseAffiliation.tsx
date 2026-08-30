import React, { useState } from 'react';
import './CbseAffiliation.css';

interface AffiliationFormData {
  schoolName: string;
  totalStudent: number | '';
  totalTeacher: number | '';
  landArea: number | '';
  stateNoc: boolean;
  fireSafetyCert: boolean;
  healthCert: boolean;
  buildingSafetyCert: boolean;
  hasLibrary: boolean;
  hasScienceLab: boolean;
  hasMathLab: boolean;
  hasSeperateWashroom: boolean;
}

interface AffiliationResult {
  success: boolean;
  schoolName: string;
  status: 'READY' | 'NOT_READY' | string;
  mendatoryCondition?: string[];
  recomendation?: string[];
  message?: string;
  [key: string]: any;
}

export const CbseAffiliation: React.FC = () => {
  const [formData, setFormData] = useState<AffiliationFormData>({
    schoolName: '',
    totalStudent: '',
    totalTeacher: '',
    landArea: '',
    stateNoc: false,
    fireSafetyCert: false,
    healthCert: false,
    buildingSafetyCert: false,
    hasLibrary: false,
    hasScienceLab: false,
    hasMathLab: false,
    hasSeperateWashroom: false,
  });

  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<AffiliationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showRawData, setShowRawData] = useState(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : type === 'number' ? (value === '' ? '' : Number(value)) : value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setResult(null);

    const payload = {
      ...formData,
      totalStudent: Number(formData.totalStudent) || 0,
      totalTeacher: Number(formData.totalTeacher) || 0,
      landArea: Number(formData.landArea) || 0,
    };

    try {
      const response = await fetch('http://127.0.0.1:8000/api/v1/check', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setResult(data);
      } else {
        setResult({
          success: false,
          schoolName: 'Evaluation Error',
          status: 'API Error',
          message: data.message || 'An unknown error occurred during validation.'
        });
      }
    } catch (err: any) {
      setError(err.message || 'Could not connect to the server. Make sure the FastAPI backend is running.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="cbse-container">
      <div className="header">
        <h1>CBSE Affiliation Checker</h1>
        <p>Verify school readiness for CBSE affiliation</p>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            <div className="form-group full-width">
              <label htmlFor="schoolName">School Name</label>
              <input
                type="text"
                id="schoolName"
                name="schoolName"
                required
                placeholder="Enter complete school name"
                value={formData.schoolName}
                onChange={handleInputChange}
              />
            </div>

            <div className="form-group">
              <label htmlFor="totalStudent">Total Students</label>
              <input
                type="number"
                id="totalStudent"
                name="totalStudent"
                required
                min="1"
                placeholder="e.g., 500"
                value={formData.totalStudent}
                onChange={handleInputChange}
              />
            </div>

            <div className="form-group">
              <label htmlFor="totalTeacher">Total Teachers</label>
              <input
                type="number"
                id="totalTeacher"
                name="totalTeacher"
                required
                min="1"
                placeholder="e.g., 25"
                value={formData.totalTeacher}
                onChange={handleInputChange}
              />
            </div>

            <div className="form-group">
              <label htmlFor="landArea">Land Area (sq. meters)</label>
              <input
                type="number"
                id="landArea"
                name="landArea"
                required
                min="1"
                step="0.01"
                placeholder="e.g., 8000"
                value={formData.landArea}
                onChange={handleInputChange}
              />
            </div>
          </div>

          <div className="form-group full-width" style={{ marginTop: '1.5rem' }}>
            <label style={{ marginBottom: '0.5rem' }}>Certificates & Facilities Requirements</label>
            <div className="checkbox-grid">
              <div className="checkbox-group">
                <input
                  type="checkbox"
                  id="stateNoc"
                  name="stateNoc"
                  checked={formData.stateNoc}
                  onChange={handleInputChange}
                />
                <label htmlFor="stateNoc">State NOC</label>
              </div>
              <div className="checkbox-group">
                <input
                  type="checkbox"
                  id="fireSafetyCert"
                  name="fireSafetyCert"
                  checked={formData.fireSafetyCert}
                  onChange={handleInputChange}
                />
                <label htmlFor="fireSafetyCert">Fire Safety Cert</label>
              </div>
              <div className="checkbox-group">
                <input
                  type="checkbox"
                  id="healthCert"
                  name="healthCert"
                  checked={formData.healthCert}
                  onChange={handleInputChange}
                />
                <label htmlFor="healthCert">Health Certificate</label>
              </div>
              <div className="checkbox-group">
                <input
                  type="checkbox"
                  id="buildingSafetyCert"
                  name="buildingSafetyCert"
                  checked={formData.buildingSafetyCert}
                  onChange={handleInputChange}
                />
                <label htmlFor="buildingSafetyCert">Building Safety</label>
              </div>
              <div className="checkbox-group">
                <input
                  type="checkbox"
                  id="hasLibrary"
                  name="hasLibrary"
                  checked={formData.hasLibrary}
                  onChange={handleInputChange}
                />
                <label htmlFor="hasLibrary">Library</label>
              </div>
              <div className="checkbox-group">
                <input
                  type="checkbox"
                  id="hasScienceLab"
                  name="hasScienceLab"
                  checked={formData.hasScienceLab}
                  onChange={handleInputChange}
                />
                <label htmlFor="hasScienceLab">Science Lab</label>
              </div>
              <div className="checkbox-group">
                <input
                  type="checkbox"
                  id="hasMathLab"
                  name="hasMathLab"
                  checked={formData.hasMathLab}
                  onChange={handleInputChange}
                />
                <label htmlFor="hasMathLab">Math Lab</label>
              </div>
              <div className="checkbox-group">
                <input
                  type="checkbox"
                  id="hasSeperateWashroom"
                  name="hasSeperateWashroom"
                  checked={formData.hasSeperateWashroom}
                  onChange={handleInputChange}
                />
                <label htmlFor="hasSeperateWashroom">Separate Washrooms</label>
              </div>
            </div>
          </div>

          <button type="submit" disabled={isLoading}>
            {!isLoading ? <span>Check Affiliation Status</span> : <div className="loader" style={{ display: 'block' }}></div>}
          </button>
        </form>
      </div>

      {(result || error) && (
        <div className="card" id="resultCard" style={{ display: 'block' }}>
          <div className="result-header">
            <h2 className="school-title">
              {error ? 'Connection Failed' : result?.schoolName}
            </h2>
            <div className={`status-badge ${error || !result?.success ? 'status-error' : result?.status === 'READY' ? 'status-ready' : 'status-not-ready'}`}>
              {error ? 'Network Error' : (!result?.success ? 'API Error' : (result?.status === 'READY' ? 'READY FOR AFFILIATION' : 'NOT READY'))}
            </div>
          </div>

          <div id="resultContent">
            {error && (
              <div className="list-box mandatory">
                <p style={{ color: '#991b1b', margin: 0 }}>Could not connect to the server. Make sure the FastAPI backend is running.</p>
                <p style={{ color: '#64748b', fontSize: '0.875rem', marginTop: '0.5rem' }}>{error}</p>
              </div>
            )}

            {!error && result && !result.success && (
              <div className="list-box mandatory">
                <p style={{ color: '#991b1b', margin: 0 }}>{result.message || 'An unknown error occurred during validation.'}</p>
              </div>
            )}

            {!error && result && result.success && (
              <>
                <div style={{ overflowX: 'auto', marginTop: '1rem', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ backgroundColor: '#f1f5f9', borderBottom: '2px solid var(--border-color)' }}>
                        <th style={{ padding: '1rem', color: 'var(--text-main)', fontWeight: 600 }}>Category</th>
                        <th style={{ padding: '1rem', color: 'var(--text-main)', fontWeight: 600 }}>Details</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '1rem', fontWeight: 500 }}>School Name</td>
                        <td style={{ padding: '1rem' }}>{result.schoolName}</td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '1rem', fontWeight: 500 }}>Status</td>
                        <td style={{ padding: '1rem' }}>
                          <span className={result.status === 'READY' ? 'status-badge status-ready' : 'status-badge status-not-ready'} style={{ display: 'inline-block', fontSize: '0.75rem' }}>
                            {result.status}
                          </span>
                        </td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '1rem', fontWeight: 500, verticalAlign: 'top' }}>Mandatory Conditions</td>
                        <td style={{ padding: '1rem' }}>
                          {result.mendatoryCondition && result.mendatoryCondition.length > 0 ? (
                            <ul style={{ margin: 0, paddingLeft: '1.25rem', color: '#ef4444' }}>
                              {result.mendatoryCondition.map((condition, index) => (
                                <li key={index} style={{ marginBottom: '0.25rem' }}>{condition}</li>
                              ))}
                            </ul>
                          ) : (
                            <span style={{ color: '#10b981' }}>&#10003; All mandatory conditions met</span>
                          )}
                        </td>
                      </tr>
                      <tr>
                        <td style={{ padding: '1rem', fontWeight: 500, verticalAlign: 'top' }}>Recommendations</td>
                        <td style={{ padding: '1rem' }}>
                          {result.recomendation && result.recomendation.length > 0 ? (
                            <ul style={{ margin: 0, paddingLeft: '1.25rem', color: '#f59e0b' }}>
                              {result.recomendation.map((rec, index) => (
                                <li key={index} style={{ marginBottom: '0.25rem' }}>{rec}</li>
                              ))}
                            </ul>
                          ) : (
                            <span style={{ color: '#10b981' }}>&#10003; No additional recommendations</span>
                          )}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
                  <button
                    type="button"
                    className="raw-data-btn"
                    onClick={() => setShowRawData(!showRawData)}
                  >
                    {showRawData ? 'Hide Raw Response Data' : 'View Raw Response Data'}
                  </button>
                  {showRawData && (
                    <div className="raw-data-container show">
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: 'var(--text-muted)', fontFamily: 'monospace', overflowX: 'auto' }}>
                        {JSON.stringify(result, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CbseAffiliation;
